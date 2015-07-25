#!/usr/bin/python

'''
	MNet Suite
	graph.py

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

import sys
import getopt
import pydot
import datetime
import os
import binascii

from snmp import *
from config import mnet_config
from util import *
from node import *
from _version import __version__


class mnet_graph_dot_node:
	ntype = None
	shape = None
	style = None
	peripheries = 0
	label = None

	def __init__(self):
		self.ntype = 'single'
		self.shape = 'ellipse'
		self.style = 'solid'
		self.peripheries = 1
		self.label = ''
		self.vss_label = ''


class mnet_graph:
	root_node = None

	nodes = []
	max_depth = 0
	config = None

	def __init__(self):
		self.config = mnet_config()

	def load_config(self, config_file):
		if (config_file):
			self.config.load(config_file)

	def set_max_depth(self, depth):
		self.max_depth = depth


	def _reset_crawled(self):
		for n in self.nodes:
			n.crawled = 0


	def crawl(self, ip):
		# pull info for this node
		node = self._get_node(ip, 0)
		if (node != None):
			self._crawl_node(node, 0)
		
		self.root_node = node
		return


	def _get_node(self, ip, depth):
		# vmware ESX reports the IP as 0.0.0.0
		# return a minimal node since we don't have
		# a real IP.
		if (ip == '0.0.0.0'):
			d = mnet_node(name = 'UNKNOWN', ip = [ip])
			self.nodes.append(d)
			return d

		# see if we know about this node by its IP first.
		# this would save us an SNMP query for the hostname.
		for ex in self.nodes:
			for exip in ex.ip:
				if (exip == ip):
					return ex

		snmpobj = mnet_snmp(ip)

		# find valid credentials for this node
		if (snmpobj.get_cred(self.config.snmp_creds) == 0):
			sys.stdout.write('+')
			for i in range(0, depth):
				sys.stdout.write('.')
			print('UNKNOWN (%s)            << UNABLE TO CONNECT WITH SNMP' % ip)
			d = mnet_node(name = 'UNKNOWN',	ip = [ip])
			self.nodes.append(d)
			return d

		system_name = shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

		# verify this node isn't already in our visited
		# list by checking for its hostname
		for ex in self.nodes:
			if (ex.name == system_name):
				for exip in ex.ip:
					if (exip == ip):
						return ex
				ex.ip.append(ip)
				return ex

		# print some info to stdout
		sys.stdout.write('+')
		for i in range(0, depth):
			sys.stdout.write('.')
		print('%s (%s)' % (system_name, ip))

		# collect general information about this node
		router = 1 if (snmpobj.get_val(OID_IP_ROUTING) == '1') else 0
		ospf = None
		bgp = None
		hsrp_pri = None
		hsrp_vip = None

		if (router == 1):
			ospf = snmpobj.get_val(OID_OSPF)
			if (ospf != None):
				ospf = snmpobj.get_val(OID_OSPF_ID)

			bgp = snmpobj.get_val(OID_BGP_LAS)
			if (bgp == '0'):	# 4500x is reporting 0 with disabled
				bgp = None

			hsrp_pri = snmpobj.get_val(OID_HSRP_PRI)
			if (hsrp_pri != None):
				hsrp_vip = snmpobj.get_val(OID_HSRP_VIP)
		
		# get stack and vss info
		stack = mnet_node_stack(snmpobj, self.config.graph.get_stack_members)
		vss = mnet_node_vss(snmpobj, self.config.graph.get_vss_members)

		serial = None
		if ((self.config.graph.include_serials == 1) & (stack.count == 0) & (vss.enabled == 0)):
			serial = snmpobj.get_val(OID_SYS_SERIAL)

		# save this node
		d = mnet_node(
				name			= system_name,
				ip				= [ip],
				plat			= None,
				router			= router,
				ospf_id			= ospf or None,
				bgp_las			= bgp or None,
				hsrp_pri		= hsrp_pri or None,
				hsrp_vip		= hsrp_vip or None,
				serial			= serial,
				vss				= vss,
				stack			= stack
			)
		d.snmp_cred = snmpobj._cred
		self.nodes.append(d)

		# Pull SVI info if needed
		if (self.config.graph.include_svi == True):
			d.svi_vbtbl			= snmpobj.get_bulk(OID_SVI_VLANIF)
			d.ifip_vbtbl		= snmpobj.get_bulk(OID_IF_IP)

			for row in d.svi_vbtbl:
				for n, v in row:
					vlan = n.prettyPrint().split('.')[14]
					svi = mnet_node_svi(vlan)
					for ifrow in d.ifip_vbtbl:
						for ifn, ifv in ifrow:
							if (ifn.prettyPrint().startswith(OID_IF_IP_ADDR)):
								if (v == ifv):
									t = ifn.prettyPrint().split('.')
									svi_ip = ".".join(t[10:])
									mask = snmpobj.cache_lookup(d.ifip_vbtbl, OID_IF_IP_NETM + svi_ip)
									nbits = get_net_bits_from_mask(mask)
									svi_ip = '%s/%i' % (svi_ip, nbits)
									svi.ip.append(svi_ip)

					d.svis.append(svi)

		# Pull loopback info if needed
		if (self.config.graph.include_lo == True):
			d.ethif_vbtbl = snmpobj.get_bulk(OID_ETH_IF)

			if (d.ifip_vbtbl == None):
				d.ifip_vbtbl = snmpobj.get_bulk(OID_IF_IP)
			
			for row in d.ethif_vbtbl:
				for n, v in row:
					if (n.prettyPrint().startswith(OID_ETH_IF_TYPE) & (v == 24)):
						ifidx = n.prettyPrint().split('.')[10]
						lo_name = snmpobj.cache_lookup(d.ethif_vbtbl, OID_ETH_IF_DESC + '.' + ifidx)
						lo_ip = get_ip_from_ifidx(snmpobj, d.ifip_vbtbl, ifidx)
						lo = mnet_node_lo(lo_name, lo_ip) 
						d.loopbacks.append(lo)

		return d


	#
	# Crawl device at this IP.
	# Recurse down a level if 'depth' > 0
	#
	def _crawl_node(self, node, depth):
		if (node == None):
			return

		if (depth >= self.max_depth):
			return
					
		if (node.crawled > 0):
			return
		node.crawled = 1

		# vmware ESX can report IP as 0.0.0.0
		# If we are allowing 0.0.0.0/32 in the config,
		# then we added it as a leaf, but don't crawl it
		if (node.ip[0] == '0.0.0.0'):
			return

		# may be a leaf we couldn't connect to previously
		if (node.snmp_cred == None):
			return

		# print some info to stdout
		sys.stdout.write('>')
		for i in range(0, depth):
			sys.stdout.write('.')
		print('%s (%s)' % (node.name, node.ip[0]))

		# get the cached snmp credentials
		snmpobj = mnet_snmp(node.ip[0])
		snmpobj._cred = node.snmp_cred

		children = []
		
		# get list of CDP neighbors
		node.cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
		if (node.cdp_vbtbl == None):
			return

		# cache some common MIB trees
		node.link_type_vbtbl	= snmpobj.get_bulk(OID_VTP_TRUNK)
		node.lag_vbtbl			= snmpobj.get_bulk(OID_LAG_LACP)
		node.vlan_vbtbl			= snmpobj.get_bulk(OID_IF_VLAN)
		node.ifname_vbtbl		= snmpobj.get_bulk(OID_IFNAME)
		
		if (node.ifip_vbtbl == None):
			node.ifip_vbtbl		= snmpobj.get_bulk(OID_IF_IP)

		for row in node.cdp_vbtbl:
			for name, val in row:
				# process only if this row is a CDP_DEVID
				if (name.prettyPrint().startswith(OID_CDP_DEVID) == 0):
					continue

				t = name.prettyPrint().split('.')
				ifidx = t[14]

				# get remote IP
				rip = snmpobj.cache_lookup(node.cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + t[15])
				rip = convert_ip_int_str(rip)

				# if the remote IP is not allowed, stop processing it here
				if (self.is_node_allowed(rip) == 0):
					continue

				# get local port
				lport = get_ifname(snmpobj, node.ifname_vbtbl, ifidx)

				# get remote port
				rport = snmpobj.cache_lookup(node.cdp_vbtbl, OID_CDP_DEVPORT + '.' + ifidx + '.' + t[15])
				rport = shorten_port_name(rport)

				# get remote platform
				rplat = snmpobj.cache_lookup(node.cdp_vbtbl, OID_CDP_DEVPLAT + '.' + ifidx + '.' + t[15])

				# get IOS version
				rios = snmpobj.cache_lookup(node.cdp_vbtbl, OID_CDP_IOS + '.' + ifidx + '.' + t[15])
				if (rios != None):
					try:
						rios = binascii.unhexlify(rios[2:])
					except:
						pass
					rios_s = re.search('Version:? ([^ ,]*)', rios)
					if (rios_s):
						rios = rios_s.group(1)

				# get link type (trunk ?)
				link_type = snmpobj.cache_lookup(node.link_type_vbtbl, OID_VTP_TRUNK + '.' + ifidx)

				# get LAG membership
				lag = snmpobj.cache_lookup(node.lag_vbtbl, OID_LAG_LACP + '.' + ifidx)
				lag = get_ifname(snmpobj, node.ifname_vbtbl, lag)

				# get VLAN info
				vlan = snmpobj.cache_lookup(node.vlan_vbtbl, OID_IF_VLAN + '.' + ifidx)

				# get IP address
				lifip = get_ip_from_ifidx(snmpobj, node.ifip_vbtbl, ifidx)

				# get the child info
				if ((self.is_node_allowed(rip) == 1) & (rip != 'UNKNOWN')):
					child = self._get_node(rip, depth+1)
					if (child != None):
						# if we couldn't pull info from SNMP fill in what we know
						if (child.snmp_cred == None):
							child.name = shorten_host_name(val.prettyPrint(), self.config.host_domains)

						# CDP advertises the platform
						child.plat = rplat.replace('cisco ', '')
						child.ios = rios

						# link child to parent
						link = mnet_node_link(node			= child,
											link_type		= link_type,
											vlan			= vlan,
											local_port		= lport,
											remote_port		= rport,
											local_lag		= lag,
											remote_lag		= None,
											local_if_ip		= lifip,
											remote_if_ip	= None)
						self.add_link(node, link)
						children.append(child)

		for child in children:
			self._crawl_node(child, depth+1)


	#
	# Returns 1 if the IP is allowed to be crawled.
	#
	def is_node_allowed(self, ip):
		if (ip == 'UNKNOWN'):
			return 1

		ipaddr = None
		if (USE_NETADDR):
			ipaddr = IPAddress(ip)

		# check exclude nodes
		for e in self.config.exclude_subnets:
			if (USE_NETADDR):
				if (ip in IPNetwork(e)):
					return 0
			else:
				if (is_ipv4_in_cidr(ip, e)):
					return 0
		
		# check allowed subnets
		if ((self.config.allowed_subnets == None) | (len(self.config.allowed_subnets) == 0)):
			return 1

		for s in self.config.allowed_subnets:
			if (USE_NETADDR):
				if (ipaddr in IPNetwork(s)):
					return 1
			else:
				if (is_ipv4_in_cidr(ip, s)):
					return 1

		return 0


	def add_link(self, node, link):
		if (link.node.crawled == 1):
			# both nodes have been crawled,
			# so try to update existing reverse link info
			# instead of adding a new link
			for n in self.nodes:
				# find the child, which was the original parent
				if (n.name == link.node.name):
					# find the existing link
					for ex_link in n.links:
						if ((ex_link.node.name == node.name) & (ex_link.local_port == link.remote_port)):
							if ((link.local_if_ip != 'UNKNOWN') & (ex_link.remote_if_ip == None)):
								ex_link.remote_if_ip = link.local_if_ip
							if ((link.local_lag != 'UNKNOWN') & (ex_link.remote_lag == None)):
								ex_link.remote_lag = link.local_lag
							return

		node.add_link(link)
		return


	def _output_stdout(self, node):
		if (node == None):
			return (0, 0)
		if (node.crawled > 0):
			return (0, 0)
		node.crawled = 1

		ret_nodes = 1
		ret_links = 0

		print('-----------------------------------------')
		print('      Name: %s' % node.name)
		print('        IP: %s' % node.ip[0])
		print('  Platform: %s' % node.plat)
		print('   IOS Ver: %s' % node.ios)

		if ((node.vss.enabled == 0) & (node.stack.count == 0)):
			print('    Serial: %s' % node.serial)

		print('   Routing: %s' % ('yes' if (node.router == 1) else 'no'))
		print('   OSPF ID: %s' % node.ospf_id)
		print('   BGP LAS: %s' % node.bgp_las)
		print('  HSRP Pri: %s' % node.hsrp_pri)
		print('  HSRP VIP: %s' % node.hsrp_vip)

		if (node.vss.enabled):
			print('  VSS Mode: %i' % node.vss.enabled)
			print('VSS Domain: %s' % node.vss.domain)
			print('       VSS Slot 0:')
			print('              IOS: %s' % node.vss.members[0].ios)
			print('           Serial: %s' % node.vss.members[0].serial)
			print('         Platform: %s' % node.vss.members[0].plat)
			print('       VSS Slot 1:')
			print('              IOS: %s' % node.vss.members[1].ios)
			print('           Serial: %s' % node.vss.members[1].serial)
			print('         Platform: %s' % node.vss.members[1].plat)

		print(' Stack Cnt: %i' % node.stack.count)
		
		if ((node.stack.count > 0) & (self.config.graph.get_stack_members)):
			print('      Stack members:')
			for smem in node.stack.members:
				print('        Switch Number: %s' % (smem.num))
				print('                 Role: %s' % (smem.role))
				print('             Priority: %s' % (smem.pri))
				print('                  MAC: %s' % (smem.mac))
				print('             Platform: %s' % (smem.plat))
				print('                Image: %s' % (smem.img))
				print('               Serial: %s' % (smem.serial))

		print('      Loopbacks:')
		if (self.config.graph.include_lo == False):
			print('        Not configured.')
		else:
			for lo in node.loopbacks:
				print('        %s - %s' % (lo.name, lo.ip))
				
		print('      SVIs:')
		if (self.config.graph.include_svi == False):
			print('        Not configured.')
		else:
			for svi in node.svis:
				for ip in svi.ip:
					print('        SVI %s - %s' % (svi.vlan, ip))

		print('     Links:')
		for link in node.links:
			print('       %s -> %s:%s' % (link.local_port, link.node.name, link.remote_port))
			ret_links += 1

		for link in node.links:
			rn, rl = self._output_stdout(link.node)
			ret_nodes += rn
			ret_links += rl

		return (ret_nodes, ret_links)


	def output_stdout(self):
		self._reset_crawled()

		print('-----')
		print('----- DEVICES')
		print('-----')
		num_nodes, num_links = self._output_stdout(self.root_node)

		print('Discovered devices: %i' % num_nodes)
		print('Discovered links:   %i' % num_links)


	def _output_dot_get_node(self, graph, node):
		dot_node = mnet_graph_dot_node()
		dot_node.ntype = 'single'
		dot_node.shape = 'ellipse'
		dot_node.style = 'solid'
		dot_node.peripheries = 1
		dot_node.label = ''

		dot_node.label = '<font point-size="10"><b>%s</b></font><br />' \
						'<font point-size="8"><i>%s</i></font>' \
						% (node.name, node.ip[0])

		if ((node.stack.count == 0) | (self.config.graph.get_stack_members == 0)):
			# show platform here or break it down by stack/vss later
			dot_node.label += '<br />%s' % node.plat

		if ((self.config.graph.include_serials == 1) & (node.stack.count == 0) & (node.vss.enabled == 0)):
			dot_node.label += '<br />%s' % node.serial

		dot_node.label += '<br />%s' % node.ios
		
		if (node.vss.enabled == 1):
			if (self.config.graph.collapse_vss == 0):
				dot_node.ntype = 'vss'
			else:
				# group VSS into one graph node
				dot_node.peripheries = 2
				s1 = ''
				s2 = ''
				if (self.config.graph.include_serials == 1):
					s1 = ' - %s' % node.vss.members[0].serial
					s2 = ' - %s' % node.vss.members[1].serial

				dot_node.label += '<br />VSS %s' % node.vss.domain
				dot_node.label += '<br />VSS 0 - %s%s' % (node.vss.members[0].plat, s1)
				dot_node.label += '<br />VSS 1 - %s%s' % (node.vss.members[1].plat, s2)

		if (node.stack.count > 0):
			if (self.config.graph.collapse_stackwise == 0):
				dot_node.ntype = 'stackwise'
			else:
				# group Stackwise into one graph node
				dot_node.peripheries = node.stack.count

				dot_node.label += '<br />Stackwise %i' % node.stack.count

				if (self.config.graph.get_stack_members):
					for smem in node.stack.members:
						serial = ''
						if (self.config.graph.include_serials == 1):
							serial = ' - %s' % smem.serial
						dot_node.label += '<br />SW %s - %s%s (%s)' % (smem.num, smem.plat, serial, smem.role)

		if (node.router == 1):
			dot_node.shape = 'diamond'
			if (node.bgp_las != None):
				dot_node.label += '<br />BGP %s' % node.bgp_las
			if (node.ospf_id != None):
				dot_node.label += '<br />OSPF %s' % node.ospf_id
			if (node.hsrp_pri != None):
				dot_node.label += '<br />HSRP VIP %s' \
								'<br />HSRP Pri %s' % (node.hsrp_vip, node.hsrp_pri)

		if (self.config.graph.include_lo == True):
			for lo in node.loopbacks:
				dot_node.label += '<br />%s - %s' % (lo.name, lo.ip)

		if (self.config.graph.include_svi == True):
			for svi in node.svis:
				for ip in svi.ip:
					dot_node.label += '<br />VLAN %s - %s' % (svi.vlan, ip)

		return dot_node


	def _output_dot(self, graph, node):
		if (node == None):
			return (0, 0)
		if (node.crawled > 0):
			return (0, 0)
		node.crawled = 1

		dot_node = self._output_dot_get_node(graph, node)

		if (dot_node.ntype == 'single'):
			graph.add_node(
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
							fontsize = self.config.graph.node_text_size,
							label = '<<br /><b>VSS %s</b>>' % node.vss.domain
						)
			for i in range(0, 2):
				serial = ''
				if (self.config.graph.include_serials == 1):
					serial = ' - %s' % node.vss.members[i].serial
				
				vss_label = 'VSS %i - %s%s' % (i, node.vss.members[i].plat, serial)

				cluster.add_node(
						pydot.Node(
							name = '%s[mnetVSS%i]' % (node.name, i+1),
							label = '<%s<br />%s>' % (dot_node.label, vss_label),
							style = dot_node.style,
							shape = dot_node.shape,
							peripheries = dot_node.peripheries
						)
				)
			graph.add_subgraph(cluster)
		elif (dot_node.ntype == 'stackwise'):
			cluster = pydot.Cluster(
							graph_name = node.name,
							suppress_disconnected = False,
							labelloc = 't',
							labeljust = 'c',
							fontsize = self.config.graph.node_text_size,
							label = '<<br /><b>Stackwise</b>>'
						)
			for i in range(0, node.stack.count):
				serial = ''
				if (self.config.graph.include_serials == 1):
					serial = ' - %s' % node.stack.members[i].serial
				
				smem = node.stack.members[i]
				sw_label = 'SW %i (%s)<br />%s%s' % (i, smem.role, smem.plat, serial)

				cluster.add_node(
						pydot.Node(
							name = '%s[mnetSW%i]' % (node.name, i+1),
							label = '<%s<br />%s>' % (dot_node.label, sw_label),
							style = dot_node.style,
							shape = dot_node.shape,
							peripheries = dot_node.peripheries
						)
				)
			graph.add_subgraph(cluster)



		for link in node.links:
			self._output_dot(graph, link.node)

			link_color = 'black'
			link_style = 'solid'

			link_label = 'P:%s\nC:%s' % (link.local_port, link.remote_port)

			# LAG
			if (link.local_lag != 'UNKNOWN'):
				link_label += '\nP:%s | C:%s' % (link.local_lag, link.remote_lag)

			# IP Addresses
			if ((link.local_if_ip != 'UNKNOWN') & (link.local_if_ip != None)):
				link_label += '\nP:%s' % link.local_if_ip
			if ((link.remote_if_ip != 'UNKNOWN') & (link.remote_if_ip != None)):
				link_label += '\nC:%s' % link.remote_if_ip
					
			if (link.link_type == '1'):
				# Trunk = Bold/Blue
				link_color = 'blue'
				link_style = 'bold'
			elif (link.link_type is None):
				# Routed = Bold/Red
				link_color = 'red'
				link_style = 'bold'
			else:
				# Switched, include VLAN ID in label
				if (link.vlan != None):
					link_label += '\nVLAN %s' % link.vlan

			edge_src = node.name
			edge_dst = link.node.name
			lmod = get_module_from_interf(link.local_port)
			rmod = get_module_from_interf(link.remote_port)

			if (self.config.graph.collapse_vss == 0):
				if (node.vss.enabled == 1):
					edge_src = '%s[mnetVSS%s]' % (node.name, lmod)
				if (link.node.vss.enabled == 1):
					edge_dst = '%s[mnetVSS%s]' % (link.node.name, rmod)

			if (self.config.graph.collapse_stackwise == 0):
				if (node.stack.count > 0):
					edge_src = '%s[mnetSW%s]' % (node.name, lmod)
				if (link.node.stack.count > 0):
					edge_dst = '%s[mnetSW%s]' % (link.node.name, rmod)

			edge = pydot.Edge(
						edge_src, edge_dst,
						dir = 'forward',
						label = link_label,
						color = link_color,
						style = link_style
					)

			graph.add_edge(edge)



	def output_dot(self, dot_file, title):
		self._reset_crawled()

		title_text_size = self.config.graph.title_text_size
		credits = '<table border="0">' \
					'<tr>' \
					 '<td balign="right">' \
					  '<font point-size="%i"><b>$title$</b></font><br />' \
					  '<font point-size="%i">$date$</font><br />' \
					  '<font point-size="7">' \
					  'Generated by MNet Suite $ver$<br />' \
					  'Written by Michael Laforest</font><br />' \
					 '</td>' \
					'</tr>' \
				   '</table>' % (title_text_size, title_text_size-2)

		today = datetime.datetime.now()
		today = today.strftime('%Y-%m-%d %H:%M')
		credits = credits.replace('$ver$', __version__)
		credits = credits.replace('$date$', today)
		credits = credits.replace('$title$', title)

		node_text_size = self.config.graph.node_text_size
		link_text_size = self.config.graph.link_text_size

		graph = pydot.Dot(
				graph_type = 'graph',
				labelloc = 'b',
				labeljust = 'r',
				fontsize = node_text_size,
				label = '<%s>' % credits
		)
		graph.set_node_defaults(
				fontsize = link_text_size
		)
		graph.set_edge_defaults(
				fontsize = link_text_size,
				labeljust = 'l'
		)

		# add all of the nodes and links
		self._output_dot(graph, self.root_node)

		# get file extension
		file_name, file_ext = os.path.splitext(dot_file)

		output_func = getattr(graph, 'write_' + file_ext.lstrip('.'))
		if (output_func == None):
			print('Error: Output type "%s" does not exist.' % file_ext)
		else:
			output_func(dot_file)
			print('Created graph: %s' % dot_file)


	def output_catalog(self, filename):
		try:
			f = open(filename, 'w')
		except:
			print('Unable to open catalog file "%s"' % filename)
			return

		for n in self.nodes:
			# pull info here that wasn't needed for the graph
			serial = ''
			bootf = ''
			
			if (n.ip[0]):
				snmpobj = mnet_snmp(n.ip[0])
				snmpobj._cred = n.snmp_cred

				if (snmpobj._cred != None):
					bootf  = snmpobj.get_val(OID_SYS_BOOT)

			if (n.stack.count > 0):
				# stackwise
				for smem in n.stack.members:
					if (snmpobj._cred != None):
						serial = smem.serial or 'NOT CONFIGURED TO POLL'
						plat   = smem.plat or 'NOT CONFIGURED TO POLL'
						
					f.write('"%s","%s","%s","%s","%s","STACK","%s"\n' % (n.name, n.ip[0], plat, n.ios, serial, bootf))
			elif (n.vss.enabled != 0):
				#vss
				for i in range(0, 2):
					serial = n.vss.members[i].serial
					plat   = n.vss.members[i].plat
					ios    = n.vss.members[i].ios
					f.write('"%s","%s","%s","%s","%s","VSS","%s"\n' % (n.name, n.ip[0], plat, ios, serial, bootf))
			else:
				# stand alone
				if ((snmpobj._cred != None) & (n.serial == None)):
					serial = snmpobj.get_val(OID_SYS_SERIAL)

				f.write('"%s","%s","%s","%s","%s","","%s"\n' % (n.name, n.ip[0], n.plat, n.ios, serial, bootf))

		f.close()

