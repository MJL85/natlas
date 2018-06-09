#!/usr/bin/python

'''
        natlas
        natlas-cli.py

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
import getopt
import os
import natlas

HOP_LIMIT   = 1000
gnatlas     = None
visited_ips = []

def mod_load(mod):
    mod.name         = 'tracemac'
    mod.version      = '0.1'
    mod.author       = 'Michael Laforest'
    mod.authoremail  = 'mjlaforest@gmail.com'
    mod.about        = 'Trace a MAC address through a layer 2 network.'
    mod.syntax       = '-n <starting node IP> -m <MAC address>'
    mod.help         = '''
                        Trace a MAC address through a layer 2 network.

                        Define a switch on that network to begin the trace using -n. tracemac will use the MAC and CDP/LLDP tables to iteratively trace the MAC defined with -m until the host port is located.
                        '''
    mod.example      = '''
                        # tracemac -n 10.10.20.1 -m d4be.d939.4fd2

                        HOP    NODE IP          NODE NAME                  VLAN     PORT          REMOTE NODE IP   REMOTE NODE NAME
                        ---    -------          ---------                  ----     ----          --------------   ----------------
                        1      10.10.20.1       SwitchA                    10       Gi1/0/10      10.10.20.2       SwitchB
                        2      10.10.20.2       SwitchB                    10       Gi1/0/22      10.10.20.5       SwitchE
                        2      10.10.20.5       SwitchE                    10       Gi0/8

                        FOUND

                        MAC Address: d4be.d939.4fd3
                            Node IP: 10.10.20.5
                          Node Name: SwitchE
                               Port: Gi0/8
                        '''
    mod.notimer      = 0
    mod.preload_conf = 1
    mod.require_api = '0.11'
    return 1

def mod_entry(natlas_obj, argv):
    global gnatlas
    gnatlas = natlas_obj

    opt_ip = None
    opt_community = None
    try:
        opts, args = getopt.getopt(argv, 'n:m:')
    except getopt.GetoptError:
        return natlas.RETURN_ERR
    for opt, arg in opts:
        if (opt == '-n'):   opt_ip = arg
        if (opt == '-m'):   opt_mac = arg

    print('HOP    NODE IP          NODE NAME                  VLAN     PORT          REMOTE NODE IP   REMOTE NODE NAME')
    print('---    -------          ---------                  ----     ----          --------------   ----------------')

    try:
        node, port = trace_node(opt_ip, opt_mac, 1)
    except Exception as e:
        print('[ERROR] %s' % e)
        return natlas.RETURN_OK

    print()
    if (node == None):
        print('NOT FOUND')
    else:
        print('FOUND\n')
        print('MAC Address: %s' % opt_mac)
        print('    Node IP: %s' % node.get_ipaddr())
        print('  Node Name: %s' % node.name)
        print('       Port: %s' % port)

    return natlas.RETURN_OK

def trace_node(node_ip, macaddr, depth):
    global visited_ips
    if (node_ip in visited_ips):
        raise Exception('Loop encountered.')
    visited_ips.append(node_ip)

    if (depth > HOP_LIMIT):
        # probably some weird problem
        raise Exception('Hop count too high. Terminating trace.')

    sys.stdout.write('{:<5}  {:<15}  '.format(depth, node_ip))
    sys.stdout.flush()

    node = gnatlas.new_node(node_ip)
    macs = gnatlas.get_switch_macs(node=node)
    gnatlas.query_node(node, get_name=True)

    match = None
    for mac in macs:
        if (mac.mac == macaddr):
            node_name = ''
            if (node.name != None):
                node_name = node.name
            sys.stdout.write('{:<25}  {:<7}  {:<12}  '.format(node_name, mac.vlan, mac.port))
            sys.stdout.flush()
            match = mac
            break

    if (match == None):
        return (None, None)

    port = node.shorten_port_name(mac.port)
    neighbors = gnatlas.get_neighbors(node)

    match = None
    for n in neighbors:
        if (n.local_port == port):
            sys.stdout.write('{:<15}  {:<25}'.format(n.remote_ip, n.remote_name))
            sys.stdout.flush()
            match = n
            break

    print()
    if (match == None):
        # MAC is on this node
        return (node, mac.port)

    # found MAC on the same port as a neighbor - trace that node
    return trace_node(match.remote_ip, macaddr, depth+1)

