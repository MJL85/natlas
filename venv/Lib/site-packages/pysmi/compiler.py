#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import sys
import os
import time

try:
    from pwd import getpwuid
except ImportError:
    # noinspection PyPep8
    getpwuid = lambda x: ['<unknown>']
from pysmi import __name__ as packageName
from pysmi import __version__ as packageVersion
from pysmi.mibinfo import MibInfo
from pysmi.codegen.symtable import SymtableCodeGen
from pysmi import error
from pysmi import debug


class MibStatus(str):
    """Indicate MIB transformation result.

    *MibStatus* is a subclass of Python string type. Some additional
    attributes may be set to indicate the details.

    The following *MibStatus* class instances are defined:

    * *compiled* - MIB is successfully transformed
    * *untouched* - fresh transformed version of this MIB already exisits
    * *failed* - MIB transformation failed. *error* attribute carries details.
    * *unprocessed* - MIB transformation required but waived for some reason
    * *missing* - ASN.1 MIB source can't be found
    * *borrowed* - MIB transformation failed but pre-transformed version was used
    """

    def setOptions(self, **kwargs):
        n = self.__class__(self)
        for k in kwargs:
            setattr(n, k, kwargs[k])
        return n


statusCompiled = MibStatus('compiled')
statusUntouched = MibStatus('untouched')
statusFailed = MibStatus('failed')
statusUnprocessed = MibStatus('unprocessed')
statusMissing = MibStatus('missing')
statusBorrowed = MibStatus('borrowed')


