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
import base64
import re
import urllib2
import threading
import cStringIO
import string
from xml.etree import cElementTree
from collections import deque

try:
    from Crypto.Cipher import DES
except ImportError:
    msg = 'Unable to import PyCrypto. Make sure it is installed '
    msg += 'and available on the Python path.'
    print msg
    sys.exit()

from pymazon.settings import PymazonSettings
from pymazon.log_util import PymazonLogger

settings = PymazonSettings()
logger = PymazonLogger('backend')


class ImageCache:
    '''A simple image cache for images residing at a url. 
    Extremely simple to use. 
    
    cache = ImageCache()
    image = cache.get(url) # url is valid text url (http://www.foo.com/foo.jpg)
    
    The cache has no size limit and image live in the cache forever. Thus, 
    this shouldn't be used for huge images if you value your memory. It is 
    intended to cache small album art thumbnails.
    
    '''    
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
    '''Parse the individual track information from 
    an Amazon .amz file.
    
    This class creates a callable object that returns a list 
    of Track objects. 
    
    Usage:
    
    parse = AmzParser()
    tracks = parse('./amz_file.amz')
    
    '''
    
    xmlns = 'http://xspf.org/ns/0/'

    def __call__(self, filename):
        f = open(filename, 'rb')
        data = f.read()
        f.close()
        decryptor = AmzDecryptor()
        amz_xml = decryptor.decrypt(data)
        return self.parse(amz_xml)
        
    def _find_elem(self, track, which, find_all=False):
        search_string = '{%s}%s' % (self.xmlns, which)
        search_func = track.findall if find_all else track.find
        return search_func(search_string)

    def parse(self, amz_xml):        
        try:
            tree = cElementTree.fromstring(amz_xml)
        except SyntaxError:
            raise ParseException('Failure parsing XML to etree, ill-formed XML.')

        parsed_tracks = []

        tracklist = tree.find('{%s}trackList' % self.xmlns)
        tracks = tracklist.findall('{%s}track' % self.xmlns)
        if not tracks:
            raise ParseException('Failure Parsing Tracks')
        
        tags = ['location', 'creator', 'title', 'trackNum', 'album', 'image']
        track_keys = ['url', 'artist', 'title', 'tracknum', 'album', 'image']
        for track in tracks:            
            track_elems = [self._find_elem(track, t) for t in tags]            
            try:
                track_data = [elem.text for elem in track_elems]
            except AttributeError, e:               
                raise ParseException('Failure parsing data from etree element. '
                                     'Perhaps the XML format has changed.')            
            pd = dict(zip(track_keys, track_data))
            
            # The filesize is special cause it's burried in metadata:
            # Amazon doesn't report proper filesizes, so this is worthless
            # for verifying the download, but handy for a progress indicator
            metas = self._find_elem(track, 'meta', find_all=True)
            if not metas:
                raise ParseException('Failure parsing meta data from etree. '
                                     'Perhaps the XML format has changed.')
            try:                
                for meta in metas:
                    if meta.attrib['rel'].endswith('fileSize'):
                        filesize = meta.text
                        break                    
                pd['filesize'] = filesize
            except AttributeError:
                raise ParseException('Failure parsing filesize '
                                     'from etree element.') 
            except NameError:
                raise ParseException('Failure finding filesize in metadata')
            
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
        '''Returns the save name of the track according to 
        the template specified by the user. It is possible
        that this will include partial path componenents,
        and thus should be os.path.join()'ed with the
        designated save directory.
        
        '''
        template = string.Template(settings.name_template)
        sn = template.safe_substitute(artist=self.artist, title=self.title,
                                      tracknum=self.tracknum,
                                      album=self.album)
        return sn


class DecryptException(Exception):
    pass


class AmzDecryptor(object):
    ''' Decrypt a base64 encoded & DES-CBC encrypted Amazon .amz file.
    
    Usage:
    
    >>> encrypted_txt = open('./amzfile.amz').read()
    >>> decryptor = AmzDecryptor()
    >>> valid_xml = decryptor.decrypt(encrypted_txt)
    
    '''
    
    # the key and initial value for the .amz DES CBC encryption
    KEY = '\x29\xAB\x9D\x18\xB2\x44\x9E\x31'
    IV = '\x5E\x72\xD7\x9A\x11\xB3\x4F\xEE'
    
    def __init__(self,):        
        self.d_obj = DES.new(self.KEY, DES.MODE_CBC, self.IV)
        
    def _strip_trailing_bytes(self, amz_xml):
        # strips the 8byte-even-block padding to make
        # a valid xml file
        match = re.match(r'.*</playlist>', amz_xml, re.DOTALL)
        if not match:
            raise DecryptException('Failure stripping ending XML padding.')
        return match.group()

    def decrypt(self, amz_data):
        cipher = base64.b64decode(amz_data)
        xml = self.d_obj.decrypt(cipher)
        valid_xml = self._strip_trailing_bytes(xml)
        return valid_xml


