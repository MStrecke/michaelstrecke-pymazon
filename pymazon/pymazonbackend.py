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

import os, sys, base64, re, urllib2, threading, logging, datetime, cStringIO, \
       string
from xml.etree import cElementTree
from collections import deque


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

# the default format string for file save name
SAVE_TEMPL = string.Template('${tracknum} - ${title}')

#-------------------------------------------------------------------------------
# The work horse backend
#-------------------------------------------------------------------------------
def set_save_templ(templ_string):
    # make sure at least the title will be present, else default to safe.
    if '${title}' not in templ_string:
        return
    if type(templ_string) != str:
        return
    global SAVE_TEMPL
    SAVE_TEMPL = string.Template(templ_string)


class ImageCache:
    def __init__(self):
        self.cache = {}        
        
    def _download(self, url):
        # Download the image data:
        handle = urllib2.urlopen(url)
        data = handle.read()
        handle.close()        
        return data
        
    def get(self, url):
        if url in self.cache:
            return self.cache[url]
        else:
            # Try to nab the url. If we don't succeed, oh well:
            try:    
                pixbuf = self._download(url)
            except: 
                pixbuf = ''        
            # Write whatever we got to the cache, and return it:
            self.cache[url] = pixbuf
            return pixbuf
            
    
class ParseException(Exception):
    pass


class AmzParser(object):
    
    namespace = 'http://xspf.org/ns/0/'    
            
    def __call__(self, filename):
        f = open(filename, 'rb')
        data = f.read()
        f.close()
        decryptor = Decryptor()
        amz_xml = decryptor.decrypt(data)
        return self.parse(amz_xml)
        
    def _strip_trailing_bytes(self, amz_xml):
        # strips the 8byte-even-block padding to make 
        # a valid xml file
        match = re.match(r'.*</playlist>', amz_xml, re.DOTALL)
        if not match:
            raise ParseException('Failure stripping ending XML padding')
        return match.group()             
        
    def parse(self, amz_xml):
        xml = self._strip_trailing_bytes(amz_xml)
        
        try:
            tree = cElementTree.fromstring(xml)
        except SyntaxError:
            raise ParseException('Failure parsing XML, ill-formed XML.')
        
        parsed_tracks = []
        
        tracklist = tree.find('{%s}trackList' % self.namespace)
        tracks = tracklist.findall('{%s}track' % self.namespace)        
        if not tracks:            
            raise ParseException('Failure Parsing Tracks')
        
        for track in tracks:            
            url = track.find('{%s}location' % self.namespace).text            
            artist = track.find('{%s}creator' % self.namespace).text
            title = track.find('{%s}title' % self.namespace).text
            tracknum = track.find('{%s}trackNum' % self.namespace).text
            album = track.find('{%s}album' % self.namespace).text
            image = track.find('{%s}image' % self.namespace).text
            metas = track.findall('{%s}meta' % self.namespace)
            for meta in metas:
                if meta.attrib['rel'].endswith('fileSize'):
                    filesize = meta.text
                    break    
            
            pd = {'url': url, 'artist': artist, 'title': title, 
                  'tracknum': tracknum, 'album': album, 'image': image,
                  'filesize': filesize}
                  
            parsed_tracks.append(Track(pd))
            
        return parsed_tracks

parse_tracks = AmzParser()


class Track(object):
    def __init__(self, track_info):       
        for key, value in track_info.iteritems():
            setattr(self, key, value)
        self.status = ''
        
    def __str__(self):
        return str(self.__dict__)
        
    def get_save_name(self):
        sn = SAVE_TEMPL.safe_substitute(artist=self.artist, title=self.title,
                                        tracknum=self.tracknum, 
                                        album=self.album)
        return sn
        
        
class Decryptor(object):
    def __init__(self,):
        self.key = KEY
        self.iv = IV
        self.d_obj = DES.new(self.key, DES.MODE_CBC, IV)        
        
    def decrypt(self, amz_data):
        cipher = base64.b64decode(amz_data)
        return self.d_obj.decrypt(cipher)


class _DownloadWorker(threading.Thread):
    '''A very simple thread worker for the download thread pool'''
    
    def __init__(self, feed, status_callback, dir_name):
        super(_DownloadWorker, self).__init__()
        self.feed = feed
        self.callback = status_callback
        self.dir_name = dir_name
        self.abort = False
        self.redirects = urllib2.HTTPRedirectHandler()
        self.cookies =  urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(self.redirects, self.cookies)
    
    def kill(self):
        self.abort = True
        
    def run(self):
        while not self.abort:
            track = self.feed()
            if not track:
                break
            self.work(track)        
        
    def work(self, track):
        # Create the URL Request
        request = urllib2.Request(track.url)
            
        self.callback(track, 0)
        try:
            url = self.opener.open(request)
        except urllib2.URLError:
            logger.error('Opening request %s' % track)
            self.callback(track, 3)
            return
        
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
            return 
        buf.close()
        
        # This will cause failures if amz_file has the wrong size listed
        ''' 
        if len(mp3) != fs:
            logger.error('Expected file size != downloaded size %s' 
                            % track)
            self.callback(track, 3)
            continue
        '''
        
        # Write track to File
        try:
            fname = os.path.join(self.dir_name, track.get_save_name() + '.mp3')
            save_file = open(fname, 'wb')
            save_file.write(mp3)
            save_file.close()    
            self.callback(track, 2)
        except:                
            logger.error('Writing to file %s' % track)
            self.callback(track, 3)
            return    
      
        
class Downloader(threading.Thread):
    '''
    Downloader Status Codes emitted to the callback:
    
    0 - Connecting
    1 - Downloading Percent
    2 - Complete
    3 - Error
    4 - Downloading Finished
    '''
    
    def __init__(self, dir_name, track_list, callback, num_threads=1):
        super(Downloader, self).__init__()
        for track in track_list:
            if type(track) != Track:
                raise ValueError('track must be of type Track')
        self.queue = deque(track_list)
        self.dir_name = dir_name        
        self.callback = callback
        self.num_threads = num_threads
        self.abort = False
        
    def kill(self):
        if self.workers:
            for worker in self.workers:
                worker.kill()
        self.abort = True
    
    def feed_work(self):
        try:
            track = self.queue.popleft()
            return track
        except IndexError:
            return None
    
    def run(self):
        n = self.num_threads
        self.workers = [_DownloadWorker(self.feed_work, self.callback, \
                                        self.dir_name) for i in range(n)]
        for worker in self.workers:
            worker.start()
        for worker in self.workers:
            worker.join()
            
        if not self.abort:
            self.callback(None, 4)  