class MibCompiler(object):
    """Top-level, user-facing, composite MIB compiler object.

    MibCompiler implements high-level MIB transformation processing logic.
    It executes its actions by calling the following specialized objects:

      * *readers* - to acquire ASN.1 MIB data
      * *searchers* - to see if transformed MIB already exists and no processing is necessary
      * *parser* - to parse ASN.1 MIB into AST
      * *code generator* - to perform actual MIB transformation
      * *borrowers* - to fetch pre-transformed MIB if transformation is impossible
      * *writer* - to store transformed MIB data

    Required components must be passed to MibCompiler on instantiation. Those
    components are: *parser*, *codegenerator* and *writer*.

    Optional components could be set or modified at later phases of MibCompiler
    life. Unlike singular, required components, optional one can be present
    in sequences to address many possible sources of data. They are
    *readers*, *searchers* and *borrowers*.
    """
    indexFile = 'index'

    def __init__(self, parser, codegen, writer):
        """Creates an instance of *MibCompiler* class.

           Args:
               parser: ASN.1 MIB parser object
               codegen: MIB transformation object
               writer: transformed MIB storing object
        """
        self._parser = parser
        self._codegen = codegen
        self._symbolgen = SymtableCodeGen()
        self._writer = writer
        self._sources = []
        self._searchers = []
        self._borrowers = []

    def addSources(self, *sources):
        """Add more ASN.1 MIB source repositories.

        MibCompiler.compile will invoke each of configured source objects
        in order of their addition asking each to fetch MIB module specified
        by name.

        Args:
            sources: reader object(s)

        Returns:
            reference to itself (can be used for call chaining)

        """
        self._sources.extend(sources)

        debug.logger & debug.flagCompiler and debug.logger(
            'current MIB source(s): %s' % ', '.join([str(x) for x in self._sources]))

        return self

    def addSearchers(self, *searchers):
        """Add more transformed MIBs repositories.

        MibCompiler.compile will invoke each of configured searcher objects
        in order of their addition asking each if already transformed MIB
        module already exists and is more recent than specified.

        Args:
            searchers: searcher object(s)

        Returns:
            reference to itself (can be used for call chaining)

        """
        self._searchers.extend(searchers)

        debug.logger & debug.flagCompiler and debug.logger(
            'current compiled MIBs location(s): %s' % ', '.join([str(x) for x in self._searchers]))

        return self

    def addBorrowers(self, *borrowers):
        """Add more transformed MIBs repositories to borrow MIBs from.

        Whenever MibCompiler.compile encounters MIB module which neither of
        the *searchers* can find or fetched ASN.1 MIB module can not be
        parsed (due to syntax errors), these *borrowers* objects will be
        invoked in order of their addition asking each if already transformed
        MIB can be fetched (borrowed).

        Args:
            borrowers: borrower object(s)

        Returns:
            reference to itself (can be used for call chaining)

        """
        self._borrowers.extend(borrowers)

        debug.logger & debug.flagCompiler and debug.logger(
            'current MIB borrower(s): %s' % ', '.join([str(x) for x in self._borrowers]))

        return self

    def _get_system_info(self):

        try:
            platform_info = os.uname()

        except AttributeError:
            platform_info = ('?',) * 6

        try:
            user_info = getpwuid(os.getuid())

        except Exception:
            user_info = ('?',) * 7

        return platform_info, user_info

    def compile(self, *mibnames, **options):
        """Transform requested and possibly referred MIBs.

        The *compile* method should be invoked when *MibCompiler* object
        is operational meaning at least *sources* are specified.

        Once called with a MIB module name, *compile* will:

        * fetch ASN.1 MIB module with given name by calling *sources*
        * make sure no such transformed MIB already exists (with *searchers*)
        * parse ASN.1 MIB text with *parser*
        * perform actual MIB transformation into target format with *code generator*
        * may attempt to borrow pre-transformed MIB through *borrowers*
        * write transformed MIB through *writer*

        The above sequence will be performed for each MIB name given in
        *mibnames* and may be performed for all MIBs referred to from
        MIBs being processed.

        Args:
            mibnames: list of ASN.1 MIBs names
            options: options that affect the way PySMI components work

        Returns:
            A dictionary of MIB module names processed (keys) and *MibStatus*
            class instances (values)

        """
        processed = {}
        parsedMibs = {}
        failedMibs = {}
        borrowedMibs = {}
        builtMibs = {}
        symbolTableMap = {}
        mibsToParse = [x for x in mibnames]
        canonicalMibNames = {}

        while mibsToParse:
            mibname = mibsToParse.pop(0)

            if mibname in parsedMibs:
                debug.logger & debug.flagCompiler and debug.logger('MIB %s already parsed' % mibname)
                continue

            if mibname in failedMibs:
                debug.logger & debug.flagCompiler and debug.logger('MIB %s already failed' % mibname)
                continue

            for source in self._sources:
                debug.logger & debug.flagCompiler and debug.logger('trying source %s' % source)

                try:
                    fileInfo, fileData = source.getData(mibname)

                    for mibTree in self._parser.parse(fileData):
                        mibInfo, symbolTable = self._symbolgen.genCode(
                            mibTree, symbolTableMap
                        )

                        symbolTableMap[mibInfo.name] = symbolTable

                        parsedMibs[mibInfo.name] = fileInfo, mibInfo, mibTree

                        if mibname in failedMibs:
                            del failedMibs[mibname]

                        mibsToParse.extend(mibInfo.imported)

                        if fileInfo.name in mibnames:
                            if mibInfo.name not in canonicalMibNames:
                                canonicalMibNames[mibInfo.name] = []
                            canonicalMibNames[mibInfo.name].append(fileInfo.name)

                        debug.logger & debug.flagCompiler and debug.logger(
                            '%s (%s) read from %s, immediate dependencies: %s' % (
                                mibInfo.name, mibname, fileInfo.path, ', '.join(mibInfo.imported) or '<none>'))

                    break

                except error.PySmiReaderFileNotFoundError:
                    debug.logger & debug.flagCompiler and debug.logger('no %s found at %s' % (mibname, source))
                    continue

                except error.PySmiError:
                    exc_class, exc, tb = sys.exc_info()
                    exc.source = source
                    exc.mibname = mibname
                    exc.msg += ' at MIB %s' % mibname

                    debug.logger & debug.flagCompiler and debug.logger('%serror %s from %s' % (
                        options.get('ignoreErrors') and 'ignoring ' or 'failing on ', exc, source))

                    failedMibs[mibname] = exc

                    processed[mibname] = statusFailed.setOptions(error=exc)

            else:
                exc = error.PySmiError('MIB source %s not found' % mibname)
                exc.mibname = mibname
                debug.logger & debug.flagCompiler and debug.logger('no %s found everywhere' % mibname)

                if mibname not in failedMibs:
                    failedMibs[mibname] = exc

                if mibname not in processed:
                    processed[mibname] = statusMissing

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs analyzed %s, MIBs failed %s' % (len(parsedMibs), len(failedMibs)))

        #
        # See what MIBs need generating
        #

        for mibname in tuple(parsedMibs):
            fileInfo, mibInfo, mibTree = parsedMibs[mibname]

            debug.logger & debug.flagCompiler and debug.logger('checking if %s requires updating' % mibname)

            for searcher in self._searchers:
                try:
                    searcher.fileExists(mibname, fileInfo.mtime, rebuild=options.get('rebuild'))

                except error.PySmiFileNotFoundError:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'no compiled MIB %s available through %s' % (mibname, searcher))
                    continue

                except error.PySmiFileNotModifiedError:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'will be using existing compiled MIB %s found by %s' % (mibname, searcher))
                    del parsedMibs[mibname]
                    processed[mibname] = statusUntouched
                    break

                except error.PySmiError:
                    exc_class, exc, tb = sys.exc_info()
                    exc.searcher = searcher
                    exc.mibname = mibname
                    exc.msg += ' at MIB %s' % mibname
                    debug.logger & debug.flagCompiler and debug.logger('error from %s: %s' % (searcher, exc))
                    continue

            else:
                debug.logger & debug.flagCompiler and debug.logger(
                    'no suitable compiled MIB %s found anywhere' % mibname)

                if options.get('noDeps') and mibname not in canonicalMibNames:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'excluding imported MIB %s from code generation' % mibname)
                    del parsedMibs[mibname]
                    processed[mibname] = statusUntouched
                    continue

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs parsed %s, MIBs failed %s' % (len(parsedMibs), len(failedMibs)))

        #
        # Generate code for parsed MIBs
        #

        for mibname in parsedMibs.copy():
            fileInfo, mibInfo, mibTree = parsedMibs[mibname]

            debug.logger & debug.flagCompiler and debug.logger('compiling %s read from %s' % (mibname, fileInfo.path))

            platform_info, user_info = self._get_system_info()

            comments = [
                'ASN.1 source %s' % fileInfo.path,
                'Produced by %s-%s at %s' % (packageName, packageVersion, time.asctime()),
                'On host %s platform %s version %s by user %s' % (platform_info[1], platform_info[0],
                                                                  platform_info[2], user_info[0]),
                'Using Python version %s' % sys.version.split('\n')[0]
            ]

            try:
                mibInfo, mibData = self._codegen.genCode(
                    mibTree,
                    symbolTableMap,
                    comments=comments,
                    genTexts=options.get('genTexts'),
                    textFilter=options.get('textFilter')
                )

                builtMibs[mibname] = fileInfo, mibInfo, mibData
                del parsedMibs[mibname]

                debug.logger & debug.flagCompiler and debug.logger(
                    '%s read from %s and compiled by %s' % (mibname, fileInfo.path, self._writer))

            except error.PySmiError:
                exc_class, exc, tb = sys.exc_info()
                exc.handler = self._codegen
                exc.mibname = mibname
                exc.msg += ' at MIB %s' % mibname

                debug.logger & debug.flagCompiler and debug.logger('error from %s: %s' % (self._codegen, exc))

                processed[mibname] = statusFailed.setOptions(error=exc)

                failedMibs[mibname] = exc
                del parsedMibs[mibname]

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs built %s, MIBs failed %s' % (len(parsedMibs), len(failedMibs)))

        #
        # Try to borrow pre-compiled MIBs for failed ones
        #

        for mibname in failedMibs.copy():
            if options.get('noDeps') and mibname not in canonicalMibNames:
                debug.logger & debug.flagCompiler and debug.logger('excluding imported MIB %s from borrowing' % mibname)
                continue

            for borrower in self._borrowers:
                debug.logger & debug.flagCompiler and debug.logger('trying to borrow %s from %s' % (mibname, borrower))
                try:
                    fileInfo, fileData = borrower.getData(
                        mibname,
                        genTexts=options.get('genTexts')
                    )

                    borrowedMibs[mibname] = fileInfo, MibInfo(name=mibname, imported=[]), fileData

                    del failedMibs[mibname]

                    debug.logger & debug.flagCompiler and debug.logger('%s borrowed with %s' % (mibname, borrower))
                    break

                except error.PySmiError:
                    debug.logger & debug.flagCompiler and debug.logger('error from %s: %s' % (borrower, sys.exc_info()[1]))

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs available for borrowing %s, MIBs failed %s' % (len(borrowedMibs), len(failedMibs)))

        #
        # See what MIBs need borrowing
        #

        for mibname in borrowedMibs.copy():
            debug.logger & debug.flagCompiler and debug.logger('checking if failed MIB %s requires borrowing' % mibname)

            fileInfo, mibInfo, mibData = borrowedMibs[mibname]

            for searcher in self._searchers:
                try:
                    searcher.fileExists(mibname, fileInfo.mtime, rebuild=options.get('rebuild'))

                except error.PySmiFileNotFoundError:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'no compiled MIB %s available through %s' % (mibname, searcher))
                    continue

                except error.PySmiFileNotModifiedError:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'will be using existing compiled MIB %s found by %s' % (mibname, searcher))
                    del borrowedMibs[mibname]
                    processed[mibname] = statusUntouched
                    break

                except error.PySmiError:
                    exc_class, exc, tb = sys.exc_info()
                    exc.searcher = searcher
                    exc.mibname = mibname
                    exc.msg += ' at MIB %s' % mibname

                    debug.logger & debug.flagCompiler and debug.logger('error from %s: %s' % (searcher, exc))

                    continue
            else:
                debug.logger & debug.flagCompiler and debug.logger(
                    'no suitable compiled MIB %s found anywhere' % mibname)

                if options.get('noDeps') and mibname not in canonicalMibNames:
                    debug.logger & debug.flagCompiler and debug.logger(
                        'excluding imported MIB %s from borrowing' % mibname)
                    processed[mibname] = statusUntouched

                else:
                    debug.logger & debug.flagCompiler and debug.logger('will borrow MIB %s' % mibname)
                    builtMibs[mibname] = borrowedMibs[mibname]

                    processed[mibname] = statusBorrowed.setOptions(
                        path=fileInfo.path, file=fileInfo.file,
                        alias=fileInfo.name
                    )

                del borrowedMibs[mibname]

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs built %s, MIBs failed %s' % (len(builtMibs), len(failedMibs)))

        #
        # We could attempt to ignore missing/failed MIBs
        #

        if failedMibs and not options.get('ignoreErrors'):
            debug.logger & debug.flagCompiler and debug.logger('failing with problem MIBs %s' % ', '.join(failedMibs))

            for mibname in builtMibs:
                processed[mibname] = statusUnprocessed

            return processed

        debug.logger & debug.flagCompiler and debug.logger(
            'proceeding with built MIBs %s, failed MIBs %s' % (', '.join(builtMibs), ', '.join(failedMibs)))

        #
        # Store compiled MIBs
        #

        for mibname in builtMibs.copy():
            fileInfo, mibInfo, mibData = builtMibs[mibname]

            try:
                if options.get('writeMibs', True):
                    self._writer.putData(
                        mibname, mibData, dryRun=options.get('dryRun')
                    )

                debug.logger & debug.flagCompiler and debug.logger('%s stored by %s' % (mibname, self._writer))

                del builtMibs[mibname]

                if mibname not in processed:
                    processed[mibname] = statusCompiled.setOptions(
                        path=fileInfo.path,
                        file=fileInfo.file,
                        alias=fileInfo.name,
                        oid=mibInfo.oid,
                        oids=mibInfo.oids,
                        identity=mibInfo.identity,
                        revision=mibInfo.revision,
                        enterprise=mibInfo.enterprise,
                        compliance=mibInfo.compliance,
                    )

            except error.PySmiError:
                exc_class, exc, tb = sys.exc_info()
                exc.handler = self._codegen
                exc.mibname = mibname
                exc.msg += ' at MIB %s' % mibname

                debug.logger & debug.flagCompiler and debug.logger('error %s from %s' % (exc, self._writer))

                processed[mibname] = statusFailed.setOptions(error=exc)
                failedMibs[mibname] = exc
                del builtMibs[mibname]

        debug.logger & debug.flagCompiler and debug.logger(
            'MIBs modified: %s' % ', '.join([x for x in processed if processed[x] in ('compiled', 'borrowed')]))

        return processed

    def buildIndex(self, processedMibs, **options):
        platform_info, user_info = self._get_system_info()

        comments = [
            'Produced by %s-%s at %s' % (packageName, packageVersion, time.asctime()),
            'On host %s platform %s version %s by user %s' % (platform_info[1], platform_info[0],
                                                              platform_info[2], user_info[0]),
            'Using Python version %s' % sys.version.split('\n')[0]
        ]

        try:
            self._writer.putData(
                self.indexFile,
                self._codegen.genIndex(
                    processedMibs,
                    comments=comments,
                    old_index_data=self._writer.getData(self.indexFile)
                ),
                dryRun=options.get('dryRun')
            )
        except error.PySmiError:
            exc_class, exc, tb = sys.exc_info()
            exc.msg += ' at MIB index %s' % self.indexFile

            debug.logger & debug.flagCompiler and debug.logger('error %s when building %s' % (exc, self.indexFile))

            if options.get('ignoreErrors'):
                return

            if hasattr(exc, 'with_traceback'):
                raise exc.with_traceback(tb)
            else:
                raise exc
