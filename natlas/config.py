#!/usr/bin/python

'''
        natlas
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
import sys

class natlas_config_diagram:
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

class natlas_discover_acl:
    '''
    Define an ACL entry for the 'discover' config block.
    Defined in the form:
        <action> <type> <str>
    Where
        <action> = permit, deny, leaf, nop
        <type>   = ip, host
        <str>    = string
    '''
    all_actions = [ ';', 'permit', 'deny', 'leaf', 'include' ]
    all_types   = [ ';', 'ip', 'host', 'software', 'platform', 'serial' ]

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

class natlas_config:
    def __init__(self):
        self.host_domains       = []
        self.snmp_creds         = []
        self.discover_acl       = []
        self.diagram            = natlas_config_diagram()

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
                entry = natlas_discover_acl(acl)
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
        fd = open(json_file)
        json_data = fd.read()
        fd.close()
        json_data = json.loads(json_data)
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


    def validate_config(self, filename):
        print('Validating config...')
        json_data = self.__load_json_conf(filename)
        if (json_data == None):
            print('Could not load config.')
            return 0

        ret = 0

        ret += self.__validate_config_snmp(json_data)
        ret += self.__validate_config_domains(json_data)
        ret += self.__validate_config_discover(json_data)
        ret += self.__validate_config_diagram(json_data)
            
        if (ret < 4):
            print('FAILED')
        else:
            print('PASSED')

    def __validate_config_snmp(self, data):
        sys.stdout.write('Checking snmp...')
        obj = None
        try:
            obj = data['snmp']
        except:
            print('does not exist')
            return 0

        if (type(obj) != list):
            print('not a list')
            return 0

        for cred in obj:
            if (type(cred) != dict):
                print('list contains a non-dict (%s)' % type(cred))
                return 0
            try:
                c = cred['community']
                if (type(c) != str):
                    print('community is not a string')
                    return 0
            except KeyError as e:
                print('one or more entries does not include %s' % e)
                return 0
            try:
                c = cred['ver']
                if (type(c) != int):
                    print('version is not an int')
                    return 0
                else:
                    if (c != 2):
                        print('version for \'%s\' is not supported' % cred['community'])
                        return 0
            except KeyError as e:
                print('one or more entries does not include %s' % e)
                return 0
        print('ok')
        return 1

    def __validate_config_domains(self, data):
        sys.stdout.write('Checking domains...')
        obj = None
        try:
            obj = data['domains']
        except:
            print('does not exist')
            return 0
        if (type(obj) != list):
            print('not a list')
            return 0
        for d in obj:
            if (type(d) != str):
                print('domain is not a string')
                return 0
        print('ok')
        return 1

    def __validate_config_discover(self, data):
        sys.stdout.write('Checking discover...')
        obj = None
        try:
            obj = data['discover']
        except:
            print('does not exist')
            return 0
        if (type(obj) != list):
            print('not a list')
            return 0
        for d in obj:
            if (type(d) != str):
                print('ACL is not a string')
                return 0

            ace = d.split(' ')
            if (len(ace) < 3):
                print('ACE not enough params \'%s\'' % d)
                return 0
            if (ace[0] not in natlas_discover_acl.all_actions):
                print('ACE op \'%s\' not valid' % ace[0])
                return 0
            if (ace[1] not in natlas_discover_acl.all_types):
                print('ACE cond \'%s\' not valid' % ace[1])
                return 0

        print('ok')
        return 1

    def __validate_config_diagram(self, data):
        sys.stdout.write('Checking diagram...')
        obj = None
        try:
            obj = data['diagram']
        except:
            print('does not exist')
            return 0
        if (type(obj) != dict):
            print('not a dict')
            return 0

        for nv in obj:
            if (nv not in ['node_text_size',
                            'link_text_size',
                            'title_text_size',
                            'get_stack_members',
                            'get_vss_members',
                            'expand_stackwise',
                            'expand_vss',
                            'expand_lag',
                            'group_vpc']):
                print('invalid value \'%s\'' % nv)
                return 0

        print('ok')
        return 1

