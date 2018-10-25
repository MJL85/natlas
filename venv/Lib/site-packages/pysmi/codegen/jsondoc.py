#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import sys
import re
from time import strptime, strftime
try:
    import json
except ImportError:
    import simplejson as json
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from pysmi.mibinfo import MibInfo
from pysmi.codegen.base import AbstractCodeGen
from pysmi import error
from pysmi import debug

if sys.version_info[0] > 2:
    # noinspection PyShadowingBuiltins
    unicode = str
    # noinspection PyShadowingBuiltins
    long = int


class JsonCodeGen(AbstractCodeGen):
    """Builds JSON document representing MIB module supplied
       in form of an Abstract Syntax Tree on input.

       Instance of this class is supposed to be passed to *MibCompiler*,
       the rest is internal to *MibCompiler*.
    """
    constImports = {
        'SNMPv2-SMI': ('iso',
                       'NOTIFICATION-TYPE',  # bug in some MIBs (e.g. A3COM-HUAWEI-DHCPSNOOP-MIB)
                       'MODULE-IDENTITY', 'OBJECT-TYPE', 'OBJECT-IDENTITY'),
        'SNMPv2-TC': ('DisplayString', 'TEXTUAL-CONVENTION',),  # XXX
        'SNMPv2-CONF': ('MODULE-COMPLIANCE', 'NOTIFICATION-GROUP',),  # XXX
    }

    # never compile these, they either:
    # - define MACROs (implementation supplies them)
    # - or carry conflicting OIDs (so that all IMPORT's of them will be rewritten)
    # - or have manual fixes
    # - or import base ASN.1 types from implementation-specific MIBs
    fakeMibs = ('ASN1',
                'ASN1-ENUMERATION',
                'ASN1-REFINEMENT') + AbstractCodeGen.baseMibs

    baseTypes = ['Integer', 'Integer32', 'Bits', 'ObjectIdentifier', 'OctetString']

    typeClasses = {
        'NetworkAddress': 'IpAddress',  # RFC1065-SMI, RFC1155-SMI -> SNMPv2-SMI
        'nullSpecific': 'zeroDotZero',  # RFC1158-MIB -> SNMPv2-SMI
        'ipRoutingTable': 'ipRouteTable',  # RFC1158-MIB -> RFC1213-MIB
        'snmpEnableAuthTraps': 'snmpEnableAuthenTraps'  # RFC1158-MIB -> SNMPv2-MIB
    }

    smiv1IdxTypes = ['INTEGER', 'OCTET STRING', 'IPADDRESS', 'NETWORKADDRESS']

    indent = ' ' * 4
    fakeidx = 1000  # starting index for fake symbols

    def __init__(self):
        self._rows = set()
        self._cols = {}  # k, v = name, datatype
        self._seenSyms = set()
        self._importMap = {}
        self._out = {}  # k, v = name, generated code
        self._moduleIdentityOid = None
        self._moduleRevision = None
        self._enterpriseOid = None
        self._oids = set()
        self._complianceOids = []
        self.moduleName = ['DUMMY']
        self.genRules = {'text': True}
        self.symbolTable = {}

    @staticmethod
    def transOpers(symbol):
        return symbol.replace('-', '_')

    def prepData(self, pdata):
        data = []
        for el in pdata:
            if not isinstance(el, tuple):
                data.append(el)
            elif len(el) == 1:
                data.append(el[0])
            else:
                data.append(
                    self.handlersTable[el[0]](self, self.prepData(el[1:]))
                )
        return data

    def genImports(self, imports):
        # convertion to SNMPv2
        toDel = []
        for module in list(imports):

            if module in self.convertImportv2:

                for symbol in imports[module]:

                    if symbol in self.convertImportv2[module]:
                        toDel.append((module, symbol))

                        for newImport in self.convertImportv2[module][symbol]:
                            newModule, newSymbol = newImport

                            if newModule in imports:
                                imports[newModule].append(newSymbol)
                            else:
                                imports[newModule] = [newSymbol]

        # removing converted symbols
        for d in toDel:
            imports[d[0]].remove(d[1])

        # merging mib and constant imports
        for module in self.constImports:
            if module in imports:
                imports[module] += self.constImports[module]
            else:
                imports[module] = self.constImports[module]

        outDict = OrderedDict()
        outDict['class'] = 'imports'
        for module in sorted(imports):
            symbols = []
            for symbol in set(imports[module]):
                symbols.append(symbol)

            if symbols:
                self._seenSyms.update(
                    [self.transOpers(s) for s in symbols]
                )
                self._importMap.update(
                    [(self.transOpers(s), module) for s in symbols]
                )
                if module not in outDict:
                    outDict[module] = []

                outDict[module].extend(symbols)

        return OrderedDict(imports=outDict), tuple(sorted(imports))

    # noinspection PyMethodMayBeStatic
    def genLabel(self, symbol):
        return '-' in symbol and symbol or ''

    def addToExports(self, symbol, moduleIdentity=0):
        self._seenSyms.add(symbol)

    # noinspection PyUnusedLocal
    def regSym(self, symbol, outDict, parentOid=None, moduleIdentity=False, moduleCompliance=False):
        if symbol in self._seenSyms and symbol not in self._importMap:
            raise error.PySmiSemanticError('Duplicate symbol found: %s' % symbol)

        self.addToExports(symbol, moduleIdentity)
        self._out[symbol] = outDict

        if 'oid' in outDict:
            self._oids.add(outDict['oid'])

            if not self._enterpriseOid and outDict['oid'].startswith('1.3.6.1.4.1.'):
                self._enterpriseOid = '.'.join(outDict['oid'].split('.')[:7])

            if moduleIdentity:
                if self._moduleIdentityOid:
                    raise error.PySmiSemanticError('Duplicate module identity')
                self._moduleIdentityOid = outDict['oid']

            if moduleCompliance:
                self._complianceOids.append(outDict['oid'])

    def genNumericOid(self, oid):
        numericOid = ()

        for part in oid:
            if isinstance(part, tuple):
                parent, module = part
                if parent == 'iso':
                    numericOid += (1,)
                    continue

                if module not in self.symbolTable:
                    # XXX do getname for possible future borrowed mibs
                    raise error.PySmiSemanticError('no module "%s" in symbolTable' % module)

                if parent not in self.symbolTable[module]:
                    raise error.PySmiSemanticError('no symbol "%s" in module "%s"' % (parent, module))
                numericOid += self.genNumericOid(self.symbolTable[module][parent]['oid'])

            else:
                numericOid += (part,)

        return numericOid

    def getBaseType(self, symName, module):
        if module not in self.symbolTable:
            raise error.PySmiSemanticError('no module "%s" in symbolTable' % module)

        if symName not in self.symbolTable[module]:
            raise error.PySmiSemanticError('no symbol "%s" in module "%s"' % (symName, module))

        symType, symSubtype = self.symbolTable[module][symName].get('syntax', (('', ''), ''))
        if not symType[0]:
            raise error.PySmiSemanticError('unknown type for symbol "%s"' % symName)

        if symType[0] in self.baseTypes:
            return symType, symSubtype

        else:
            baseSymType, baseSymSubtype = self.getBaseType(*symType)
            if isinstance(baseSymSubtype, list):
                if isinstance(symSubtype, list):
                    symSubtype += baseSymSubtype
                else:
                    symSubtype = baseSymSubtype

            return baseSymType, symSubtype

    # Clause generation functions

    # noinspection PyUnusedLocal
    def genAgentCapabilities(self, data):
        name, productRelease, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'agentcapabilities'

        if productRelease:
            outDict['productrelease'] = productRelease

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genModuleIdentity(self, data):
        name, lastUpdated, organization, contactInfo, description, revisions, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'moduleidentity'

        if revisions:
            outDict['revisions'] = revisions

            self._moduleRevision = revisions[0]['revision']

        if self.genRules['text']:
            if lastUpdated:
                outDict['lastupdated'] = lastUpdated
            if organization:
                outDict['organization'] = organization
            if contactInfo:
                outDict['contactinfo'] = contactInfo
            if description:
                outDict['description'] = description

        self.regSym(name, outDict, parentOid, moduleIdentity=True)

        return outDict

    # noinspection PyUnusedLocal
    def genModuleCompliance(self, data):
        name, status, description, reference, compliances, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'modulecompliance'

        if compliances:
            outDict['modulecompliance'] = compliances

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid, moduleCompliance=True)

        return outDict

    # noinspection PyUnusedLocal
    def genNotificationGroup(self, data):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'notificationgroup'

        if objects:
            outDict['objects'] = [{'module': self._importMap.get(obj, self.moduleName[0]), 'object': self.transOpers(obj)} for obj in objects]

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genNotificationType(self, data):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'notificationtype'

        if objects:
            outDict['objects'] = [{'module': self._importMap.get(obj, self.moduleName[0]), 'object': self.transOpers(obj)} for obj in objects]

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genObjectGroup(self, data):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outDict = OrderedDict({'name': name,
                               'oid': oidStr,
                               'class': 'objectgroup'})

        if objects:
            outDict['objects'] = [{'module': self._importMap.get(obj, self.moduleName[0]), 'object': self.transOpers(obj)} for obj in objects]

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genObjectIdentity(self, data):
        name, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'objectidentity'

        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genObjectType(self, data):
        name, syntax, units, maxaccess, status, description, reference, augmention, index, defval, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        indexStr, fakeStrlist, fakeSyms = index or ('', '', [])

        defval = self.genDefVal(defval, objname=name)

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr

        if syntax[0]:
            nodetype = syntax[0] == 'Bits' and 'scalar' or syntax[0]  # Bits hack
            nodetype = name in self.symbolTable[self.moduleName[0]]['_symtable_cols'] and 'column' or nodetype
            outDict['nodetype'] = nodetype

        outDict['class'] = 'objecttype'

        if syntax[1]:
            outDict['syntax'] = syntax[1]
        if defval:
            outDict['default'] = defval
        if units:
            outDict['units'] = units
        if maxaccess:
            outDict['maxaccess'] = maxaccess
        if indexStr:
            outDict['indices'] = indexStr
        if self.genRules['text'] and reference:
            outDict['reference'] = reference
        if augmention:
            augmention = self.transOpers(augmention)
            outDict['augmention'] = OrderedDict()
            outDict['augmention']['name'] = name
            outDict['augmention']['module'] = self.moduleName[0]
            outDict['augmention']['object'] = augmention
        if status:
            outDict['status'] = status

        if self.genRules['text'] and description:
            outDict['description'] = description

        self.regSym(name, outDict, parentOid)
