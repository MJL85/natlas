#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import os
import sys
import tempfile
from pysmi.writer.base import AbstractWriter
from pysmi.compat import encode, decode
from pysmi import debug
from pysmi import error


class FileWriter(AbstractWriter):
    """Stores transformed MIB modules in files at specified location.

       User is expected to pass *FileReader* class instance to
       *MibCompiler* on instantiation. The rest is internal to *MibCompiler*.
    """
    suffix = ''

    def __init__(self, path):
        """Creates an instance of *FileReader* class.

           Args:
               path: writable directory to store created files
        """
        self._path = decode(os.path.normpath(path))

    def __str__(self):
        return '%s{"%s"}' % (self.__class__.__name__, self._path)

    def getData(self, mibname, dryRun=False):
        filename = os.path.join(self._path, decode(mibname)) + self.suffix

        f = None

        try:
            f = open(filename)
            data = f.read()
            f.close()
            return data

        except (OSError, IOError, UnicodeEncodeError):
            if f:
                f.close()
            return ''

    def putData(self, mibname, data, comments=(), dryRun=False):
        if dryRun:
            debug.logger & debug.flagWriter and debug.logger('dry run mode')
            return

        if not os.path.exists(self._path):
            try:
                os.makedirs(self._path)

            except OSError:
                raise error.PySmiWriterError(
                    'failure creating destination directory %s: %s' % (self._path, sys.exc_info()[1]), writer=self)

        if comments:
            data = '#\n' + ''.join(['# %s\n' % x for x in comments]) + '#\n' + data

        filename = os.path.join(self._path, decode(mibname)) + self.suffix

        tfile = None

        try:
            fd, tfile = tempfile.mkstemp(dir=self._path)
            os.write(fd, encode(data))
            os.close(fd)
            os.rename(tfile, filename)

        except (OSError, IOError, UnicodeEncodeError):
            exc = sys.exc_info()
            if tfile:
                try:
                    os.unlink(tfile)

                except OSError:
                    pass

            raise error.PySmiWriterError('failure writing file %s: %s' % (filename, exc[1]), file=filename, writer=self)

        debug.logger & debug.flagWriter and debug.logger('%s stored in %s' % (mibname, filename))
