#!/usr/bin/python

'''
	MNet Suite
	mnet.py

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
import datetime
import os

import mnetsuite

def print_syntax():
	print('Usage:\n'
			'  mnet.py graph -r <root IP>\n'
			'                -f <file>\n'
			'                [-d <max depth>]\n'
			'                [-c <config file>]\n'
			'                [-t <diagram title>]\n'
			'                [-C <catalog file>]\n'
			'\n'
			'  mnet.py tracemac -r <root IP>\n'
			'                   -m <MAC Address>\n'
			'                   [-c <config file>]\n'
			'\n'
			'  mnet.py config\n'
		)


def print_banner():
	print('MNet Suite v%s' % mnetsuite.__version__)
	print('Written by Michael Laforest <mjlaforest@gmail.com>')
	print('')


def main(argv):
	opt_root_ip = None
	if (len(argv) < 1):
		print_banner()
		print_syntax()
		return

	mod = argv[0]
	if (mod == 'graph'):
		print_banner()
		graph(argv[1:])
	elif (mod == 'tracemac'):
		print_banner()
		tracemac(argv[1:])
	elif (mod == 'config'):
		generate_config()
	else:
		print_banner()
		print_syntax()


def graph(argv):
	max_depth = 0

	graph = mnetsuite.mnet_graph()

	opt_dot = None
	opt_depth = 0
	opt_title = 'MNet Network Diagram'
	opt_conf = './mnet.conf'
	opt_catalog = None

	try:
		opts, args = getopt.getopt(argv, 'f:d:r:t:F:c:C:')
	except getopt.GetoptError:
		print_syntax()
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
		print_syntax()
		print('Invalid arguments.')
		return

	print('     Config file: %s' % opt_conf)
	print('       Root node: %s' % opt_root_ip)
	print('     Output file: %s' % opt_dot)
	print('     Crawl depth: %s' % opt_depth)
	print('   Diagram title: %s' % opt_title)
	print('Out Catalog file: %s' % opt_catalog)

	print('\n\n')

	# load the config
	if (graph.load_config(opt_conf) == 0):
		return
	graph.set_max_depth(opt_depth)

	# start
	graph.crawl(opt_root_ip)
		
	# outputs
	graph.output_stdout()

	if (opt_dot != None):
		graph.output_dot(opt_dot, opt_title)

	if (opt_catalog != None):
		graph.output_catalog(opt_catalog)


def tracemac(argv):
	trace = mnetsuite.mnet_tracemac()

	opt_root_ip = None
	opt_conf = './mnet.conf'
	opt_mac = None

	try:
		opts, args = getopt.getopt(argv, 'r:c:m:')
	except getopt.GetoptError:
		print_syntax()
		return
	for opt, arg in opts:
		if (opt == '-r'):
			opt_root_ip = arg
		if (opt == '-c'):
			opt_conf = arg
		if (opt == '-m'):
			opt_mac = arg

	if ((opt_root_ip == None) | (opt_mac == None)):
		print_syntax()
		print('Invalid arguments.')
		return

	print('     Config file: %s' % opt_conf)
	print('       Root node: %s' % opt_root_ip)
	print('     MAC address: %s' % opt_mac)

	print('\n\n')

	mac = trace.parse_mac(opt_mac)
	if (mac == None):
		print('MAC address is invalid.')
		return

	# load config
	trace.load_config(opt_conf)

	# start
	print('Start trace.')
	print('------------')

	ip = opt_root_ip
	while (ip != None):
		ip = trace.trace(ip, mac)
		print('------------')

	print('Trace complete.\n')


def generate_config():
	conf = mnetsuite.config.mnet_config()
	print('%s' % conf.generate_new())


if __name__ == "__main__":
	main(sys.argv[1:])

