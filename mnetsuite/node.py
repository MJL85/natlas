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
from util import *
import sys

class mnet_node_link:
	node			= None
	link_type		= None
	vlan			= None
	local_native_vlan		= None
	local_allowed_vlans		= None
	remote_native_vlan		= None
	remote_allowed_vlans	= None
	local_port		= None
	remote_port		= None
	local_lag		= None
	remote_lag		= None
	local_if_ip		= None
	remote_if_ip	= None
	remote_platform = None
	remote_ios		= None

	def __init__(
				self,
				node					= None,
				link_type				= None,
				vlan					= None,
				local_allowed_vlans		= None,
				local_native_vlan		= None,
				remote_allowed_vlans	= None,
				remote_native_vlan		= None,
				local_port				= None,
				remote_port				= None,
				local_lag				= None,
				remote_lag				= None,
				local_if_ip				= None,
				remote_if_ip			= None,
				remote_platform			= None,
				remote_ios				= None
			):
		self.node					= node
		self.link_type				= link_type
		self.vlan					= vlan
		self.local_native_vlan		= local_native_vlan
		self.local_allowed_vlans	= local_allowed_vlans
		self.remote_native_vlan		= remote_native_vlan
		self.remote_allowed_vlans	= remote_allowed_vlans
		self.local_port				= local_port
		self.remote_port			= remote_port
		self.local_lag				= local_lag
		self.remote_lag				= remote_lag
		self.local_if_ip			= local_if_ip
		self.remote_if_ip			= remote_if_ip
		self.remote_platform		= remote_platform
		self.remote_ios				= remote_ios


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
	plat = None

	def __init__(self):
		self.num = 0
		self.role = 0
		self.pri = 0
		self.mac = None
		self.img = None
		self.serial = None
		self.plat = None


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

		serial_vbtbl = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
		platf_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)

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

					m.serial = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + idx)
					m.plat   = snmpobj.cache_lookup(platf_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + idx)

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


class mnet_node_vss_member:
	ios = None
	serial = None
	plat = None

	def __init__(self):
		self.ios = None
		self.serial = None
		self.plat = None


class mnet_node_vss:
	members = []
	enabled = 0
	domain = None

	def __init__(self, snmpobj = None, get_details = 0):
		self.members = [ mnet_node_vss_member(), mnet_node_vss_member() ]
		enabled = 0
		domain = None

		if (snmpobj != None):
			self.get_members(snmpobj, get_details)

	def get_members(self, snmpobj, get_details):
		self.enabled = 1 if (snmpobj.get_val(OID_VSS_MODE) == '2') else 0
		if (self.enabled == 0):
			return

		self.domain = snmpobj.get_val(OID_VSS_DOMAIN)

		if (get_details == 0):
			return

		class_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_CLASS)
		ios_vbtbl    = snmpobj.get_bulk(OID_ENTPHYENTRY_SOFTWARE)
		serial_vbtbl = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
		plat_vbtbl   = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)

		module = 0

		for row in class_vbtbl:
			for n, v in row:
				if (v == 9):
					t = n.prettyPrint().split('.')
					modidx = t[12]
					if (module > 1):
						print('[E] More than 2 modules found for VSS device! Skipping after the second...')
						return

					self.members[module].ios    = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + modidx)
					self.members[module].serial = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + modidx)
					self.members[module].plat   = snmpobj.cache_lookup(plat_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + modidx)
					module += 1


