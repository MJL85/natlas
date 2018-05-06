#!/usr/bin/python

'''
        MNet Suite
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
from .config import mnet_config
from .util import *
from .node import *


class mnet_network:
    # def set_max_depth(self, depth)
    # def discover(self, ip)
    # def output_stdout(self)
    # def output_dot(self, dot_file, title)
    # def output_catalog(self, filename)
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
    
    def __init__(self, conf):
        self.root_node  = None
        self.nodes      = []
        self.max_depth  = 0
        self.config     = conf

    def __str__(self):
        return ('<root_node="%s", num_nodes=%i>' % (self.root_node.name, len(self.nodes)))
    def __repr__(self):
        return self.__str__()

    
    def set_max_depth(self, depth):
        self.max_depth = depth


    def reset_discovered(self):
        for n in self.nodes:
            n.discovered = 0


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

        print('Discovery codes:\n'                                      \
              '    . depth             %s connection error\n'           \
              '    %s discovering node  %s numerating adjacencies\n'    \
              '    %s include node      %s leaf node\n' %
              (mnet_network.DCODE_ERR_SNMP_STR,
               mnet_network.DCODE_DISCOVERED_STR, mnet_network.DCODE_STEP_INTO_STR,
               mnet_network.DCODE_INCLUDE_STR, mnet_network.DCODE_LEAF_STR)
            )

        print('Discovering network...')

        # Start the process of querying this node and recursing adjacencies.
        node, new_node = self.__query_node(ip, 'UNKNOWN')
        self.root_node = node

        if (node != None):
            self.__print_step(node.ip[0], node.name, 0, mnet_network.DCODE_ROOT|mnet_network.DCODE_DISCOVERED)
            self.__discover_node(node, 0)

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

        print('\nCollecting node details...')

        ni = 0
        for n in self.nodes:
            ni = ni + 1

            indicator = '+'
            if (n.snmpobj.success == 0):
                indicator = '!'

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
            print(' %.2f sec' % (end - start))

        # There is some back fill information we can populate now that
        # we know all there is to know.
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
        if (dcodes & mnet_network.DCODE_DISCOVERED):
            sys.stdout.write('%-3i' % len(self.nodes))
        else:
            sys.stdout.write('   ')

        if (dcodes & mnet_network.DCODE_INCLUDE):
            # flip this off cause we didn't even try
            dcodes = dcodes & ~mnet_network.DCODE_ERR_SNMP

        if   (dcodes & mnet_network.DCODE_ROOT):        sys.stdout.write( mnet_network.DCODE_ROOT_STR )
        elif (dcodes & mnet_network.DCODE_CDP):         sys.stdout.write( mnet_network.DCODE_CDP_STR )
        elif (dcodes & mnet_network.DCODE_LLDP):        sys.stdout.write( mnet_network.DCODE_LLDP_STR )
        else:                                           sys.stdout.write('      ')

        status = ''        
        if   (dcodes & mnet_network.DCODE_ERR_SNMP):    status += mnet_network.DCODE_ERR_SNMP_STR
        if   (dcodes & mnet_network.DCODE_LEAF):        status += mnet_network.DCODE_LEAF_STR
        elif (dcodes & mnet_network.DCODE_INCLUDE):     status += mnet_network.DCODE_INCLUDE_STR
        if   (dcodes & mnet_network.DCODE_DISCOVERED):  status += mnet_network.DCODE_DISCOVERED_STR
        elif (dcodes & mnet_network.DCODE_STEP_INTO):   status += mnet_network.DCODE_STEP_INTO_STR
        sys.stdout.write('%3s' % status)

        for i in range(0, depth):
            sys.stdout.write('.')

        name = util.shorten_host_name(name, self.config.host_domains)
        print('%s (%s)' % (name, ip))


    def __query_node(self, ip, host):
        '''
        Query this node for info about itself.

        Args:
            ip:                 IP Address of the node.
            host:               Hostname of this known (if known from CDP/LLDP)

        Returns:
            mnet_node:          Node of this object
            int:                Newly discovered node=1, already discovered=0
        '''

        host = util.shorten_host_name(host, self.config.host_domains)
        node_new = 1
        node, node_updated = self.__get_known_node(ip, host)

        if (node == None):
            # new node
            node        = mnet_node()
            node.name   = host
            node.ip     = [ip]
        else:
            # existing node
            node_new = 0
            if (node.snmpobj.success == 1):
                # we already queried this node successfully - return it
                return (node, node_new)

        if (ip == 'UNKNOWN'):
            if (node_new):
                self.nodes.append(node)
            return (node, node_new|node_updated)

        node.name = host

        # vmware ESX reports the IP as 0.0.0.0
        # LLDP can return an empty string for IPs.
        if ((ip == '0.0.0.0') | (ip == '')):
            if (node_new):
                self.nodes.append(node)
            return (node, node_new|node_updated)

        # find valid credentials for this node
        if (node.try_snmp_creds(self.config.snmp_creds) == 0):
            if (node_new):
                self.nodes.append(node)
            return (node, node_new)

        node.name = node.get_system_name(self.config.host_domains)
        if (node.name != host):
            # the hostname changed (cdp/lldp vs snmp)!
            # double check we don't already know about this node
            if (node_new):
                node2, node_updated2 = self.__get_known_node(ip, host)
                if ((node2 != None) & (node_updated2 == 0)):
                    return (node, 0)
                node_updated = node_updated2

        # Finally, if we still don't have a name, use the IP.
        # e.g. Maybe CDP/LLDP was empty and we dont have good credentials
        # for this device.  A blank name can break Dot.
        if ((node.name == None) | (node.name == '')):
            node.name = node.get_ipaddr()

        # if this is a new non-updated node, save it to the list
        if ((node_new == 1) & (node_updated == 0)):
            self.nodes.append(node)

        node.query_node()
        return (node, 1)


    def __get_known_node(self, ip, host):
        '''
        Look for known nodes by IP and HOST.
        If found by HOST, add the IP if not already known.

        Return:
            node:       Node if found
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
            node:   mnet_node object to enumerate.
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
        dcodes = mnet_network.DCODE_STEP_INTO
        if (depth == 0):
            dcodes |= mnet_network.DCODE_ROOT
        self.__print_step(node.ip[0], node.name, depth, dcodes)

        # get the cached snmp credentials
        snmpobj = node.snmpobj

        # list of valid neighbors to discover next
        valid_neighbors = []

        # get list of CDP neighbors
        cdp_neighbors = node.get_cdp_neighbors()

        # get list of LLDP neighbors
        lldp_neighbors = node.get_lldp_neighbors()

        if ((cdp_neighbors == None) & (lldp_neighbors == None)):
            return

        neighbors = cdp_neighbors + lldp_neighbors

        for n in neighbors:
            # some neighbors may not advertise IP addresses - default them to 0.0.0.0
            if (n.remote_ip == None):
                n.remote_ip = '0.0.0.0'

            # check the ACL
            acl_action = self.__match_node_acl(n.remote_ip, n.remote_name)
            if (acl_action == 'deny'):
                # deny inclusion of this node
                continue
            
            # the code to display to stdout about this discovery
            dcodes = mnet_network.DCODE_DISCOVERED

            child    = None
            new_node = 1
            if (acl_action == 'include'):
                # include this node but do not discover it
                child    = mnet_node()
                child.ip = [n.remote_ip]
                dcodes  |= mnet_network.DCODE_INCLUDE
            else:
                # discover this node
                child, new_node = self.__query_node(n.remote_ip, n.remote_name)

            # if we couldn't pull info from SNMP fill in what we know
            if (child.snmpobj.success == 0):
                child.name = util.shorten_host_name(n.remote_name, self.config.host_domains)
                dcodes  |= mnet_network.DCODE_ERR_SNMP
            
            if (new_node == 1):
                # report this new node to stdout.
                # this could be a repeat either through
                # cylical diagrams or redundant links.
                if (acl_action == 'leaf'):          dcodes |= mnet_network.DCODE_LEAF
                if (n.discovered_proto == 'cdp'):   dcodes |= mnet_network.DCODE_CDP
                if (n.discovered_proto == 'lldp'):  dcodes |= mnet_network.DCODE_LLDP
                self.__print_step(n.remote_ip, n.remote_name, depth+1, dcodes)

            # CDP/LLDP advertises the platform
            child.plat = n.remote_platform
            child.ios  = n.remote_ios

            # add the discovered node to the link object and link to the parent
            n.node = child
            self.__add_link(node, n)

            # if we need to discover this node then add it to the list
            if ((new_node == 1) & (acl_action != 'leaf') & (acl_action != 'include')):
                valid_neighbors.append(child)

        # discover the valid neighbors
        for n in valid_neighbors:
            self.__discover_node(n, depth+1)


    def __match_node_acl(self, ip, host):
        for acl in self.config.discover_acl:
            if (acl.type == 'ip'):
                # ___ ip ipaddr
                if (self.__match_ip(ip, acl.str)):
                    return acl.action
            elif (acl.type == 'host'):
                # ___ host hoststr
                if (self.__match_host(host, acl.str)):
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


    def __match_host(self, host, pattern):
        if (host == '*'):
            return 1
        if (re.search(pattern, host)):
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

