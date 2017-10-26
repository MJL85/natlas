#!/usr/bin/python

'''
	MNet Suite
	snmp.py

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

from pysnmp.entity.rfc3413.oneliner import cmdgen

SNMP_PORT = 161

OID_SYSNAME		= '1.3.6.1.2.1.1.5.0'

OID_SYS_SERIAL	= '1.3.6.1.4.1.9.3.6.3.0'
OID_SYS_BOOT	= '1.3.6.1.4.1.9.2.1.73.0'

OID_IFNAME		= '1.3.6.1.2.1.31.1.1.1.1'				# + ifidx (BULK)

OID_CDP			= '1.3.6.1.4.1.9.9.23.1.2.1.1'			# (BULK)
OID_CDP_IPADDR	= '1.3.6.1.4.1.9.9.23.1.2.1.1.4'
OID_CDP_IOS		= '1.3.6.1.4.1.9.9.23.1.2.1.1.5'
OID_CDP_DEVID	= '1.3.6.1.4.1.9.9.23.1.2.1.1.6'		# + .ifidx.53
OID_CDP_DEVPORT	= '1.3.6.1.4.1.9.9.23.1.2.1.1.7'
OID_CDP_DEVPLAT	= '1.3.6.1.4.1.9.9.23.1.2.1.1.8'
OID_CDP_INT		= '1.3.6.1.4.1.9.9.23.1.1.1.1.'			# 6.ifidx

OID_LLDP	     = '1.0.8802.1.1.2.1.4'
OID_LLDP_TYPE    = '1.0.8802.1.1.2.1.4.1.1.4.0'
OID_LLDP_DEVID   = '1.0.8802.1.1.2.1.4.1.1.5.0'
OID_LLDP_DEVPORT = '1.0.8802.1.1.2.1.4.1.1.7.0'
OID_LLDP_DEVNAME = '1.0.8802.1.1.2.1.4.1.1.9.0'
OID_LLDP_DEVDESC = '1.0.8802.1.1.2.1.4.1.1.10.0'
OID_LLDP_DEVADDR = '1.0.8802.1.1.2.1.4.2.1.5.0'

OID_TRUNK_ALLOW  = '1.3.6.1.4.1.9.9.46.1.6.1.1.4'		# + ifidx (Allowed VLANs)
OID_TRUNK_NATIVE = '1.3.6.1.4.1.9.9.46.1.6.1.1.5'		# + ifidx (Native VLAN)
OID_TRUNK_VTP	 = '1.3.6.1.4.1.9.9.46.1.6.1.1.14'		# + ifidx (VTP Status)
OID_LAG_LACP	 = '1.2.840.10006.300.43.1.2.1.1.12'	# + ifidx (BULK)

OID_IP_ROUTING	= '1.3.6.1.2.1.4.1.0'
OID_IF_VLAN		= '1.3.6.1.4.1.9.9.68.1.2.2.1.2'		# + ifidx (BULK)

OID_IF_IP		= '1.3.6.1.2.1.4.20.1'					# (BULK)
OID_IF_IP_ADDR	= '1.3.6.1.2.1.4.20.1.2'				# + a.b.c.d = ifid
OID_IF_IP_NETM	= '1.3.6.1.2.1.4.20.1.3.'				# + a.b.c.d

OID_SVI_VLANIF	= '1.3.6.1.4.1.9.9.128.1.1.1.1.3'		# cviRoutedVlanIfIndex

OID_ETH_IF		= '1.3.6.1.2.1.2.2.1'					# ifEntry
OID_ETH_IF_TYPE	= '1.3.6.1.2.1.2.2.1.3'					# ifEntry.ifType	24=loopback
OID_ETH_IF_DESC	= '1.3.6.1.2.1.2.2.1.2'					# ifEntry.ifDescr

OID_OSPF		= '1.3.6.1.2.1.14.1.2.0'
OID_OSPF_ID		= '1.3.6.1.2.1.14.1.1.0'

OID_BGP_LAS		= '1.3.6.1.2.1.15.2.0'

OID_HSRP_PRI	= '1.3.6.1.4.1.9.9.106.1.2.1.1.3.1.10'
OID_HSRP_VIP	= '1.3.6.1.4.1.9.9.106.1.2.1.1.11.1.10'

OID_STACK		= '1.3.6.1.4.1.9.9.500'
OID_STACK_NUM	= '1.3.6.1.4.1.9.9.500.1.2.1.1.1'
OID_STACK_ROLE	= '1.3.6.1.4.1.9.9.500.1.2.1.1.3'
OID_STACK_PRI	= '1.3.6.1.4.1.9.9.500.1.2.1.1.4'
OID_STACK_MAC	= '1.3.6.1.4.1.9.9.500.1.2.1.1.7'
OID_STACK_IMG	= '1.3.6.1.4.1.9.9.500.1.2.1.1.8'

OID_VSS_MODULES = '1.3.6.1.4.1.9.9.388.1.4.1.1.1'		# .modidx = 1
OID_VSS_MODE	= '1.3.6.1.4.1.9.9.388.1.1.4.0'
OID_VSS_DOMAIN	= '1.3.6.1.4.1.9.9.388.1.1.1.0'

OID_ENTPHYENTRY_CLASS    = '1.3.6.1.2.1.47.1.1.1.1.5'		# + .modifx (3=chassis) (9=module)
OID_ENTPHYENTRY_SOFTWARE = '1.3.6.1.2.1.47.1.1.1.1.9'		# + .modidx
OID_ENTPHYENTRY_SERIAL   = '1.3.6.1.2.1.47.1.1.1.1.11'		# + .modidx
OID_ENTPHYENTRY_PLAT     = '1.3.6.1.2.1.47.1.1.1.1.13'		# + .modidx

# mnet-tracemac
OID_VLANS			= '1.3.6.1.4.1.9.9.46.1.3.1.1.2'
OID_VLAN_CAM		= '1.3.6.1.2.1.17.4.3.1.1'

OID_BRIDGE_PORTNUMS	= '1.3.6.1.2.1.17.4.3.1.2'
OID_IFINDEX			= '1.3.6.1.2.1.17.1.4.1.2'

OID_ERR			= 'No Such Object currently exists at this OID'
OID_ERR_INST	= 'No Such Instance currently exists at this OID'

# OID_ENTPHYENTRY_CLASS values
ENTPHYCLASS_OTHER         = 1
ENTPHYCLASS_UNKNOWN       = 2
ENTPHYCLASS_CHASSIS       = 3
ENTPHYCLASS_BACKPLANE     = 4
ENTPHYCLASS_CONTAINER     = 5
ENTPHYCLASS_POWERSUPPLY   = 6
ENTPHYCLASS_FAN           = 7
ENTPHYCLASS_SENSOR        = 8
ENTPHYCLASS_MODULE        = 9
ENTPHYCLASS_PORT          = 10
ENTPHYCLASS_STACK         = 11
ENTPHYCLASS_PDU           = 12

class mnet_snmp:
	success = 0
	ver = 0
	v2_community = None
	_ip = None

	def __init__(self, ip='0.0.0.0'):
		self.success = 0
		self.ver = 0
		self.v2_community = None
		self._ip = ip

	#
	# Try to find valid SNMP credentials in the provided list.
	# Returns 1 if success, 0 if failed.
	#
	def get_cred(self, snmp_creds):
		for cred in snmp_creds:
			# we don't currently support anything other than SNMPv2
			if (cred['ver'] != 2):
				continue

			community = cred['community']

			cmdGen = cmdgen.CommandGenerator()
			errIndication, errStatus, errIndex, varBinds = cmdGen.getCmd(
					cmdgen.CommunityData(community),
					cmdgen.UdpTransportTarget((self._ip, SNMP_PORT)),
					'1.3.6.1.2.1.1.5.0',
					lookupNames = False, lookupValues = False
			)
			if errIndication:
				continue
			else:
				self.ver = 2
				self.success = 1
				self.v2_community = community

				return 1

		return 0

	#
	# Get single SNMP value at OID.
	#
	def get_val(self, oid):
		cmdGen = cmdgen.CommandGenerator()
		errIndication, errStatus, errIndex, varBinds = cmdGen.getCmd(
				cmdgen.CommunityData(self.v2_community),
				cmdgen.UdpTransportTarget((self._ip, SNMP_PORT), retries=2),
				oid, lookupNames = False, lookupValues = False
		)

		if errIndication:
			print '[E] get_snmp_val(%s): %s' % (self.v2_community, errIndication)
		else:
			r = varBinds[0][1].prettyPrint()
			if ((r == OID_ERR) | (r == OID_ERR_INST)):
				return None
			return r

		return None


	#
	# Get bulk SNMP value at OID.
	#
	# Returns 1 on success, 0 on failure.
	#
	def get_bulk(self, oid):
		cmdGen = cmdgen.CommandGenerator()
		errIndication, errStatus, errIndex, varBindTable = cmdGen.bulkCmd(
				cmdgen.CommunityData(self.v2_community),
				cmdgen.UdpTransportTarget((self._ip, SNMP_PORT), timeout=30, retries=2),
				0, 10,
				oid,
				lookupNames = False, lookupValues = False
		)

		if errIndication:
			print '[E] get_snmp_bulk(%s): %s' % (self.v2_community, errIndication)
		else:
			ret = []
			for r in varBindTable:
				for n, v in r:
					n = str(n)
					if (n.startswith(oid) == 0):
						return ret
					ret.append(r)
			return ret

		return None


	#
	# Lookup a value from the return table of get_bulk()
	#
	def cache_lookup(self, varBindTable, name):
		if (varBindTable == None):
			return None

		for r in varBindTable:
			for n, v in r:
				n = str(n)
				if (n == name):
					return v.prettyPrint()
		return None

