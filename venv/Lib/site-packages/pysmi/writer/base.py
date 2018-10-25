#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#

class AbstractWriter(object):
    def setOptions(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
        return self

    def putData(self, mibname, data, comments=(), dryRun=False):
        raise NotImplementedError()

    def getData(self, filename):
        raise NotImplementedError()
