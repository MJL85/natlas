#!/usr/bin/python

'''
        natlas
        mac.py

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

import os
import re
import sys

from timeit import default_timer as timer
from .snmp import *
from .config import natlas_config
from .util import *
from ._version import __version__

class natlas_mac:

    class mac_object:
        def __init__(self, _host, _ip, _vlan, _mac, _port):
            self.node_host  = _host
            self.node_ip    = _ip
            self.vlan       = int(_vlan)
            self.mac        = _mac
            self.port       = _port

        def __str__(self):
            return ('<node_host="%s", node_ip="%s", vlan="%s", mac="%s", port="%s">'
                    % (self.node_host, self.node_ip, self.vlan, self.mac, self.port))
        def __repr__(self):
            return self.__str__()


    def __init__(self, conf):
        self.config = conf


    def __str__(self):
        return ('<macs=%i>' % len(self.macs))
    def __repr__(self):
        return self.__str__()


    def get_macs(self, ip, display_progress):
        '''
        Return array of MAC addresses from single node at IP
        '''
        if (ip == '0.0.0.0'):
            return None

        ret_macs = []
        snmpobj = natlas_snmp(ip)

        # find valid credentials for this node
        if (snmpobj.get_cred(self.config.snmp_creds) == 0):
            return None

        system_name = util.shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

        # cache some common MIB trees
        vlan_vbtbl      = snmpobj.get_bulk(OID_VLANS)
        ifname_vbtbl    = snmpobj.get_bulk(OID_IFNAME)

        for vlan_row in vlan_vbtbl:
            for vlan_n, vlan_v in vlan_row:
                # get VLAN ID from OID
                vlan = natlas_snmp.get_last_oid_token(vlan_n)
                if (vlan >= 1002):
                    continue
                vmacs = self.get_macs_for_vlan(ip, vlan, display_progress, snmpobj, system_name, ifname_vbtbl)
                if (vmacs != None):
                    ret_macs.extend(vmacs)

        if (display_progress == 1):
            print('')

        return ret_macs


    def get_macs_for_vlan(self, ip, vlan, display_progress=0, snmpobj=None, system_name=None, ifname_vbtbl=None):
        '''
        Return array of MAC addresses for a single VLAN from a single node at an IP
        '''
        ret_macs = []

        if (snmpobj == None):
            snmpobj = natlas_snmp(ip)
            if (snmpobj.get_cred(self.config.snmp_creds) == 0):
                return None
        if (ifname_vbtbl == None):
            ifname_vbtbl = snmpobj.get_bulk(OID_IFNAME)
        if (system_name == None):
            system_name = util.shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

        # change our SNMP credentials
        old_cred = snmpobj.v2_community
        snmpobj.v2_community = old_cred + '@' + str(vlan)

        if (display_progress == 1):
            sys.stdout.write(str(vlan)) # found VLAN
            sys.stdout.flush()

        # get CAM table for this VLAN
        cam_vbtbl       = snmpobj.get_bulk(OID_VLAN_CAM)
        portnum_vbtbl   = snmpobj.get_bulk(OID_BRIDGE_PORTNUMS)
        ifindex_vbtbl   = snmpobj.get_bulk(OID_IFINDEX)
        cam_match       = None

        if (cam_vbtbl == None):
            # error getting CAM for VLAN
            return None

        for cam_row in cam_vbtbl:
            for cam_n, cam_v in cam_row:
                cam_entry = natlas_mac.mac_format_ascii(cam_v, 0)

                # find the interface index
                p               = cam_n.getOid()
                portnum_oid     = '%s.%i.%i.%i.%i.%i.%i' % (OID_BRIDGE_PORTNUMS, p[11], p[12], p[13], p[14], p[15], p[16])
                bridge_portnum  = snmpobj.cache_lookup(portnum_vbtbl, portnum_oid)

                # get the interface index and description
                try:
                    ifidx       = snmpobj.cache_lookup(ifindex_vbtbl, OID_IFINDEX + '.' + bridge_portnum)
                    port        = snmpobj.cache_lookup(ifname_vbtbl, OID_IFNAME + '.' + ifidx)
                except TypeError:
                    port = 'None'

                mac_addr = natlas_mac.mac_format_ascii(cam_v, 1)
                
                if (display_progress == 1):
                    sys.stdout.write('.') # found CAM entry
                    sys.stdout.flush()

                entry = natlas_mac.mac_object(system_name, ip, vlan, mac_addr, port)
                ret_macs.append(entry)

        # restore SNMP credentials
        snmpobj.v2_community = old_cred
        return ret_macs


    #
    # Parse an ASCII MAC address string to a hex string.
    #
    def mac_ascii_to_hex(mac_str):
        mac_str = re.sub('[\.:]', '', mac_str)
        if (len(mac_str) != 12):
            return None
        mac_hex = ''
        for i in range(0, len(mac_str), 2):
            mac_hex += chr(int(mac_str[i:i+2], 16))
        return mac_hex

    def mac_format_ascii(mac_hex, inc_dots):
        v = mac_hex.prettyPrint()
        return natlas_mac.mac_hex_to_ascii(v, inc_dots)

    def mac_hex_to_ascii(mac_hex, inc_dots):
        '''
        Format a hex MAC string to ASCII

        Args:
            mac_hex:    Value from SNMP
            inc_dots:   1 to format as aabb.ccdd.eeff, 0 to format aabbccddeeff

        Returns:
            String representation of the mac_hex
        '''
        v = mac_hex[2:]
        ret = ''
        for i in range(0, len(v), 4):
            ret += v[i:i+4]
            if ((inc_dots) & ((i+4) < len(v))):
                ret += '.'

        return ret

