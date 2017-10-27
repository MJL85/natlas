#!/usr/bin/python

'''
	MNet Suite
	config.py

	Michael Laforest
	mjlaforest@gmail.com

	Copyright (C) 2015 Michael Laforest

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

class mnet_config_graph:
	node_text_size = 8
	link_text_size = 7
	title_text_size = 15 
	include_svi	= False
	include_lo = False
	include_serials = False
	get_stack_members = False
	get_vss_members = False
	expand_stackwise = False
	expand_vss = False
	expand_lag = True

class mnet_config:
	host_domains	= []
	snmp_cred	= []
	exclude_subnets	= []
	allowed_subnets	= []
        exclude_hosts   = []
	graph = None

	def __init__(self):
		self.host_domains		= []
		self.snmp_creds			= []
		self.exclude_subnets	= []
		self.allowed_subnets	= []
		self.graph				= mnet_config_graph()

	def load(self, filename):
		# load config
		json_data = self._load_json_conf(filename)
		if (json_data == None):
			return 0

		self.host_domains	= json_data['domains']
		self.snmp_creds		= json_data['snmp']
		self.exclude_subnets	= json_data['exclude']
		self.allowed_subnets	= json_data['subnets']
		self.exclude_hosts      = json_data['exclude_hosts']

		json_graph = json_data.get('graph', None)
		if (json_graph != None):
			self.graph.node_text_size     = json_graph.get('node_text_size', 8)
			self.graph.link_text_size     = json_graph.get('link_text_size', 7)
			self.graph.title_text_size    = json_graph.get('title_text_size', 15)
			self.graph.include_svi        = json_graph.get('include_svi', False)
			self.graph.include_lo         = json_graph.get('include_lo', False)
			self.graph.include_serials    = json_graph.get('include_serials', False)
			self.graph.get_stack_members  = json_graph.get('get_stack_members', False)
			self.graph.get_vss_members    = json_graph.get('get_vss_members', False)
			self.graph.expand_stackwise   = json_graph.get('expand_stackwise', False)
			self.graph.expand_vss         = json_graph.get('expand_vss', False)
			self.graph.expand_lag         = json_graph.get('expand_lag', True)

		return 1

	def _load_json_conf(self, json_file):
		json_data = None

		try:
			json_data = json.loads(open(json_file).read())

		except:
			print('Invalid JSON file or file not found.')
			return None

		return json_data

	def generate_new(self):
		return '{\n' \
				'	"snmp" : [\n' \
				'		{ "community":"private",	"ver":2 },\n' \
				'		{ "community":"public",		"ver":2 }\n' \
				'	],\n' \
				'	"domains" : [\n' \
				'		".company.net",\n' \
				'		".company.com"\n' \
				'	],\n' \
				'	"exclude" : [\n' \
				'		"192.168.0.0/16"\n' \
				'	],\n' \
				'	"subnets" : [\n' \
				'		"10.0.0.0/8",\n' \
				'		"0.0.0.0/32"\n' \
				'	],\n' \
                                '       "exclude_hosts": [\n' \
                                '       ],\n' \
				'	"graph" : {\n' \
				'		"node_text_size" : 10,\n' \
				'		"link_text_size" : 9,\n' \
				'		"title_text_size" : 15,\n' \
				'		"include_svi" : 0,\n' \
				'		"include_lo" : 0,\n' \
				'		"include_serials" : 0,\n' \
				'		"get_stack_members" : 0,\n' \
				'		"get_vss_members" : 0,\n' \
				'		"expand_stackwise" : 0,\n' \
				'		"expand_vss" : 0,\n' \
				'		"expand_lag" : 1\n' \
				'	}\n' \
				'}'

