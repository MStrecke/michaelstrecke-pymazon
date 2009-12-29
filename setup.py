#!/usr/bin/env python

from distutils.core import setup

setup(name='Pymazon',
      version='0.1beta',
      description='Python Based Downloader for the Amazon mp3 Store',
      author='S. Chris Colbert',
      author_email='sccolbert@gmail.com',
      url='http://code.google.com/p/pymazon/',
      packages=['pymazon'],
      scripts=['./bin/pymazon'],
      license='GPLv3',
      long_description=\
'''Pymazon is a Python implemented alternative to the Amazon mp3 downloader.
It allows you to download legally purchased mp3's from the Amazon mp3 store
using the .amz file provided by Amazon after the purchase. Pymazon can be
used as both a command line client or a gui (if PyQt4 is installed). The 
only hard external dependency is PyCrypto, which is available in the 
Ubuntu (and likely other distro's) repositories (python-crypto), 
and the cheese shop.''' 
     )
