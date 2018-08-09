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
import datetime
import os
import re
from timeit import default_timer as timer
from distutils.version import LooseVersion

import natlas

DEFAULT_OPT_DEPTH   = 100
DEFAULT_OPT_TITLE   = 'natlas Diagram'
DEFAULT_OPT_CONF    = './natlas.conf'

class natlas_mod:
    def __init__(self):
        self.filename     = ''
        self.name         = ''
        self.version      = ''
        self.author       = ''
        self.authoremail  = ''
        self.syntax       = None
        self.about        = None
        self.help         = None
        self.example      = None
        self.entryfunc    = None
        self.notimer      = 0
        self.require_api  = None
        self.preload_conf = 1
    def __str__(self):
        return ('<name="%s", version="%s", author="%s">' % (self.name, self.version, self.author))
    def __repr__(self):
        return self.__str__()

try:
    natlas_obj = natlas.natlas()
except Exception as e:
    print(e)
    exit()

def main(argv):
    if (len(argv) < 1):
        print_banner()
        print_syntax()
        return

    if (argv[0] != 'newconfig'):
        print_banner()
    
    modules = load_modules()

    if (argv[0] == 'list'):
        list_mods(modules)
        return
    if (argv[0] == 'info'):
        print_mod_info(modules, argv[1])
        return
    if (argv[0] == 'help'):
        if (len(argv) < 2):
            print_syntax()
            return
        print_mod_help(modules, argv[1])
        return
    if (argv[0] == 'syntax'):
        print_mod_syntax(modules, argv[1])
        return

    mod = get_mod(modules, argv[0])
    if (mod != None):
        exec_mod(mod, argv[1:])
        return

    print_syntax()

    return

def print_syntax():
    print('Usage:\n'
          '  natlas-cli.py list              - Display available modules\n'
          '  natlat-cli.py info <module>     - Display information about the module\n'
          '  natlat-cli.py help <module>     - Display help for module\n'
          '  natlat-cli.py syntax <module>   - Display syntax for module\n')

def print_banner():
    print('natlas v%s' % natlas.__version__)
    print('Michael Laforest <mjlaforest@gmail.com>')
    print('Python %s\n' % sys.version.split(' ')[0])

def load_modules():
    sys.path.insert(0, './modules')
    ret = []
    for f in os.listdir('./modules'):
        if (f[-3:] == '.py'):
            mod = None
            try:
                mod = __import__(f[:-3], ['mod_load', 'mod_entry'])
            except Exception as e:
                print(e)
                continue

            if (hasattr(mod, 'mod_load') == 0):
                print('[ERROR] No mod_load() for %s' % f)
                continue

            m = natlas_mod()
            if (mod.mod_load(m) == 0):
                print('[ERROR] mod_load() returned an error for %s' % f)
                continue
            m.filename = f
            m.entryfunc = mod.mod_entry
            ret.append(m)

    return ret

def exec_mod(module, argv):
    if (does_mod_accept_api(module) == 0):
        print('Module is disabled.')
        return 0

    start = timer()

    try:
        natlas_obj = natlas.natlas()
    except Exception as e:
        print('[ERROR] %s' % e)
        return 0

    if (module.preload_conf == 1):
        try:
            argv, opt_conf = argv_get_conf(argv)
        except Exception as e:
            print('[ERROR] %s' % e)
            return 0

        try:
            natlas_obj.config_load(opt_conf)
        except Exception as e:
            print(e)
            return 0

    modret = module.entryfunc(natlas_obj, argv)
    if (modret == natlas.RETURN_SYNTAXERR):
        print('Invalid syntax for module.  See "syntax %s" for more info.' % module.name)
        return 0
    if (modret == natlas.RETURN_ERR):
        print('[ERROR] Error encountered in module.')
        return 0

    if (module.notimer == 0):
        s = timer() - start
        h=int(s/3600)
        m=int((s-(h*3600))/60)
        s=s-(int(s/3600)*3600)-(m*60)
        print('\nCompleted in %i:%i:%.2fs' % (h, m, s))
    
    return 1

