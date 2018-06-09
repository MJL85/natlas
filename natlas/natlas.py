#!/usr/bin/python

'''
        natlas
        natlas.py

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

'''
    This file defines the natlas API.
'''

import sys
import re

from .config import natlas_config
from .network import natlas_network
from .node import natlas_node, natlas_vlan, natlas_arp
from .mac import natlas_mac
from .output import natlas_output
from .output_diagram import natlas_output_diagram
from .output_catalog import natlas_output_catalog

REQUIRES_PYTHON = (3, 6)

# module return codes
RETURN_SYNTAXERR    = -1
RETURN_ERR          = 0
RETURN_OK           = 1

class natlas:
    def __init__(self):
        if (sys.version_info < REQUIRES_PYTHON):
            raise Exception('Requires Python %i.%i' % (REQUIRES_PYTHON[0], REQUIRES_PYTHON[1]))
            return
        self.config_file    = None
        self.config         = None
        self.network        = None
        self.diagram        = None
        self.catalog        = None

    def __try_snmp(self, node):
        if (node == None):              return 0
        if (node.snmpobj == None):      return 0
        if (node.snmpobj.success == 1): return 1
        if (node.try_snmp_creds(self.config.snmp_creds) == 0):
            raise Exception('No valid SNMP credentials for %s' % node.ip)
        return 1

    def config_generate(self):
        return natlas_config().generate_new()

    def config_validate(self, conf_file):
        return natlas_config().validate_config(conf_file)

    def config_load(self, conf_file):
        self.config = None
        c = natlas_config()
        c.load(conf_file)
        self.config = c
        self.config_file = conf_file
        
        # initalize objects
        self.network  = natlas_network(self.config)

    def snmp_add_credential(self, snmp_ver, snmp_community):
        if (self.config == None):
            self.config = natlas_config()
        if (snmp_ver != 2):
            raise ValueError('snmp_ver is not valid')
            return
        cred                = {}
        cred['ver']         = snmp_ver
        cred['community']   = snmp_community
        self.config.snmp_creds.append(cred)

    def set_discover_maxdepth(self, depth):
        self.network.set_max_depth(int(depth))

    def set_verbose(self, verbose):
        self.network.set_verbose(verbose)

    def discover_network(self, root_ip, details):
        self.network.discover(root_ip)
        if (details == 1):
            self.network.discover_details()
        
        # initalize the output objects
        self.diagram = natlas_output_diagram(self.network)
        self.catalog = natlas_output_catalog(self.network)

    def new_node(self, node_ip):
        node = natlas_node(ip=node_ip)
        self.__try_snmp(node)
        return node

    def query_node(self, node, **get_values):
        # see natlas_node._node_opts in node.py for what get_values are available
        self.__try_snmp(node)
        node.opts.reset(False)
        for getv in get_values:
            setattr(node.opts, getv, get_values[getv])
        node.query_node()
        return

    def write_diagram(self, output_file, diagram_title): 
        self.diagram.generate(output_file, diagram_title)

    def write_catalog(self, output_file): 
        self.catalog.generate(output_file)

    def get_switch_vlans(self, switch_ip):
        node = natlas_node(switch_ip)
        if (node.try_snmp_creds(self.config.snmp_creds) == 0):
            return []
        return node.get_vlans()

    def get_switch_macs(self, switch_ip=None, node=None, vlan=None, mac=None, port=None, verbose=0):
        '''
        Get the CAM table from a switch.

        Args:
            switch_ip           IP address of the device
            node                natlas_node from new_node()
            vlan                Filter results by VLAN
            MAC                 Filter results by MAC address (regex)
            port                Filter results by port (regex)
            verbose             Display progress to stdout

            switch_ip or node is required

        Return:
            Array of natlas_mac objects
        '''
        if (switch_ip == None):
            if (node == None):
                raise Exception('get_switch_macs() requires switch_ip or node parameter')
                return None
            switch_ip = node.get_ipaddr()

        mac_obj = natlas_mac(self.config)

        if (vlan == None):
            # get all MACs
            macs = mac_obj.get_macs(switch_ip, verbose)
        else:
            # get MACs only for one VLAN
            macs = mac_obj.get_macs_for_vlan(switch_ip, vlan, verbose)

        if ((mac == None) & (port == None)):
            return macs if macs else []

        # filter results
        ret = []
        for m in macs:
            if (mac != None):
                if (re.match(mac, m.mac) == None):
                    continue
            if (port != None):
                if (re.match(port, m.port) == None):
                    continue
            ret.append(m)
        return ret

    def get_discovered_nodes(self):
        return self.network.nodes

    def get_node_ip(self, node):
        return node.get_ipaddr()

    def get_arp_table(self, switch_ip, ip=None, mac=None, interf=None, arp_type=None):
        '''
        Get the ARP table from a switch.

        Args:
            switch_ip           IP address of the device
            ip                  Filter results by IP (regex)
            mac                 Filter results by MAC (regex)
            interf              Filter results by INTERFACE (regex)
            arp_type            Filter results by ARP Type

        Return:
            Array of natlas_arp objects
        '''
        node = natlas_node(switch_ip)
        if (node.try_snmp_creds(self.config.snmp_creds) == 0):
            return []
        arp = node.get_arp_table()
        if (arp == None):
            return []

        if ((ip == None) & (mac == None) & (interf == None) & (arp_type == None)):
            # no filtering
            return arp

        interf = str(interf) if vlan else None

        # filter the result table
        ret = []
        for a in arp:
            if (ip != None):
                if (re.match(ip, a.ip) == None):
                    continue
            if (mac != None):
                if (re.match(mac, a.mac) == None):
                    continue
            if (interf != None):
                if (re.match(interf, str(a.interf)) == None):
                    continue
            if (arp_type != None):
                if (re.match(arp_type, a.arp_type) == None):
                    continue
            ret.append(a)
        return ret

    def get_neighbors(self, node):
        self.__try_snmp(node)
        cdp  = node.get_cdp_neighbors()
        lldp = node.get_lldp_neighbors()
        return cdp+lldp



