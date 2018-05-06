#!/usr/bin/python

'''
        MNet Suite
        output_stdout.py

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

from .config import mnet_config
from .network import mnet_network
from .output import mnet_output
from ._version import __version__


class mnet_output_stdout:

    def __init__(self, network):
        mnet_output.__init__(self)
        self.network = network
        self.config  = network.config

    def generate(self):
        self.network.reset_discovered()

        print('-----')
        print('----- DEVICES')
        print('-----')
        num_nodes, num_links = self.__generate(self.network.root_node)

        print('Discovered devices: %i' % num_nodes)
        print('Discovered links:   %i' % num_links)

    def __generate(self, node):
        if (node == None):
            return (0, 0)
        if (node.discovered > 0):
            return (0, 0)
        node.discovered = 1

        ret_nodes = 1
        ret_links = 0

        print('-----------------------------------------')
        print('      Name: %s' % node.name)
        print('        IP: %s' % node.get_ipaddr())
        print('  Platform: %s' % node.plat)
        print('   IOS Ver: %s' % node.ios)

        if ((node.vss.enabled == 0) & (node.stack.count == 0)):
            print('    Serial: %s' % node.serial)

        print('   Routing: %s' % ('yes' if (node.router == 1) else 'no'))
        print('   OSPF ID: %s' % node.ospf_id)
        print('   BGP LAS: %s' % node.bgp_las)
        print('  HSRP Pri: %s' % node.hsrp_pri)
        print('  HSRP VIP: %s' % node.hsrp_vip)

        if (node.vss.enabled):
            print('  VSS Mode: %i' % node.vss.enabled)
            print('VSS Domain: %s' % node.vss.domain)
            print('       VSS Slot 0:')
            print('              IOS: %s' % node.vss.members[0].ios)
            print('           Serial: %s' % node.vss.members[0].serial)
            print('         Platform: %s' % node.vss.members[0].plat)
            print('       VSS Slot 1:')
            print('              IOS: %s' % node.vss.members[1].ios)
            print('           Serial: %s' % node.vss.members[1].serial)
            print('         Platform: %s' % node.vss.members[1].plat)

        if ((node.stack.count > 0) & (self.config.diagram.get_stack_members)):
            print(' Stack Cnt: %i' % node.stack.count)
            print('      Stack members:')
            for smem in node.stack.members:
                print('        Switch Number: %s' % (smem.num))
                print('                 Role: %s' % (smem.role))
                print('             Priority: %s' % (smem.pri))
                print('                  MAC: %s' % (smem.mac))
                print('             Platform: %s' % (smem.plat))
                print('                Image: %s' % (smem.img))
                print('               Serial: %s' % (smem.serial))

        if (node.vpc_domain != None):
            print('VPC Domain: %s' % (node.vpc_domain))
            print(' VPC plink: %s' % (node.vpc_peerlink_if))
            if (node.vpc_peerlink_node != None):
                print(' VPC plink: %s (%s)' % (node.vpc_peerlink_node.name, node.vpc_peerlink_node.get_ipaddr()))

        print('      Loopbacks:')
        for lo in node.loopbacks:
            for lo_ip in lo.ips:
                print('        %s - %s' % (lo.name, lo_ip))

        print('      SVIs:')
        for svi in node.svis:
            for ip in svi.ip:
                print('        SVI %s - %s' % (svi.vlan, ip))

        print('     Links:')
        for link in node.links:
            lag = ''
            if ((link.local_lag != None) | (link.remote_lag != None)):
                lag = 'LAG[%s:%s]' % (link.local_lag or '', link.remote_lag or '')
            print('       %s -> %s:%s %s' % (link.local_port, link.node.name, link.remote_port, lag))
            ret_links += 1

        for link in node.links:
            rn, rl = self.__generate(link.node)
            ret_nodes += rn
            ret_links += rl

        return (ret_nodes, ret_links)