# TODO
#        if fakeSyms:  # fake symbols for INDEX to support SMIv1
#            for i in range(len(fakeSyms)):
#                fakeOutStr = fakeStrlist[i] % oidStr
#                self.regSym(fakeSyms[i], fakeOutStr, name)

        return outDict

    # noinspection PyUnusedLocal
    def genTrapType(self, data):
        name, enterprise, variables, description, reference, value = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        enterpriseStr, parentOid = enterprise

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = enterpriseStr + '0.' + str(value)
        outDict['class'] = 'notificationtype'

        if variables:
            outDict['objects'] = [{'module': self._importMap.get(obj, self.moduleName[0]), 'object': self.transOpers(obj)} for obj in variables]

        if self.genRules['text'] and description:
            outDict['description'] = description

        if self.genRules['text'] and reference:
            outDict['reference'] = reference

        self.regSym(name, outDict, parentOid)

        return outDict

    # noinspection PyUnusedLocal
    def genTypeDeclaration(self, data):
        name, declaration = data

        outDict = OrderedDict()
        outDict['name'] = name
        outDict['class'] = 'type'

        if declaration:
            parentType, attrs = declaration
            if parentType:  # skipping SEQUENCE case
                name = self.transOpers(name)
                outDict.update(attrs)
                self.regSym(name, outDict)

        return outDict

    # noinspection PyUnusedLocal
    def genValueDeclaration(self, data):
        name, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outDict = OrderedDict()
        outDict['name'] = name
        outDict['oid'] = oidStr
        outDict['class'] = 'objectidentity'

        self.regSym(name, outDict, parentOid)

        return outDict

    # Subparts generation functions

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genBitNames(self, data):
        names = data[0]
        return names

    def genBits(self, data):
        bits = data[0]

        outDict = OrderedDict()
        outDict['type'] = 'Bits'
        outDict['class'] = 'type'
        outDict['bits'] = OrderedDict()

        for name, bit in sorted(bits, key=lambda x: x[1]):
            outDict['bits'][name] = bit

        return 'scalar', outDict

    # noinspection PyUnusedLocal
    def genCompliances(self, data):
        compliances = []

        for complianceModule in data[0]:
            name = complianceModule[0] or self.moduleName[0]
            compliances += [{'object': self.transOpers(compl), 'module': name} for compl in complianceModule[1]]

        return compliances

    # noinspection PyUnusedLocal
    def genConceptualTable(self, data):
        row = data[0]

        if row[1] and row[1][-2:] == '()':
            row = row[1][:-2]
            self._rows.add(row)

        return 'table', ''

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genContactInfo(self, data):
        text = data[0]
        return self.textFilter('contact-info', text)

    # noinspection PyUnusedLocal
    def genDisplayHint(self, data):
        return data[0]

    # noinspection PyUnusedLocal
    def genDefVal(self, data, objname=None):
        if not data:
            return {}
        if not objname:
            return data

        outDict = OrderedDict()

        defval = data[0]
        defvalType = self.getBaseType(objname, self.moduleName[0])

        if isinstance(defval, (int, long)):  # number
            outDict.update(value=defval, format='decimal')

        elif self.isHex(defval):  # hex
            if defvalType[0][0] in ('Integer32', 'Integer'):  # common bug in MIBs
                outDict.update(value=str(int(len(defval) > 3 and defval[1:-2] or '0', 16)), format='hex')
            else:
                outDict.update(value=defval[1:-2], format='hex')

        elif self.isBinary(defval):  # binary
            binval = defval[1:-2]
            if defvalType[0][0] in ('Integer32', 'Integer'):  # common bug in MIBs
                outDict.update(value=str(int(binval or '0', 2)), format='bin')
            else:
                hexval = binval and hex(int(binval, 2))[2:] or ''
                outDict.update(value=hexval, format='hex')

        elif defval[0] == defval[-1] and defval[0] == '"':  # quoted string
            if defval[1:-1] == '' and defvalType != 'OctetString':  # common bug
                # a warning should be here
                return {}  # we will set no default value
            outDict.update(value=defval[1:-1], format='string')

        else:  # symbol (oid as defval) or name for enumeration member
            if (defvalType[0][0] == 'ObjectIdentifier' and
                    (defval in self.symbolTable[self.moduleName[0]] or defval in self._importMap)):  # oid

                module = self._importMap.get(defval, self.moduleName[0])

                try:
                    val = str(self.genNumericOid(self.symbolTable[module][defval]['oid']))
                    outDict.update(value=val, format='oid')
                except:
                    # or no module if it will be borrowed later
                    raise error.PySmiSemanticError('no symbol "%s" in module "%s"' % (defval, module))

            # enumeration
            elif defvalType[0][0] in ('Integer32', 'Integer') and isinstance(defvalType[1], list):
                if isinstance(defval, list):  # buggy MIB: DEFVAL { { ... } }
                    defval = [dv for dv in defval if dv in dict(defvalType[1])]
                    if defval:
                        outDict.update(value=defval[0], format='enum')
                elif defval in dict(defvalType[1]):  # good MIB: DEFVAL { ... }
                    outDict.update(value=defval, format='enum')

            elif defvalType[0][0] == 'Bits':
                defvalBits = []

                bits = dict(defvalType[1])

                for bit in defval:
                    bitValue = bits.get(bit, None)
                    if bitValue is not None:
                        defvalBits.append((bit, bitValue))
                    else:
                        raise error.PySmiSemanticError('no such bit as "%s" for symbol "%s"' % (bit, objname))

                outDict.update(value=self.genBits([defvalBits])[1], format='bits')

                return outDict

            else:
                raise error.PySmiSemanticError(
                    'unknown type "%s" for defval "%s" of symbol "%s"' % (defvalType, defval, objname))

        return {'default': outDict}

    # noinspection PyMethodMayBeStatic
    def genDescription(self, data):
        return self.textFilter('description', data[0])

    # noinspection PyMethodMayBeStatic
    def genReference(self, data):
        return self.textFilter('reference', data[0])

    # noinspection PyMethodMayBeStatic
    def genStatus(self, data):
        return data[0]

    def genProductRelease(self, data):
        return data[0]

    def genEnumSpec(self, data):
        items = data[0]
        return {'enumeration': dict(items)}

    # noinspection PyUnusedLocal
    def genTableIndex(self, data):
        def genFakeSyms(fakeidx, idxType):
            objType = self.typeClasses.get(idxType, idxType)
            objType = self.transOpers(objType)

            return {'module': self.moduleName[0],
                    object: objType}

        indexes = data[0]
        idxStrlist, fakeSyms, fakeStrlist = [], [], []

        for idx in indexes:
            idxName = idx[1]
            if idxName in self.smiv1IdxTypes:  # SMIv1 support
                idxType = idxName
                fakeSymStr, idxName = genFakeSyms(self.fakeidx, idxType)
                fakeStrlist.append(fakeSymStr)
                fakeSyms.append(idxName)
                self.fakeidx += 1

            index = OrderedDict()
            index['module'] = self._importMap.get(idxName, self.moduleName[0])
            index['object'] = idxName
            idxStrlist.append(index)

        return idxStrlist, fakeStrlist, fakeSyms

    def genIntegerSubType(self, data):
        ranges = []
        for rng in data[0]:
            vmin, vmax = len(rng) == 1 and (rng[0], rng[0]) or rng
            vmin, vmax = self.str2int(vmin), self.str2int(vmax)
            ran = OrderedDict()
            ran['min'] = vmin
            ran['max'] = vmax
            ranges.append(ran)

        return {'range': ranges}

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genMaxAccess(self, data):
        return data[0]

    def genOctetStringSubType(self, data):
        sizes = []
        for rng in data[0]:
            vmin, vmax = len(rng) == 1 and (rng[0], rng[0]) or rng
            vmin, vmax = self.str2int(vmin), self.str2int(vmax)

            size = OrderedDict()
            size['min'] = vmin
            size['max'] = vmax
            sizes.append(size)

        return {'size': sizes}

    # noinspection PyUnusedLocal
    def genOid(self, data):
        out = ()
        parent = ''
        for el in data[0]:
            if isinstance(el, (str, unicode)):
                parent = self.transOpers(el)
                out += ((parent, self._importMap.get(parent, self.moduleName[0])),)

            elif isinstance(el, (int, long)):
                out += (el,)

            elif isinstance(el, tuple):
                out += (el[1],)  # XXX Do we need to create a new object el[0]?

            else:
                raise error.PySmiSemanticError('unknown datatype for OID: %s' % el)

        return '.'.join([str(x) for x in self.genNumericOid(out)]), parent

    # noinspection PyUnusedLocal
    def genObjects(self, data):
        if data[0]:
            return [self.transOpers(obj) for obj in data[0]]  # XXX self.transOpers or not??
        return []

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genTime(self, data):
        times = []
        for timeStr in data:

            if len(timeStr) == 11:
                timeStr = '19' + timeStr

            # XXX raise in strict mode
            # elif lenTimeStr != 13:
            #  raise error.PySmiSemanticError("Invalid date %s" % t)
            try:
                times.append(strftime('%Y-%m-%d %H:%M', strptime(timeStr, '%Y%m%d%H%MZ')))

            except ValueError:
                # XXX raise in strict mode
                # raise error.PySmiSemanticError("Invalid date %s: %s" % (t, sys.exc_info()[1]))
                timeStr = '197001010000Z'  # dummy date for dates with typos
                times.append(strftime('%Y-%m-%d %H:%M', strptime(timeStr, '%Y%m%d%H%MZ')))

        return times

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genLastUpdated(self, data):
        return data[0]

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genOrganization(self, data):
        return self.textFilter('organization', data[0])

    # noinspection PyUnusedLocal
    def genRevisions(self, data):
        revisions = []
        for x in data[0]:
            revision = OrderedDict()
            revision['revision'] = self.genTime([x[0]])[0]
            revision['description'] = self.textFilter('description', x[1][1])
            revisions.append(revision)
        return revisions

    def genRow(self, data):
        row = data[0]
        row = self.transOpers(row)

        return row in self.symbolTable[self.moduleName[0]]['_symtable_rows'] and (
             'row', '') or self.genSimpleSyntax(data)

    # noinspection PyUnusedLocal
    def genSequence(self, data):
        cols = data[0]
        self._cols.update(cols)
        return '', ''

    def genSimpleSyntax(self, data):
        objType = data[0]
        objType = self.typeClasses.get(objType, objType)
        objType = self.transOpers(objType)

        subtype = len(data) == 2 and data[1] or {}

        outDict = OrderedDict()
        outDict['type'] = objType
        outDict['class'] = 'type'

        if subtype:
            outDict['constraints'] = subtype

        return 'scalar', outDict

    # noinspection PyUnusedLocal
    def genTypeDeclarationRHS(self, data):
        if len(data) == 1:
            parentType, attrs = data[0]

            outDict = OrderedDict()
            if not attrs:
                return outDict
            # just syntax
            outDict['type'] = attrs

        else:
            # Textual convention
            display, status, description, reference, syntax = data
            parentType, attrs = syntax

            outDict = OrderedDict()
            outDict['type'] = attrs
            outDict['class'] = 'textualconvention'
            if display:
                outDict['displayhint'] = display
            if status:
                outDict['status'] = status
            if self.genRules['text'] and description:
                outDict['description'] = description
            if self.genRules['text'] and reference:
                outDict['reference'] = reference

        return parentType, outDict

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genUnits(self, data):
        text = data[0]
        return self.textFilter('units', text)

    handlersTable = {
        'agentCapabilitiesClause': genAgentCapabilities,
        'moduleIdentityClause': genModuleIdentity,
        'moduleComplianceClause': genModuleCompliance,
        'notificationGroupClause': genNotificationGroup,
        'notificationTypeClause': genNotificationType,
        'objectGroupClause': genObjectGroup,
        'objectIdentityClause': genObjectIdentity,
        'objectTypeClause': genObjectType,
        'trapTypeClause': genTrapType,
        'typeDeclaration': genTypeDeclaration,
        'valueDeclaration': genValueDeclaration,
        'PRODUCT-RELEASE': genProductRelease,
        'ApplicationSyntax': genSimpleSyntax,
        'BitNames': genBitNames,
        'BITS': genBits,
        'ComplianceModules': genCompliances,
        'conceptualTable': genConceptualTable,
        'CONTACT-INFO': genContactInfo,
        'DISPLAY-HINT': genDisplayHint,
        'DEFVAL': genDefVal,
        'DESCRIPTION': genDescription,
        'REFERENCE': genReference,
        'Status': genStatus,
        'enumSpec': genEnumSpec,
        'INDEX': genTableIndex,
        'integerSubType': genIntegerSubType,
        'MaxAccessPart': genMaxAccess,
        'Notifications': genObjects,
        'octetStringSubType': genOctetStringSubType,
        'objectIdentifier': genOid,
        'Objects': genObjects,
        'LAST-UPDATED': genLastUpdated,
        'ORGANIZATION': genOrganization,
        'Revisions': genRevisions,
        'row': genRow,
        'SEQUENCE': genSequence,
        'SimpleSyntax': genSimpleSyntax,
        'typeDeclarationRHS': genTypeDeclarationRHS,
        'UNITS': genUnits,
        'VarTypes': genObjects,
        # 'a': lambda x: genXXX(x, 'CONSTRAINT')
    }

    def genCode(self, ast, symbolTable, **kwargs):
        self.genRules['text'] = kwargs.get('genTexts', False)
        self.textFilter = kwargs.get('textFilter') or (lambda symbol, text: re.sub('\s+', ' ', text))
        self.symbolTable = symbolTable
        self._rows.clear()
        self._cols.clear()
        self._seenSyms.clear()
        self._importMap.clear()
        self._out.clear()
        self._moduleIdentityOid = None
        self._enterpriseOid = None
        self._oids = set()
        self._complianceOids = []
        self.moduleName[0], moduleOid, imports, declarations = ast

        outDict, importedModules = self.genImports(imports and imports or {})

        for declr in declarations or []:
            if declr:
                self.handlersTable[declr[0]](self, self.prepData(declr[1:]))

        for sym in self.symbolTable[self.moduleName[0]]['_symtable_order']:
            if sym not in self._out:
                raise error.PySmiCodegenError('No generated code for symbol %s' % sym)

            outDict[sym] = self._out[sym]

        if 'comments' in kwargs:
            outDict['meta'] = OrderedDict()
            outDict['meta']['comments'] = kwargs['comments']
            outDict['meta']['module'] = self.moduleName[0]

        debug.logger & debug.flagCodegen and debug.logger(
            'canonical MIB name %s (%s), imported MIB(s) %s, Python code size %s bytes' % (
                self.moduleName[0], moduleOid, ','.join(importedModules) or '<none>', len(outDict)))

        return MibInfo(oid=moduleOid,
                       identity=self._moduleIdentityOid,
                       name=self.moduleName[0],
                       revision=self._moduleRevision,
                       oids=self._oids,
                       enterprise=self._enterpriseOid,
                       compliance=self._complianceOids,
                       imported=tuple([x for x in importedModules if x not in self.fakeMibs])), json.dumps(outDict, indent=2)

    def genIndex(self, processed, **kwargs):
        outDict = {
            'meta': {},
            'identity': {},
            'enterprise': {},
            'compliance': {},
            'oids': {},
        }
        if kwargs.get('old_index_data'):
            try:
                outDict.update(
                    json.loads(kwargs['old_index_data'])
                )

            except Exception:
                raise error.PySmiCodegenError('Index load error: %s' % sys.exc_info()[1])

        def order(top):
            if isinstance(top, dict):
                new_top = OrderedDict()
                try:
                    # first try to sort keys as OIDs
                    for k in sorted(top, key=lambda x: [int(y) for y in x.split('.')]):
                        new_top[k] = order(top[k])

                except ValueError:
                    for k in sorted(top):
                        new_top[k] = order(top[k])

                return new_top
            elif isinstance(top, list):
                new_top = []
                for e in sorted(set(top)):
                    new_top.append(order(e))

                return new_top

            return top

        for module, status in processed.items():
            modData = outDict['identity']
            identity_oid = getattr(status, 'identity', None)
            if identity_oid:
                if identity_oid not in modData:
                    modData[identity_oid] = []

                modData[identity_oid].append(module)

            modData = outDict['enterprise']
            enterprise_oid = getattr(status, 'enterprise', None)
            if enterprise_oid:
                if enterprise_oid not in modData:
                    modData[enterprise_oid] = []

                modData[enterprise_oid].append(module)

            modData = outDict['compliance']
            compliance_oids = getattr(status, 'compliance', ())
            for compliance_oid in compliance_oids:
                if compliance_oid not in modData:
                    modData[compliance_oid] = []
                modData[compliance_oid].append(module)

            modData = outDict['oids']
            objects_oids = getattr(status, 'oids', ())
            for object_oid in objects_oids:
                if object_oid not in modData:
                    modData[object_oid] = []

                modData[object_oid].append(module)

            if modData:
                unique_prefixes = {}
                for oid in sorted(modData, key=lambda x: x.count('.')):
                    for oid_prefix, modules in unique_prefixes.items():
                        if oid.startswith(oid_prefix) and set(modules).issuperset(modData[oid]):
                            break
                    else:
                        unique_prefixes[oid] = modData[oid]

                outDict['oids'] = unique_prefixes

        if 'comments' in kwargs:
            outDict['meta']['comments'] = kwargs['comments']

        debug.logger & debug.flagCodegen and debug.logger(
            'OID->MIB index built, %s entries' % len(processed))

        return json.dumps(order(outDict), indent=2)
