#!/usr/bin/python

'''
	MNet Suite
	tracemac.py

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


	# mnet-tracemac.py -r <root IP> -m <MAC Address> [-c <config file>]
'''

import os
import re

from snmp import *
from config import mnet_config
from util import *
from _version import __version__

class mnet_tracemac:
	config = None
	nodes = []

	def __init__(self):
		self.config = mnet_config()

	def load_config(self, config_file):
		if (config_file):
			self.config.load(config_file)
	
	
	#
	# Connect to the node at the specified IP and search for the
	# specified MAC address in the table.
	#
	# Returns the IP to the next node or None
	#
	def trace(self, ip, mac_addr):
		snmpobj = mnet_snmp(ip)

		# find valid credentials for this node
		if (snmpobj.get_cred(self.config.snmp_creds) == 0):
			return None

		system_name = shorten_host_name(snmpobj.get_val(OID_SYSNAME), self.config.host_domains)

		print('%s (%s)' % (system_name, ip))

		# check for loops
		for n in self.nodes:
			if (n == system_name):
				print('\n**************************\n'
						'*** ENCOUNTERED A LOOP ***\n'
						'**************************\n\n'
						'This means the MAC address is likely attached to\n'
						'a transparent, unmanaged, or undiscoverable bridge\n'
						'somewhere between the nodes that were crawled.')
				return None
		self.nodes.append(system_name)

		# cache some common MIB trees
		vlan_vbtbl	= snmpobj.get_bulk(OID_VLANS)

		for vlan_row in vlan_vbtbl:
			for vlan_n, vlan_v in vlan_row:
				t = vlan_n.prettyPrint().split('.')
				vlan = int(t[15])

				if (vlan >= 1002):
					continue

				# change our SNMP credentials
				old_cred = snmpobj.v2_community
				snmpobj.v2_community = old_cred + '@' + str(vlan)

				cam_vbtbl = snmpobj.get_bulk(OID_VLAN_CAM)
				cam_match = None

				for cam_row in cam_vbtbl:
					for cam_n, cam_v in cam_row:
						if (mac_addr == cam_v):
							cam_match = cam_n
							break
					if (cam_match != None):
						break

				if (cam_match == None):
					# try next VLAN
					continue

				p = cam_match.prettyPrint().split('.')
				bridge_portnum = snmpobj.get_val(OID_BRIDGE_PORTNUMS +'.'+p[11]+'.'+p[12]+ '.'+p[13]+'.'+p[14]+'.'+p[15]+'.'+p[16])

				ifidx = snmpobj.get_val(OID_IFINDEX + '.' + bridge_portnum)

				# restore SNMP credentials
				snmpobj.v2_community = old_cred
				
				port = snmpobj.get_val(OID_IFNAME + '.' + ifidx)

				print('          VLAN: %s' % vlan)
				print('          Port: %s' % port)
				
				# get list of CDP neighbors
				cdp_vbtbl = snmpobj.get_bulk(OID_CDP)
				if (cdp_vbtbl == None):
					return None

				for cdp_row in cdp_vbtbl:
					for cdp_n, cdp_v in cdp_row:
						# process only if this row is a CDP_DEVID
						if (cdp_n.prettyPrint().startswith(OID_CDP_DEVID) == 0):
							continue
						
						t = cdp_n.prettyPrint().split('.')
						if (ifidx != t[14]):
							continue

						# get remote IP
						rip = snmpobj.cache_lookup(cdp_vbtbl, OID_CDP_IPADDR + '.' + ifidx + '.' + t[15])
						rip = convert_ip_int_str(rip)

						rname = shorten_host_name(cdp_v.prettyPrint(), self.config.host_domains)

						print('     Next Node: %s' % rname)
						print('  Next Node IP: %s' % rip)

						return rip

				return None

		print('  MAC not found in CAM table.')
		return None


	#
	# Parse an ASCII MAC address string to a hex string.
	# 1122.3344.5566
	# 11:22:33:44:55:66
	#
	def parse_mac(self, mac_str):
		mac_str = re.sub('[\.:]', '', mac_str)

		if (len(mac_str) != 12):
			return None

		mac_hex = ''
		for i in range(0, len(mac_str), 2):
			mac_hex += chr(int(mac_str[i:i+2], 16))

		return mac_hex


