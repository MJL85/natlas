#!/usr/bin/python

'''
        natlas
        natlas-cli.py

        Michael Laforest
        mjlaforest@gmail.com

        Copyright (C) 2015-2018 Michael Laforest

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
import os
import natlas


def mod_load(mod):
    '''
    The function mod_load() is called by natlas to load information about
    the module.  This information is available to the user from the cli by
    using:
        # natlas-cli list
        # natlas-cli help <name>
        etc
    '''


    '''
    The name of your module.  This is also the subcommand you will run in natlas.
    For example, if you set name to 'mymodule' then you would run it with:
         # natlas-cli mymodule <options>

    The name can not include any whitespaces.
    '''
    mod.name         = 'TemplateModule'


    '''
    What version number your module is.  The version number is arbitrary
    and can be any string.
    '''

    mod.version      = '0.1'

    '''
    Your name.
    '''
    mod.author       = 'Michael Laforest'


    '''
    Your email address.
    '''
    mod.authoremail  = 'mjlaforest@gmail.com'


    '''
    What will be displayed to the console when a user runs
        # natlas-cli list

    This should be brief, just a few words.  A more descriptive
    explaination of your module should be set under the 'help'
    attribute below.
    '''
    mod.about        = 'Template module'

    '''
    The command line options available for your module.
    If you have multiple combinations you can set this to an array
    of strings rather than a single string.

    Example:
        mod.syntax = '-n <opt> -g <opt> -x'
        
         The outout of help will be:
                name -n <opt> -g <opt> -x
        
        mod.syntax = ['-n <opt>', '-g <opt> -x']
        
            The outout of help will be:
                name -n <opt>
                name -g <opt> -x
    '''
    mod.syntax       = '''
                        -n <opt> -x
                        '''

    '''
    Provide an example of typical output users will see when
    running this module.  If left blank no example will be
    shown from the help.
    '''
    mod.example      = ''


    '''
    A more descriptive definition of your module.  Where the 'about' section
    is brief, this section should be more explicit.

    Indents will be removed.
    '''
    mod.help         = '''
                       This is a blank template showing how
                       you can create your own module.  Simply
                       modify some attributes and add
                       some code below.

                       Your module will then show up with
                       # natlas-cli list
                       '''

    '''
    If set to 1, natlas will display the total run time after your
    module has compeleted.  If is recommended to leave this as 1
    unless the stdout needs to be formatted specifically.
    '''
    mod.notimer      = 1

    '''
    If set to 1, natlas will load the configuration file prior to calling
    your entry function.

    The configuration file can be specified by the user with -c, or the
    default will be used (./natlas.conf).  The configuration file is needed
    for several API functions to work correctly, such as discover_network().
    '''
    mod.preload_conf = 1

    '''
    What natlas version is required for your module.  natlas will only allow
    your module to run if it meets the minimum version specified here.
    '''
    mod.require_api = '999'

    return 1



def mod_entry(natlas_obj, argv):
    '''
    This function is called when a user runs your module.
    natlas_obj is an initialized natlas object needed by the API.
    argv is a standard argv list from the CLI, minus -c if natlas preloaded the config.

    This function must always return one of the below codes:

        natlas.RETURN_OK        - your module finished with no errors
        natlas.RETURN_ERR       - your module had an error
        natlas.RETURN_SYNTAXERR - your module had a syntax error from the cli
    '''
    return natlas.RETURN_OK

