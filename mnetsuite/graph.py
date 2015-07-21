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
from node import mnet_node, mnet_node_link, mnet_node_svi
from _version import __version__


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
			d = mnet_node(name = 'UNKNOWN', ip = ip)
			self.nodes.append(d)
			return d

		snmpobj = mnet_snmp(ip)

		# find valid credentials for this node
		if (snmpobj.get_cred(self.config.snmp_creds) == 0):
			sys.stdout.write('?')
			for i in range(0, depth):
				sys.stdout.write('.')
			print('UNKNOWN (%s)            << UNABLE TO CONNECT WITH SNMP' % ip)
			d = mnet_node(name = 'UNKNOWN',	ip = ip)
			self.nodes.append(d)
			return d

		system_name = shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

		# verify this node isn't already in our visited list
		for ex in self.nodes:
			if (ex.name == system_name):
				return ex

		# print some info to stdout
		sys.stdout.write('?')
		for i in range(0, depth):
			sys.stdout.write('.')
		print('%s (%s)' % (system_name, ip))

		# collect general information about this node
		stack_count = get_stackwise_count(snmpobj)
		vss_enable = 1 if (snmpobj.get_val(OID_VSS_MODE) == '2') else 0
		vss_domain = None

		router = 1 if (snmpobj.get_val(OID_IP_ROUTING) == '1') else 0
		ospf = None
		bgp = None
		hsrp_pri = None
		hsrp_vip = None

		if (vss_enable == 1):
			vss_domain = snmpobj.get_val(OID_VSS_DOMAIN)

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

		# save this node
		d = mnet_node(
				name			= system_name,
				ip				= ip,
				plat			= get_sys_platform(snmpobj),
				router			= router,
				ospf_id			= ospf or None,
				bgp_las			= bgp or None,
				hsrp_pri		= hsrp_pri or None,
				hsrp_vip		= hsrp_vip or None,
				stack_count		= stack_count,
				vss_enable		= vss_enable,
				vss_domain		= vss_domain
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
		if (node.ip == '0.0.0.0'):
			return

		# may be a leaf we couldn't connect to previously
		if (node.snmp_cred == None):
			return

		# print some info to stdout
		sys.stdout.write('>')
		for i in range(0, depth):
			sys.stdout.write('.')
		print('%s (%s)' % (node.name, node.ip))

		# get the cached snmp credentials
		snmpobj = mnet_snmp(node.ip)
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

						# always prefer CDP advertised platform over what we pulled from SNMP
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
		print('        IP: %s' % node.ip)
		print('  Platform: %s' % node.plat)
		print('   IOS Ver: %s' % node.ios)
		print('   Routing: %s' % ('yes' if (node.router == 1) else 'no'))
		print('   OSPF ID: %s' % node.ospf_id)
		print('   BGP LAS: %s' % node.bgp_las)
		print('  HSRP Pri: %s' % node.hsrp_pri)
		print('  HSRP VIP: %s' % node.hsrp_vip)
		print(' Stack Cnt: %i' % node.stack_count)
		print('  VSS Mode: %i' % node.vss_enable)
		print('VSS Domain: %s' % node.vss_domain)

		print('      SVIs:')
		for svi in node.svis:
			for ip in svi.ip:
				print('     SVI(%s) IP: %s' % (svi.vlan, ip))
				
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


	def _output_dot(self, graph, node):
		if (node == None):
			return (0, 0)
		if (node.crawled > 0):
			return (0, 0)
		node.crawled = 1

		node_label = '<font point-size="10"><b>%s</b></font><br />' \
						'<font point-size="8"><i>%s</i></font><br />' \
						'%s<br />%s' \
						% (node.name, node.ip, node.plat, node.ios)
		node_style = 'solid'
		node_shape = 'ellipse'
		node_peripheries = 1

		if (node.vss_enable == 1):
			node_label += '<br />VSS %s' % node.vss_domain
			node_peripheries = 2

		if (node.stack_count > 0):
			node_label += '<br />Stackwise %i' % node.stack_count
			node_peripheries = node.stack_count

		if (node.router == 1):
			node_shape = 'diamond'
			if (node.bgp_las != None):
				node_label += '<br />BGP %s' % node.bgp_las
			if (node.ospf_id != None):
				node_label += '<br />OSPF %s' % node.ospf_id
			if (node.hsrp_pri != None):
				node_label += '<br />HSRP VIP %s' \
								'<br />HSRP Pri %s' % (node.hsrp_vip, node.hsrp_pri)

		if (self.config.graph.include_svi == True):
			for svi in node.svis:
				for ip in svi.ip:
					node_label += '<br />VLAN %s - %s' % (svi.vlan, ip)

		graph.add_node(
				pydot.Node(
					name = node.name,
					label = '<%s>' % node_label,
					style = node_style,
					shape = node_shape,
					peripheries = node_peripheries
				)
		)

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

			graph.add_edge(
					pydot.Edge(
						node.name, link.node.name,
						dir = 'forward',
						label = link_label,
						color = link_color,
						style = link_style
					)
			)



	def output_dot(self, dot_file, title):
		self._reset_crawled()

		credits = '<table border="0">' \
					'<tr>' \
					 '<td balign="right">' \
					  '<font point-size="15"><b>$title$</b></font><br />' \
					  '<font point-size="9">$date$</font><br />' \
					  '<font point-size="7">' \
					  'Generated by MNet Suite $ver$<br />' \
					  'Written by Michael Laforest</font><br />' \
					 '</td>' \
					'</tr>' \
				   '</table>'

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
			
			if (n.ip):
				snmpobj = mnet_snmp(n.ip)
				snmpobj.get_cred(self.config.snmp_creds)

				serial = snmpobj.get_val(OID_SYS_SERIAL)
				bootf  = snmpobj.get_val(OID_SYS_BOOT)

			f.write('"%s","%s","%s","%s","%s"\n' % (n.name, n.ip, n.plat, n.ios, serial, bootf))

		f.close()

