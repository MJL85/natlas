#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import os
import sys
import time
from pysmi.searcher.base import AbstractSearcher
from pysmi.compat import decode
from pysmi import debug
from pysmi import error


class AnyFileSearcher(AbstractSearcher):
    """Figures out if given file exists at given location.
    """
    exts = []

    def __init__(self, path):
        """Create an instance of *AnyFileSearcher* bound to specific directory.

           Args:
             path (str): path to local directory
        """
        self._path = os.path.normpath(decode(path))

    def __str__(self):
        return '%s{"%s"}' % (self.__class__.__name__, self._path)

    def fileExists(self, mibname, mtime, rebuild=False):
        if rebuild:
            debug.logger & debug.flagSearcher and debug.logger('pretend %s is very old' % mibname)
            return

        mibname = decode(mibname)
        basename = os.path.join(self._path, mibname)

        for sfx in self.exts:
            f = basename + sfx
            if not os.path.exists(f) or not os.path.isfile(f):
                debug.logger & debug.flagSearcher and debug.logger('%s not present or not a file' % f)
                continue

            try:
                fileTime = os.stat(f)[8]

            except OSError:
                raise error.PySmiSearcherError('failure opening compiled file %s: %s' % (f, sys.exc_info()[1]),
                                               searcher=self)

            debug.logger & debug.flagSearcher and debug.logger(
                'found %s, mtime %s' % (f, time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(fileTime))))

            if fileTime >= mtime:
                raise error.PySmiFileNotModifiedError()

        raise error.PySmiFileNotFoundError('no compiled file %s found' % mibname, searcher=self)
