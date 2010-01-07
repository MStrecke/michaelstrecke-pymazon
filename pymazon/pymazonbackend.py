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

import os, sys, base64, re, urllib2, threading, logging, datetime, cStringIO

try:
    from Crypto.Cipher import DES
except ImportError:
    msg = 'Unable to import PyCrypto. Make sure it is installed '
    msg += 'and available on the Python path.'
    raise ImportError(msg)
    

# the key and initial value for the .amz DES CBC encryption
KEY = '\x29\xAB\x9D\x18\xB2\x44\x9E\x31'
IV = '\x5E\x72\xD7\x9A\x11\xB3\x4F\xEE'

logger = logging.getLogger('pymazon.pymazonbackend')

#-------------------------------------------------------------------------------
# The work horse backend
#-------------------------------------------------------------------------------
class ParseException(Exception):
    pass


class AmzParser(object):
    def __init__(self, amz_data):        
        self.amz = amz_data        
        self.re_tag = re.compile(r'<.*?>')        
        self.re_tracks = re.compile(r'<track>.*?</track>', re.DOTALL)
        self.re_url = re.compile(r'<location>.*?</location>')
        self.re_artist = re.compile(r'<creator>.*?</creator>')
        self.re_title = re.compile(r'<title>.*?</title>')
        self.re_tracknum = re.compile(r'<trackNum>.*?</trackNum>')
        self.re_album = re.compile(r'<album>.*?</album>')
        self.re_image = re.compile(r'<image>.*?</image>')
        self.re_filesize = re.compile(r'<meta.*?fileSize">.*?</meta>')        
        
    def strip_tags(self, phrase):        
        tags = self.re_tag.findall(phrase)
        ltag = tags[0]
        rtag = tags[-1]        
        return phrase.replace(ltag, '').replace(rtag, '').replace('&amp;', '&')     
        
    def parse(self):
        parsed_tracks = []
        tracks = self.re_tracks.findall(self.amz)
        if not tracks:            
            raise ParseException('Failure Parsing Tracks')
        for track in tracks:
            match = self.re_url.search(track)
            if not match:
                raise ParseException('Failure Parsing URL')
            url = self.strip_tags(match.group())
            
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
            
            match = self.re_image.search(track)
            if not match:
                raise ParseException('Failure Parsing Image')
            image = self.strip_tags(match.group())
            
            match = self.re_filesize.search(track)
            if not match:
                raise ParseException('Failure Parsing File Size')
            filesize = self.strip_tags(match.group())
            
            pd = {'url': url, 'artist': artist, 'title': title, 
                  'tracknum': tracknum, 'album': album, 'image': image,
                  'filesize': filesize}
                  
            parsed_tracks.append(Track(pd))
            
        return parsed_tracks


class Track(object):
    def __init__(self, track_info):       
        for key, value in track_info.iteritems():
            setattr(self, key, value)
        self.status = ''
        
    def __str__(self):
        return str(self.__dict__)
        
        
class Decryptor(object):
    def __init__(self, f):
        self.key = KEY
        self.iv = IV
        self.d_obj = DES.new(self.key, DES.MODE_CBC, IV)
        self.data = f.read()
        
    def decrypt(self):
        cipher = base64.b64decode(self.data)
        return self.d_obj.decrypt(cipher)
        
        
class Downloader(threading.Thread):
    '''
    Downloader Status Codes emitted to the callback:
    
    0 - Connecting
    1 - Downloading Percent
    2 - Complete
    3 - Error
    4 - Downloading Finished
    '''
    
    def __init__(self, dir_name, track_list, callback):
        super(Downloader, self).__init__()
        for track in track_list:
            if type(track) != Track:
                raise ValueError('track must be of type Track')
        self.track_list = track_list
        self.dir_name = dir_name
        self.redirects = urllib2.HTTPRedirectHandler()
        self.cookies =  urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(self.redirects, self.cookies)
        self.callback = callback
        self.abort = False
        
    def kill(self):
        self.abort = True
        
    def run(self):
        for track in self.track_list:
            if self.abort:
                break
            
            # Create the URL Request
            request = urllib2.Request(track.url)
            
            self.callback(track, 0)
            try:
                url = self.opener.open(request)
            except urllib2.URLError:
                logger.error('Opening request %s' % track)
                self.callback(track, 3)
                continue
            
            # Download the track
            fs = int(track.filesize)
            perc_complete = 0
            chunk_size = fs / 100
            buf = cStringIO.StringIO()
            self.callback(track, 1, perc_complete)
            try:
                while True:
                    chunk = url.read(chunk_size)
                    if not chunk:
                        break
                    buf.write(chunk)
                    perc_complete += 1
                    if perc_complete > 100:
                        perc_complete = 100
                    self.callback(track, 1, perc_complete)
                mp3 = buf.getvalue()
            except:
                logger.error('Reading from opened url %s' % track)
                self.callback(track, 3)
                continue 
            buf.close()
            
            if len(mp3) != fs:
                logger.error('Expected file size != downloaded size %s' 
                             % track)
                self.callback(track, 3)
                continue
            
            # Write track to File
            try:
                fname = os.path.join(self.dir_name, track.title + '.mp3')
                save_file = open(fname, 'wb')
                save_file.write(mp3)
                save_file.close()    
                self.callback(track, 2)
            except:                
                logger.error('Writing to file %s' % track)
                self.callback(track, 3)
                continue
        
        if not self.abort:
            self.callback(None, 4)   
            

def parse_tracks(filename):
    f = open(filename, 'r')
    dc = Decryptor(f)
    f.close()
    prsr = AmzParser(dc.decrypt())
    parsed_tracks = prsr.parse()
    return parsed_tracks