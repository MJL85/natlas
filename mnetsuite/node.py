#!/usr/bin/python

'''
	MNet Suite
	node.py

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

class mnet_node_link:
	node			= None
	link_type		= None
	vlan			= None
	local_port		= None
	remote_port		= None
	local_lag		= None
	remote_lag		= None
	local_if_ip		= None
	remote_if_ip	= None

	def __init__(
				self,
				node,
				link_type		= None,
				vlan			= None,
				local_port		= None,
				remote_port		= None,
				local_lag		= None,
				remote_lag		= None,
				local_if_ip		= None,
				remote_if_ip	= None
			):
		self.node			= node
		self.link_type		= link_type
		self.vlan			= vlan
		self.local_port		= local_port
		self.remote_port	= remote_port
		self.local_lag		= local_lag
		self.remote_lag		= remote_lag
		self.local_if_ip	= local_if_ip
		self.remote_if_ip	= remote_if_ip


class mnet_node_svi:
	vlan = None
	ip = None

	def __init__(self, vlan):
		self.vlan = vlan
		self.ip = []


class mnet_node:
	snmp_cred = None
	crawled = 0
	links = []

	name			= None
	ip				= None
	plat			= None
	ios				= None
	router			= None
	ospf_id			= None
	bgp_las			= None
	hsrp_pri		= None
	hsrp_vip		= None
	stack_count		= 0
	vss_enable		= 0
	vss_domain		= None

	svis			= []

	# cached MIB trees
	link_type_vbtbl	= None
	lag_vbtbl		= None
	vlan_vbtbl		= None
	ifname_vbtbl	= None
	ifip_vbtbl		= None

	def __init__(
				self,
				name			= None,
				ip				= None,
				plat			= None,
				ios				= None,
				router			= None,
				ospf_id			= None,
				bgp_las			= None,
				hsrp_pri		= None,
				hsrp_vip		= None,
				stack_count		= 0,
				vss_enable		= 0,
				vss_domain		= None
			):
		self.snmp_cred			= None
		self.links				= []
		self.crawled			= 0

		self.name				= name
		self.ip					= ip
		self.plat				= plat
		self.ios				= ios
		self.router				= router
		self.ospf_id			= ospf_id
		self.bgp_las			= bgp_las
		self.hsrp_pri			= hsrp_pri
		self.hsrp_vip			= hsrp_vip
		self.stack_count		= stack_count
		self.vss_enable			= vss_enable
		self.vss_domain			= vss_domain

		self.svis = []

	def add_link(self, link):
		self.links.append(link)

