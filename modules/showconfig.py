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

def mod_load(mod):
    mod.name         = 'showconfig'
    mod.version      = '0.1'
    mod.author       = 'Michael Laforest'
    mod.authoremail  = 'mjlaforest@gmail.com'
    mod.notimer      = 1
    mod.about        = 'Display the config'
    mod.syntax       = '[-c <config file>]'
    mod.help         = 'Print the configuration file to the console.'
    mod.preload_conf = 0
    return 1

def mod_entry(natlas_obj, argv):
    opt_conf = './natlas.conf'
    try:
        opts, args = getopt.getopt(argv, 'c:')
    except getopt.GetoptError:
        return natlas.RETURN_SYNTAXERR
    for opt, arg in opts:
        if (opt == '-c'):
            opt_conf = arg

    try:
        conf = open(opt_conf, 'r').read()
    except:
        print('Unable to open config file.')
        return
    print('%s' % conf)

    return natlas.RETURN_OK

