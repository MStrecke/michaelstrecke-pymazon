"""
Pymazon - A Python based downloader for the Amazon.com MP3 store
Copyright (c) 2009 Steven C. Colbert

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import warnings
from ConfigParser import ConfigParser

def pymazon_showwarning(message, category, *args):
    print 'Warning:'
    print message
warnings.showwarning = pymazon_showwarning


# so they can spell them however they want
_toolkits = {'qt':'qt4', 'Qt':'qt4', 'qt4':'qt4', 'Qt4':'qt4', 'pyqt':'qt4',
             'PyQt':'qt4', 'Pyqt':'qt4', 'pyqt4':'qt4', 'PyQt4':'qt4',
             'Pyqt4':'qt4', 'gtk':'gtk', 'Gtk':'gtk', 'pygtk':'gtk',
             'PyGtk':'gtk', 'Pygtk':'gtk'}             


def _get_pymazon_dir():
    try:
        pymazon_dir = os.path.join(os.path.expanduser('~'), '.pymazon')
        if not os.path.exists(pymazon_dir):
            os.makedirs(pymazon_dir)
        if not os.access(pymazon_dir, os.W_OK):
            raise
        return pymazon_dir
    except:
        print ('Pymazon is unable to write to the Pymazon config '
               'directory: %s. This directory is required for proper '
               'Pymazon operation. Please make sure it exists and write '
               'access is granted. Then, restart Pymazon.' % pymazon_dir)
        sys.exit()
        
        
#-------------------------------------------------------------------------------
# Program-wide settings Class 
#-------------------------------------------------------------------------------

class PymazonSettingsError(Exception):
    pass


class PymazonSettings(object):   
            
    # some sensible defaults
    pymazon_dir = _get_pymazon_dir()
    save_dir = os.getcwd()
    amz_dir = os.getcwd()
    name_template = '${tracknum} - ${title}'
    toolkit = 'qt4'
    num_threads = 5      
    __all__ = ['pymazon_dir', 'save_dir', 'amz_dir', 'name_template', 'toolkit',
               'num_threads']   
            
    def __setattr__(self, attr, value):
        if attr not in PymazonSettings.__all__:
            msg = 'The specified setting is not a valid setting. '
            msg += 'Valid settings are: %s' % PymazonSettings.__all__
            raise PymazonSettingsError(msg)
        
        # handle the special cases
        if attr == 'name_template':
            if not self.__validate_name_template(value):
               # stay with the current
               return 
        elif attr == 'toolkit':
            # will print a warning if invalid
            if not self.__validate_toolkit(value):
                # stay with the current
                return
            value = _toolkits[value]
        elif attr == 'num_threads':
            # will convert to int and print a warning if invalid
            value = self.__validate_numthreads(value)
            if not value:
                # stay with the current
                return
        else:
            pass               
                
        setattr(PymazonSettings, attr, value)
            
    def __validate_name_template(self, templ):
        # make sure at least the title will be present, else default to safe.
        # this prevents malformed format names from saving just one file
        # for each track due to overwrites.
        template_string = str(templ)
        if '${title}'in template_string:
            return True
        else:
            return False
            
    def __validate_toolkit(self, toolkit):
        if toolkit not in _toolkits:
            msg = 'Invalid toolkit specified. '
            msg += 'Valid toolkit identifiers are: %s ' % _toolkits.keys()
            msg += 'Reverting to default: %s' % PymazonSettings.toolkit
            warnings.warn(msg)
            return False
        return True
            
    def __validate_numthreads(self, numthreads):
        msg = 'Invalid number of threads. Should be an integer >= 1, '
        msg += 'got "%s" instead. ' % numthreads
        msg += 'Reverting to default: %s.' % PymazonSettings.num_threads
        
        try:
            n = int(numthreads)
        except ValueError:            
            warnings.warn(msg)
            return False
        if n < 1:
            warnings.warn(msg)
            return False
        return n
        
            
#-------------------------------------------------------------------------------
# pymazonrc handling
#-------------------------------------------------------------------------------

def _handle_config_file():
    settings = PymazonSettings()
    config_file = os.path.join(settings.pymazon_dir, 'pymazonrc')
    if os.path.exists(config_file):
        cp = ConfigParser()
        cp.read(config_file)
        try:
            templ = cp.get('config', 'name_template')
            settings.name_template = templ
        except (NoOptionError, NoSectionError):
            pass
        try:
            toolkit = cp.get('config', 'toolkit')
            settings.toolkit = toolkit
        except (NoOptionError, NoSectionError):
            pass
        try:
            save_dir = cp.get('config', 'save_dir')
            settings.save_dir = save_dir
        except (NoOptionError, NoSectionError):
            pass
        try:
            amz_dir = cp.get('config', 'amz_dir')
            settings.amz_dir = amz_dir
        except (NoOptionError, NoSectionError):
            pass
        try:
            num_threads = cp.get('config', 'num_threads')
            settings.num_threads = num_threads
        except (NoOptionError, NoSectionError):
            pass
_handle_config_file()