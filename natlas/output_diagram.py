#!/usr/bin/python

'''
        natlas
        output_diagram.py

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

import pydot
import datetime
import os

from .config import natlas_config
from .network import natlas_network
from .output import natlas_output
from .util import *
from ._version import __version__


class natlas_diagram_dot_node:
    def __init__(self):
        self.ntype = 'single'
        self.shape = 'ellipse'
        self.style = 'solid'
        self.peripheries = 1
        self.label = ''
        self.vss_label = ''


class natlas_output_diagram:

    def __init__(self, network):
        natlas_output.__init__(self)
        self.network = network
        self.config  = network.config

    def generate(self, dot_file, title, raw_dot_file=None):
        self.network.reset_discovered()

        title_text_size = self.config.diagram.title_text_size
        credits = '<table border="0">' \
                                '<tr>' \
                                 '<td balign="right">' \
                                  '<font point-size="%i"><b>$title$</b></font><br />' \
                                  '<font point-size="%i">$date$</font><br />' \
                                  '<font point-size="7">' \
                                  'Generated by natlas $ver$<br />' \
                                  'Michael Laforest</font><br />' \
                                 '</td>' \
                                '</tr>' \
                           '</table>' % (title_text_size, title_text_size-2)

        today = datetime.datetime.now()
        today = today.strftime('%Y-%m-%d %H:%M')
        credits = credits.replace('$ver$', __version__)
        credits = credits.replace('$date$', today)
        credits = credits.replace('$title$', title)

        node_text_size = self.config.diagram.node_text_size
        link_text_size = self.config.diagram.link_text_size

        diagram = pydot.Dot(
                        graph_type = 'graph',
                        labelloc = 'b',
                        labeljust = 'r',
                        fontsize = node_text_size,
                        label = '<%s>' % credits
        )
        diagram.set_node_defaults(
                        fontsize = link_text_size
        )
        diagram.set_edge_defaults(
                        fontsize = link_text_size,
                        labeljust = 'l'
        )

        # add all of the nodes and links
        self.__generate(diagram, self.network.root_node)

#       ## Writing the raw DOT file
        if raw_dot_file is not None:
            diagram.write_dot(raw_dot_file)
            print('Created DOT file: %s' % raw_dot_file)

        # expand output string
        files = util.expand_path_pattern(dot_file)
        for f in files:
            # get file extension
            file_name, file_ext = os.path.splitext(f)
            output_func = getattr(diagram, 'write_' + file_ext.lstrip('.'))
            if (output_func == None):
                print('Error: Output type "%s" does not exist.' % file_ext)
            else:
                output_func(f)
                print('Created diagram: %s' % f)


    def __generate(self, diagram, node):
        if (node == None):
            return (0, 0)
        if (node.discovered > 0):
            return (0, 0)
        node.discovered = 1

        dot_node = self.__get_node(diagram, node)

        if (dot_node.ntype == 'single'):
            diagram.add_node(
                            pydot.Node(
                                    name = node.name,
                                    label = '<%s>' % dot_node.label,
                                    style = dot_node.style,
                                    shape = dot_node.shape,
                                    peripheries = dot_node.peripheries
                            )
            )
        elif (dot_node.ntype == 'vss'):
            cluster = pydot.Cluster(
                                        graph_name = node.name,
                                        suppress_disconnected = False,
                                        labelloc = 't',
                                        labeljust = 'c',
                                        fontsize = self.config.diagram.node_text_size,
                                        label = '<<br /><b>VSS %s</b>>' % node.vss.domain
                                    )
            for i in range(0, 2):
                # {vss.} vars
                nlabel = dot_node.label.format(vss=node.vss.members[i])
                cluster.add_node(
                                pydot.Node(
                                        name = '%s[natlasVSS%i]' % (node.name, i+1),
                                        label = '<%s>' % nlabel,
                                        style = dot_node.style,
                                        shape = dot_node.shape,
                                        peripheries = dot_node.peripheries
                                )
                )
            diagram.add_subgraph(cluster)
        elif (dot_node.ntype == 'vpc'):
            cluster = pydot.Cluster(
                                        graph_name = node.name,
                                        suppress_disconnected = False,
                                        labelloc = 't',
                                        labeljust = 'c',
                                        fontsize = self.config.diagram.node_text_size,
                                        label = '<<br /><b>VPC %s</b>>' % node.vpc_domain
                                    )
            cluster.add_node(
                            pydot.Node(
                                    name = node.name,
                                    label = '<%s>' % dot_node.label,
                                    style = dot_node.style,
                                    shape = dot_node.shape,
                                    peripheries = dot_node.peripheries
                            )
                    )
            if (node.vpc_peerlink_node != None):
                node2 = node.vpc_peerlink_node
                node2.discovered = 1
                dot_node2 = self.__get_node(diagram, node2)
                cluster.add_node(
                                pydot.Node(
                                        name = node2.name,
                                        label = '<%s>' % dot_node2.label,
                                        style = dot_node2.style,
                                        shape = dot_node2.shape,
                                        peripheries = dot_node2.peripheries
                                )
                        )
            diagram.add_subgraph(cluster)
        elif (dot_node.ntype == 'stackwise'):
            cluster = pydot.Cluster(
                                        graph_name = node.name,
                                        suppress_disconnected = False,
                                        labelloc = 't',
                                        labeljust = 'c',
                                        fontsize = self.config.diagram.node_text_size,
                                        label = '<<br /><b>Stackwise</b>>'
                                    )
            for i in range(0, node.stack.count):
                # {stack.} vars
                if (len(node.stack.members) == 0):
                    nlabel = dot_node.label
                else:
                    nlabel = dot_node.label.format(stack=node.stack.members[i])
                cluster.add_node(
                                pydot.Node(
                                        name = '%s[natlasSW%i]' % (node.name, i+1),
                                        label = '<%s>' % nlabel,
                                        style = dot_node.style,
                                        shape = dot_node.shape,
                                        peripheries = dot_node.peripheries
                                )
                )
            diagram.add_subgraph(cluster)

        lags = []
        for link in node.links:
            self.__generate(diagram, link.node)

            # determine if this link should be broken out or not
            expand_lag = 0
            if (self.config.diagram.expand_lag == 1):
                expand_lag = 1
            elif (link.local_lag == 'UNKNOWN'):
                expand_lag = 1
            elif (self.__does_lag_span_devs(link.local_lag, node.links) > 1):
                # a LAG could span different devices, eg Nexus.
                # in this case we should always break it out, otherwise we could
                # get an unlinked node in the diagram.
                expand_lag = 1

            if (expand_lag == 1):
                self.__create_link(diagram, node, link, 0)
            else:
                found = 0
                for lag in lags:
                    if (link.local_lag == lag):
                        found = 1
                        break
                if (found == 0):
                    lags.append(link.local_lag)
                    self.__create_link(diagram, node, link, 1)


    def __get_node(self, diagram, node):
        dot_node = natlas_diagram_dot_node()
        dot_node.ntype = 'single'
        dot_node.shape = 'ellipse'
        dot_node.style = 'solid'
        dot_node.peripheries = 1
        dot_node.label = ''

        # get the node text
        dot_node.label = self.__get_node_text(diagram, node, self.config.diagram.node_text)

        # set the node properties
        if (node.vss.enabled == 1):
            if (self.config.diagram.expand_vss == 1):
                dot_node.ntype = 'vss'
            else:
                # group VSS into one diagram node
                dot_node.peripheries = 2

        if (node.stack.count > 0):
            if (self.config.diagram.expand_stackwise == 1):
                dot_node.ntype = 'stackwise'
            else:
                # group Stackwise into one diagram node
                dot_node.peripheries = node.stack.count

        if (node.vpc_domain != None):
            if (self.config.diagram.group_vpc == 1):
                dot_node.ntype = 'vpc'

        if (node.router == 1):
            dot_node.shape = 'diamond'

        return dot_node


    def __create_link(self, diagram, node, link, draw_as_lag):
        link_color = 'black'
        link_style = 'solid'
        link_label = ''

        if ((link.local_port == node.vpc_peerlink_if) | (link.local_lag == node.vpc_peerlink_if)):
            link_label += 'VPC '

        if (draw_as_lag):
            link_label += 'LAG'
            members = 0
            for l in node.links:
                if (l.local_lag == link.local_lag):
                    members += 1
            link_label += '\n%i Members' % members
        else:
            link_label += 'P:%s\nC:%s' % (link.local_port, link.remote_port)

        is_lag = 1 if (link.local_lag != 'UNKNOWN') else 0

        if (draw_as_lag == 0):
            # LAG as member
            if (is_lag):
                local_lag_ip = ''
                remote_lag_ip = ''
                if (len(link.local_lag_ips)):
                    local_lag_ip = ' - %s' % link.local_lag_ips[0]
                if (len(link.remote_lag_ips)):
                    remote_lag_ip = ' - %s' % link.remote_lag_ips[0]

                link_label += '\nLAG Member'

                if ((local_lag_ip == '') & (remote_lag_ip == '')):
                    link_label += '\nP:%s | C:%s' % (link.local_lag, link.remote_lag)
                else:
                    link_label += '\nP:%s%s' % (link.local_lag, local_lag_ip)
                    link_label += '\nC:%s%s' % (link.remote_lag, remote_lag_ip)

            # IP Addresses
            if ((link.local_if_ip != 'UNKNOWN') & (link.local_if_ip != None)):
                link_label += '\nP:%s' % link.local_if_ip
            if ((link.remote_if_ip != 'UNKNOWN') & (link.remote_if_ip != None)):
                link_label += '\nC:%s' % link.remote_if_ip
        else:
            # LAG as grouping
            for l in node.links:
                if (l.local_lag == link.local_lag):
                    link_label += '\nP:%s | C:%s' % (l.local_port, l.remote_port)

            local_lag_ip = ''
            remote_lag_ip = ''

            if (len(link.local_lag_ips)):
                local_lag_ip = ' - %s' % link.local_lag_ips[0]
            if (len(link.remote_lag_ips)):
                remote_lag_ip = ' - %s' % link.remote_lag_ips[0]

            if ((local_lag_ip == '') & (remote_lag_ip == '')):
                link_label += '\nP:%s | C:%s' % (link.local_lag, link.remote_lag)
            else:
                link_label += '\nP:%s%s' % (link.local_lag, local_lag_ip)
                link_label += '\nC:%s%s' % (link.remote_lag, remote_lag_ip)


        if (link.link_type == '1'):
            # Trunk = Bold/Blue
            link_color = 'blue'
            link_style = 'bold'

            if ((link.local_native_vlan == link.remote_native_vlan) | (link.remote_native_vlan == None)):
                link_label += '\nNative %s' % link.local_native_vlan
            else:
                link_label += '\nNative P:%s C:%s' % (link.local_native_vlan, link.remote_native_vlan)

            if (link.local_allowed_vlans == link.remote_allowed_vlans):
                link_label += '\nAllowed %s' % link.local_allowed_vlans
            else:
                link_label += '\nAllowed P:%s' % link.local_allowed_vlans
                if (link.remote_allowed_vlans != None):
                    link_label += '\nAllowed C:%s' % link.remote_allowed_vlans
        elif (link.link_type is None):
            # Routed = Bold/Red
            link_color = 'red'
            link_style = 'bold'
        else:
            # Switched access, include VLAN ID in label
            if (link.vlan != None):
                link_label += '\nVLAN %s' % link.vlan

        edge_src = node.name
        edge_dst = link.node.name
        lmod = util.get_module_from_interf(link.local_port)
        rmod = util.get_module_from_interf(link.remote_port)

        if (self.config.diagram.expand_vss == 1):
            if (node.vss.enabled == 1):
                edge_src = '%s[natlasVSS%s]' % (node.name, lmod)
            if (link.node.vss.enabled == 1):
                edge_dst = '%s[natlasVSS%s]' % (link.node.name, rmod)

        if (self.config.diagram.expand_stackwise == 1):
            if (node.stack.count > 0):
                edge_src = '%s[natlasSW%s]' % (node.name, lmod)
            if (link.node.stack.count > 0):
                edge_dst = '%s[natlasSW%s]' % (link.node.name, rmod)

        edge = pydot.Edge(
                                edge_src, edge_dst,
                                dir = 'forward',
                                label = link_label,
                                color = link_color,
                                style = link_style
                        )

        diagram.add_edge(edge)

    
    def __does_lag_span_devs(self, lag_name, links):
        if (lag_name == None):
            return 0

        devs = []
        for link in links:
            if (link.local_lag == lag_name):
                if (link.node.name not in devs):
                    devs.append(link.node.name)

        return len(devs)


    def __eval_if_block(self, if_cond, node):
        # evaluate condition
        if_cond_eval = if_cond.format(node=node, config=self.config).strip()
        try:
            if eval(if_cond_eval):
                return 1
        except:
            if ((if_cond_eval != '0') & (if_cond_eval != 'None') & (if_cond_eval != '')):
                return 1
            else:
                return 0

        return 0


    def __get_node_text(self, diagram, node, fmt):
        '''
        Generate the node text given the format string 'fmt'
        '''
        fmt_proc = fmt

        # IF blocks
        while (1):
            if_block = re.search('<%if ([^%]*): ([^%]*)%>', fmt_proc)
            if (if_block == None):
                break

            # evaluate condition
            if_cond = if_block[1]
            if_val  = if_block[2]
            if (self.__eval_if_block(if_cond, node) == 0):
                if_val = ''
            fmt_proc = fmt_proc[:if_block.span()[0]] + if_val + fmt_proc[if_block.span()[1]:]

        # {node.ip} = best IP
        ip = node.get_ipaddr()
        fmt_proc = fmt_proc.replace('{node.ip}', ip)

        # stackwise
        stack_block = re.search('<%stack ([^%]*)%>', fmt_proc)
        if (stack_block != None):
            if (node.stack.count == 0):
                # no stackwise, remove this
                fmt_proc = fmt_proc[:stack_block.span()[0]] + fmt_proc[stack_block.span()[1]:]
            else:
                val = ''
                if (self.config.diagram.expand_stackwise == 0):
                    if (self.config.diagram.get_stack_members):
                        for smem in node.stack.members:
                            nval = stack_block[1]
                            nval = nval.replace('{stack.num}',    str(smem.num))
                            nval = nval.replace('{stack.plat}',   smem.plat)
                            nval = nval.replace('{stack.serial}', smem.serial)
                            nval = nval.replace('{stack.role}',   smem.role)
                            val += nval
                fmt_proc = fmt_proc[:stack_block.span()[0]] + val + fmt_proc[stack_block.span()[1]:]
        
        # loopbacks
        loopback_block = re.search('<%loopback ([^%]*)%>', fmt_proc)
        if (loopback_block != None):
            val = ''
            for lo in node.loopbacks:
                for lo_ip in lo.ips:
                    nval = loopback_block[1]
                    nval = nval.replace('{lo.name}', lo.name)
                    nval = nval.replace('{lo.ip}', lo_ip)
                    val += nval
            fmt_proc = fmt_proc[:loopback_block.span()[0]] + val + fmt_proc[loopback_block.span()[1]:]

        # SVIs
        svi_block = re.search('<%svi ([^%]*)%>', fmt_proc)
        if (svi_block != None):
            val = ''
            for svi in node.svis:
                for svi_ip in svi.ip:
                    nval = svi_block[1]
                    nval = nval.replace('{svi.vlan}', svi.vlan)
                    nval = nval.replace('{svi.ip}', svi_ip)
                    val += nval
            fmt_proc = fmt_proc[:svi_block.span()[0]] + val + fmt_proc[svi_block.span()[1]:]

        # replace {stack.} with magic
        fmt_proc = re.sub('{stack\.(([a-zA-Z])*)}', '$stack2354$\g<1>$stack2354$', fmt_proc)
        fmt_proc = re.sub('{vss\.(([a-zA-Z])*)}', '$vss2354$\g<1>$vss2354$', fmt_proc)

        # {node.} variables
        fmt_proc = fmt_proc.format(node=node)
        
        # replace magics
        fmt_proc = re.sub('\$stack2354\$(([a-zA-Z])*)\$stack2354\$', '{stack.\g<1>}', fmt_proc)
        fmt_proc = re.sub('\$vss2354\$(([a-zA-Z])*)\$vss2354\$', '{vss.\g<1>}', fmt_proc)

        return fmt_proc

