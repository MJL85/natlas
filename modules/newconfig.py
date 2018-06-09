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
    mod.name         = 'newconfig'
    mod.version      = '0.1'
    mod.author       = 'Michael Laforest'
    mod.authoremail  = 'mjlaforest@gmail.com'
    mod.notimer      = 1
    mod.about        = 'Generate a new config'
    mod.syntax       = ''
    mod.help         = 'Generate a new configuration file.'
    mod.preload_conf = 0
    return 1

def mod_entry(natlas_obj, argv):
    print(natlas_obj.config_generate())
    return natlas.RETURN_OK
