#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import os


class AbstractReader(object):
    maxMibSize = 10000000  # MIBs can't be that large
    fuzzyMatching = True  # try different file names while searching for MIB
    originalMatching = uppercaseMatching = lowcaseMatching = True
    exts = ['',
            os.path.extsep + 'txt',
            os.path.extsep + 'mib',
            os.path.extsep + 'my']
    exts.extend([x.upper() for x in exts if x])

    def setOptions(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
        return self

    def getMibVariants(self, mibname):
        filenames = []

        if self.originalMatching:
            filenames.append(mibname)

        if self.uppercaseMatching:
            filenames.append(mibname.upper())

        if self.lowcaseMatching:
            filenames.append(mibname.lower())

        if self.fuzzyMatching:
            part = filenames[-1].find('-mib')
            if part != -1:
                filenames.extend(
                    [x[:part] for x in filenames]
                )
            else:
                suffixed = mibname + '-mib'
                filenames.append(suffixed.upper())
                filenames.append(suffixed.lower())

        return ((x, x + y) for x in filenames for y in self.exts)

    def getData(self, filename):
        raise NotImplementedError()
