#!/usr/bin/python

'''
        natlas
        network.py

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

from timeit import default_timer as timer
from .config import natlas_config
from .util import *
from .node import *

DCODE_ROOT              = 0x01
DCODE_ERR_SNMP          = 0x02
DCODE_DISCOVERED        = 0x04
DCODE_STEP_INTO         = 0x08
DCODE_CDP               = 0x10
DCODE_LLDP              = 0x20
DCODE_INCLUDE           = 0x40
DCODE_LEAF              = 0x80

DCODE_ROOT_STR          = '[root]'
DCODE_ERR_SNMP_STR      = '!'
DCODE_DISCOVERED_STR    = '+'
DCODE_STEP_INTO_STR     = '>'
DCODE_CDP_STR           = '[ cdp]'
DCODE_LLDP_STR          = '[lldp]'
DCODE_INCLUDE_STR       = 'i'
DCODE_LEAF_STR          = 'L'

NODE_KNOWN              = 0
NODE_NEW                = 1
NODE_NEWIP              = 2

class natlas_network:

    def __init__(self, conf):
        self.root_node  = None
        self.nodes      = []
        self.max_depth  = 0
        self.config     = conf
        self.verbose    = 1

    def __str__(self):
        return ('<root_node="%s", num_nodes=%i>' % (self.root_node.name, len(self.nodes)))
    def __repr__(self):
        return self.__str__()

    def set_max_depth(self, depth):
        self.max_depth = depth

    def reset_discovered(self):
        for n in self.nodes:
            n.discovered = 0

    def set_verbose(self, level):
        '''
        Set the verbose output level for discovery output.

        Args:
            Level       0 = no output
                        1 = normal output
        '''
        self.verbose = level    
    
    def discover(self, ip):
        '''
        Discover the network starting at the defined root node IP.
        Recursively enumerate the network tree up to self.depth.
        Populates self.nodes[] as a list of discovered nodes in the
        network with self.root_node being the root.

        This function will discover the network with minimal information.
        It is enough to define the structure of the network but will not
        include much data on each node.  Call discover_details() after this
        to update the self.nodes[] array with more info.
        '''

        if (self.verbose > 0):
            print('Discovery codes:\n'                                      \
                  '    . depth             %s connection error\n'           \
                  '    %s discovering node  %s numerating adjacencies\n'    \
                  '    %s include node      %s leaf node\n' %
                  (DCODE_ERR_SNMP_STR,
                   DCODE_DISCOVERED_STR, DCODE_STEP_INTO_STR,
                   DCODE_INCLUDE_STR, DCODE_LEAF_STR)
                )

            print('Discovering network...')

        # Start the process of querying this node and recursing adjacencies.
        node, new_node = self.__query_node(ip, 'UNKNOWN')
        self.root_node = node

        if (node != None):
            self.nodes.append(node)
            self.__print_step(node.ip[0], node.name, 0, DCODE_ROOT|DCODE_DISCOVERED)
            self.__discover_node(node, 0)
        else:
            return

        # we may have missed chassis info
        for n in self.nodes:
            if ((n.serial == None) | (n.plat == None) | (n.ios == None)):
                n.opts.get_chassis_info = True
                if (n.serial == None):
                    n.opts.get_serial   = True
                if (n.ios == None):
                    n.opts.get_ios      = True
                if (n.plat == None):
                    n.opts.get_plat     = True
                n.query_node()


    def discover_details(self):
        '''
        Enumerate the discovered nodes from discover() and update the
        nodes in the array with additional info.
        '''
        if (self.root_node == None):
            return

        if (self.verbose > 0):
            print('\nCollecting node details...')

        ni = 0
        for n in self.nodes:
            ni = ni + 1

            indicator = '+'
            if (n.snmpobj.success == 0):
                indicator = '!'

            if (self.verbose > 0):
                sys.stdout.write('[%i/%i]%s %s (%s)' % (ni, len(self.nodes), indicator, n.name, n.snmpobj._ip))
                sys.stdout.flush()

            # set what details to discover for this node
            n.opts.get_router        = True
            n.opts.get_ospf_id       = True
            n.opts.get_bgp_las       = True
            n.opts.get_hsrp_pri      = True
            n.opts.get_hsrp_vip      = True
            n.opts.get_serial        = True 
            n.opts.get_stack         = True
            n.opts.get_stack_details = self.config.diagram.get_stack_members
            n.opts.get_vss           = True
            n.opts.get_vss_details   = self.config.diagram.get_vss_members
            n.opts.get_svi           = True
            n.opts.get_lo            = True
            n.opts.get_vpc           = True
            n.opts.get_ios           = True
            n.opts.get_plat          = True

            start = timer()
            n.query_node()
            end = timer()
            if (self.verbose > 0):
                print(' %.2f sec' % (end - start))

        # There is some back fill information we can populate now that
        # we know all there is to know.
        if (self.verbose > 0):
            print('\nBack filling node details...')

        for n in self.nodes:
            # Find and link VPC nodes together for easy reference later
            if ((n.vpc_domain != None) & (n.vpc_peerlink_node == None)):
                for link in n.links:
                    if ((link.local_port == n.vpc_peerlink_if) | (link.local_lag == n.vpc_peerlink_if)):
                        n.vpc_peerlink_node         = link.node
                        link.node.vpc_peerlink_node = n
                        break


    def __print_step(self, ip, name, depth, dcodes):
        if (self.verbose == 0):
            return

        if (dcodes & DCODE_DISCOVERED):
            sys.stdout.write('%-3i' % len(self.nodes))
        else:
            sys.stdout.write('   ')

        if (dcodes & DCODE_INCLUDE):
            # flip this off cause we didn't even try
            dcodes = dcodes & ~DCODE_ERR_SNMP

        if   (dcodes & DCODE_ROOT):         sys.stdout.write( DCODE_ROOT_STR )
        elif (dcodes & DCODE_CDP):          sys.stdout.write( DCODE_CDP_STR )
        elif (dcodes & DCODE_LLDP):         sys.stdout.write( DCODE_LLDP_STR )
        else:                               sys.stdout.write('      ')

        status = ''        
        if   (dcodes & DCODE_ERR_SNMP):     status += DCODE_ERR_SNMP_STR
        if   (dcodes & DCODE_LEAF):         status += DCODE_LEAF_STR
        elif (dcodes & DCODE_INCLUDE):      status += DCODE_INCLUDE_STR
        if   (dcodes & DCODE_DISCOVERED):   status += DCODE_DISCOVERED_STR
        elif (dcodes & DCODE_STEP_INTO):    status += DCODE_STEP_INTO_STR
        sys.stdout.write('%3s' % status)

        for i in range(0, depth):
            sys.stdout.write('.')

        name = util.shorten_host_name(name, self.config.host_domains)
        if (self.verbose > 0):
            print('%s (%s)' % (name, ip))


    def __query_node(self, ip, host):
        '''
        Query this node.
        Return node details and if we already knew about it or if this is a new node.
        Don't save the node to the known list, just return info about it.

        Args:
            ip:                 IP Address of the node.
            host:               Hostname of this known (if known from CDP/LLDP)

        Returns:
            natlas_node:        Node of this object
            int:                NODE_NEW   = Newly discovered node
                                NODE_NEWIP = Already knew about this node but not by this IP
                                NODE_KNOWN = Already knew about this node
        '''
        host = util.shorten_host_name(host, self.config.host_domains)
        node, node_updated = self.__get_known_node(ip, host)

        if (node == None):
            # new node
            node        = natlas_node()
            node.name   = host
            node.ip     = [ip]
            state       = NODE_NEW
        else:
            # existing node
            if (node.snmpobj.success == 1):
                # we already queried this node successfully - return it
                return (node, NODE_KNOWN)
            # existing node but we couldn't connect before
            if (node_updated == 1):
                state = NODE_NEWIP
            else:
                state = NODE_KNOWN
            node.name = host

        if (ip == 'UNKNOWN'):
            return (node, state)

        # vmware ESX reports the IP as 0.0.0.0
        # LLDP can return an empty string for IPs.
        if ((ip == '0.0.0.0') | (ip == '')):
            return (node, state)

        # find valid credentials for this node
        if (node.try_snmp_creds(self.config.snmp_creds) == 0):
            return (node, state)

        node.name = node.get_system_name(self.config.host_domains)
        if (node.name != host):
            # the hostname changed (cdp/lldp vs snmp)!
            # double check we don't already know about this node
            if (state == NODE_NEW):
                node2, node_updated2 = self.__get_known_node(ip, host)
                if ((node2 != None) & (node_updated2 == 0)):
                    return (node, NODE_KNOWN)
                if (node_updated2 == 1):
                    state = NODE_NEWIP

        # Finally, if we still don't have a name, use the IP.
        # e.g. Maybe CDP/LLDP was empty and we dont have good credentials
        # for this device.  A blank name can break Dot.
        if ((node.name == None) | (node.name == '')):
            node.name = node.get_ipaddr()

        node.opts.get_serial = True     # CDP/LLDP does not report, need for extended ACL
        node.query_node()
        return (node, state)


    def __get_known_node(self, ip, host):
        '''
        Look for known nodes by IP and HOST.
        If found by HOST, add the IP if not already known.

        Return:
            node:       Node, if found. Otherwise None.
            updated:    1=updated, 0=not updated
        '''
        # already known by IP ?
        for ex in self.nodes:
            for exip in ex.ip:
                if (exip == '0.0.0.0'):
                    continue
                if (exip == ip):
                    return (ex, 0)

        # already known by HOST ?
        node = self.__get_known_node_by_host(host)
        if (node != None):
            # node already known
            if (ip not in node.ip):
                node.ip.append(ip)
                return (node, 1)
            return (node, 0)

        return (None, 0)


    def __discover_node(self, node, depth):
        '''
        Given a node, recursively enumerate its adjacencies
        until we reach the specified depth (>0).

        Args:
            node:   natlas_node object to enumerate.
            depth:  The depth left that we can go further away from the root.
        '''
        if (node == None):
            return

        if (depth >= self.max_depth):
            return

        if (node.discovered > 0):
            return
        node.discovered = 1

        # vmware ESX can report IP as 0.0.0.0
        # If we are allowing 0.0.0.0/32 in the config,
        # then we added it as a leaf, but don't discover it
        if (node.ip[0] == '0.0.0.0'):
            return

        # may be a leaf we couldn't connect to previously
        if (node.snmpobj.success == 0):
            return

        # print some info to stdout
        dcodes = DCODE_STEP_INTO
        if (depth == 0):
            dcodes |= DCODE_ROOT
        self.__print_step(node.ip[0], node.name, depth, dcodes)

        # get the cached snmp credentials
        snmpobj = node.snmpobj

        # list of valid neighbors to discover next
        valid_neighbors = []

        # get list of neighbors
        cdp_neighbors  = node.get_cdp_neighbors()
        lldp_neighbors = node.get_lldp_neighbors()
        neighbors      = cdp_neighbors + lldp_neighbors
        if (len(neighbors) == 0):
            return

        for n in neighbors:
            # some neighbors may not advertise IP addresses - default them to 0.0.0.0
            if (n.remote_ip == None):
                n.remote_ip = '0.0.0.0'

            # check the ACL
            acl_action = self.__match_node_acl(n.remote_ip, n.remote_name)
            if (acl_action == 'deny'):
                # deny inclusion of this node
                continue
            
            dcodes = DCODE_DISCOVERED
            child = None
            if (acl_action == 'include'):
                # include this node but do not discover it
                child    = natlas_node()
                child.ip = [n.remote_ip]
                dcodes  |= DCODE_INCLUDE
            else:
                # discover this node
                child, query_result = self.__query_node(n.remote_ip, n.remote_name)

            # if we couldn't pull info from SNMP fill in what we know
            if (child.snmpobj.success == 0):
                child.name = util.shorten_host_name(n.remote_name, self.config.host_domains)
                dcodes  |= DCODE_ERR_SNMP
            
            # need to check the ACL again for extended ops (we have more info)
            acl_action = self.__match_node_acl(n.remote_ip, n.remote_name, n.remote_plat, n.remote_ios, child.serial)
            if (acl_action == 'deny'):
                continue

            if (query_result == NODE_NEW):
                self.nodes.append(child)
                if (acl_action == 'leaf'):          dcodes |= DCODE_LEAF
                if (n.discovered_proto == 'cdp'):   dcodes |= DCODE_CDP
                if (n.discovered_proto == 'lldp'):  dcodes |= DCODE_LLDP
                self.__print_step(n.remote_ip, n.remote_name, depth+1, dcodes)

            # CDP/LLDP advertises the platform
            child.plat = n.remote_plat
            child.ios  = n.remote_ios
            
            # add the discovered node to the link object and link to the parent
            n.node = child
            self.__add_link(node, n)

            # if we need to discover this node then add it to the list
            if ((query_result == NODE_NEW) & (acl_action != 'leaf') & (acl_action != 'include')):
                valid_neighbors.append(child)

        # discover the valid neighbors
        for n in valid_neighbors:
            self.__discover_node(n, depth+1)


    def __match_node_acl(self, ip, host, platform=None, software=None, serial=None):
        for acl in self.config.discover_acl:
            if (acl.type == 'ip'):
                if (self.__match_ip(ip, acl.str)):
                    return acl.action
            elif (acl.type == 'host'):
                if (self.__match_strpattern(host, acl.str)):
                    return acl.action
            elif (acl.type == 'platform'):
                if ((platform != None) and self.__match_strpattern(platform, acl.str)):
                    return acl.action
            elif (acl.type == 'software'):
                if ((software != None) and self.__match_strpattern(software, acl.str)):
                    return acl.action
            elif (acl.type == 'serial'):
                if ((serial != None) and self.__match_strpattern(serial, acl.str)):
                    return acl.action
        return 'deny'


    def __match_ip(self, ip, cidr):
        if (cidr == 'any'):
            return 1
        
        validate = re.match('^([0-2]?[0-9]?[0-9]\.){3}[0-2]?[0-9]?[0-9]$', ip)
        if (validate == None):
            return 0

        if (USE_NETADDR):
            if (ip in IPNetwork(cidr)):
                return 1
        else:
            if (util.is_ipv4_in_cidr(ip, cidr)):
                return 1
        return 0


    def __match_strpattern(self, str, pattern):
        if (str == '*'):
            return 1
        if (re.search(pattern, str)):
            return 1
        return 0

    #
    # Add or update a link.
    # Return
    #    0 - Found an existing link and updated it
    #    1 - Added as a new link
    #
    def __add_link(self, node, link):
        if (link.node.discovered == 1):
            # both nodes have been discovered,
            # so try to update existing reverse link info
            # instead of adding a new link
            for n in self.nodes:
                # find the child, which was the original parent
                if (n.name == link.node.name):
                    # find the existing link
                    for ex_link in n.links:
                        if ((ex_link.node.name == node.name) & (ex_link.local_port == link.remote_port)):
                            if ((link.local_if_ip != 'UNKNOWN') & (ex_link.remote_if_ip == None)):
                                ex_link.remote_if_ip = link.local_if_ip

                            if ((link.local_lag != 'UNKNOWN') & (ex_link.remote_lag == None)):
                                ex_link.remote_lag = link.local_lag

                            if ((len(link.local_lag_ips) == 0) & len(ex_link.remote_lag_ips)):
                                ex_link.remote_lag_ips = link.local_lag_ips

                            if ((link.local_native_vlan != None) & (ex_link.remote_native_vlan == None)):
                                ex_link.remote_native_vlan = link.local_native_vlan

                            if ((link.local_allowed_vlans != None) & (ex_link.remote_allowed_vlans == None)):
                                ex_link.remote_allowed_vlans = link.local_allowed_vlans

                            return 0
        else:
            for ex_link in node.links:
                if ((ex_link.node.name == link.node.name) & (ex_link.local_port == link.local_port)):
                    # haven't discovered yet but somehow we have this link twice.
                    # maybe from different discovery processes?
                    return 0

        node.add_link(link)
        return 1


    def __get_known_node_by_host(self, hostname):
        '''
        Determine if the node is already known by hostname.
        If it is, return it.
        '''
        for n in self.nodes:
            if (n.name == hostname):
                return n
        return None

