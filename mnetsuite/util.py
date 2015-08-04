#!/usr/bin/python

'''
	MNet Suite
	util.py

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

# Set the below line =0 if you do not want to use PyNetAddr
USE_NETADDR = 1 

import re
import struct
import binascii

from snmp import *
from config import mnet_config

if (USE_NETADDR == 1):
	from netaddr import IPAddress, IPNetwork


def get_net_bits_from_mask(netm):
	cidr = 0

	mt = netm.split('.')
	for b in range(0, 4):
		v = int(mt[b])
		while (v > 0):
			if (v & 0x01):
				cidr += 1
			v = v >> 1

	return cidr


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


#
# Shorten the port name string.
#
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


#
# Shorten the hostname by removing any defined domain suffixes.
#
def shorten_host_name(host, domains):
	if (host == None):
		return 'UNKNOWN'

	# some Motorola devices report as hex strings
#	if (host.startswith('0x')):
#		try:
#			host = binascii.unhexlify(host[2:])
#		except:
#			pass

	# Nexus appends (SERIAL) to hosts
	host = re.sub('\([^\(]*\)$', '', host)
	for domain in domains:
		host = host.replace(domain, '')

	host = re.sub('-', '_', host)
	return host


#
# Return a string representation of an IPv4 address
#
def convert_ip_int_str(iip):
	if ((iip != None) & (iip != '')):
		ip = int(iip, 0)
		ip = '%i.%i.%i.%i' % (((ip >> 24) & 0xFF), ((ip >> 16) & 0xFF), ((ip >> 8) & 0xFF), (ip & 0xFF))
		return ip

	return 'UNKNOWN'


def get_module_from_interf(port):
	try:
		s = re.search('[^\d]*(\d*)/\d*/\d*', port)
		if (s):
			return s.group(1)
	except:
		pass

	return '1'

