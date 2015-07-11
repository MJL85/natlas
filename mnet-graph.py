#!/usr/bin/python

'''
	MNet-Graph.py
	v0.4

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



	# mnet-graph.py -r <root IP> <-f <file>> [-d <max depth>]
					[-c <config file>] [-t <diagram title>]
					[-C <catalog file>]

	Collects information about a network starting at the specified
	root device using SNMP.

	Neighbors are discovered through CDP.

	Dependencies:
		- GraphViz
		- PyDot
		- PySNMP
		- PyNetAddr
'''

# Set the below line =0 if you do not want to use PyNetAddr
USE_NETADDR = 1 

import sys
import getopt
import pydot
import datetime
import os
import re
import struct

from snmp import mnet_snmp
from config import mnet_config

if (USE_NETADDR == 1):
	from netaddr import IPAddress, IPNetwork

MNET_GRAPH_VERSION	= 'v0.4'

OID_PLATFORM1	= '1.3.6.1.2.1.47.1.1.1.1.2.1001'
OID_PLATFORM2	= '1.3.6.1.4.1.9.9.92.1.1.1.13.1'		# AIR-CAP1702
OID_PLATFORM3	= '1.3.6.1.4.1.9.9.249.1.1.1.1.3.1000'	# C4500
OID_PLATFORM4	= '1.3.6.1.2.1.47.1.1.1.1.2'			# Nexus

OID_SYSNAME		= '1.3.6.1.2.1.1.5.0'

OID_SYS_SERIAL	= '1.3.6.1.4.1.9.3.6.3.0'
OID_SYS_BOOT	= '1.3.6.1.4.1.9.2.1.73.0'

OID_IFNAME		= '1.3.6.1.2.1.31.1.1.1.1'				# + ifidx (BULK)

OID_CDP			= '1.3.6.1.4.1.9.9.23.1.2.1.1'			# (BULK)
OID_CDP_IPADDR	= '1.3.6.1.4.1.9.9.23.1.2.1.1.4'
OID_CDP_DEVID	= '1.3.6.1.4.1.9.9.23.1.2.1.1.6'		# + .ifidx.53
OID_CDP_DEVPORT	= '1.3.6.1.4.1.9.9.23.1.2.1.1.7'
OID_CDP_DEVPLAT	= '1.3.6.1.4.1.9.9.23.1.2.1.1.8'
OID_CDP_INT		= '1.3.6.1.4.1.9.9.23.1.1.1.1.'			# 6.ifidx

OID_VTP_TRUNK	= '1.3.6.1.4.1.9.9.46.1.6.1.1.14'		# + ifidx (BULK)
OID_LAG_LACP	= '1.2.840.10006.300.43.1.2.1.1.12'		# + ifidx (BULK)

OID_IP_ROUTING	= '1.3.6.1.2.1.4.1.0'
OID_IF_VLAN		= '1.3.6.1.4.1.9.9.68.1.2.2.1.2'		# + ifidx (BULK)

OID_IF_IP		= '1.3.6.1.2.1.4.20.1'					# (BULK)
OID_IF_IP_ADDR	= '1.3.6.1.2.1.4.20.1.2'				# + a.b.c.d = ifid
OID_IF_IP_NETM	= '1.3.6.1.2.1.4.20.1.3.'				# + a.b.c.d

OID_OSPF		= '1.3.6.1.2.1.14.1.2.0'
OID_OSPF_ID		= '1.3.6.1.2.1.14.1.1.0'

OID_BGP_LAS		= '1.3.6.1.2.1.15.2.0'

OID_HSRP_PRI	= '1.3.6.1.4.1.9.9.106.1.2.1.1.3.1.10'
OID_HSRP_VIP	= '1.3.6.1.4.1.9.9.106.1.2.1.1.11.1.10'

OID_STACK_IMG	= '1.3.6.1.4.1.9.9.500.1.2.1.1.1'		# (BULK)
OID_VSS_MODE	= '1.3.6.1.4.1.9.9.388.1.1.4.0'
OID_VSS_DOMAIN	= '1.3.6.1.4.1.9.9.388.1.1.1.0'

OID_ERR			= 'No Such Object currently exists at this OID'
OID_ERR_INST	= 'No Such Instance currently exists at this OID'

