#!/usr/bin/python

'''
        MNet Suite
        config.py

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

import json

class mnet_config_diagram:
    node_text_size      = 8
    link_text_size      = 7
    title_text_size     = 15
    get_stack_members   = False
    get_vss_members     = False
    expand_stackwise    = False
    expand_vss          = False
    expand_lag          = True
    group_vpc           = False
    node_text           = '<font point-size="10"><b>{node.name}</b></font><br />' \
                            '{node.ip}<br />' \
                            '<%if {node.ios}: {node.ios}<br />%>' \
                            '<%if {node.plat}: {node.plat}<br />%>' \
                            '<%if ("{node.serial}"!=None)&({node.vss.enabled}==0)&({node.stack.enabled}==0): {node.serial}<br />%>' \
                            '<%if ({node.stack.enabled}==1)&({config.diagram.expand_stackwise}==1): {stack.serial}<br />%>' \
                            '<%if {node.vss.enabled}&({config.diagram.expand_vss}==1): {vss.serial}<br />%>' \
                            '<%if ({node.vss.enabled}==1)&({config.diagram.expand_vss}==0): VSS {node.vss.domain}<br />%>' \
                            '<%if {node.vss.enabled}&({config.diagram.expand_vss}==0): VSS 0 - {node.vss.members[0].plat} - {node.vss.members[0].serial}<br />VSS 1 - {node.vss.members[1].plat} - {node.vss.members[1].serial}<br />%>' \
                            '<%if {node.bgp_las}: BGP {node.bgp_las}<br />%>' \
                            '<%if {node.ospf_id}: OSPF {node.ospf_id}<br />%>' \
                            '<%if {node.hsrp_pri}: HSRP VIP {node.hsrp_vip}<br />HSRP Pri {node.hsrp_pri}<br />%>' \
                            '<%if {node.stack.enabled}: Stackwise {node.stack.count}<br />%>' \
                            '<%stack SW {stack.num} - {stack.plat} {stack.serial} ({stack.role})<br />%>' \
                            '<%loopback {lo.name} - {lo.ip}<br />%>' \
                            '<%svi VLAN {svi.vlan} - {svi.ip}<br />%>'

class mnet_discover_acl:
    '''
    Define an ACL entry for the 'discover' config block.
    Defined in the form:
        <action> <type> <str>
    Where
        <action> = permit, deny, leaf, nop
        <type>   = ip, host
        <str>    = string
    '''
    all_actions = [ ";", "permit", "deny", "leaf", "include" ]
    all_types   = [ ";", "ip", "host" ]

    def __init__(self, str):
        self.action     = "nop"
        self.type       = "nop"
        self.str        = "nop"

        t = list(filter(None, str.split()))
        if (len(t) < 3):
            raise Exception('Invalid ACL entry: "%s"' % str)

        self.action     = t[0]
        self.type       = t[1]
        self.str        = t[2]

        if (self.action not in self.all_actions):
            raise Exception('Invalid ACL entry: "%s"; %s' % (str, self.action))
        if (self.type not in self.all_types):
            raise Exception('Invalid ACL entry: "%s"; %s' % (str, self.type))

    def __repr__(self):
        return '<%s %s %s>' % (self.action, self.type, self.str)

class mnet_config:
    def __init__(self):
        self.host_domains       = []
        self.snmp_creds         = []
        self.discover_acl       = []
        self.diagram            = mnet_config_diagram()

    def load(self, filename):
        # load config
        json_data = self.__load_json_conf(filename)
        if (json_data == None):
            return 0

        self.host_domains       = json_data['domains']
        self.snmp_creds         = json_data['snmp']

        # parse 'discover' block ACL entries
        for acl in json_data['discover']:
            try:
                entry = mnet_discover_acl(acl)
            except Exception as e:
                print(e)
                return 0

            self.discover_acl.append(entry)

        json_diagram = json_data.get('diagram', None)
        if (json_diagram != None):
            self.diagram.node_text_size     = json_diagram.get('node_text_size', 8)
            self.diagram.link_text_size     = json_diagram.get('link_text_size', 7)
            self.diagram.title_text_size    = json_diagram.get('title_text_size', 15)
            self.diagram.get_stack_members  = json_diagram.get('get_stack_members', False)
            self.diagram.get_vss_members    = json_diagram.get('get_vss_members', False)
            self.diagram.expand_stackwise   = json_diagram.get('expand_stackwise', False)
            self.diagram.expand_vss         = json_diagram.get('expand_vss', False)
            self.diagram.expand_lag         = json_diagram.get('expand_lag', True)
            self.diagram.group_vpc          = json_diagram.get('group_vpc', False)
            self.diagram.node_text          = json_diagram.get('node_text', self.diagram.node_text)

        return 1

    def __load_json_conf(self, json_file):
        json_data = None

        try:
            json_data = json.loads(open(json_file).read())
        except:
            print('Invalid JSON file or file not found.')
            return None

        return json_data

    def generate_new(self):
        return '{\n' \
                        '       "snmp" : [\n' \
                        '               { "community":"private", "ver":2 },\n' \
                        '               { "community":"public", "ver":2 }\n' \
                        '       ],\n' \
                        '       "domains" : [\n' \
                        '               ".company.net",\n' \
                        '               ".company.com"\n' \
                        '       ],\n' \
                        '       "discover" : [\n' \
                        '               "permit ip 10.0.0.0/8",\n' \
                        '               "permit ip 192.168.1.0/24",\n' \
                        '               "permit ip 0.0.0.0/32"\n' \
                        '       ],\n' \
                        '       "diagram" : {\n' \
                        '               "node_text_size" : 10,\n' \
                        '               "link_text_size" : 9,\n' \
                        '               "title_text_size" : 15,\n' \
                        '               "get_stack_members" : 0,\n' \
                        '               "get_vss_members" : 0,\n' \
                        '               "expand_stackwise" : 0,\n' \
                        '               "expand_vss" : 0,\n' \
                        '               "expand_lag" : 1,\n' \
                        '               "group_vpc" : 0\n' \
                        '       }\n' \
                        '}'

