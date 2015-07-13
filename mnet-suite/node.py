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

class mnet_node:
	name		= None
	ip			= None
	plat		= None
	router		= None
	ospf_id		= None
	bgp_las		= None
	hsrp_pri	= None
	hsrp_vip	= None
	stack_count	= None
	vss_enable	= None
	vss_domain	= None

	def __init__(
				self,
				name			= None,
				ip				= None,
				plat			= None,
				router			= None,
				ospf_id			= None,
				bgp_las			= None,
				hsrp_pri		= None,
				hsrp_vip		= None,
				stack_count		= None,
				vss_enable		= None,
				vss_domain		= None
			):
		self.name				= name
		self.ip					= ip
		self.plat				= plat
		self.router				= router
		self.ospf_id			= ospf_id
		self.bgp_las			= bgp_las
		self.hsrp_pri			= hsrp_pri
		self.hsrp_vip			= hsrp_vip
		self.stack_count		= stack_count
		self.vss_enable			= vss_enable
		self.vss_domain			= vss_domain

