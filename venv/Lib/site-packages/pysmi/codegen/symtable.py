#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
# Build an internally used symbol table for each passed MIB.
#
import sys
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


class SymtableCodeGen(AbstractCodeGen):
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
        self._rows = set()
        self._cols = {}  # k, v = name, datatype
        self._exports = set()
        self._postponedSyms = {}  # k, v = symbol, (parents, properties)
        self._parentOids = set()
        self._importMap = {}  # k, v = symbol, MIB
        self._symsOrder = []
        self._out = {}  # k, v = symbol, properties
        self.moduleName = ['DUMMY']
        self._moduleRevision = None
        self.genRules = {'text': True}

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
                data.append(self.handlersTable[el[0]](self, self.prepData(el[1:], classmode=classmode), classmode=classmode))

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

        for module in sorted(imports):
            symbols = ()
            for symbol in set(imports[module]):
                symbols += self.symTrans(symbol)

            if symbols:
                self._importMap.update([(self.transOpers(s), module) for s in symbols])

        return {}, tuple(sorted(imports))

    def allParentsExists(self, parents):
        parentsExists = True
        for parent in parents:
            if not (parent in self._out or
                    parent in self._importMap or
                    parent in self.baseTypes or
                    parent in ('MibTable', 'MibTableRow', 'MibTableColumn') or
                    parent in self._rows):
                parentsExists = False
                break

        return parentsExists

    def regSym(self, symbol, symProps, parents=()):
        if symbol in self._out or symbol in self._postponedSyms:  # add to strict mode - or symbol in self._importMap:
            raise error.PySmiSemanticError('Duplicate symbol found: %s' % symbol)

        if self.allParentsExists(parents):
            self._out[symbol] = symProps
            self._symsOrder.append(symbol)
            self.regPostponedSyms()

        else:
            self._postponedSyms[symbol] = (parents, symProps)

    def regPostponedSyms(self):
        regedSyms = []
        for sym, val in self._postponedSyms.items():
            parents, symProps = val

            if self.allParentsExists(parents):
                self._out[sym] = symProps
                self._symsOrder.append(sym)
                regedSyms.append(sym)

        for sym in regedSyms:
            self._postponedSyms.pop(sym)

        # Clause handlers

    # noinspection PyUnusedLocal
    def genAgentCapabilities(self, data, classmode=False):
        origName, release, status, description, reference, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'AgentCapabilities',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genModuleIdentity(self, data, classmode=False):
        origName, lastUpdated, organization, contactInfo, description, revisions, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'ModuleIdentity',
                    'oid': oid,
                    'origName': origName}

        if revisions:
            self._moduleRevision = revisions[0]

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genModuleCompliance(self, data, classmode=False):
        origName, status, description, reference, compliances, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'ModuleCompliance',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genNotificationGroup(self, data, classmode=False):
        origName, objects, status, description, reference, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'NotificationGroup',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genNotificationType(self, data, classmode=False):
        origName, objects, status, description, reference, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'NotificationType',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genObjectGroup(self, data, classmode=False):
        origName, objects, status, description, reference, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'ObjectGroup',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genObjectIdentity(self, data, classmode=False):
        origName, status, description, reference, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'ObjectIdentity',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genObjectType(self, data, classmode=False):
        origName, syntax, units, maxaccess, status, description, reference, augmention, index, defval, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'ObjectType',
                    'oid': oid,
                    'syntax': syntax,  # (type, module), subtype
                    'origName': origName}

        parents = [syntax[0][0]]

        if augmention:
            parents.append(self.transOpers(augmention))

        if defval:  # XXX
            symProps['defval'] = defval

        if index and index[1]:
            namepart, fakeIndexes, fakeSymSyntax = index
            for fakeIdx, fakeSyntax in zip(fakeIndexes, fakeSymSyntax):
                fakeName = namepart + str(fakeIdx)

                fakeSymProps = {'type': 'fakeColumn',
                                'oid': oid + (fakeIdx,),
                                'syntax': fakeSyntax,
                                'origName': fakeName}

                self.regSym(fakeName, fakeSymProps)

        self.regSym(pysmiName, symProps, parents)

    # noinspection PyUnusedLocal
    def genTrapType(self, data, classmode=False):
        origName, enterprise, variables, description, reference, value = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'NotificationType',
                    'oid': enterprise + (0, value),
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # noinspection PyUnusedLocal
    def genTypeDeclaration(self, data, classmode=False):
        origName, declaration = data

        pysmiName = self.transOpers(origName)

        if declaration:
            parentType, attrs = declaration
            if parentType:  # skipping SEQUENCE case
                symProps = {'type': 'TypeDeclaration',
                            'syntax': declaration,  # (type, module), subtype
                            'origName': origName}

                self.regSym(pysmiName, symProps, [declaration[0][0]])

    # noinspection PyUnusedLocal
    def genValueDeclaration(self, data, classmode=False):
        origName, oid = data

        pysmiName = self.transOpers(origName)

        symProps = {'type': 'MibIdentifier',
                    'oid': oid,
                    'origName': origName}

        self.regSym(pysmiName, symProps)

    # Subparts generation functions
    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def genBitNames(self, data, classmode=False):
        names = data[0]
        return names

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def genBits(self, data, classmode=False):
        bits = data[0]
        return ('Bits', ''), bits

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genCompliances(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal
    def genConceptualTable(self, data, classmode=False):
        row = data[0]
        if row[0] and row[0][0]:
            self._rows.add(self.transOpers(row[0][0]))
        return ('MibTable', ''), ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genContactInfo(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genDisplayHint(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal
    def genDefVal(self, data, classmode=False):  # XXX should be fixed, see pysnmp.py
        defval = data[0]

        if isinstance(defval, (int, long)):  # number
            val = str(defval)

        elif self.isHex(defval):  # hex
            val = 'hexValue="' + defval[1:-2] + '"'  # not working for Integer baseTypes

        elif self.isBinary(defval):  # binary
            binval = defval[1:-2]
            hexval = binval and hex(int(binval, 2))[2:] or ''
            val = 'hexValue="' + hexval + '"'

        elif isinstance(defval, list):  # bits list
            val = defval

        elif defval[0] == defval[-1] and defval[0] == '"':  # quoted strimg
            val = dorepr(defval[1:-1])

        else:  # symbol (oid as defval) or name for enumeration member
            if defval in self._out or defval in self._importMap:
                val = defval + '.getName()'
            else:
                val = dorepr(defval)

        return val

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genDescription(self, data, classmode=False):
        return ''

    def genReference(self, data, classmode=False):
        return ''

    def genStatus(self, data, classmode=False):
        return ''

    def genProductRelease(self, data, classmode=False):
        return ''

    def genEnumSpec(self, data, classmode=False):
        return self.genBits(data, classmode=classmode)[1]

    def genIndex(self, data, classmode=False):
        indexes = data[0]

        fakeIdxName = 'pysmiFakeCol'
        fakeIndexes, fakeSymsSyntax = [], []

        for idx in indexes:
            idxName = idx[1]
            if idxName in self.smiv1IdxTypes:  # SMIv1 support
                idxType = idxName

                objType = self.typeClasses.get(idxType, idxType)
                objType = self.transOpers(objType)

                fakeIndexes.append(self.fakeidx)
                fakeSymsSyntax.append((('MibTableColumn', ''), objType))
                self.fakeidx += 1

        return fakeIdxName, fakeIndexes, fakeSymsSyntax

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genIntegerSubType(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genMaxAccess(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genOctetStringSubType(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal
    def genOid(self, data, classmode=False):
        out = ()
        for el in data[0]:
            if isinstance(el, (str, unicode)):
                parent = self.transOpers(el)
                self._parentOids.add(parent)
                out += ((parent, self._importMap.get(parent, self.moduleName[0])),)

            elif isinstance(el, (int, long)):
                out += (el,)

            elif isinstance(el, tuple):
                out += (el[1],)  # XXX Do we need to create a new object el[0]?

            else:
                raise error.PySmiSemanticError('unknown datatype for OID: %s' % el)

        return out

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genObjects(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genTime(self, data, classmode=False):
        return ''

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genLastUpdated(self, data, classmode=False):
        return data[0]

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genOrganization(self, data, classmode=False):
        return data[0]

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genRevisions(self, data, classmode=False):
        lastRevision, lastDescription = data[0][0][0], data[0][0][1][1]
        return lastRevision, lastDescription

    def genRow(self, data, classmode=False):
        row = data[0]
        row = self.transOpers(row)
        return row in self._rows and (('MibTableRow', ''), '') or self.genSimpleSyntax(data, classmode=classmode)

    # noinspection PyUnusedLocal
    def genSequence(self, data, classmode=False):
        cols = data[0]
        self._cols.update(cols)
        return '', ''

    # noinspection PyUnusedLocal
    def genSimpleSyntax(self, data, classmode=False):
        objType = data[0]

        module = ''

        objType = self.typeClasses.get(objType, objType)
        objType = self.transOpers(objType)

        if objType not in self.baseTypes:
            module = self._importMap.get(objType, self.moduleName[0])

        subtype = len(data) == 2 and data[1] or ''

        return (objType, module), subtype

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def genTypeDeclarationRHS(self, data, classmode=False):
        if len(data) == 1:
            parentType, attrs = data[0]  # just syntax

        else:
            # Textual convention
            display, status, description, reference, syntax = data
            parentType, attrs = syntax

        return parentType, attrs

    # noinspection PyUnusedLocal,PyUnusedLocal,PyMethodMayBeStatic
    def genUnits(self, data, classmode=False):
        return ''

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
        'INDEX': genIndex,
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
    }

    def genCode(self, ast, symbolTable, **kwargs):
        self.genRules['text'] = kwargs.get('genTexts', False)
        self._rows.clear()
        self._cols.clear()
        self._parentOids.clear()
        self._symsOrder = []
        self._postponedSyms.clear()
        self._importMap.clear()
        self._out = {}  # should be new object, do not use `clear` method
        self.moduleName[0], moduleOid, imports, declarations = ast

        out, importedModules = self.genImports(imports or {})

        for declr in declarations or []:
            if declr:
                clausetype = declr[0]
                classmode = clausetype == 'typeDeclaration'
                self.handlersTable[declr[0]](self, self.prepData(declr[1:], classmode), classmode)

        if self._postponedSyms:
            raise error.PySmiSemanticError('Unknown parents for symbols: %s' % ', '.join(self._postponedSyms))

        for sym in self._parentOids:
            if sym not in self._out and sym not in self._importMap:
                raise error.PySmiSemanticError('Unknown parent symbol: %s' % sym)

        self._out['_symtable_order'] = list(self._symsOrder)
        self._out['_symtable_cols'] = list(self._cols)
        self._out['_symtable_rows'] = list(self._rows)

        debug.logger & debug.flagCodegen and debug.logger(
            'canonical MIB name %s (%s), imported MIB(s) %s, Symbol table size %s symbols' % (
                self.moduleName[0], moduleOid, ','.join(importedModules) or '<none>', len(self._out)))

        return MibInfo(oid=None,
                       name=self.moduleName[0],
                       revision=self._moduleRevision,
                       imported=tuple([x for x in importedModules])), self._out