nodes = []
l2links = []
max_depth = 0

config = mnet_config()


#
# Get the platform type for this IP.
#
def get_sys_platform(snmpobj):
	oids = [
			OID_PLATFORM1,
			OID_PLATFORM2,
			OID_PLATFORM3,
			OID_PLATFORM4
	]

	for oid in oids:
		p = snmpobj.get_val(oid)

		if ((p != None) & (p != '') & (p != 'Port Container') & (p != OID_ERR)):
			return p
	
	return 'UNKNOWN'


#
# Lookup and format an interface name from a cache table of indexes.
#
def get_ifname(snmpobj, ifname_tbl, ifidx):
	if ((ifidx == None) | (ifidx == OID_ERR)):
		return 'UNKNOWN'

	str = snmpobj.cache_lookup(ifname_tbl, OID_IFNAME + '.' + ifidx)
	str = shorten_port_name(str)

	return str or 'UNKNOWN'


def get_ip_from_ifidx(snmpobj, ifip_tbl, ifidx):
	if ((ifip_tbl == None) | (ifidx == None) | (ifidx == OID_ERR)):
		return 'UNKNOWN'

	for row in ifip_tbl:
		for name, val in row:
			if (str(val) != str(ifidx)):
				continue

			t = name.prettyPrint().split('.')
			ip = '%s.%s.%s.%s' % (t[10], t[11], t[12], t[13])

			netm = snmpobj.cache_lookup(ifip_tbl, OID_IF_IP_NETM + ip)
			cidr = 0

			# layer 3 unnumbered interface
			if (netm == None):
				return 'Unnumbered'

			mt = netm.split('.')
			for b in range(0, 4):
				v = int(mt[b])
				while (v > 0):
					if (v & 0x01):
						cidr += 1
					v = v >> 1

			return '%s/%i' % (ip, cidr)

	return 'UNKNOWN'


def get_stackwise_count(snmpobj):
	varBindTable = snmpobj.get_bulk(OID_STACK_IMG)
	if (varBindTable == None):
		return 0

	c = 0

	for varBindTableRow in varBindTable:
		for name, val in varBindTableRow:
			c = c + 1

	# 3750x's stack by default, even if there's only 1
	if (c == 1):
		return 0

	return c


#
# Crawl device at this IP.
# Recurse down a level if 'depth' > 0
#
def crawl_node(ip, depth):
	if (is_node_allowed(ip) == 0):
		return

	snmpobj = mnet_snmp(ip)

	# find valid credentials for this node
	if (snmpobj.get_cred(config.snmp_creds) == 0):
		return

	system_name = shorten_host_name(snmpobj.get_val(OID_SYSNAME))

	# prevent loops by checking if we've already done this node by host name
	for ex in nodes:
		if (ex['name'] == system_name):
			return

	# print some info to stdout
	for i in range(0, max_depth-depth):
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
	d = {}
	d['name']			= system_name
	d['ip']				= ip
	d['plat']			= get_sys_platform(snmpobj)
	d['router']			= router
	d['ospf_id']		= ospf or None
	d['bgp_las']		= bgp or None
	d['hsrp_pri']		= hsrp_pri or None
	d['hsrp_vip']		= hsrp_vip or None
	d['stack_count']	= stack_count
	d['vss_enable']		= vss_enable
	d['vss_domain']		= vss_domain
	nodes.append(d)

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
			if (is_node_allowed(rip) == 0):
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

			l2 = {}
			l2['lip']		= ip
			l2['lname']		= system_name
			l2['lport']		= lport
			l2['rname']		= shorten_host_name(val.prettyPrint())
			l2['rport']		= rport
			l2['rip']		= rip
			l2['link_type']	= link_type
			l2['llag']		= lag
			l2['rlag']		= None
			l2['vlan']		= vlan
			l2['lifip']		= lifip
			l2['rifip']		= None
			
			add_l2_link(l2)
			children.append(rip)
					
	for child in children:
		crawl_node(child, depth-1)


