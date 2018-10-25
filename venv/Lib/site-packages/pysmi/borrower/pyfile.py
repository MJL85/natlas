#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import imp
from pysmi.borrower.base import AbstractBorrower


class PyFileBorrower(AbstractBorrower):
    """Create PySNMP MIB file borrowing object"""
    for sfx, mode, typ in imp.get_suffixes():
        if typ == imp.PY_SOURCE:
            exts = [sfx]
            break
