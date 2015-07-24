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

from snmp import *

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


class mnet_node_lo:
	name = None
	ip = None

	def __init__(self, name, ip):
		self.name = name.replace('Loopback', 'lo')
		self.ip = ip


class mnet_node_stack_member:
	num = 0
	role = 0
	pri = 0
	mac = None
	img = None
	serial = None

	def __init__(self):
		self.num = 0
		self.role = 0
		self.pri = 0
		self.mac = None
		self.img = None
		self.serial = None


class mnet_node_stack:
	members = []
	count = 0

	def __init__(self, snmpobj = None, get_details = 0):
		self.members = []
		self.count = 0

		if (snmpobj != None):
			self.get_members(snmpobj, get_details)

	def get_members(self, snmpobj, get_details):
		vbtbl = snmpobj.get_bulk(OID_STACK)
		if (vbtbl == None):
			return None

		if (get_details == 0):
			self.count = 0
			for row in vbtbl:
				for n, v in row:
					if (n.prettyPrint().startswith(OID_STACK_NUM + '.')):
						self.count += 1

			if (self.count == 1):
				self.count = 0
			return				

		serial_vbtbl = snmpobj.get_bulk(OID_3750X_SERIAL)

		for row in vbtbl:
			for n, v in row:
				if (n.prettyPrint().startswith(OID_STACK_NUM + '.')):
					m = mnet_node_stack_member()

					t = n.prettyPrint().split('.')
					idx = t[14]

					m.num  = v
					m.role = snmpobj.cache_lookup(vbtbl, OID_STACK_ROLE + '.' + idx)
					m.pri  = snmpobj.cache_lookup(vbtbl, OID_STACK_PRI + '.' + idx)
					m.mac  = snmpobj.cache_lookup(vbtbl, OID_STACK_MAC + '.' + idx)
					m.img  = snmpobj.cache_lookup(vbtbl, OID_STACK_IMG + '.' + idx)

					m.serial = snmpobj.cache_lookup(serial_vbtbl, OID_3750X_SERIAL + '.' + idx)

					if (m.role == '1'):
						m.role = 'master'
					elif (m.role == '2'):
						m.role = 'member'
					elif (m.role == '3'):
						m.role = 'notMember'
					elif (m.role == '4'):
						m.role = 'standby'

					mac_seg = [m.mac[x:x+4] for x in xrange(2, len(m.mac), 4)]
					m.mac = '.'.join(mac_seg)

					self.members.append(m)

		self.count = len(self.members)
		if (self.count == 1):
			self.count = 0

		return


class mnet_node:
	snmp_cred = None
	crawled = 0
	links = []

	name			= None
	ip				= []
	plat			= None
	ios				= None
	router			= None
	ospf_id			= None
	bgp_las			= None
	hsrp_pri		= None
	hsrp_vip		= None
	vss_enable		= 0
	vss_domain		= None

	svis			= []
	loopbacks		= []
	stack			= None

	# cached MIB trees
	link_type_vbtbl	= None
	lag_vbtbl		= None
	vlan_vbtbl		= None
	ifname_vbtbl	= None
	ifip_vbtbl		= None
	ethif_vbtbl		= None

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
				vss_enable		= 0,
				vss_domain		= None,
				stack			= None
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
		self.vss_enable			= vss_enable
		self.vss_domain			= vss_domain

		self.svis = []
		self.loopbacks = []

		self.stack				= stack
		if (self.stack == None):
			self.stack = mnet_node_stack()

		link_type_vbtbl	= None
		lag_vbtbl		= None
		vlan_vbtbl		= None
		ifname_vbtbl	= None
		ifip_vbtbl		= None
		ethif_vbtbl		= None

	def add_link(self, link):
		self.links.append(link)

