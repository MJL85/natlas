#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
from pysmi import error
from pysmi import debug


class AbstractBorrower(object):
    genTexts = False
    exts = ''

    def __init__(self, reader, genTexts=False):
        """Creates an instance of *Borrower* class.

           Args:
               reader: a *reader* object

           Keyword Args:
               genText: indicates whether this borrower should be looking
                        for transformed MIBs that include human-oriented texts
        """
        if genTexts is not None:
            self.genTexts = genTexts

        self._reader = reader

    def __str__(self):
        return '%s{%s, genTexts=%s, exts=%s}' % (self.__class__.__name__,
                                                 self._reader, self.genTexts,
                                                 self.exts)

    def setOptions(self, **kwargs):
        self._reader.setOptions(**kwargs)

        for k in kwargs:
            setattr(self, k, kwargs[k])

        return self

    def getData(self, mibname, **kwargs):
        if bool(kwargs.get('genTexts')) != self.genTexts:
            debug.logger & debug.flagBorrower and debug.logger(
                'skipping incompatible borrower %s for file %s' % (self, mibname))
            raise error.PySmiFileNotFoundError(mibname=mibname, reader=self._reader)

        debug.logger & debug.flagBorrower and (
            debug.logger('trying to borrow file %s from %s' % (mibname, self._reader))
        )

        return self._reader.getData(mibname)