class _DownloadWorker(threading.Thread):
    '''A very simple thread worker for the download thread pool.
    This is a `private` class to be used only by the Downloader class.
    See the documentation for that class.'''

    def __init__(self, feed_func, status_callback, dir_name):
        super(_DownloadWorker, self).__init__()
        self.feed = feed_func
        self.callback = status_callback
        self.dir_name = dir_name
        self.abort = False
        
        # just in case the amazon servers want to get sneaky and redirect 
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
        # exceptions in the download process are logged 
        # and a message sent to the callback. Rather than raise 
        # an exception, the function returns None so processing
        # can continue on other tracks.
        mp3_data = self._download(track)        
        if not mp3_data:
            return
        self._save_mp3(track, mp3_data)

    def _download(self, track):        
        request = urllib2.Request(track.url)
        
        # Connecting
        self.callback(track, 0)
        try:
            url = self.opener.open(request)
        except urllib2.URLError:
            logger.error('Opening request %s' % track)
            self.callback(track, 3)
            return None

        # Download the track
        fs = int(track.filesize)
        perc_complete = 0
        chunk_size = fs / 100 # totally arbitray chunksize, 1% of file per chunk
        buf = cStringIO.StringIO()
        self.callback(track, 1, perc_complete)
        try:
            while True:
                chunk = url.read(chunk_size)
                if not chunk: # we got the whole file
                    break
                buf.write(chunk)
                perc_complete += 1
                if perc_complete > 100:
                    perc_complete = 100
                self.callback(track, 1, perc_complete)
                
        # purposely swallow any and all exceptions during downloading so 
        # other tracks can continue
        except:
            logger.error('Reading from opened url %s' % track)
            self.callback(track, 3)
            buf.close()
            return None
            
        mp3 = buf.getvalue()
        buf.close()
        
        return mp3

    def _save_mp3(self, track, data):
        # Write track to File
        # Creating sub-directories as needed
        try:
            fname = os.path.join(self.dir_name, track.get_save_name() + '.mp3')
            
            # don't overwrite any files
            i = 1
            nfname = fname
            while True:
                if not os.path.isfile(nfname):
                    break
                nfname = os.path.splitext(fname)[0]
                nfname = ''.join([nfname, '(', str(i), ')', '.mp3'])
                i += 1
            fname = nfname
                
            dir_name = os.path.dirname(fname)
            if not os.path.exists(dir_name):
                # if this excepts, it's because of permissions, 
                # and we'll catch it in the outer clause 
                try:
                    os.makedirs(dir_name)                   
                except OSError: 
                    pass
            save_file = open(fname, 'wb')
            save_file.write(data)
            save_file.close()
            self.callback(track, 2)
        except IOError:
            logger.error('Writing to file %s' % track)
            self.callback(track, 3)    


class Downloader(threading.Thread):
    ''' A Downloader to manage the downloading of a list of Track 
    objects. 
    
    downloader = Downloader(dir_name, track_list, callback, num_threads=1)
    downloader.start()    
    
    dir_name: The path to the desired save directory
    track_list: A list of Track objects to download.
    callback: The callback function to update the status during downloading.
              See the description of callback codes below. The callback is
              called with two arguments: the Track object, and the status code.
              i.e.  callback(track, status_code). The reason the track object 
              is passed to the callback is because the downloader can run 
              multiple threads and we need a way to identify the track whose
              status is being updated.
    num_thread: The number of simultaneous download threads to run.              
    
    Downloader Status Codes emitted to the callback:

    0 - Connecting
    1 - Downloading Percent
    2 - Complete
    3 - Error
    4 - Downloading Finished
    
    The downloader is threaded and will not block. downloader.start() returns 
    immediately. Call downloader.join() right after downloader.start() to 
    wait for the downloader to finish.
    
    Use downloader.kill() to kill the current downloads. This will kill all
    download threads. However, any in-progress downloads will complete 
    before the thread is killed.
    
    '''

    def __init__(self, dir_name, track_list, callback):
        super(Downloader, self).__init__()
        for track in track_list:
            if type(track) != Track:
                raise ValueError('track must be of type Track')
        self.queue = deque(track_list)
        self.dir_name = dir_name
        self.callback = callback
        self.num_threads = settings.num_threads
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
        # don't start more threads than we can use
        n = min(self.num_threads, len(self.queue))
        self.workers = [_DownloadWorker(self.feed_work, self.callback, \
                                        self.dir_name) for i in range(n)]
        for worker in self.workers:
            worker.start()
        for worker in self.workers:
            worker.join()

        if not self.abort:
            self.callback(None, 4)


