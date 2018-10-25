#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import os
import sys
import time
from pysmi.reader.base import AbstractReader
from pysmi.mibinfo import MibInfo
from pysmi.compat import decode
from pysmi import debug
from pysmi import error


class FileReader(AbstractReader):
    """Fetch ASN.1 MIB text by name from local file.

    *FileReader* class instance tries to locate ASN.1 MIB files
    by name, fetch and return their contents to caller.
    """
    useIndexFile = True  # optional .index file mapping MIB to file name
    indexFile = '.index'

    def __init__(self, path, recursive=True, ignoreErrors=True):
        """Create an instance of *FileReader* serving a directory.

           Args:
               path (str): directory to search MIB files

           Keyword Args:
               recursive (bool): whether to include subdirectories
               ignoreErrors (bool): ignore filesystem access errors
        """
        self._path = os.path.normpath(path)
        self._recursive = recursive
        self._ignoreErrors = ignoreErrors
        self._indexLoaded = False
        self._mibIndex = None

    def __str__(self):
        return '%s{"%s"}' % (self.__class__.__name__, self._path)

    def getSubdirs(self, path, recursive=True, ignoreErrors=True):
        if not recursive:
            return [path]

        dirs = [path]

        try:
            subdirs = os.listdir(path)

        except OSError:
            if ignoreErrors:
                return dirs

            else:
                raise error.PySmiError('directory %s access error: %s' % (path, sys.exc_info()[1]))

        for d in subdirs:
            d = os.path.join(decode(path), decode(d))
            if os.path.isdir(d):
                dirs.extend(self.getSubdirs(d, recursive))

        return dirs

    @staticmethod
    def loadIndex(indexFile):
        mibIndex = {}
        if os.path.exists(indexFile):
            try:
                f = open(indexFile)
                mibIndex = dict(
                    [x.split()[:2] for x in f.readlines()]
                )
                f.close()
                debug.logger & debug.flagReader and debug.logger(
                    'loaded MIB index map from %s file, %s entries' % (indexFile, len(mibIndex)))

            except IOError:
                pass

        return mibIndex

    def getMibVariants(self, mibname):
        if self.useIndexFile:
            if not self._indexLoaded:
                self._mibIndex = self.loadIndex(
                    os.path.join(self._path, self.indexFile)
                )
                self._indexLoaded = True

            if mibname in self._mibIndex:
                debug.logger & debug.flagReader and debug.logger(
                    'found %s in MIB index: %s' % (mibname, self._mibIndex[mibname]))
                return [(mibname, self._mibIndex[mibname])]

        return super(FileReader, self).getMibVariants(mibname)

    def getData(self, mibname):
        debug.logger & debug.flagReader and debug.logger(
            '%slooking for MIB %s' % (self._recursive and 'recursively ' or '', mibname))

        for path in self.getSubdirs(self._path, self._recursive, self._ignoreErrors):

            for mibalias, mibfile in self.getMibVariants(mibname):
                f = os.path.join(decode(path), decode(mibfile))

                debug.logger & debug.flagReader and debug.logger('trying MIB %s' % f)

                if os.path.exists(f) and os.path.isfile(f):
                    try:
                        mtime = os.stat(f)[8]

                        debug.logger & debug.flagReader and debug.logger(
                            'source MIB %s mtime is %s, fetching data...' % (
                                f, time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))))

                        fp = open(f, mode='rb')
                        mibData = fp.read(self.maxMibSize)
                        fp.close()

                        if len(mibData) == self.maxMibSize:
                            raise IOError('MIB %s too large' % f)

                        return MibInfo(path='file://%s' % f, file=mibfile, name=mibalias, mtime=mtime), decode(mibData)

                    except (OSError, IOError):
                        debug.logger & debug.flagReader and debug.logger(
                            'source file %s open failure: %s' % (f, sys.exc_info()[1]))

                        if not self._ignoreErrors:
                            raise error.PySmiError('file %s access error: %s' % (f, sys.exc_info()[1]))

                    raise error.PySmiReaderFileNotModifiedError('source MIB %s is older than needed' % f, reader=self)

        raise error.PySmiReaderFileNotFoundError('source MIB %s not found' % mibname, reader=self)
