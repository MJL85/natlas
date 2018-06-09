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

DEFAULT_OPT_DEPTH   = 100
DEFAULT_OPT_TITLE   = 'natlas Diagram'

def mod_load(mod):
    mod.name        = 'diagram'
    mod.version     = '0.11'
    mod.author      = 'Michael Laforest'
    mod.authoremail = 'mjlaforest@gmail.com'
    mod.about       = 'Discover and diagram the network'
    mod.syntax      = '-r <root IP>\n'                          \
                      '        -o <output file>\n'              \
                      '        [-d <max depth>]\n'              \
                      '        [-c <config file>]\n'            \
                      '        [-t <diagram title>]\n'          \
                      '        [-C <catalog file>]'
    mod.require_api = '0.12'
    mod_help        = 'Discover and diagram the network beginning at the specified root node.'
    return 1

def mod_entry(natlas_obj, argv):
    opt_root_ip = None
    opt_output  = None
    opt_catalog = None
    opt_depth   = DEFAULT_OPT_DEPTH
    opt_title   = DEFAULT_OPT_TITLE

    try:
        opts, args = getopt.getopt(argv, 'o:d:r:t:F:c:C:')
    except getopt.GetoptError:
        print('Invalid arguments.')
        return
    for opt, arg in opts:
        if (opt == '-r'):   opt_root_ip = arg
        if (opt == '-o'):   opt_output = arg
        if (opt == '-d'):   opt_depth = int(arg)
        if (opt == '-t'):   opt_title = arg
        if (opt == '-C'):   opt_catalog = arg

    if ((opt_root_ip == None) | (opt_output == None)):
        print('Invalid arguments.')
        return

    print('     Config file: %s' % natlas_obj.config_file)
    print('     Output file: %s' % opt_output)
    print('Out Catalog file: %s' % opt_catalog)
    print('       Root node: %s' % opt_root_ip)
    print('  Discover depth: %s' % opt_depth)
    print('   Diagram title: %s' % opt_title)
    print()

    # start discovery
    natlas_obj.set_discover_maxdepth(opt_depth)
    natlas_obj.set_verbose(1)
    natlas_obj.discover_network(opt_root_ip, 1)

    # outputs
    if (opt_output != None):    natlas_obj.write_diagram(opt_output, opt_title)
    if (opt_catalog != None):   natlas_obj.write_catalog(opt_catalog)

    return
