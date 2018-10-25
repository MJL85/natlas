#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import sys
import re
from time import strptime, strftime
from keyword import iskeyword
from pysmi.mibinfo import MibInfo
from pysmi.codegen.base import AbstractCodeGen, dorepr
from pysmi import error
from pysmi import debug


if sys.version_info[0] > 2:
    # noinspection PyShadowingBuiltins
    unicode = str
    # noinspection PyShadowingBuiltins
    long = int


class PySnmpCodeGen(AbstractCodeGen):
    """Builds PySNMP-specific Python code representing MIB module supplied
       in form of an Abstract Syntax Tree on input.

       Instance of this class is supposed to be passed to *MibCompiler*,
       the rest is internal to *MibCompiler*.
    """
    defaultMibPackages = ('pysnmp.smi.mibs', 'pysnmp_mibs')

    symsTable = {
        'MODULE-IDENTITY': ('ModuleIdentity',),
        'OBJECT-TYPE': ('MibScalar', 'MibTable', 'MibTableRow', 'MibTableColumn'),
        'NOTIFICATION-TYPE': ('NotificationType',),
        'TEXTUAL-CONVENTION': ('TextualConvention',),
        'MODULE-COMPLIANCE': ('ModuleCompliance',),
        'OBJECT-GROUP': ('ObjectGroup',),
        'NOTIFICATION-GROUP': ('NotificationGroup',),
        'AGENT-CAPABILITIES': ('AgentCapabilities',),
        'OBJECT-IDENTITY': ('ObjectIdentity',),
        'TRAP-TYPE': ('NotificationType',),  # smidump always uses NotificationType
        'BITS': ('Bits',),
    }

    constImports = {
        'ASN1': ('Integer', 'OctetString', 'ObjectIdentifier'),
        'ASN1-ENUMERATION': ('NamedValues',),
        'ASN1-REFINEMENT': ('ConstraintsUnion', 'ConstraintsIntersection', 'SingleValueConstraint',
                            'ValueRangeConstraint', 'ValueSizeConstraint'),
        'SNMPv2-SMI': ('iso',
                       'Bits',  # XXX
                       'Integer32',  # XXX
                       'TimeTicks',  # bug in some IETF MIBs
                       'Counter32',  # bug in some IETF MIBs (e.g. DSA-MIB)
                       'Counter64',  # bug in some MIBs (e.g.A3COM-HUAWEI-LswINF-MIB)
                       'NOTIFICATION-TYPE',  # bug in some MIBs (e.g. A3COM-HUAWEI-DHCPSNOOP-MIB)
                       'Gauge32',  # bug in some IETF MIBs (e.g. DSA-MIB)
                       'MODULE-IDENTITY', 'OBJECT-TYPE', 'OBJECT-IDENTITY', 'Unsigned32', 'IpAddress',  # XXX
                       'MibIdentifier'),  # OBJECT IDENTIFIER
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
                'ASN1-REFINEMENT')
    baseMibs = ('PYSNMP-USM-MIB',
                'SNMP-FRAMEWORK-MIB',
                'SNMP-TARGET-MIB',
                'TRANSPORT-ADDRESS-MIB',
                'INET-ADDRESS-MIB') + AbstractCodeGen.baseMibs

    baseTypes = ['Integer', 'Integer32', 'Bits', 'ObjectIdentifier', 'OctetString']

    typeClasses = {
        'COUNTER32': 'Counter32',
        'COUNTER64': 'Counter64',
        'GAUGE32': 'Gauge32',
        'INTEGER': 'Integer32',  # XXX
        'INTEGER32': 'Integer32',
        'IPADDRESS': 'IpAddress',
        'NETWORKADDRESS': 'IpAddress',
        'OBJECT IDENTIFIER': 'ObjectIdentifier',
        'OCTET STRING': 'OctetString',
        'OPAQUE': 'Opaque',
        'TIMETICKS': 'TimeTicks',
        'UNSIGNED32': 'Unsigned32',
        'Counter': 'Counter32',
        'Gauge': 'Gauge32',
        'NetworkAddress': 'IpAddress',  # RFC1065-SMI, RFC1155-SMI -> SNMPv2-SMI
        'nullSpecific': 'zeroDotZero',  # RFC1158-MIB -> SNMPv2-SMI
        'ipRoutingTable': 'ipRouteTable',  # RFC1158-MIB -> RFC1213-MIB
        'snmpEnableAuthTraps': 'snmpEnableAuthenTraps'  # RFC1158-MIB -> SNMPv2-MIB
    }

    smiv1IdxTypes = ['INTEGER', 'OCTET STRING', 'IPADDRESS', 'NETWORKADDRESS']

    ifTextStr = 'if mibBuilder.loadTexts: '
    indent = ' ' * 4
    fakeidx = 1000  # starting index for fake symbols

    def __init__(self):
        self._snmpTypes = set(self.typeClasses.values())
        self._snmpTypes.add('Bits')
        self._rows = set()
        self._cols = {}  # k, v = name, datatype
        self._exports = set()
        self._seenSyms = set()
        self._importMap = {}
        self._out = {}  # k, v = name, generated code
        self._moduleIdentityOid = None
        self._moduleRevision = None
        self.moduleName = ['DUMMY']
        self.genRules = {'text': True}
        self.symbolTable = {}

    def symTrans(self, symbol):
        if symbol in self.symsTable:
            return self.symsTable[symbol]

        return symbol,

    @staticmethod
    def transOpers(symbol):
        if iskeyword(symbol):
            symbol = 'pysmi_' + symbol

        return symbol.replace('-', '_')

    def prepData(self, pdata, classmode=False):
        data = []

        for el in pdata:
            if not isinstance(el, tuple):
                data.append(el)

            elif len(el) == 1:
                data.append(el[0])

            else:
                data.append(
                    self.handlersTable[el[0]](self, self.prepData(el[1:], classmode=classmode), classmode=classmode)
                )

        return data

    def genImports(self, imports):
        outStr = ''

        # conversion to SNMPv2
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

        for module in sorted(imports):
            symbols = ()

            for symbol in set(imports[module]):
                symbols += self.symTrans(symbol)

            if symbols:
                self._seenSyms.update([self.transOpers(s) for s in symbols])
                self._importMap.update([(self.transOpers(s), module) for s in symbols])

                outStr += ', '.join([self.transOpers(s) for s in symbols])
                if len(symbols) < 2:
                    outStr += ','
                outStr += ' = mibBuilder.importSymbols("%s")\n' % ('", "'.join((module,) + symbols))

        return outStr, tuple(sorted(imports))

    def genExports(self, ):
        exports = list(self._exports)
        if not exports:
            return ''

        numFuncCalls = len(exports) // 254 + 1

        outStr = ''

        for idx in range(numFuncCalls):
            outStr += 'mibBuilder.exportSymbols("' + self.moduleName[0] + '", '
            outStr += ', '.join(exports[254 * idx:254 * (idx + 1)]) + ')\n'

        return outStr

    # noinspection PyMethodMayBeStatic
    def genLabel(self, symbol, classmode=False):
        if '-' in symbol or iskeyword(symbol):
            return classmode and 'label = "' + symbol + '"\n' or '.setLabel("' + symbol + '")'

        return ''

    def addToExports(self, symbol, moduleIdentity=0):
        if moduleIdentity:
            self._exports.add('PYSNMP_MODULE_ID=%s' % symbol)

        self._exports.add('%s=%s' % (symbol, symbol))
        self._seenSyms.add(symbol)

    # noinspection PyUnusedLocal
    def regSym(self, symbol, outStr, oidStr=None, moduleIdentity=False):
        if symbol in self._seenSyms and symbol not in self._importMap:
            raise error.PySmiSemanticError('Duplicate symbol found: %s' % symbol)

        self.addToExports(symbol, moduleIdentity)
        self._out[symbol] = outStr

        if moduleIdentity:
            if self._moduleIdentityOid:
                raise error.PySmiSemanticError('Duplicate module identity')
            # TODO: turning literal tuple into a string - hackerish
            self._moduleIdentityOid = '.'.join(oidStr.split(', '))[1:-1]

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
    def genAgentCapabilities(self, data, classmode=False):
        name, productRelease, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outStr = name + ' = AgentCapabilities(' + oidStr + ')' + label + '\n'

        if productRelease:
            outStr += """\
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(name)s = %(name)s%(productRelease)s
""" % dict(name=name, productRelease=productRelease)

        if status:
            outStr += """\
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(name)s = %(name)s%(status)s
""" % dict(name=name, status=status)

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genModuleIdentity(self, data, classmode=False):
        name, lastUpdated, organization, contactInfo, description, revisionsAndDescrs, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outStr = name + ' = ModuleIdentity(' + oidStr + ')' + label + '\n'

        if revisionsAndDescrs:
            last_revision, revisions, descriptions = revisionsAndDescrs

            self._moduleRevision = last_revision

            if revisions:
                outStr += name + revisions + '\n'

            if self.genRules['text'] and descriptions:
                outStr += """
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(ifTextStr)s%(name)s%(descriptions)s
""" % dict(ifTextStr=self.ifTextStr, name=name, descriptions=descriptions)

        if lastUpdated:
            outStr += self.ifTextStr + name + lastUpdated + '\n'

        if organization:
            outStr += self.ifTextStr + name + organization + '\n'

        if self.genRules['text'] and contactInfo:
            outStr += self.ifTextStr + name + contactInfo + '\n'

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        self.regSym(name, outStr, oidStr, moduleIdentity=True)

        return outStr

    # noinspection PyUnusedLocal
    def genModuleCompliance(self, data, classmode=False):
        name, status, description, reference, compliances, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outStr = name + ' = ModuleCompliance(' + oidStr + ')' + label
        outStr += compliances + '\n'

        if status:
            outStr += """\
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(name)s = %(name)s%(status)s
""" % dict(name=name, status=status)

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genNotificationGroup(self, data, classmode=False):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outStr = name + ' = NotificationGroup(' + oidStr + ')' + label

        if objects:
            objects = ['("' + self._importMap.get(obj, self.moduleName[0]) + '", "' + self.transOpers(obj) + '")'
                       for obj in objects]

            numFuncCalls = len(objects) // 255 + 1

            if numFuncCalls > 1:
                objStrParts = []

                for idx in range(numFuncCalls):
                    objStrParts.append('[' + ', '.join(objects[255 * idx:255 * (idx + 1)]) + ']')

                outStr += """
for _%(name)s_obj in [%(objects)s]:
    if getattr(mibBuilder, 'version', 0) < (4, 4, 2):
        # WARNING: leading objects get lost here! Upgrade your pysnmp version!
        %(name)s = %(name)s.setObjects(*_%(name)s_obj)
    else:
        %(name)s = %(name)s.setObjects(*_%(name)s_obj, **dict(append=True))\
""" % dict(name=name, objects=', '.join(objStrParts))

            else:
                outStr += '.setObjects(' + ', '.join(objects) + ')'

        outStr += '\n'

        if status:
            outStr += """\
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(name)s = %(name)s%(status)s
""" % dict(name=name, status=status)

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genNotificationType(self, data, classmode=False):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outStr = name + ' = NotificationType(' + oidStr + ')' + label

        if objects:
            objects = ['("' + self._importMap.get(obj, self.moduleName[0]) + '", "' + self.transOpers(obj) + '")'
                       for obj in objects]

            numFuncCalls = len(objects) // 255 + 1

            if numFuncCalls > 1:
                objStrParts = []

                for idx in range(numFuncCalls):
                    objStrParts.append('[' + ', '.join(objects[255 * idx:255 * (idx + 1)]) + ']')

                outStr += """
for _%(name)s_obj in [%(objects)s]:
    if getattr(mibBuilder, 'version', 0) < (4, 4, 2):
        # WARNING: leading objects get lost here! Upgrade your pysnmp version!
        %(name)s = %(name)s.setObjects(*_%(name)s_obj)
    else:
        %(name)s = %(name)s.setObjects(*_%(name)s_obj, **dict(append=True))\
""" % dict(name=name, objects=', '.join(objStrParts))

            else:
                outStr += '.setObjects(' + ', '.join(objects) + ')'

        outStr += '\n'

        if status:
            outStr += self.ifTextStr + name + status + '\n'

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genObjectGroup(self, data, classmode=False):
        name, objects, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        outStr = name + ' = ObjectGroup(' + oidStr + ')' + label

        if objects:
            objects = ['("' + self._importMap.get(obj, self.moduleName[0]) + '", "' + self.transOpers(obj) + '")'
                       for obj in objects]

            numFuncCalls = len(objects) // 255 + 1

            if numFuncCalls > 1:
                objStrParts = []

                for idx in range(numFuncCalls):
                    objStrParts.append('[' + ', '.join(objects[255 * idx:255 * (idx + 1)]) + ']')

                outStr += """
for _%(name)s_obj in [%(objects)s]:
    if getattr(mibBuilder, 'version', 0) < (4, 4, 2):
        # WARNING: leading objects get lost here!
        %(name)s = %(name)s.setObjects(*_%(name)s_obj)
    else:
        %(name)s = %(name)s.setObjects(*_%(name)s_obj, **dict(append=True))\
""" % dict(name=name, objects=', '.join(objStrParts))

            else:
                outStr += '.setObjects(' + ', '.join(objects) + ')'

        outStr += '\n'

        if status:
            outStr += """\
if getattr(mibBuilder, 'version', (0, 0, 0)) > (4, 4, 0):
    %(name)s = %(name)s%(status)s
""" % dict(name=name, status=status)

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genObjectIdentity(self, data, classmode=False):
        name, status, description, reference, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outStr = name + ' = ObjectIdentity(' + oidStr + ')' + label + '\n'

        if status:
            outStr += self.ifTextStr + name + status + '\n'

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genObjectType(self, data, classmode=False):
        name, syntax, units, maxaccess, status, description, reference, augmention, index, defval, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid

        indexStr, fakeStrlist, fakeSyms = index or ('', '', [])
        subtype = syntax[0] == 'Bits' and 'Bits()' + syntax[1] or syntax[1]  # Bits hack #1

        classtype = self.typeClasses.get(syntax[0], syntax[0])
        classtype = self.transOpers(classtype)
        classtype = syntax[0] == 'Bits' and 'MibScalar' or classtype  # Bits hack #2
        classtype = name in self.symbolTable[self.moduleName[0]]['_symtable_cols'] and 'MibTableColumn' or classtype

        defval = self.genDefVal(defval, objname=name)

        outStr = name + ' = ' + classtype + '(' + oidStr + ', ' + subtype + (defval or '') + ')' + label
        outStr += units or ''
        outStr += maxaccess or ''
        outStr += indexStr or ''
        outStr += '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        if augmention:
            augmention = self.transOpers(augmention)
            outStr += augmention + '.registerAugmentions(("' + self._importMap.get(name, self.moduleName[0]) + '", "' + name + '"))\n'
            outStr += name + '.setIndexNames(*' + augmention + '.getIndexNames())\n'

        if status:
            outStr += self.ifTextStr + name + status + '\n'

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        self.regSym(name, outStr, parentOid)

        if fakeSyms:  # fake symbols for INDEX to support SMIv1
            for idx, fakeSym in enumerate(fakeSyms):
                fakeOutStr = fakeStrlist[idx] % oidStr
                self.regSym(fakeSym, fakeOutStr, oidStr)

        return outStr

    # noinspection PyUnusedLocal
    def genTrapType(self, data, classmode=False):
        name, enterprise, objects, description, reference, value = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        enterpriseStr, parentOid = enterprise

        outStr = name + ' = NotificationType(' + enterpriseStr + ' + (0,' + str(value) + '))' + label

        if objects:
            objects = ['("' + self._importMap.get(obj, self.moduleName[0]) + '", "' + self.transOpers(obj) + '")'
                       for obj in objects]

            numFuncCalls = len(objects) // 255 + 1

            if numFuncCalls > 1:
                objStrParts = []

                for idx in range(numFuncCalls):
                    objStrParts.append('[' + ', '.join(objects[255 * idx:255 * (idx + 1)]) + ']')

                outStr += """
for _%(name)s_obj in [%(objects)s]:
    if getattr(mibBuilder, 'version', 0) < (4, 4, 2):
        # WARNING: leading objects get lost here! Upgrade your pysnmp version!
        %(name)s = %(name)s.setObjects(*_%(name)s_obj)
    else:
        %(name)s = %(name)s.setObjects(*_%(name)s_obj, **dict(append=True))\
""" % dict(name=name, objects=', '.join(objStrParts))

            else:
                outStr += '.setObjects(' + ', '.join(objects) + ')'

        outStr += '\n'

        if self.genRules['text'] and description:
            outStr += self.ifTextStr + name + description + '\n'

        if self.genRules['text'] and reference:
            outStr += self.ifTextStr + name + reference + '\n'

        self.regSym(name, outStr, enterpriseStr)

        return outStr

    # noinspection PyUnusedLocal
    def genTypeDeclaration(self, data, classmode=False):
        outStr = ''

        name, declaration = data

        if declaration:
            parentType, attrs = declaration
            if parentType:  # skipping SEQUENCE case
                name = self.transOpers(name)
                outStr = 'class ' + name + '(' + parentType + '):\n' + attrs + '\n'
                self.regSym(name, outStr)

        return outStr

    # noinspection PyUnusedLocal
    def genValueDeclaration(self, data, classmode=False):
        name, oid = data

        label = self.genLabel(name)
        name = self.transOpers(name)

        oidStr, parentOid = oid
        outStr = name + ' = MibIdentifier(' + oidStr + ')' + label + '\n'

        self.regSym(name, outStr, oidStr)

        return outStr

    # Subparts generation functions

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def ftNames(self, data, classmode=False):
        names = data[0]
        return names

    def genBitNames(self, data, classmode=False):
        names = data[0]
        return names

    def genBits(self, data, classmode=False):
        bits = data[0]

        namedval = ['("' + bit[0] + '", ' + str(bit[1]) + ')' for bit in bits]

        numFuncCalls = len(namedval) // 255 + 1

        funcCalls = ''
        for idx in range(numFuncCalls):
            funcCalls += 'NamedValues(' + ', '.join(namedval[255 * idx:255 * (idx + 1)]) + ') + '

        funcCalls = funcCalls[:-3]

        outStr = classmode and self.indent + 'namedValues = ' + funcCalls + '\n' or '.clone(namedValues=' + funcCalls + ')'

        return 'Bits', outStr

    # noinspection PyUnusedLocal
    def genCompliances(self, data, classmode=False):
        if not data[0]:
            return ''

        objects = []

        for complianceModule in data[0]:
            name = complianceModule[0] or self.moduleName[0]
            objects += ['("' + name + '", "' + self.transOpers(compl) + '")' for compl in complianceModule[1]]

        outStr = ''

        numFuncCalls = len(objects) // 255 + 1

        if numFuncCalls > 1:
            objStrParts = []

            for idx in range(numFuncCalls):
                objStrParts.append('[' + ', '.join(objects[255 * idx:255 * (idx + 1)]) + ']')

            outStr += """
for _%(name)s_obj in [%(objects)s]:
    if getattr(mibBuilder, 'version', 0) < (4, 4, 2):
        # WARNING: leading objects get lost here! Upgrade your pysnmp version!
        %(name)s = %(name)s.setObjects(*_%(name)s_obj)
    else:
        %(name)s = %(name)s.setObjects(*_%(name)s_obj, **dict(append=True))

""" % dict(name=name, objects=', '.join(objStrParts))

        else:
            outStr += '.setObjects(' + ', '.join(objects) + ')\n'

        return outStr

    # noinspection PyUnusedLocal
    def genConceptualTable(self, data, classmode=False):
        row = data[0]
        if row[1] and row[1][-2:] == '()':
            row = row[1][:-2]
            self._rows.add(row)

        return 'MibTable', ''

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genContactInfo(self, data, classmode=False):
        text = self.textFilter('contact-info', data[0])
        return '.setContactInfo(' + dorepr(text) + ')'

    # noinspection PyUnusedLocal
    def genDisplayHint(self, data, classmode=False):
        return self.indent + 'displayHint = ' + dorepr(data[0]) + '\n'

    # noinspection PyUnusedLocal
    def genDefVal(self, data, classmode=False, objname=None):
        if not data:
            return ''

        if not objname:
            return data

        defval = data[0]
        defvalType = self.getBaseType(objname, self.moduleName[0])

        if isinstance(defval, (int, long)):  # number
            val = str(defval)

        elif self.isHex(defval):  # hex
            if defvalType[0][0] in ('Integer32', 'Integer'):  # common bug in MIBs
                val = str(int(defval[1:-2], 16))
            else:
                val = 'hexValue="' + defval[1:-2] + '"'

        elif self.isBinary(defval):  # binary
            binval = defval[1:-2]
            if defvalType[0][0] in ('Integer32', 'Integer'):  # common bug in MIBs
                val = str(int(binval or '0', 2))
            else:
                hexval = binval and hex(int(binval, 2))[2:] or ''
                val = 'hexValue="' + hexval + '"'

        elif defval[0] == defval[-1] and defval[0] == '"':  # quoted string
            if defval[1:-1] == '' and defvalType != 'OctetString':  # common bug
                # a warning should be here
                return False  # we will set no default value

            val = dorepr(defval[1:-1])

        else:  # symbol (oid as defval) or name for enumeration member
            if (defvalType[0][0] == 'ObjectIdentifier' and
                    (defval in self.symbolTable[self.moduleName[0]] or defval in self._importMap)):  # oid
                module = self._importMap.get(defval, self.moduleName[0])

                try:
                    val = str(self.genNumericOid(self.symbolTable[module][defval]['oid']))
                except:
                    # or no module if it will be borrowed later
                    raise error.PySmiSemanticError('no symbol "%s" in module "%s"' % (defval, module))

            # enumeration
            elif defvalType[0][0] in ('Integer32', 'Integer') and isinstance(defvalType[1], list):
                if isinstance(defval, list):  # buggy MIB: DEFVAL { { ... } }
                    defval = [dv for dv in defval if dv in dict(defvalType[1])]
                    val = defval and dorepr(defval[0]) or ''
                elif defval in dict(defvalType[1]):  # good MIB: DEFVAL { ... }
                    val = dorepr(defval)
                else:
                    val = ''

            elif defvalType[0][0] == 'Bits':
                defvalBits = []
                bits = dict(defvalType[1])

                for bit in defval:
                    bitValue = bits.get(bit, None)
                    if bitValue is not None:
                        defvalBits.append((bit, bitValue))
                    else:
                        raise error.PySmiSemanticError('no such bit as "%s" for symbol "%s"' % (bit, objname))

                return self.genBits([defvalBits])[1]

            else:
                raise error.PySmiSemanticError(
                    'unknown type "%s" for defval "%s" of symbol "%s"' % (defvalType, defval, objname))

        return '.clone(' + val + ')'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genDescription(self, data, classmode=False):
        text = self.textFilter('description', data[0])
        return classmode and self.indent + 'description = ' + dorepr(text) + '\n' or '.setDescription(' + dorepr(text) + ')'

    # noinspection PyMethodMayBeStatic
    def genReference(self, data, classmode=False):
        text = self.textFilter('reference', data[0])
        return classmode and self.indent + 'reference = ' + dorepr(text) + '\n' or '.setReference(' + dorepr(text) + ')'

    # noinspection PyMethodMayBeStatic
    def genStatus(self, data, classmode=False):
        text = data[0]
        return classmode and self.indent + 'status = ' + dorepr(text) + '\n' or '.setStatus(' + dorepr(text) + ')'

    # noinspection PyMethodMayBeStatic
    def genProductRelease(self, data, classmode=False):
        text = data[0]
        return classmode and self.indent + 'productRelease = ' + dorepr(text) + '\n' or '.setProductRelease(' + dorepr(text) + ')'

    def genEnumSpec(self, data, classmode=False):
        items = data[0]
        singleval = [str(item[1]) for item in items]
        outStr = classmode and self.indent + 'subtypeSpec = %s.subtypeSpec + ' or '.subtype(subtypeSpec='
        numFuncCalls = len(singleval) / 255 + 1
        singleCall = numFuncCalls == 1
        funcCalls = ''

        outStr += not singleCall and 'ConstraintsUnion(' or ''

        for idx in range(int(numFuncCalls)):
            if funcCalls:
                funcCalls += ', '
            funcCalls += 'SingleValueConstraint(' + ', '.join(singleval[255 * idx:255 * (idx + 1)]) + ')'

        outStr += funcCalls
        outStr += not singleCall and (classmode and ')\n' or '))') or (not classmode and ')' or '\n')
        outStr += self.genBits(data, classmode=classmode)[1]

        return outStr

    # noinspection PyUnusedLocal
    def genTableIndex(self, data, classmode=False):
        def genFakeSyms(fakeidx, idxType):
            fakeSymName = 'pysmiFakeCol%s' % fakeidx

            objType = self.typeClasses.get(idxType, idxType)
            objType = self.transOpers(objType)

            return (fakeSymName + ' = MibTableColumn(%s + (' + str(fakeidx) +
                    ', ), ' + objType + '())\n',  # stub for parentOid
                    fakeSymName)

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

            idxStrlist.append('(' + str(idx[0]) + ', "' +
                              self._importMap.get(idxName, self.moduleName[0]) +
                              '", "' + idxName + '")')

        return '.setIndexNames(' + ', '.join(idxStrlist) + ')', fakeStrlist, fakeSyms

    def genIntegerSubType(self, data, classmode=False):
        singleRange = len(data[0]) == 1

        outStr = classmode and self.indent + 'subtypeSpec = %s.subtypeSpec + ' or '.subtype(subtypeSpec='
        outStr += not singleRange and 'ConstraintsUnion(' or ''

        for rng in data[0]:
            vmin, vmax = len(rng) == 1 and (rng[0], rng[0]) or rng
            vmin, vmax = str(self.str2int(vmin)), str(self.str2int(vmax))
            outStr += 'ValueRangeConstraint(' + vmin + ', ' + vmax + ')' + (not singleRange and ', ' or '')

        outStr += not singleRange and (classmode and ')' or '))') or (not classmode and ')' or '\n')

        return outStr

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genMaxAccess(self, data, classmode=False):
        access = data[0].replace('-', '')
        return access != 'notaccessible' and '.setMaxAccess("' + access + '")' or ''

    def genOctetStringSubType(self, data, classmode=False):
        singleRange = len(data[0]) == 1

        outStr = classmode and self.indent + 'subtypeSpec = %s.subtypeSpec + ' or '.subtype(subtypeSpec='
        outStr += not singleRange and 'ConstraintsUnion(' or ''

        for rng in data[0]:
            vmin, vmax = len(rng) == 1 and (rng[0], rng[0]) or rng
            vmin, vmax = str(self.str2int(vmin)), str(self.str2int(vmax))
            outStr += ('ValueSizeConstraint(' + vmin + ', ' + vmax + ')' +
                       (not singleRange and ', ' or ''))

        outStr += not singleRange and (classmode and ')' or '))') or (not classmode and ')' or '\n')

        if data[0]:
            # noinspection PyUnboundLocalVariable
            outStr += (singleRange
                       and vmin == vmax
                       and (classmode and self.indent + 'fixedLength = ' + vmin + '\n' or '.setFixedLength(' + vmin + ')') or '')

        return outStr

    # noinspection PyUnusedLocal
    def genOid(self, data, classmode=False):
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

        return str(self.genNumericOid(out)), parent

    # noinspection PyUnusedLocal
    def genObjects(self, data, classmode=False):
        if data[0]:
            return [self.transOpers(obj) for obj in data[0]]  # XXX self.transOpers or not??
        return []

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genTime(self, data, classmode=False):
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
    def genLastUpdated(self, data, classmode=False):
        text = data[0]
        return '.setLastUpdated(' + dorepr(text) + ')'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genOrganization(self, data, classmode=False):
        text = self.textFilter('organization', data[0])
        return '.setOrganization(' + dorepr(text) + ')'

    # noinspection PyUnusedLocal
    def genRevisions(self, data, classmode=False):
        times = self.genTime([x[0] for x in data[0]])
        times = [dorepr(x) for x in times]

        revisions = '.setRevisions((%s,))' % ', '.join(times)

        descriptions = '.setRevisionsDescriptions((%s,))' % ', '.join(
            [dorepr(self.textFilter('description', x[1][1])) for x in data[0]]
        )

        lastRevision = data[0][0][0]

        return lastRevision, revisions, descriptions

    def genRow(self, data, classmode=False):
        row = data[0]
        row = self.transOpers(row)
        return row in self.symbolTable[self.moduleName[0]]['_symtable_rows'] and (
             'MibTableRow', '') or self.genSimpleSyntax(data, classmode=classmode)

    # noinspection PyUnusedLocal
    def genSequence(self, data, classmode=False):
        cols = data[0]
        self._cols.update(cols)
        return '', ''

    def genSimpleSyntax(self, data, classmode=False):
        objType = data[0]
        objType = self.typeClasses.get(objType, objType)
        objType = self.transOpers(objType)

        subtype = len(data) == 2 and data[1] or ''

        if classmode:
            subtype = '%s' in subtype and subtype % objType or subtype  # XXX hack?
            return objType, subtype

        outStr = objType + '()' + subtype

        return 'MibScalar', outStr

    # noinspection PyUnusedLocal
    def genTypeDeclarationRHS(self, data, classmode=False):
        if len(data) == 1:
            parentType, attrs = data[0]  # just syntax

        else:
            # Textual convention
            display, status, description, reference, syntax = data
            parentType, attrs = syntax

            if parentType in self._snmpTypes:
                parentType = 'TextualConvention, ' + parentType

            if display:
                attrs = display + attrs

            if status:
                attrs = status + attrs

            if self.genRules['text'] and description:
                attrs = description + attrs

            if reference:
                attrs = reference + attrs

        attrs = attrs or self.indent + 'pass\n'

        return parentType, attrs

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def genUnits(self, data, classmode=False):
        text = data[0]
        return '.setUnits(' + dorepr(self.textFilter('units', text)) + ')'

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
        'PRODUCT-RELEASE': genProductRelease,
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
        self._exports.clear()
        self._seenSyms.clear()
        self._importMap.clear()
        self._out.clear()
        self._moduleIdentityOid = None
        self.moduleName[0], moduleOid, imports, declarations = ast

        out, importedModules = self.genImports(imports or {})

        for declr in declarations or []:
            if declr:
                clausetype = declr[0]
                classmode = clausetype == 'typeDeclaration'
                self.handlersTable[declr[0]](self, self.prepData(declr[1:], classmode), classmode)

        for sym in self.symbolTable[self.moduleName[0]]['_symtable_order']:
            if sym not in self._out:
                raise error.PySmiCodegenError('No generated code for symbol %s' % sym)
            out += self._out[sym]

        out += self.genExports()

        if 'comments' in kwargs:
            out = ''.join(['# %s\n' % x for x in kwargs['comments']]) + '#\n' + out
            out = '#\n# PySNMP MIB module %s (http://snmplabs.com/pysmi)\n' % self.moduleName[0] + out

        debug.logger & debug.flagCodegen and debug.logger(
            'canonical MIB name %s (%s), imported MIB(s) %s, Python code size %s bytes' % (
                self.moduleName[0], moduleOid, ','.join(importedModules) or '<none>', len(out)))

        return MibInfo(oid=moduleOid,
                       identity=self._moduleIdentityOid,
                       name=self.moduleName[0],
                       revision=self._moduleRevision,
                       oids=[],
                       enterprise=None,
                       compliance=[],
                       imported=tuple([x for x in importedModules if x not in self.fakeMibs])), out

    def genIndex(self, processed, **kwargs):
        out = '\nfrom pysnmp.proto.rfc1902 import ObjectName\n\noidToMibMap = {\n'
        count = 0
        for module, status in processed.items():
            value = getattr(status, 'oid', None)
            if value:
                out += 'ObjectName("%s"): "%s",\n' % (value, module)
                count += 1
        out += '}\n'

        if 'comments' in kwargs:
            out = ''.join(['# %s\n' % x for x in kwargs['comments']]) + '#\n' + out
            out = '#\n# PySNMP MIB indices (http://snmplabs.com/pysmi)\n' + out

        debug.logger & debug.flagCodegen and debug.logger(
            'OID->MIB index built, %s entries, %s bytes' % (count, len(out)))

        return out

# backward compatibility
baseMibs = PySnmpCodeGen.baseMibs
fakeMibs = PySnmpCodeGen.fakeMibs
