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

from snmp import *
from config import mnet_config
from util import *
from node import mnet_node
from _version import __version__

class mnet_graph:
	nodes = []
	links = []
	max_depth = 0
	config = None

	def __init__(self):
		self.config = mnet_config()

	def load_config(self, config_file):
		if (config_file):
			self.config.load(config_file)

	def set_max_depth(self, depth):
		self.max_depth = depth

	#
	# Crawl device at this IP.
	# Recurse down a level if 'depth' > 0
	#
	def crawl_node(self, ip, depth):
		if ((self.is_node_allowed(ip) == 0) | (ip == 'UNKNOWN')):
			return

		snmpobj = mnet_snmp(ip)

		# find valid credentials for this node
		if (snmpobj.get_cred(self.config.snmp_creds) == 0):
			return

		system_name = shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

		# prevent loops by checking if we've already done this node by host name
		for ex in self.nodes:
			if (ex.name == system_name):
				return

		# print some info to stdout
		for i in range(0, self.max_depth - depth):
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
		self.nodes.append(d)

		if (depth <= 0):
			return
						
		children = []

		# get list of CDP neighbors
		cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
		if (cdp_vbtbl == None):
			return

		# cache some common MIB trees
		link_type_vbtbl	= snmpobj.get_bulk(OID_VTP_TRUNK)
		lag_vbtbl		= snmpobj.get_bulk(OID_LAG_LACP)
		vlan_vbtbl		= snmpobj.get_bulk(OID_IF_VLAN)
		ifname_vbtbl	= snmpobj.get_bulk(OID_IFNAME)
		ifip_vbtbl		= snmpobj.get_bulk(OID_IF_IP)

		for row in cdp_vbtbl:
			for name, val in row:
				# process only if this row is a CDP_DEVID
				if (name.prettyPrint().startswith(OID_CDP_DEVID) == 0):
					continue

				t = name.prettyPrint().split('.')
				ifidx = t[14]

				# get remote IP
				rip = snmpobj.cache_lookup(cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + t[15])
				rip = convert_ip_int_str(rip)

				# if the remote IP is not allowed, stop processing it here
				if (self.is_node_allowed(rip) == 0):
					continue

				# get local port
				lport = get_ifname(snmpobj, ifname_vbtbl, ifidx)

				# get remote port
				rport = snmpobj.cache_lookup(cdp_vbtbl, OID_CDP_DEVPORT + '.' + ifidx + '.' + t[15])
				rport = shorten_port_name(rport)

				# get link type (trunk ?)
				link_type = snmpobj.cache_lookup(link_type_vbtbl, OID_VTP_TRUNK + '.' + ifidx)

				# get LAG membership
				lag = snmpobj.cache_lookup(lag_vbtbl, OID_LAG_LACP + '.' + ifidx)
				lag = get_ifname(snmpobj, ifname_vbtbl, lag)

				# get VLAN info
				vlan = snmpobj.cache_lookup(vlan_vbtbl, OID_IF_VLAN + '.' + ifidx)

				# get IP address
				lifip = get_ip_from_ifidx(snmpobj, ifip_vbtbl, ifidx)

				link = {}
				link['lip']			= ip
				link['lname']		= system_name
				link['lport']		= lport
				link['rname']		= shorten_host_name(val.prettyPrint(), self.config.host_domains)
				link['rport']		= rport
				link['rip']			= rip
				link['link_type']	= link_type
				link['llag']		= lag
				link['rlag']		= None
				link['vlan']		= vlan
				link['lifip']		= lifip
				link['rifip']		= None
				
				self.add_link(link)
				children.append(rip)
						
		for child in children:
			self.crawl_node(child, depth-1)


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


	def add_link(self, node):
		for link in self.links:
			if (	  (node['lname'] == link['lname'])
					& (node['lport'] == link['lport'])
					& (node['rname'] == link['rname'])
					& (node['rport'] == link['rport'])
					):
				# same mapping in the same direction.
				return
			if (	  (node['lname'] == link['rname'])
					& (node['lport'] == link['rport'])
					& (node['rname'] == link['lname'])
					& (node['rport'] == link['lport'])
					):
				# same mapping in opposite direction.
				# maybe we can save the local IP address if we have one
				if ((node['lifip'] != 'UNKNOWN') & (link['rifip'] == None)):
					link['rifip'] = node['lifip']
				if ((node['llag'] != 'UNKNOWN') & (link['rlag'] == None)):
					link['rlag'] = node['llag']

				return

		self.links.append(node)


	def output_stdout(self):
		print('-----')
		print('----- DEVICES')
		print('-----')

		for n in self.nodes:
			print('      Name: %s' % n.name)
			print('        IP: %s' % n.ip)
			print('  Platform: %s' % n.plat)
			print('   Routing: %s' % ('yes' if (n.router == 1) else 'no'))
			print('   OSPF ID: %s' % n.ospf_id)
			print('   BGP LAS: %s' % n.bgp_las)
			print('  HSRP Pri: %s' % n.hsrp_pri)
			print('  HSRP VIP: %s' % n.hsrp_vip)
			print(' Stack Cnt: %i' % n.stack_count)
			print('  VSS Mode: %i' % n.vss_enable)
			print('VSS Domain: %s' % n.vss_domain)
			print

		print('-----')
		print('----- LINKS')
		print('-----')

		for link in self.links:
			print('[%s] %s:%s -(%s)-> %s:%s' % (link['link_type'], link['lname'], link['lport'], link['llag'], link['rname'], link['rport']))
			if ((link['lifip'] != None) | (link['rifip'] != None)):
				print('    %s -> %s' % (link['lifip'], link['rifip']))

		print('-----')
		print('----- Summary')
		print('-----')

		print('Discovered devices: %i' % (len(self.nodes)))
		print('Discovered links:   %i' % (len(self.links)))


	def output_dot(self, dot_file, title):
		credits = '<table border="0"> \
					<tr> \
					 <td balign="right"> \
					  <font point-size="15"><b>$title$</b></font><br /> \
					  <font point-size="9">$date$</font><br /> \
					  Generated by MNet Suite $ver$<br /> \
					  Written by Michael Laforest<br /> \
					 </td> \
					</tr> \
				   </table>'

		today = datetime.datetime.now()
		today = today.strftime('%Y-%m-%d %H:%M')
		credits = credits.replace('$ver$', __version__)
		credits = credits.replace('$date$', today)
		credits = credits.replace('$title$', title)

		graph = pydot.Dot(
				graph_type = 'graph',
				labelloc = 'b',
				labeljust = 'r',
				fontsize = 8,
				label = '<%s>' % credits
		)
		graph.set_node_defaults(
				fontsize = 7
		)
		graph.set_edge_defaults(
				fontsize = 7,
				labeljust = 'l'
		)

		for n in self.nodes:
			node_label = '<font point-size="10"><b>%s</b></font><br /> \
							<font point-size="8"><i>%s</i></font><br /> \
							%s'	% (n.name, n.ip, n.plat)
			node_style = 'solid'
			node_shape = 'ellipse'
			node_peripheries = 1

			if (n.vss_enable == 1):
				node_label += '<br />VSS %s' % n.vss_domain
				node_peripheries = 2

			if (n.stack_count > 0):
				node_label += '<br />Stackwise %i' % n.stack_count
				node_peripheries = n.stack_count

			if (n.router == 1):
				node_shape = 'diamond'
				if (n.bgp_las != None):
					node_label += '<br />BGP %s' % n.bgp_las
				if (n.ospf_id != None):
					node_label += '<br />OSPF %s' % n.ospf_id
				if (n.hsrp_pri != None):
					node_label += '<br />HSRP VIP %s \
									<br />HSRP Pri %s' % (n.hsrp_vip, n.hsrp_pri)

			graph.add_node(
					pydot.Node(
						name = n.name,
						label = '<%s>' % node_label,
						style = node_style,
						shape = node_shape,
						peripheries = node_peripheries
					)
			)

		for link in self.links:
			link_color = 'black'
			link_style = 'solid'

			link_label = 'P:%s\nC:%s' % (link['lport'], link['rport'])

			# LAG
			if (link['llag'] != 'UNKNOWN'):
				link_label += '\nP:%s | C:%s' % (link['llag'], link['rlag'])

			# IP Addresses
			if ((link['lifip'] != 'UNKNOWN') & (link['lifip'] != None)):
				link_label += '\nP:%s' % link['lifip']
			if ((link['rifip'] != 'UNKNOWN') & (link['rifip'] != None)):
				link_label += '\nC:%s' % link['rifip']
					
			if (link['link_type'] == '1'):
				# Trunk = Bold/Blue
				link_color = 'blue'
				link_style = 'bold'
			elif (link['link_type'] is None):
				# Routed = Bold/Red
				link_color = 'red'
				link_style = 'bold'
			else:
				# Switched, include VLAN ID in label
				if (link['vlan'] != None):
					link_label += '\nVLAN %s' % link['vlan']

			graph.add_edge(
					pydot.Edge(
						link['lname'], link['rname'],
						dir = 'forward',
						label = link_label,
						color = link_color,
						style = link_style
					)
			)

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

			f.write('"%s","%s","%s","%s","%s"\n' % (n.name, n.ip, n.plat, serial, bootf))

		f.close()

