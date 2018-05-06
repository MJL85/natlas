#!/usr/bin/python

'''
        MNet Suite
        tracemac.py

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

from .snmp import *
from .config import mnet_config
from .util import *
from ._version import __version__

class mnet_tracemac:

    def __init__(self, conf):
        self.config = conf
        self.nodes  = []

    #
    # Connect to the node at the specified IP and search for the
    # specified MAC address in the table.
    #
    # Returns the IP to the next node or None
    #
    def trace(self, ip, mac_addr):
        mac_addr = re.sub('[\.:]', '', mac_addr)
        if (mac_addr == None):
            print('MAC address is invalid.')
            
        snmpobj = mnet_snmp(ip)

        # find valid credentials for this node
        if (snmpobj.get_cred(self.config.snmp_creds) == 0):
            return None

        system_name = util.shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

        print('%s (%s)' % (system_name, ip))

        # check for loops
        for n in self.nodes:
            if (n == system_name):
                print('\n**************************\n'
                                '*** ENCOUNTERED A LOOP ***\n'
                                '**************************\n\n'
                                'This means the MAC address is likely attached to\n'
                                'a transparent, unmanaged, or undiscoverable bridge\n'
                                'somewhere between the nodes that were crawled.')
                return None
        self.nodes.append(system_name)

        # cache some common MIB trees
        vlan_vbtbl = snmpobj.get_bulk(OID_VLANS)

        for vlan_row in vlan_vbtbl:
            for vlan_n, vlan_v in vlan_row:
                # get VLAN ID from OID
                vlan = mnet_snmp.get_last_oid_token(vlan_n)
                if (vlan >= 1002):
                    continue

                # change our SNMP credentials
                old_cred = snmpobj.v2_community
                snmpobj.v2_community = old_cred + '@' + str(vlan)

                # get CAM table for this VLAN
                cam_vbtbl = snmpobj.get_bulk(OID_VLAN_CAM)
                cam_match = None

                print('Try VLAN %s' % vlan)

                for cam_row in cam_vbtbl:
                    for cam_n, cam_v in cam_row:

                        cam_entry = self.mac_format_ascii(cam_v, 0)

                        print('[VLAN %s](%s) = (%s) == %s' % (vlan, mac_addr, cam_entry, (mac_addr==cam_entry)))

                        if (mac_addr == cam_entry):
                            cam_match = cam_n
                            break

                    if (cam_match != None):
                        break

                if (cam_match == None):
                    # try next VLAN
                    continue

                # find the interface index
                p               = cam_match.getOid()
                portnum_oid     = '%s.%i.%i.%i.%i.%i.%i' % (OID_BRIDGE_PORTNUMS, p[11], p[12], p[13], p[14], p[15], p[16])
                bridge_portnum  = snmpobj.get_val(portnum_oid)
                ifidx           = snmpobj.get_val(OID_IFINDEX + '.' + bridge_portnum)

                # restore SNMP credentials
                snmpobj.v2_community = old_cred

                # get the interface description from the index
                port = snmpobj.get_val(OID_IFNAME + '.' + ifidx)

                print('          VLAN: %s' % vlan)
                print('          Port: %s' % port)

                # get list of CDP neighbors
                cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
                if (cdp_vbtbl == None):
                    return None

                for cdp_row in cdp_vbtbl:
                    for cdp_n, cdp_v in cdp_row:
                        # process only if this row is a CDP_DEVID
                        if (cdp_n.prettyPrint().startswith(OID_CDP_DEVID) == 0):
                            continue

                        t = cdp_n.prettyPrint().split('.')
                        if (ifidx != t[14]):
                            continue

                        # get remote IP
                        rip = snmpobj.cache_lookup(cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + t[15])
                        rip = util.convert_ip_int_str(rip)

                        rname = util.shorten_host_name(cdp_v.prettyPrint(), self.config.host_domains)

                        print('     Next Node: %s' % rname)
                        print('  Next Node IP: %s' % rip)

                        return rip

                return None

        print('  MAC not found in CAM table.')
        return None


    #
    # Parse an ASCII MAC address string to a hex string.
    #
    def mac_ascii_to_hex(self, mac_str):
        mac_str = re.sub('[\.:]', '', mac_str)

        if (len(mac_str) != 12):
            return None

        mac_hex = ''
        for i in range(0, len(mac_str), 2):
            mac_hex += chr(int(mac_str[i:i+2], 16))

        return mac_hex

    def mac_format_ascii(self, mac_hex, inc_dots):
        '''
        Format an SNMP MAC string to ASCII

        Args:
            mac_hex:    Value from SNMP
            inc_dots:   1 to format as aabb.ccdd.eeff, 0 to format aabbccddeeff

        Returns:
            String representation of the mac_hex
        '''
        v = mac_hex.prettyPrint()[2:]
        ret = ''
        for i in range(0, len(v), 4):
            ret += v[i:i+4]
            if ((inc_dots) & ((i+4) < len(v))):
                ret += '.'

        return ret
