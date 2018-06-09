#!/usr/bin/python

'''
        natlas
        node_stack.py

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

from .snmp import *
from .util import *
import sys


class natlas_node_stack_member:

    def __init__(self):
        self.opts   = None
        self.num    = 0
        self.role   = 0
        self.pri    = 0
        self.mac    = None
        self.img    = None
        self.serial = None
        self.plat   = None

    def __str__(self):
        return ('<num=%s,role=%s,serial=%s>' % (self.num, self.role, self.serial))
    def __repr__(self):
        return self.__str__()


class natlas_node_stack:

    def __init__(self, snmpobj = None, opts = None):
        self.members = []
        self.count   = 0
        self.enabled = 0
        self.opts    = opts

        if (snmpobj != None):
            self.get_members(snmpobj)


    def __str__(self):
        return ('<enabled=%s,count=%s,members=%s>' % (self.enabled, self.count, self.members))
    def __repr__(self):
        return self.__str__()


    def get_members(self, snmpobj):
        if (self.opts == None):
            return

        vbtbl = snmpobj.get_bulk(OID_STACK)
        if (vbtbl == None):
            return None

        if (self.opts.get_stack_details == 0):
            self.count = 0
            for row in vbtbl:
                for n, v in row:
                    n = str(n)
                    if (n.startswith(OID_STACK_NUM + '.')):
                        self.count += 1

            if (self.count == 1):
                self.count = 0
            return

        if (self.opts.get_serial):   serial_vbtbl = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
        if (self.opts.get_plat):     platf_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)

        for row in vbtbl:
            for n, v in row:
                n = str(n)
                if (n.startswith(OID_STACK_NUM + '.')):
                    # Get info on this stack member and add to the list
                    m = natlas_node_stack_member()
                    t = n.split('.')
                    idx = t[14]

                    m.num       = v
                    m.role      = snmpobj.cache_lookup(vbtbl, OID_STACK_ROLE + '.' + idx)
                    m.pri       = snmpobj.cache_lookup(vbtbl, OID_STACK_PRI + '.' + idx)
                    m.mac       = snmpobj.cache_lookup(vbtbl, OID_STACK_MAC + '.' + idx)
                    m.img       = snmpobj.cache_lookup(vbtbl, OID_STACK_IMG + '.' + idx)
                    
                    if (self.opts.get_serial):   m.serial    = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + idx)
                    if (self.opts.get_plat):     m.plat      = snmpobj.cache_lookup(platf_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + idx)

                    if (m.role == '1'):
                        m.role = 'master'
                    elif (m.role == '2'):
                        m.role = 'member'
                    elif (m.role == '3'):
                        m.role = 'notMember'
                    elif (m.role == '4'):
                        m.role = 'standby'

                    mac_seg = [m.mac[x:x+4] for x in range(2, len(m.mac), 4)]
                    m.mac = '.'.join(mac_seg)
                    self.members.append(m)

        self.count = len(self.members)
        if (self.count == 1):
            self.count = 0
        if (self.count > 0):
            self.enabled = 1

