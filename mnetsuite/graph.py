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
import dot_parser
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
		node = self._get_node(ip, 0, 'root')
		if (node != None):
			self._crawl_node(node, 0)
		
		self.root_node = node

		# we may have missed chassis info
		for n in self.nodes:
			if ((n.serial == None) | (n.plat == None) | (n.ios == None)):
				n.opts.get_chassis_info = True
				n.query_node()

		return


	def _print_step(self, ip, name, indicator, depth, discovered_proto, can_connect):
		if (discovered_proto == 'cdp'):
			sys.stdout.write('[ cdp]')
		elif (discovered_proto == 'lldp'):
			sys.stdout.write('[lldp]')
		else:
			sys.stdout.write('      ')

		sys.stdout.write(indicator)

		for i in range(0, depth):
			sys.stdout.write('.')

		if (can_connect == 1):
			print('%s (%s)' % (name, ip))
		else:
			print('UNKNOWN (%s)            << UNABLE TO CONNECT WITH SNMP' % ip)


	def _get_node(self, ip, depth, discovered_proto):
		node = mnet_node()
		node.name = 'UNKNOWN'
		node.ip = [ip]

		# vmware ESX reports the IP as 0.0.0.0
		# return a minimal node since we don't have
		# a real IP.
		# LLDP can return an empty string for IPs.
		if ((ip == '0.0.0.0') | (ip == '')):
			self.nodes.append(node)
			return node

		# see if we know about this node by its IP first.
		# this would save us an SNMP query for the hostname.
		for ex in self.nodes:
			for exip in ex.ip:
				if (exip == ip):
					return ex

		# find valid credentials for this node
		if (node.try_snmp_creds(self.config.snmp_creds) == 0):
			self._print_step(ip, None, '+', depth, discovered_proto, 0)
			self.nodes.append(node)
			return node

		node.name = node._get_system_name(self.config.host_domains)

		# verify this node isn't already in our visited
		# list by checking for its hostname
		for ex in self.nodes:
			if (ex.name == node.name):
				for exip in ex.ip:
					if (exip == ip):
						return ex
				ex.ip.append(ip)
				return ex

		# print some info to stdout
		self._print_step(ip, node.name, '+', depth, discovered_proto, 1)

		node.opts.get_router = True
		node.opts.get_ospf_id = True
		node.opts.get_bgp_las = True
		node.opts.get_hsrp_pri = True
		node.opts.get_hsrp_vip = True
		node.opts.get_serial = self.config.graph.include_serials
		node.opts.get_stack = True
		node.opts.get_stack_details = self.config.graph.get_stack_members
		node.opts.get_vss = True
		node.opts.get_vss_details = self.config.graph.get_vss_members
		node.opts.get_svi = self.config.graph.include_svi
		node.opts.get_lo = self.config.graph.include_lo

		node.query_node()
		self.nodes.append(node)

		return node


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
		if (node.snmpobj.success == 0):
			return

		# print some info to stdout
		self._print_step(node.ip[0], node.name, '>', depth, '', 1)

		# get the cached snmp credentials
		snmpobj = node.snmpobj

		# list of valid neighbors to crawl next
		valid_neighbors = []

		# get list of CDP neighbors
		cdp_neighbors = node.get_cdp_neighbors()

		# get list of LLDP neighbors
		lldp_neighbors = node.get_lldp_neighbors()

		if ((cdp_neighbors == None) & (lldp_neighbors == None)):
			return

		neighbors = cdp_neighbors + lldp_neighbors

		for n in neighbors:
			# if the remote IP is not allowed, stop processing it here
			if (self.is_node_allowed(n.remote_ip) == 0):
				continue

			# get the child info
			if (n.remote_ip != 'UNKNOWN'):
				child = self._get_node(n.remote_ip, depth+1, n.discovered_proto)
				if (child != None):
					# if we couldn't pull info from SNMP fill in what we know
					if (child.snmpobj.success == 0):
						child.name = shorten_host_name(n.remote_name, self.config.host_domains)
						self._print_step(n.remote_ip, n.remote_name, '+', depth, n.discovered_proto, 1)

					# CDP/LLDP advertises the platform
					child.plat = n.remote_platform
					child.ios = n.remote_ios

					# link child to parent
					n.node = child
					if (self.add_link(node, n) == 1):
						valid_neighbors.append(child)

		# crawl the valid neighbors
		for n in valid_neighbors:
			self._crawl_node(n, depth+1)


	#
	# Returns 1 if the IP is allowed to be crawled.
	#
	def is_node_allowed(self, ip):
		if ((ip == 'UNKNOWN') | (ip == '')):
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


	#
	# Add or update a link.
	# Return
	#    0 - Found an existing link and updated it
	#    1 - Added as a new link
	#
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

							if ((len(link.local_lag_ips) == 0) & len(ex_link.remote_lag_ips)):
								ex_link.remote_lag_ips = link.local_lag_ips

							if ((link.local_native_vlan != None) & (ex_link.remote_native_vlan == None)):
								ex_link.remote_native_vlan = link.local_native_vlan

							if ((link.local_allowed_vlans != None) & (ex_link.remote_allowed_vlans == None)):
								ex_link.remote_allowed_vlans = link.local_allowed_vlans

							return 0
		else:
			for ex_link in node.links:
				if ((ex_link.node.name == link.node.name) & (ex_link.local_port == link.local_port)):
					# haven't crawled yet but somehow we have this link twice.
					# maybe from different discovery processes?
					return 0

		node.add_link(link)
		return 1


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
				for lo_ip in lo.ips:
					print('        %s - %s' % (lo.name, lo_ip))
				
		print('      SVIs:')
		if (self.config.graph.include_svi == False):
			print('        Not configured.')
		else:
			for svi in node.svis:
				for ip in svi.ip:
					print('        SVI %s - %s' % (svi.vlan, ip))

		print('     Links:')
		for link in node.links:
			lag = ''
			if ((link.local_lag != None) | (link.remote_lag != None)):
				lag = 'LAG[%s:%s]' % (link.local_lag or '', link.remote_lag or '')
			print('       %s -> %s:%s %s' % (link.local_port, link.node.name, link.remote_port, lag))
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

		dot_node.label = '<font point-size="10"><b>%s</b></font>' % node.name

		if (node.ip[0] != ''):
			dot_node.label += '<br /><font point-size="8"><i>%s</i></font>' % node.ip[0]

		if ((node.stack.count == 0) | (self.config.graph.get_stack_members == 0)):
			# show platform here or break it down by stack/vss later
			dot_node.label += '<br />%s' % node.plat

		if ((self.config.graph.include_serials == 1) & (node.stack.count == 0) & (node.vss.enabled == 0)):
			dot_node.label += '<br />%s' % node.serial

		dot_node.label += '<br />%s' % node.ios
		
		if (node.vss.enabled == 1):
			if (self.config.graph.expand_vss == 1):
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
			if (self.config.graph.expand_stackwise == 1):
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
				for lo_ip in lo.ips:
					dot_node.label += '<br />%s - %s' % (lo.name, lo_ip)

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

		lags = []
		for link in node.links:
			self._output_dot(graph, link.node)

			if ((self.config.graph.expand_lag == 1) | (link.local_lag == 'UNKNOWN')):
				self._output_dot_link(graph, node, link, 0)
			else:
				found = 0
				for lag in lags:
					if (link.local_lag == lag):
						found = 1
						break
				if (found == 0):
					lags.append(link.local_lag)
					self._output_dot_link(graph, node, link, 1)


	def _output_dot_link(self, graph, node, link, draw_as_lag):
		link_color = 'black'
		link_style = 'solid'

		if (draw_as_lag):
			link_label = 'LAG'
			members = 0
			for l in node.links:
				if (l.local_lag == link.local_lag):
					members += 1
			link_label += '\n%i Members' % members
		else:
			link_label = 'P:%s\nC:%s' % (link.local_port, link.remote_port)

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
		lmod = get_module_from_interf(link.local_port)
		rmod = get_module_from_interf(link.remote_port)

		if (self.config.graph.expand_vss == 1):
			if (node.vss.enabled == 1):
				edge_src = '%s[mnetVSS%s]' % (node.name, lmod)
			if (link.node.vss.enabled == 1):
				edge_dst = '%s[mnetVSS%s]' % (link.node.name, rmod)

		if (self.config.graph.expand_stackwise == 1):
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

