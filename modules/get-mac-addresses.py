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
    mod.name         = 'get-mac-table'
    mod.version      = '0.1'
    mod.author       = 'Michael Laforest'
    mod.authoremail  = 'mjlaforest@gmail.com'
    mod.about        = 'Get MAC table from device'
    mod.syntax       = '-n <node IP> -c <snmp v2 community> [-m <mac regex>] [-p <port regex>] [-v <vlan>]'
    mod.preload_conf = 0
    mod.help         = '''
                        Query a switch and collect all VLANs and MAC addresses.
                        The output can be filtered down using the -m, -p, and -v options.
                        '''
    mod.example      = '''
                        Get all MAC addresses on ports Gi4/0/*

                        # get-mac-table -n 10.10.10.10 -c public -p "Gi4/0/.*"

                        VLAN        Name
                        1           default
                        10          Data

                        Collecting MACS...

                        1..10.....
                        PORT        MAC               VLAN        VLAN_Name
                        Gi4/0/5     c472.95db.318a    1           default
                        Gi4/0/39    0023.2477.2d4b    10          Data
                        Gi4/0/24    00a3.d1e6.0b71    10          Data
                        Gi4/0/12    00f8.2c07.bad7    10          Data
                        Gi4/0/42    00f8.2c07.bb7f    10          Data
                        Gi4/0/40    00f8.2c07.bbed    10          Data
                        '''
    return 1

def mod_entry(natlas_obj, argv):
    opt_ip = None
    opt_community = None
    opt_mac = None
    opt_port = None
    opt_vlan = None
    try:
        opts, args = getopt.getopt(argv, 'n:c:m:p:v:')
    except getopt.GetoptError:
        return natlas.RETURN_ERR
    for opt, arg in opts:
        if (opt == '-n'):   opt_ip = arg
        if (opt == '-c'):   opt_community = arg
        if (opt == '-m'):   opt_mac = arg
        if (opt == '-p'):   opt_port = arg
        if (opt == '-v'):   opt_vlan = arg

    if ((opt_ip == None) | (opt_community == None)):
        return natlas.RETURN_ERR

    # set some snmp credentials for us to use
    natlas_obj.snmp_add_credential(2, opt_community)
    
    # get the switch VLANs
    try:
        vlans = natlas_obj.get_switch_vlans(opt_ip)
    except Exception as e:
        print(e)
        return natlas.RETURN_ERR
    print('VLAN        Name')
    for vlan in vlans:
        print('{:<8}    {:}'.format(vlan.id, vlan.name))

    if (opt_vlan != None):
        valid_vlan = 0
        for vlan in vlans:
            if (str(vlan.id) == opt_vlan):
                valid_vlan = 1
                break
        if (valid_vlan == 0):
            print('\n[ERROR] VLAN %s does not exist on this device.' % opt_vlan)
            return natlas.RETURN_OK
   
    # get the switch MAC table
    print('\nCollecting MACs...')
    macs = natlas_obj.get_switch_macs(opt_ip, mac=opt_mac, port=opt_port, vlan=opt_vlan, verbose=1)
    
    # print the MAC table
    print('\n\n')
    print('PORT        MAC               VLAN        VLAN_Name')
    print('----        ---               ----        ---------')
    for mac in macs:
        vlan_name = ''
        for vlan in vlans:
            if (vlan.id == mac.vlan):
                vlan_name = vlan.name
        print('{:<8}    {:<14}    {:<8}    {:}'.format(mac.port, mac.mac, mac.vlan, vlan_name))

    print()
    print('Found %i VLANs' % len(vlans))
    print('Found %i MAC addresses' % len(macs))
    return natlas.RETURN_OK

