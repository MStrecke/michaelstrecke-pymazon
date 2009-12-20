"""
pymazon - A Python based downloader for the Amazon.com MP3 store
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
from optparse import OptionParser
import base64
import re
import urllib2
from Crypto.Cipher import DES

# the key and initial value for the .amz DES CBC encryption
KEY = '\x29\xAB\x9D\x18\xB2\x44\x9E\x31'
IV = '\x5E\x72\xD7\x9A\x11\xB3\x4F\xEE'


class ParseException(Exception):
    pass

class AmzParser(object):
    def __init__(self, amz_data):        
        self.amz = amz_data        
        self.re_tag = re.compile(r'<.*?>')        
        self.re_tracks = re.compile(r'<track>.*?</track>', re.DOTALL)
        self.re_uri = re.compile(r'<location>.*?</location>', re.DOTALL)
        self.re_artist = re.compile(r'<creator>.*?</creator>', re.DOTALL)
        self.re_title = re.compile(r'<title>.*?</title>', re.DOTALL)
        self.re_tracknum = re.compile(r'<trackNum>.*?</trackNum>', re.DOTALL)
        self.re_album = re.compile(r'<album>.*?</album>', re.DOTALL)
        
    def strip_tags(self, phrase):        
        tags = self.re_tag.findall(phrase)
        ltag = tags[0]
        rtag = tags[-1]        
        return phrase.replace(ltag, '').replace(rtag, '')        
        
    def parse(self):
        parsed_tracks = []
        tracks = self.re_tracks.findall(self.amz)
        if not tracks:
            print tracks
            raise ParseException('Failure Parsing Tracks')
        for track in tracks:
            match = self.re_uri.search(track)
            if not match:
                raise ParseException('Failure Parsing URI')
            uri = self.strip_tags(match.group()).replace('&amp;', '&')
            
            match = self.re_artist.search(track)
            if not match:
                raise ParseException('Failure Parsing Artist')
            artist = self.strip_tags(match.group())
            
            match = self.re_title.search(track)
            if not match:
                raise ParseException('Failure Parsing Title')
            title = self.strip_tags(match.group())
            
            match = self.re_tracknum.search(track)
            if not match:
                raise ParseException('Failure Parsing Track Number')
            tracknum = self.strip_tags(match.group())
            
            match = self.re_album.search(track)
            if not match:
                raise ParseException('Failure Parsing Album Name')
            album = self.strip_tags(match.group())
            
            pd = {'uri': uri, 'artist': artist, 'title': title, 
                  'tracknum': tracknum, 'album': album}
                  
            parsed_tracks.append(pd)
            
        return parsed_tracks
        
class Decryptor(object):
    def __init__(self, f):
        self.key = KEY
        self.iv = IV
        self.d_obj = DES.new(self.key, DES.MODE_CBC, IV)
        self.data = f.read()
        
    def decrypt(self):
        cipher = base64.b64decode(self.data)
        return self.d_obj.decrypt(cipher)
        
class Downloader(object):
    def __init__(self, dir_name, track_list):
        self.track_list = track_list
        self.dir_name = dir_name
        self.redirects = urllib2.HTTPRedirectHandler()
        self.cookies =  urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(self.redirects, self.cookies)
        
    def download(self):
        for track in self.track_list:
            fname = os.path.join(self.dir_name, track['title']+'.mp3')
            save_file = open(fname, 'wb')
            request = urllib2.Request(track['uri'])
            url = self.opener.open(request)
            print 'downloading track %s by %s on album %s' % \
                  (track['title'], track['artist'], track['album'])
            mp3 = url.read()
            save_file.write(mp3)
            save_file.close()       
        

if __name__=='__main__':
    parser = OptionParser()    
    parser.add_option('-d', '--dir', dest='save_dir', 
                      help='Directory to save the downloads', default=os.getcwd())
                      
    (options, args) = parser.parse_args()
    
    if len(args)!=1:
        raise ValueError('A single positional argument must be supplied.')
        sys.exit()
        
    amz_file = args[0]
    if not os.path.isfile(amz_file):
        raise ValueError('File not Found.')
        sys.exit()
    if not amz_file.endswith('.amz'):
        raise ValueError('Positional argument must be a path to a .amz file.')
        sys.exit()
        
    save_dir = options.save_dir   
    if not os.access(save_dir, os.W_OK):
        raise RuntimeError('Unable to write to target directory. Ensure the directory exits and write permission is granted.')
        sys.exit()
        
    f = open(amz_file, 'r')
    dc = Decryptor(f)
    f.close()

    prsr = AmzParser(dc.decrypt())
    parsed_tracks = prsr.parse()
    
    dl = Downloader(options.save_dir, parsed_tracks)
    dl.download()
    print 'Downloads Complete!'
    
    
    
    
