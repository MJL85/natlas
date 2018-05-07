#!/usr/bin/env python

'''
        MNet Suite
        mnet.py

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
import datetime
import os
from timeit import default_timer as timer

import mnetsuite

DEFAULT_OPT_DEPTH   = 100
DEFAULT_OPT_TITLE   = 'mnet Network Diagram'
DEFAULT_OPT_CONF    = './mnet.conf'

def print_syntax():
    print('Usage:\n'
                    '  mnet.py diagram -r <root IP>\n'
                    '                -o <output file>\n'
                    '                [-d <max depth>]\n'
                    '                [-c <config file>]\n'
                    '                [-t <diagram title>]\n'
                    '                [-C <catalog file>]\n'
                    '\n'
                    '  mnet.py tracemac -r <root IP>\n'
                    '                   -m <MAC Address>\n'
                    '                   [-c <config file>]\n'
                    '\n'
                    '  mnet.py getmacs -r <root IP>\n'
                    '                  -o <output CSV file>\n'
                    '                  [-d <max depth>]\n'
                    '                  [-c <config file>]\n'
                    '\n'
                    '  mnet.py config\n'
            )


def print_banner():
    print('mnet suite v%s' % mnetsuite.__version__)
    print('Michael Laforest <mjlaforest@gmail.com>')
    print('')


def main(argv):
    opt_root_ip = None
    if (len(argv) < 1):
        print_banner()
        print_syntax()
        return

    start = timer()
    mod = argv[0]
    if (mod == 'diagram'):
        print_banner()
        diagram(argv[1:])
    elif (mod == 'tracemac'):
        print_banner()
        tracemac(argv[1:])
    elif (mod == 'getmacs'):
        print_banner()
        getmacs(argv[1:])
    elif (mod == 'config'):
        generate_config()
    else:
        print_banner()
        print_syntax()

    s = timer() - start
    h=int(s/3600)
    m=int((s-(h*3600))/60)
    s=s-(int(s/3600)*3600)-(m*60)
    print('Completed in %i:%i:%.2fs' % (h, m, s))

def diagram(argv):
    opt_root_ip = None
    opt_output  = None
    opt_catalog = None
    opt_depth   = DEFAULT_OPT_DEPTH
    opt_title   = DEFAULT_OPT_TITLE
    opt_conf    = DEFAULT_OPT_CONF

    try:
        opts, args = getopt.getopt(argv, 'o:d:r:t:F:c:C:')
    except getopt.GetoptError:
        print_syntax()
        sys.exit(1)
    for opt, arg in opts:
        if (opt == '-r'):
            opt_root_ip = arg
        if (opt == '-o'):
            opt_output = arg
        if (opt == '-d'):
            opt_depth = int(arg)
        if (opt == '-t'):
            opt_title = arg
        if (opt == '-c'):
            opt_conf = arg
        if (opt == '-C'):
            opt_catalog = arg

    if ((opt_root_ip == None) | (opt_output == None)):
        print_syntax()
        print('Invalid arguments.')
        return

    print('     Config file: %s' % opt_conf)
    print('     Output file: %s' % opt_output)
    print('Out Catalog file: %s' % opt_catalog)
    print('       Root node: %s' % opt_root_ip)
    print('  Discover depth: %s' % opt_depth)
    print('   Diagram title: %s' % opt_title)
    print()

    # load the config
    config = mnetsuite.mnet_config()
    if (config.load(opt_conf) == 0):
        return 0

    # start discovery
    network = mnetsuite.mnet_network(config)
    network.set_max_depth(opt_depth)
    network.discover(opt_root_ip)
    network.discover_details()

    # outputs
    #stdout = mnetsuite.mnet_output_stdout(network)
    #stdout.generate()

    if (opt_output != None):
        diagram = mnetsuite.mnet_output_diagram(network)
        diagram.generate(opt_output, opt_title)

    if (opt_catalog != None):
        catalog = mnetsuite.mnet_output_catalog(network)
        catalog.generate(opt_catalog)


def tracemac(argv):
    opt_root_ip = None
    opt_mac     = None
    opt_conf    = DEFAULT_OPT_CONF

    try:
        opts, args = getopt.getopt(argv, 'r:c:m:')
    except getopt.GetoptError:
        print_syntax()
        return
    for opt, arg in opts:
        if (opt == '-r'):
            opt_root_ip = arg
        if (opt == '-c'):
            opt_conf = arg
        if (opt == '-m'):
            opt_mac = arg

    if ((opt_root_ip == None) | (opt_mac == None)):
        print_syntax()
        print('Invalid arguments.')
        return

    print('     Config file: %s' % opt_conf)
    print('       Root node: %s' % opt_root_ip)
    print('     MAC address: %s' % opt_mac)
    print('\n')

    # load the config
    config = mnetsuite.mnet_config()
    if (config.load(opt_conf) == 0):
        return 0

    trace = mnetsuite.mnet_tracemac(config)

    # start
    print('Start trace.')
    print('------------')

    ip = opt_root_ip
    while (ip != None):
        ip = trace.trace(ip, opt_mac)
        print('------------')

    print('Trace complete.\n')


def getmacs(argv):
    opt_root_ip = None
    opt_output  = None
    opt_conf    = DEFAULT_OPT_CONF
    opt_depth   = DEFAULT_OPT_DEPTH

    try:
        opts, args = getopt.getopt(argv, 'o:r:c:d:')
    except getopt.GetoptError:
        print_syntax()
        return
    for opt, arg in opts:
        if (opt == '-r'):
            opt_root_ip = arg
        if (opt == '-d'):
            opt_depth = int(arg)
        if (opt == '-c'):
            opt_conf = arg
        if (opt == '-o'):
            opt_output = arg

    if ((opt_root_ip == None) | (opt_output == None)):
        print_syntax()
        print('Invalid arguments.')
        return

    print('     Config file: %s' % opt_conf)
    print('     Output file: %s' % opt_output)
    print('       Root node: %s' % opt_root_ip)
    print('  Discover depth: %s' % opt_depth)
    print('\n')

    # load the config
    config = mnetsuite.mnet_config()
    if (config.load(opt_conf) == 0):
        return 0

    # start discovery
    network = mnetsuite.mnet_network(config)
    network.set_max_depth(opt_depth)
    network.discover(opt_root_ip)

    # get macs
    mac = mnetsuite.mnet_mac(config)
    macs = mac.get_macs_from_network_discovery(network, 1)

    # generate output csv
    if (opt_output):
        mac.output_csv(opt_output)


def generate_config():
    conf = mnetsuite.config.mnet_config()
    print('%s' % conf.generate_new())


if __name__ == "__main__":
    main(sys.argv[1:])
    