#
# Returns 1 if the IP is allowed to be crawled.
#
def is_node_allowed(ip):
	ipaddr = None
	if (USE_NETADDR):
		ipaddr = IPAddress(ip)

	# check exclude nodes
	for e in config.exclude_subnets:
		if (USE_NETADDR):
			if (ip in IPNetwork(e)):
				return 0
		else:
			if (is_ipv4_in_cidr(ip, e)):
				return 0
	
	# check allowed subnets
	if ((config.allowed_subnets == None) | (len(config.allowed_subnets) == 0)):
		return 1

	for s in config.allowed_subnets:
		if (USE_NETADDR):
			if (ipaddr in IPNetwork(s)):
				return 1
		else:
			if (is_ipv4_in_cidr(ip, s)):
				return 1

	return 0


#
# Return 1 if IP is in the CIDR range.
#
def is_ipv4_in_cidr(ip, cidr):
	t = cidr.split('/')
	cidr_ip = t[0]
	cidr_m  = t[1]

	o = cidr_ip.split('.')
	cidr_ip = ((int(o[0])<<24) + (int(o[1]) << 16) + (int(o[2]) << 8) + (int(o[3])))

	cidr_mb = 0
	zeros = 32 - int(cidr_m)
	for b in range(0, zeros):
		cidr_mb = (cidr_mb << 1) | 0x01
	cidr_mb = 0xFFFFFFFF & ~cidr_mb

	o = ip.split('.')
	ip = ((int(o[0])<<24) + (int(o[1]) << 16) + (int(o[2]) << 8) + (int(o[3])))

	return ((cidr_ip & cidr_mb) == (ip & cidr_mb))


def shorten_port_name(port):
	if (port == OID_ERR):
		return 'UNKNOWN'
	
	if (port != None):
		port = port.replace('TenGigabitEthernet', 'te')
		port = port.replace('GigabitEthernet', 'gi')
		port = port.replace('FastEthernet', 'fa')
		port = port.replace('Te', 'te')
		port = port.replace('Gi', 'gi')
		port = port.replace('Fa', 'fa')

	return port


def shorten_host_name(host):
	if (host == None):
		return 'UNKNOWN'

	# Nexus appends (SERIAL) to hosts
	host = re.sub('\([^\(]*\)$', '', host)
	for domain in config.host_domains:
		host = host.replace(domain, '')

	return host


def convert_ip_int_str(iip):
	if (iip != None):
		ip = int(iip, 0)
		ip = '%i.%i.%i.%i' % (((ip >> 24) & 0xFF), ((ip >> 16) & 0xFF), ((ip >> 8) & 0xFF), (ip & 0xFF))
		return ip

	return 'UNKNOWN'


def add_l2_link(node):
	for link in l2links:
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

	l2links.append(node)


def main(argv):
	global max_depth
	global config

	print('MNet-Graph %s' % MNET_GRAPH_VERSION)
	print('Written by Michael Laforest <mjlaforest@gmail.com>')
	print

	opt_root_ip = None
	opt_dot = None
	opt_depth = 0
	opt_title = 'MNet Network Diagram'
	opt_conf = './mnet.conf'
	opt_catalog = None

	try:
		opts, args = getopt.getopt(argv, 'f:d:r:t:F:c:C:')
	except getopt.GetoptError:
		print('usage: mnet-graph.py -r <root IP> <-f <file>> [-d <max depth>] [-c <config file>] [-t <diagram title>] [-C <catalog file>]')
		sys.exit(1)
	for opt, arg in opts:
		if (opt == '-r'):
			opt_root_ip = arg
		if (opt == '-f'):
			opt_dot = arg
		if (opt == '-d'):
			opt_depth = int(arg)
			max_depth = int(arg)
		if (opt == '-t'):
			opt_title = arg
		if (opt == '-c'):
			opt_conf = arg
		if (opt == '-C'):
			opt_catalog = arg

	if ((opt_root_ip == None) | (opt_dot == None)):
		print('Invalid arguments.')
		return

	print('     Config file: %s' % opt_conf)
	print('       Root node: %s' % opt_root_ip)
	print('     Output file: %s' % opt_dot)
	print('     Crawl depth: %s' % opt_depth)
	print('   Diagram title: %s' % opt_title)
	print('Out Catalog file: %s' % opt_catalog)

	print('\n\n')

	# load config
	if (config.load(opt_conf) == 0):
		return

	# start
	crawl_node(opt_root_ip, opt_depth)
		
	# outputs
	output_stdout()

	if (opt_dot != None):
		output_dot(opt_dot, opt_title)

	if (opt_catalog != None):
		output_catalog(opt_catalog)


