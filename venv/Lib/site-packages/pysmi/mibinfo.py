#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2018, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#


class MibInfo(object):
    #: actual MIB name
    name = ''

    #: possible alternative to MIB name
    alias = ''

    #: URL to MIB file
    path = ''

    #: MIB file name
    file = ''

    #: MIB file modification time
    mtime = 0

    #: module OID
    oid = ''

    #: MIB revision as `datetime`
    revision = None

    #: all OIDs defined in this module
    oids = ()

    #: MODULE-IDENTITY OID
    identity = ''

    #: Enterprise OID
    enterprise = ()

    #: MODULE-COMPLIANCE OIDs
    compliance = ()

    #: imported MIB names
    imported = ()

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
