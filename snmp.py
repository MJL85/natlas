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

OID_ERR			= 'No Such Object currently exists at this OID'
OID_ERR_INST	= 'No Such Instance currently exists at this OID'

class mnet_snmp:
	_cred = []
	_ip = None

	def __init__(self, ip):
		self._cred = []
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
			
			self._cred = cred

			community = cred['community']

			cmdGen = cmdgen.CommandGenerator()
			errIndication, errStatus, errIndex, varBinds = cmdGen.getCmd(
					cmdgen.CommunityData(community),
					cmdgen.UdpTransportTarget((self._ip, SNMP_PORT)),
					'1.3.6.1.2.1.1.5.0',
					lookupNames = False, lookupValues = True
			)
			if errIndication:
				continue
			else:
				return 1

		return 0

	#
	# Get single SNMP value at OID.
	#
	def get_val(self, oid):
		community = self._cred['community']

		cmdGen = cmdgen.CommandGenerator()
		errIndication, errStatus, errIndex, varBinds = cmdGen.getCmd(
				cmdgen.CommunityData(community),
				cmdgen.UdpTransportTarget((self._ip, SNMP_PORT), retries=2),
				oid, lookupNames = False, lookupValues = True
		)

		if errIndication:
			print '[E] get_snmp_val(%s): %s' % (community, errIndication)
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
		community = self._cred['community']

		cmdGen = cmdgen.CommandGenerator()
		errIndication, errStatus, errIndex, varBindTable = cmdGen.bulkCmd(
				cmdgen.CommunityData(community),
				cmdgen.UdpTransportTarget((self._ip, SNMP_PORT), timeout=30, retries=2),
				0, 10,
				oid,
				lookupNames = False, lookupValues = True
		)

		if errIndication:
			print '[E] get_snmp_bulk(%s): %s' % (community, errIndication)
		else:
			ret = []
			for r in varBindTable:
				for n, v in r:
					if (n.prettyPrint().startswith(oid) == 0):
						return ret
					ret.append(r)
			return ret

		return None


	#
	# Lookup a value from the return table of get_bulk()
	#
	def cache_lookup(self, varBindTable, name):
		for r in varBindTable:
			for n, v in r:
				if (n.prettyPrint() == name):
					return v.prettyPrint()
		return None