def argv_get_conf(argv):
    opt_conf = DEFAULT_OPT_CONF
    for i in range(0, len(argv)):
        if (argv[i] == '-c'):
            if ((i+1) >= len(argv)):
                raise Exception('-c used but no file specified')
            opt_conf = argv[i+1]
            del argv[i+1]
            del argv[i]
            break
    return (argv, opt_conf)

def list_mods(modules):
    print('Module                  Version   Status    Author                    About')
    print('------                  -------   ------    ------                    -----')
    for m in modules:
        status = 'Disabled'
        accept = does_mod_accept_api(m)
        if (accept == 1):
            status = 'OK'
        elif (accept == 2):
            status = 'OK*'
        print('{:<22}  {:<8}  {:<8}  {:<24}  {:}'.format(m.name, m.version, status, m.author, m.about))
    print()
    if (re.match('^.*-dev.*$', natlas.__version__)):
        print('* Development version %s overrides disabled modules.' % natlas.__version__)
        print()
    return

def get_mod(modules, mod_name):
    for m in modules:
        if (m.name == mod_name):
            return m
    return None

def does_mod_accept_api(mod):
    if (mod.require_api == None):
        # no minimum version specified
        return 1
    accepted = (LooseVersion(mod.require_api) <= LooseVersion(natlas.__version__))
    if (accepted == 0):
        if (re.match('^.*-dev.*$', natlas.__version__)):
            return 2
        return 0
    return 1

def print_mod_info(modules, mod):
    m = get_mod(modules, mod)
    if (m == None):
        print('Invalid module')
        return
    require_api = 'Not specified'
    status      = 'OK (default)'
    if (m.require_api != None):
        require_api = m.require_api
        accept      = does_mod_accept_api(m)
        if (accept == 0):
            status = 'Disabled (requires newer version of natlas)'
        elif (accept == 2):
            status = 'OK (using development API)'
    print('         Module: %s' % m.name)
    print('        Version: %s' % m.version)
    print('         Author: %s <%s>' % (m.author, m.authoremail))
    print('           File: modules/%s' % m.filename)
    print('Requires natlas: %s' % require_api)
    print('         Status: %s' % status)
    print()

def print_mod_help(modules, mod):
    m = get_mod(modules, mod)
    if (m == None):
        print('Invalid module')
        return

    print('MODULE\n')
    print('    %s v%s' % (m.name, m.version))
    print('    %s <%s>' % (m.author, m.authoremail))
    if (m.about != None):
        print('\nABOUT\n')
        print_indented(m.about)
    if (m.syntax != None):
        print('\nSYNTAX\n')
        if (type(m.syntax) == type([])):
            for s in m.syntax:
                print('    %s %s' % (m.name, s))
        else:
            print('    %s %s' % (m.name, m.syntax))
    if (m.help != None):
        print('\nDETAILS\n')
        print_indented(m.help)
    if (m.example != None):
        print('\nEXAMPLE\n')
        print_indented(m.example, 0)
    print()

def print_mod_syntax(modules, mod):
    m = get_mod(modules, mod)
    if (m == None):
        print('Invalid module')
        return
    if (type(m.syntax) == type([])):
        for s in m.syntax:
            print('%s %s' % (m.name, s))
    else:
        print('%s %s' % (m.name, m.syntax))

def print_indented(str, wrap=1):
    lines = str.lstrip().splitlines()
    for line in lines:
        line = line.lstrip()
        if (line == ''):
            print()
            continue
        if (wrap == 1):
            wlines = [line[i:i+70] for i in range(0, len(line), 70)]
            for wline in wlines:
                print('    ', wline)
        else:
            print('    ', line)

if __name__ == "__main__":
    main(sys.argv[1:])
    
