__license__ = '''
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

from setuptools import setup
import os

import imp
_version = imp.load_source('', 'mnetsuite/_version.py')

long_description = open('README.md').read()

setup(
	name				= 'mnet',
	version				= _version.__version__,
	author				= 'Michael Laforest',
	author_email		= 'mjlaforest@gmail.com',
	license				= 'LICENSE',
	url					= 'http://github.com/MJL85/mnet/',

	description			= 'MNet Suite is a collection of Python tools for network professionals.',
	long_description	= long_description,
	keywords			= 'python network cisco diagram snmp cdp',

	classifiers = [
		'Development Status :: 4 - Beta',
		'Intended Audience :: Information Technology',
		'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Topic :: Utilities'
	],

	packages = ['mnetsuite'],
	include_package_data = True,

	scripts = [ 'mnet.py' ],

	install_requires = [
		'pysnmp>=4.2.5',
		'pyparsing==2.0.6',	
		'pydot2',
		'netaddr>=0.7.14'
	]
)

