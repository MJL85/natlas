#!/usr/bin/python

'''
        natlas
        output_catalog.py

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

from .config import natlas_config
from .network import natlas_network
from .output import natlas_output
from ._version import __version__


class natlas_output_catalog:

    def __init__(self, network):
        natlas_output.__init__(self)
        self.network = network
        self.config  = network.config

    def generate(self, filename):
        try:
            f = open(filename, 'w')
        except:
            print('Unable to open catalog file "%s"' % filename)
            return

        for n in self.network.nodes:
            # get info that we may not have yet
            n.opts.get_serial = True
            n.opts.get_plat   = True
            n.opts.get_bootf  = True
            n.query_node()

            if (n.stack.count > 0):
                # stackwise
                for smem in n.stack.members:
                    serial = smem.serial or 'NOT CONFIGURED TO POLL'
                    plat   = smem.plat or 'NOT CONFIGURED TO POLL'
                    f.write('"%s","%s","%s","%s","%s","STACK","%s"\n' % (n.name, n.ip[0], plat, n.ios, serial, n.bootfile))
            elif (n.vss.enabled != 0):
                #vss
                for i in range(0, 2):
                    serial = n.vss.members[i].serial
                    plat   = n.vss.members[i].plat
                    ios    = n.vss.members[i].ios
                    f.write('"%s","%s","%s","%s","%s","VSS","%s"\n' % (n.name, n.ip[0], plat, ios, serial, n.bootfile))
            else:
                # stand alone
                f.write('"%s","%s","%s","%s","%s","","%s"\n' % (n.name, n.ip[0], n.plat, n.ios, n.serial, n.bootfile))

        f.close()

