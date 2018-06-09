#!/usr/bin/python

'''
        natlas
        node_vss.py

        Michael Laforest
        mjlaforest@gmail.com

        Copyright (C) 2015-2018 Michael Laforest

        This program is free software; you can redistribute it and/or
        modify it under the terms of the GNU General Public License
        as published by the Free Software Foundation; either version 2
        of the License, or (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program; if not, write to the Free Software
        Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import sys
from .snmp import *
from .util import *


class natlas_node_vss_member:
    def __init__(self):
        self.opts   = None
        self.ios    = None
        self.serial = None
        self.plat   = None

    def __str__(self):
        return ('<serial=%s,plat=%s>' % (self.serial, self.plat))
    def __repr__(self):
        return self.__str__()


class natlas_node_vss:
    def __init__(self, snmpobj = None, opts = None):
        self.members = [ natlas_node_vss_member(), natlas_node_vss_member() ]
        self.enabled = 0
        self.domain = None
        self.opts = opts

        if (snmpobj != None):
            self.get_members(snmpobj)

    def __str__(self):
        return ('<enabled=%s,domain=%s,members=%s>' % (self.enabled, self.domain, self.members))
    def __repr__(self):
        return self.__str__()

    def get_members(self, snmpobj):
        # check if VSS is enabled
        self.enabled = 1 if (snmpobj.get_val(OID_VSS_MODE) == '2') else 0
        if (self.enabled == 0):
            return

        if (self.opts == None):
            return

        self.domain = snmpobj.get_val(OID_VSS_DOMAIN)

        if (self.opts.get_vss_details == 0):
            return

        # pull some VSS-related info
        module_vbtbl    = snmpobj.get_bulk(OID_VSS_MODULES)

        if (self.opts.get_ios):     ios_vbtbl       = snmpobj.get_bulk(OID_ENTPHYENTRY_SOFTWARE)
        if (self.opts.get_serial):  serial_vbtbl    = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
        if (self.opts.get_plat):    plat_vbtbl      = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)

        chassis = 0

        # enumerate VSS modules and find chassis info
        for row in module_vbtbl:
            for n,v in row:
                if (v == 1):
                    modidx = str(n).split('.')[14]
                    # we want only chassis - line card module have no software
                    ios = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + modidx)

                    if (ios != ''):
                        if (self.opts.get_ios):     self.members[chassis].ios    = ios
                        if (self.opts.get_plat):    self.members[chassis].plat   = snmpobj.cache_lookup(plat_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + modidx)
                        if (self.opts.get_serial):  self.members[chassis].serial = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + modidx)
                        chassis += 1

                if (chassis > 1):
                    return

