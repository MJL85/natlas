#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import time
from pysmi.reader.base import AbstractReader
from pysmi.mibinfo import MibInfo
from pysmi import error
from pysmi import debug


class CallbackReader(AbstractReader):
    """Fetch ASN.1 MIB text by name by calling user-defined callable.

    *CallbackReader* class instance tries to retrieve ASN.1 MIB files
    by name and return their contents to caller.
    """
    def __init__(self, cbFun, cbCtx=None):
        """Create an instance of *CallbackReader* bound to specific URL.

           Args:
               cbFun (callable): user callable accepting *MIB name* and *cbCtx* objects

           Keyword Args:
               cbCtx (object): user object that can be used to communicate state information
                   between user-scope code and the *cbFun* callable scope
        """
        self._cbFun = cbFun
        self._cbCtx = cbCtx

    def __str__(self):
        return '%s{"%s"}' % (self.__class__.__name__, self._cbFun)

    def getData(self, mibname):
        debug.logger & debug.flagReader and debug.logger('calling user callback %s for MIB %s' % (self._cbFun, mibname))

        res = self._cbFun(mibname, self._cbCtx)
        if res:
            return MibInfo(path='file:///dev/stdin', file='', name=mibname, mtime=time.time()), res

        raise error.PySmiReaderFileNotFoundError(mibname=mibname, reader=self)
