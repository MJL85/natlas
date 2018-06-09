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
import natlas

def mod_load(mod):
    mod.name         = 'get-arp-table'
    mod.version      = '0.1'
    mod.author       = 'Michael Laforest'
    mod.authoremail  = 'mjlaforest@gmail.com'
    mod.preload_conf = 0
    mod.about        = 'Display the ARP table'
    mod.syntax       = '-n <node IP> -c <snmp v2 community> [-s | -d] [-i <IP regex>] [-v <vlan regex>] [-m <mac regex>]'
    mod.help         = '''
                        Query a switch display the ARP table.

                        The table can be filtered with:
                            -s          Include Static entries only
                            -d          Include Dynamic entries only
                            -i <regex>  Include entries with IP addresses that match regex pattern
                            -v <regex>  Include entries with VLANs that match regex pattern
                            -m <regex>  Include entries with MAC addreses that match regex pattern
                        '''
    mod.example      = '''
                        Get all ARP entries where the MAC begins with 84b8.0262. and is in VLAN 800 or 801

                        # get-arp-table -n 10.10.1.66 -c public -m '84b8\.0262\..*' -v "80[01]"

                        IP                 MAC               VLAN     TYPE
                        10.10.19.93        84b8.0262.361c    800      dynamic
                        10.10.19.102       84b8.0262.3948    800      dynamic
                        10.10.29.104       84b8.0262.1890    801      dynamic

                        Found 3 ARP entries
                        '''
    return 1


def mod_entry(natlas_obj, argv):
    opt_devip = None
    opt_community = None
    opt_type = None
    opt_vlan = None
    opt_mac = None
    opt_ip = None
    try:
        opts, args = getopt.getopt(argv, 'n:c:sdv:m:i:')
    except getopt.GetoptError:
        return
    for opt, arg in opts:
        if (opt == '-n'):   opt_devip = arg
        if (opt == '-c'):   opt_community = arg
        if (opt == '-s'):   opt_type = 'static'
        if (opt == '-d'):   opt_type = 'dynamic'
        if (opt == '-v'):   opt_vlan = arg
        if (opt == '-m'):   opt_mac = arg
        if (opt == '-i'):   opt_ip = arg

    if ((opt_devip == None) | (opt_community == None)):
        return

    # set some snmp credentials for us to use
    natlas_obj.snmp_add_credential(2, opt_community)
    
    # get the ARP table
    try:
        arp = natlas_obj.get_arp_table(opt_devip, ip=opt_ip, mac=opt_mac, interf=opt_vlan, arp_type=opt_type)
    except Exception as e:
        print(e)
        return
  
    # print ARP table
    print()
    print('IP                 MAC               VLAN     TYPE')
    print('--                 ---               ----     ----')
    for a in arp:
        print('{:<15}    {:<14}    {:<5}    {:}'.format(a.ip, a.mac, str(a.interf).lstrip('Vl'), a.arp_type))
    
    print('\nFound %i ARP entries' % len(arp))
    
