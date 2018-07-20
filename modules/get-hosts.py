#!/usr/bin/python
'''
        natlas

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
import socket
import natlas

def mod_load(mod):
    mod.name        = 'get-hosts'
    mod.version     = '0.1'
    mod.author      = 'Michael Laforest'
    mod.authoremail = 'mjlaforest@gmail.com'
    mod.about       = 'Display details about connected hosts'
    mod.syntax      = [
                        '-r <root IP> -c <config file> [-o <csv file>] [-d <discovery depth>]',
                        '-n <node IP> [-r <router IP>] -C <snmp v2 community> [-v <vlan regex>] [-p <port regex>] [-o <csv file>]'
                      ]
    mod.help         = '''
                        Collect information about hosts connected to the network.

                        To get information from just one node, use the -n option.
                        To get information from discovered nodes, use the -r option.

                        If -r is used, a network discovery is performed at the specified root node. The discovered nodes are then queried to determine hosts connected to each node.

                        Details about hosts include MAC addresses, IP addresses, VLANs, switch ports, and DNS names if available.

                        The resulting data is printed to stdout and can also be saved to a CSV file using the -o option.
                        '''

    mod.example      = '''
                        Get devices connected to 10.10.10.3 on vlan 20 and on ports starting with "Gi".
                        The gateway for vlan 44 is on 10.10.10.1.

                        # get-hosts -n 10.10.10.3 -r 10.10.10.1 -C public -v 20 -p "Gi.*"

                        Collecting MACs from 10.10.10.3...
                        20....................................................................................................
                        Collecting ARPs from 10.10.10.1...

                        Found 25 MAC entries
                        Found 104 ARP entries

                        PORT        IP                MAC               VLAN        DNS
                        Gi1/0/2     10.115.82.130     0023.246b.e7e8    20          super12
                        Gi1/0/5     10.115.82.158     0023.246b.ea43    20          david
                        Gi1/0/30    10.115.82.225     0023.246c.27a8    20          jerry
                        Gi1/0/15    10.115.82.216     0023.246d.9956    20          john1
                        Gi1/0/21    10.115.82.171     0023.2474.e2ef    20          kiosk3
                        Gi1/0/22    10.115.82.202     0023.2474.e330    20          bobb
                        Gi1/0/6     10.115.82.172     0023.2477.9bbd    20          brendam
                        Gi1/0/23    10.115.82.102     0023.2477.9c18    20          debbie2
                        Gi2/0/45    10.115.82.126     0023.2493.9dad    20          serverA
                        Gi2/0/44    10.115.82.153     0023.2493.9df0    20          serverB
                        Gi2/0/48    10.115.82.16      00c0.b788.aa3c    20
                        Gi1/0/6                       00f8.2c07.bea4
                        Gi1/0/24                      00f8.2c07.bf49
                        Gi1/0/30                      00f8.2c07.ef38
                        Gi1/0/16                      00f8.2c07.ef4c
                        Gi1/0/17                      00f8.2c07.ef57
                        Gi1/0/21                      00f8.2c07.ef5d
                        Gi1/0/5                       00f8.2c07.f08d
                        Gi1/0/25    10.115.82.154     1c87.2c58.c83d    20          kiosk2
                        Gi1/0/29    10.115.82.205     305a.3a46.9825    20          kiosk1
                        Gi2/0/42    10.115.82.113     4ccc.6a16.bf92    20          president
                        Gi1/0/9     10.115.82.45      5065.f357.b289    20
                        Gi1/0/27    10.115.82.73      5820.b152.d24d    20
                        Gi1/0/31    10.115.82.116     9457.a5cb.c16b    20          comptroller
                        Gi1/0/8                       f0b2.e576.cd7c
                        '''
    return 1

def mod_entry(natlas_obj, argv):
    opt_root_ip     = None
    opt_node_ip     = None
    opt_router_ip   = None
    opt_community   = None
    opt_vlan        = None
    opt_port        = None
    opt_output      = None
    opt_depth       = 100
    try:
        opts, args = getopt.getopt(argv, 'r:n:o:d:C:v:p:')
    except getopt.GetoptError:
        return natlas.RETURN_SYNTAXERR
    for opt, arg in opts:
        if (opt == '-r'):   opt_root_ip = arg
        if (opt == '-n'):   opt_node_ip = arg
        if (opt == '-o'):   opt_output = arg
        if (opt == '-d'):   opt_depth = arg
        if (opt == '-C'):   opt_community = arg
        if (opt == '-v'):   opt_vlan = arg
        if (opt == '-p'):   opt_depth = arg

    if ((opt_root_ip == None) & (opt_node_ip == None)):
        return natlas.RETURN_SYNTAXERR

    if (opt_node_ip != None):
        return single_node(natlas_obj, opt_node_ip, opt_root_ip, opt_community, opt_vlan, opt_port, opt_output)
        
    return all_nodes(natlas_obj, opt_root_ip, opt_output, opt_depth)


def get_arp_entry_for_mac(arps, macaddr):
    for a in arps:
        if (a.mac == macaddr):
            return a
    return None


def create_csv_file(filepath, colnames):
    f = None
    if (filepath != None):
        try:
            f = open(filepath, 'w')
            f.write('%s\n' % colnames)
        except:
            print('Unable to open CSV output file "%s"' % filepath)
    return f


def all_nodes(natlas_obj, opt_root_ip, opt_output, opt_depth):
    # discover the network
    natlas_obj.set_discover_maxdepth(opt_depth)
    natlas_obj.set_verbose(1)
    natlas_obj.discover_network(opt_root_ip, 0)

    network_macs = [] 
    network_arps = []

    # iterate through each discovered node
    natlas_nodes = natlas_obj.get_discovered_nodes()
    for node in natlas_nodes:
        # get the switch MAC table
        nip = natlas_obj.get_node_ip(node)
        print('Collecting MACs from %s...' % nip)
        try:
            macs = natlas_obj.get_switch_macs(nip, verbose=1)
            network_macs.extend(macs)
        except Exception as e:
            print(e)
            pass
  
        # get the ARP table for the router
        print('Collecting ARPs from %s...' % nip)
        try:
            arps = natlas_obj.get_arp_table(nip)
            network_arps.extend(arps)
        except Exception as e:
            print(e)
            pass
    
    print()
    print('Found %i MAC entries' % len(network_macs))
    print('Found %i ARP entries' % len(network_arps))
    print()
    print('NODE_NAME               NODE_IP            PORT        IP                MAC               VLAN        DNS')
    print('---------               -------            ----        --                ---               ----        ---')

    # create the output csv file
    f = create_csv_file(opt_output, 'NODE_NAME,NODE_IP,PORT,IP,MAC,VLAN,DNS')
    for m in network_macs:
        arp = get_arp_entry_for_mac(network_arps, m.mac)
        ip   = ''
        interf = ''
        dns  = ''
        if (arp != None):
            ip   = arp.ip
            interf = str(arp.interf).lstrip('Vl')
            try:
                dns  = socket.gethostbyaddr(ip)[0]
            except:
                pass
        print('{:<20}    {:<15}    {:<8}    {:<14}    {:<5}    {:<8}    {:}'.format(m.node_host, m.node_ip, m.port, ip, m.mac, interf, dns))

        if (f != None):
            f.write('"%s","%s","%s","%s","%s","%s","%s"\n' % (m.node_host, m.node_ip, m.port, ip, m.mac, interf, dns))
    
    if (f != None):
        f.close()

    return natlas.RETURN_OK


def single_node(natlas_obj, opt_devip, opt_routerip, opt_community, opt_vlan, opt_port, opt_output):
    if ((opt_devip == None) | (opt_community == None)):
        return natlas.RETURN_SYNTAXERR
    if (opt_routerip == None):
        opt_routerip = opt_devip

    # set some snmp credentials for us to use
    natlas_obj.snmp_add_credential(2, opt_community)
    
    # get the switch MAC table
    print('\nCollecting MACs from %s...' % opt_devip)
    try:
        macs = natlas_obj.get_switch_macs(opt_devip, vlan=opt_vlan, port=opt_port, verbose=1)
    except Exception as e:
        print(e)
        return natlas.RETURN_ERR
  
    # get the ARP table for the router
    print('\nCollecting ARPs from %s...' % opt_routerip)
    try:
        arps = natlas_obj.get_arp_table(opt_routerip)
    except Exception as e:
        print(e)
        return natlas.RETURN_ERR
    
    print()
    print('Found %i MAC entries' % len(macs))
    print('Found %i ARP entries' % len(arps))
    print()
    print('PORT        IP                MAC               VLAN        DNS')
    print('----        --                ---               ----        ---')

    f = create_csv_file(opt_output, 'NODE_NAME,NODE_IP,PORT,IP,MAC,VLAN,DNS')

    for m in macs:
        arp    = get_arp_entry_for_mac(arps, m.mac)
        ip     = ''
        interf = ''
        dns    = ''
        if (arp != None):
            ip     = arp.ip
            interf = str(arp.interf).lstrip('Vl')
            if ((opt_vlan != None) & (interf != opt_vlan)):
                continue
            try:
                dns = socket.gethostbyaddr(ip)[0]
            except:
                pass
        print('{:<8}    {:<14}    {:<5}    {:<8}    {:}'.format(m.port, ip, m.mac, interf, dns))
        
        if (f != None):
            f.write('"","%s","%s","%s","%s","%s","%s"\n' % (opt_devip, m.port, ip, m.mac, interf, dns))
    
    if (f != None):
        f.close()
    
    return natlas.RETURN_OK