class mnet_node:

	class _node_opts:
		get_name = False
		get_ip = False
		get_plat = False
		get_ios = False
		get_router = False
		get_ospf_id = False
		get_bgp_las = False
		get_hsrp_pri = False
		get_hsrp_vip = False
		get_serial = False
		get_stack = False
		get_stack_details = False
		get_vss = False
		get_vss_details = False
		get_svi = False
		get_lo = False
		get_bootf = False
		get_chassis_info = False
	
		def __init__(self):
			self.reset()

		def reset(self):
			self.get_name = False
			self.get_ip = False
			self.get_plat = False
			self.get_ios = False
			self.get_router = False
			self.get_ospf_id = False
			self.get_bgp_las = False
			self.get_hsrp_pri = False
			self.get_hsrp_vip = False
			self.get_serial = False
			self.get_stack = False
			self.get_stack_details = False
			self.get_vss = False
			self.get_vss_details = False
			self.get_svi = False
			self.get_lo = False
			self.get_bootf = False
			self.get_chassis_info = False


	opts = None
	snmpobj			= mnet_snmp()
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
	serial			= None
	bootfile		= None

	svis			= []
	loopbacks		= []
	stack			= None
	vss				= None

	# cached MIB trees
	link_type_vbtbl	= None
	lag_vbtbl		= None
	vlan_vbtbl		= None
	ifname_vbtbl	= None
	ifip_vbtbl		= None
	ethif_vbtbl		= None
	trk_allowed_vbtbl = None
	trk_native_vbtbl  = None

	def __init__(self):
		self.opts				= mnet_node._node_opts()
		self.snmpobj			= mnet_snmp()

		self.links				= []
		self.crawled			= 0

		self.name				= None
		self.ip					= None
		self.plat				= None
		self.ios				= None
		self.router				= None
		self.ospf_id			= None
		self.bgp_las			= None
		self.hsrp_pri			= None
		self.hsrp_vip			= None
		self.serial				= None
		self.bootfile			= None

		self.svis = []
		self.loopbacks = []

		self.stack = mnet_node_stack()
		self.vss = mnet_node_vss()

		link_type_vbtbl	= None
		lag_vbtbl		= None
		vlan_vbtbl		= None
		ifname_vbtbl	= None
		ifip_vbtbl		= None
		ethif_vbtbl		= None
		trk_allowed_vbtbl = None
		trk_native_vbtbl  = None

	def add_link(self, link):
		self.links.append(link)


	# find valid credentials for this node
	def try_snmp_creds(self, snmp_creds):
		if (self.snmpobj.success == 0):
			self.snmpobj._ip = self.ip[0]
			if (self.snmpobj.get_cred(snmp_creds) == 0):
				return 0
		return 1


	# Query this node.
	# Set .opts and .snmp_creds before calling.
	def query_node(self):
		if (self.snmpobj.ver == 0):
			# call try_snmp_creds() first or it failed to find good creds
			return 0

		snmpobj = self.snmpobj

		# router
		if (self.opts.get_router == True):
			if (self.router == None):
				self.router = 1 if (snmpobj.get_val(OID_IP_ROUTING) == '1') else 0

			if (self.router == 1):
				# OSPF
				if (self.opts.get_ospf_id == True):
					self.ospf_id = snmpobj.get_val(OID_OSPF)
					if (self.ospf_id != None):
						self.ospf_id = snmpobj.get_val(OID_OSPF_ID)

				# BGP
				if (self.opts.get_bgp_las == True):
					self.bgp_las = snmpobj.get_val(OID_BGP_LAS)
					if (self.bgp_las == '0'):	# 4500x is reporting 0 with disabled
						self.bgp_las = None

				# HSRP
				if (self.opts.get_hsrp_pri == True):
					self.hsrp_pri = snmpobj.get_val(OID_HSRP_PRI)
					if (self.hsrp_pri != None):
						self.hsrp_vip = snmpobj.get_val(OID_HSRP_VIP)

		# stack
		if (self.opts.get_stack):
			self.stack = mnet_node_stack(snmpobj, self.opts.get_stack_details)

		# vss
		if (self.opts.get_vss):
			self.vss = mnet_node_vss(snmpobj, self.opts.get_vss_details)
		
		# serial
		if ((self.opts.get_serial == 1) & (self.stack.count == 0) & (self.vss.enabled == 0)):
			self.serial = snmpobj.get_val(OID_SYS_SERIAL)

		# SVI
		if (self.opts.get_svi == True):
			self.svi_vbtbl		= snmpobj.get_bulk(OID_SVI_VLANIF)
			self.ifip_vbtbl		= snmpobj.get_bulk(OID_IF_IP)

			for row in self.svi_vbtbl:
				for n, v in row:
					vlan = n.prettyPrint().split('.')[14]
					svi = mnet_node_svi(vlan)
					for ifrow in self.ifip_vbtbl:
						for ifn, ifv in ifrow:
							if (ifn.prettyPrint().startswith(OID_IF_IP_ADDR)):
								if (v == ifv):
									t = ifn.prettyPrint().split('.')
									svi_ip = ".".join(t[10:])
									mask = snmpobj.cache_lookup(self.ifip_vbtbl, OID_IF_IP_NETM + svi_ip)
									nbits = get_net_bits_from_mask(mask)
									svi_ip = '%s/%i' % (svi_ip, nbits)
									svi.ip.append(svi_ip)

					self.svis.append(svi)

		# loopback
		if (self.opts.get_lo == True):
			self.ethif_vbtbl = snmpobj.get_bulk(OID_ETH_IF)

			if (self.ifip_vbtbl == None):
				self.ifip_vbtbl = snmpobj.get_bulk(OID_IF_IP)
			
			for row in self.ethif_vbtbl:
				for n, v in row:
					if (n.prettyPrint().startswith(OID_ETH_IF_TYPE) & (v == 24)):
						ifidx = n.prettyPrint().split('.')[10]
						lo_name = snmpobj.cache_lookup(self.ethif_vbtbl, OID_ETH_IF_DESC + '.' + ifidx)
						lo_ip = get_ip_from_ifidx(snmpobj, self.ifip_vbtbl, ifidx)
						lo = mnet_node_lo(lo_name, lo_ip) 
						self.loopbacks.append(lo)

		# bootfile
		if (self.opts.get_bootf):
			self.bootfile = snmpobj.get_val(OID_SYS_BOOT)

		# chassis info (serial, IOS, platform)
		if (self.opts.get_chassis_info):
			self._get_chassis_info()

		# reset the get options
		self.opts.reset()
		return 1


	#
	# Get a list of neighbor IP addresses.
	# Pulled from CDP neighbor table.
	#
	def get_neighbors(self):
		children = []
		snmpobj = self.snmpobj
		
		# get list of CDP neighbors
		self.cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
		if (self.cdp_vbtbl == None):
			return None

		# cache some common MIB trees
		self.link_type_vbtbl	= snmpobj.get_bulk(OID_TRUNK_VTP)
		self.lag_vbtbl			= snmpobj.get_bulk(OID_LAG_LACP)
		self.vlan_vbtbl			= snmpobj.get_bulk(OID_IF_VLAN)
		self.ifname_vbtbl		= snmpobj.get_bulk(OID_IFNAME)
		self.trk_allowed_vbtbl  = snmpobj.get_bulk(OID_TRUNK_ALLOW)
		self.trk_native_vbtbl   = snmpobj.get_bulk(OID_TRUNK_NATIVE)
		
		if (self.ifip_vbtbl == None):
			self.ifip_vbtbl		= snmpobj.get_bulk(OID_IF_IP)

		for row in self.cdp_vbtbl:
			for name, val in row:
				# process only if this row is a CDP_DEVID
				if (name.prettyPrint().startswith(OID_CDP_DEVID) == 0):
					continue

				t = name.prettyPrint().split('.')
				ifidx = t[14]

				# get remote IP
				rip = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + t[15])
				rip = convert_ip_int_str(rip)

				# collect CDP info into dict
				n = {}
				n['ip'] = rip
				n['name'] = val.prettyPrint()
				n['ifidx'] = ifidx
				n['ifidx2'] = t[15]

				children.append(n)

		return children


	def get_node_link_info(self, ifidx, ifidx2):
		snmpobj = self.snmpobj

		# get local port
		lport = get_ifname(snmpobj, self.ifname_vbtbl, ifidx)

		# get remote port
		rport = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_DEVPORT + '.' + ifidx + '.' + ifidx2)
		rport = shorten_port_name(rport)

		# get remote platform
		rplat = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_DEVPLAT + '.' + ifidx + '.' + ifidx2)

		# get IOS version
		rios = snmpobj.cache_lookup(self.cdp_vbtbl, OID_CDP_IOS + '.' + ifidx + '.' + ifidx2)
		if (rios != None):
			try:
				rios = binascii.unhexlify(rios[2:])
			except:
				pass
			rios_s = re.search('Version:? ([^ ,]*)', rios)
			if (rios_s):
				rios = rios_s.group(1)

		# get link type (trunk ?)
		link_type = snmpobj.cache_lookup(self.link_type_vbtbl, OID_TRUNK_VTP + '.' + ifidx)

		native_vlan = None
		allowed_vlans = 'All'
		if (link_type == '1'):
			native_vlan = snmpobj.cache_lookup(self.trk_native_vbtbl, OID_TRUNK_NATIVE + '.' + ifidx)

			allowed_vlans = snmpobj.cache_lookup(self.trk_allowed_vbtbl, OID_TRUNK_ALLOW + '.' + ifidx)
			allowed_vlans = self._parse_allowed_vlans(allowed_vlans)

		# get LAG membership
		lag = snmpobj.cache_lookup(self.lag_vbtbl, OID_LAG_LACP + '.' + ifidx)
		lag = get_ifname(snmpobj, self.ifname_vbtbl, lag)

		# get VLAN info
		vlan = snmpobj.cache_lookup(self.vlan_vbtbl, OID_IF_VLAN + '.' + ifidx)

		# get IP address
		lifip = get_ip_from_ifidx(snmpobj, self.ifip_vbtbl, ifidx)

		link = mnet_node_link(link_type			= link_type,
							vlan				= vlan,
							local_native_vlan	= native_vlan,
							local_allowed_vlans = allowed_vlans,
							local_port			= lport,
							remote_port			= rport,
							local_lag			= lag,
							remote_lag			= None,
							local_if_ip			= lifip,
							remote_if_ip		= None,
							remote_platform		= rplat,
							remote_ios			= rios)
		return link


	def _parse_allowed_vlans(self, allowed_vlans):
		if (allowed_vlans.startswith('0x') == False):
			return 'All'
	
		ret = ''
		group = 0
		op = 0

		for i in range(2, len(allowed_vlans)):
			v = int(allowed_vlans[i], 16)
			for b in range(0, 4):
				a = v & (0x1 << (3 - b))
				vlan = ((i-2)*4)+b

				if (a):
					if (op == 1):
						group += 1
					else:
						if (len(ret)):
							if (group > 1):
								ret += '-'
								ret += str(vlan - 1) if vlan else '1'
							else:
								ret += ',%i' % vlan
						else:
							ret += str(vlan)
						group = 0
						op = 1
				else:
					if (op == 0):
						group += 1
					else:
						if (len(ret)):
							if (group > 1):
								ret += '-%i' % (vlan - 1)
						group = 0
						op = 0

		if (op):
			if (ret == '1'):
				return 'All'
			if (group):
				ret += '-1001'
			else:
				ret += ',1001'

		return ret if len(ret) else 'All'


	def _get_chassis_info(self):
		# Get:
		#    Serial number
		#    Platform
		#    IOS
		# Slow but reliable method by using SNMP directly.
		# Usually we will get this via CDP.
		snmpobj = self.snmpobj

		if ((self.stack.count > 0) | (self.vss.enabled == 1)):
			# Use opts.get_stack_details
			# or  opts.get_vss_details
			# for this.
			return

		class_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_CLASS)
		serial_vbtbl = snmpobj.get_bulk(OID_ENTPHYENTRY_SERIAL)
		platf_vbtbl  = snmpobj.get_bulk(OID_ENTPHYENTRY_PLAT)
		ios_vbtbl    = snmpobj.get_bulk(OID_ENTPHYENTRY_SOFTWARE)

		if (class_vbtbl == None):
			return

		for row in class_vbtbl:
			for n, v in row:
				if (v != ENTPHYCLASS_CHASSIS):
					continue

				t = n.prettyPrint().split('.')
				idx = t[12]

				self.serial = snmpobj.cache_lookup(serial_vbtbl, OID_ENTPHYENTRY_SERIAL + '.' + idx)
				self.plat   = snmpobj.cache_lookup(platf_vbtbl, OID_ENTPHYENTRY_PLAT + '.' + idx)
				self.ios    = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + idx)

		# modular switches might have IOS on a module rather than chassis
		if (self.ios == ''):
			for row in class_vbtbl:
				for n, v in row:
					if (v != ENTPHYCLASS_MODULE):
						continue

					t = n.prettyPrint().split('.')
					idx = t[12]

					self.ios = snmpobj.cache_lookup(ios_vbtbl, OID_ENTPHYENTRY_SOFTWARE + '.' + idx)
					if (self.ios != ''):
						break

				if (self.ios != ''):
					break
		return


	def get_system_name(self, domains):
		return shorten_host_name(self.snmpobj.get_val(OID_SYSNAME), domains)

