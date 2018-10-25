#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
from pysmi.searcher.base import AbstractSearcher
from pysmi import debug
from pysmi import error


class StubSearcher(AbstractSearcher):
    """Figures out if given MIB module is present in a fixed list of modules.
    """

    def __init__(self, *mibnames):
        """Create an instance of *StubSearcher* initialized with a fixed list
           or MIB modules names.

           Args:
               mibnames (str): blacklisted MIB names
        """
        self._mibnames = mibnames

    def __str__(self):
        return '%s' % self.__class__.__name__

    def fileExists(self, mibname, mtime, rebuild=False):
        if mibname in self._mibnames:
            debug.logger & debug.flagSearcher and debug.logger('pretend compiled %s exists and is very new' % mibname)
            raise error.PySmiFileNotModifiedError('compiled file %s is among %s' % (mibname, ', '.join(self._mibnames)),
                                                  searcher=self)

        raise error.PySmiFileNotFoundError('no compiled file %s found among %s' % (mibname, ', '.join(self._mibnames)),
                                           searcher=self)