def output_stdout():
	print '-----'
	print '----- DEVICES'
	print '-----'

	for n in nodes:
		print('      Name: %s' % n['name'])
		print('        IP: %s' % n['ip'])
		print('  Platform: %s' % n['plat'])
		print('   Routing: %s' % ('yes' if (n['router'] == 1) else 'no'))
		print('   OSPF ID: %s' % n['ospf_id'])
		print('   BGP LAS: %s' % n['bgp_las'])
		print('  HSRP Pri: %s' % n['hsrp_pri'])
		print('  HSRP VIP: %s' % n['hsrp_vip'])
		print(' Stack Cnt: %i' % n['stack_count'])
		print('  VSS Mode: %i' % n['vss_enable'])
		print('VSS Domain: %s' % n['vss_domain'])
		print

	print '-----'
	print '----- LINKS'
	print '-----'

	for link in l2links:
		print('[%s] %s:%s -(%s)-> %s:%s' % (link['link_type'], link['lname'], link['lport'], link['llag'], link['rname'], link['rport']))
		if ((link['lifip'] != None) | (link['rifip'] != None)):
			print('    %s -> %s' % (link['lifip'], link['rifip']))

	print '-----'
	print '----- Summary'
	print '-----'

	print 'Discovered devices: %i' % (len(nodes))
	print 'Discovered links:   %i' % (len(l2links))


def output_dot(dot_file, title):
	global MNET_GRAPH_VERSION

	credits = '<table border="0"> \
				<tr> \
				 <td balign="right"> \
				  <font point-size="15"><b>$title$</b></font><br /> \
				  <font point-size="9">$date$</font><br /> \
				  Generated by MNet-Graph $ver$<br /> \
				  Written by Michael Laforest<br /> \
				 </td> \
				</tr> \
			   </table>'

	today = datetime.datetime.now()
	today = today.strftime('%Y-%m-%d %H:%M')
	credits = credits.replace('$ver$', MNET_GRAPH_VERSION)
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

	for n in nodes:
		node_label = '<font point-size="10"><b>%s</b></font><br /> \
						<font point-size="8"><i>%s</i></font><br /> \
						%s'	% (n['name'], n['ip'], n['plat'])
		node_style = 'solid'
		node_shape = 'ellipse'
		node_peripheries = 1

		if (n['vss_enable'] == 1):
			node_label += '<br />VSS %s' % n['vss_domain']
			node_peripheries = 2

		if (n['stack_count'] > 0):
			node_label += '<br />Stackwise %i' % n['stack_count']
			node_peripheries = n['stack_count']

		if (n['router'] == 1):
			node_shape = 'diamond'
			if (n['bgp_las'] != None):
				node_label += '<br />BGP %s' % n['bgp_las']
			if (n['ospf_id'] != None):
				node_label += '<br />OSPF %s' % n['ospf_id']
			if (n['hsrp_pri'] != None):
				node_label += '<br />HSRP VIP %s \
								<br />HSRP Pri %s' % (n['hsrp_vip'], n['hsrp_pri'])

		graph.add_node(
				pydot.Node(
					name = n['name'],
					label = '<%s>' % node_label,
					style = node_style,
					shape = node_shape,
					peripheries = node_peripheries
				)
		)

	for link in l2links:
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
		print 'Error: Output type "%s" does not exist.' % file_ext
	else:
		output_func(dot_file)
		print 'Created graph: %s' % (dot_file)


def output_catalog(filename):
	try:
		f = open(filename, 'w')
	except:
		print 'Unable to open catalog file "%s"' % filename
		return

	for n in nodes:
		# pull info here that wasn't needed for the graph
		serial = ''
		bootf = ''
		
		if (n['ip']):
			snmpobj = mnet_snmp(n['ip'])
			snmpobj.get_cred(config.snmp_creds)

			serial = snmpobj.get_val(OID_SYS_SERIAL)
			bootf  = snmpobj.get_val(OID_SYS_BOOT)

		f.write('"%s","%s","%s","%s","%s"\n' % (n['name'], n['ip'], n['plat'], serial, bootf))

	f.close()


if __name__ == "__main__":
	main(sys.argv[1:])
