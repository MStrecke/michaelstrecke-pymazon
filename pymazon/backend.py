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
sys.path.append('/home/brucewayne/development/pymazon/hg')
import base64
import urllib2
import threading
from cStringIO import StringIO
import string
from xml.parsers import expat
from collections import deque, defaultdict

try:
    from Crypto.Cipher import DES
except ImportError:
    msg = 'Unable to import PyCrypto. Make sure it is installed '
    msg += 'and available on the Python path.'
    print msg
    sys.exit()

from pymazon.settings import settings
from pymazon.log_util import PymazonLogger


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
            except urllib2.URLError:
                pixbuf = ''
            # Write whatever we got to the cache, and return it:
            self.cache[url] = pixbuf
            return pixbuf
        
        
image_cache = ImageCache()        
        

class Album(object):
    def __init__(self, title=None, artist=None, image_url=None, tracks=None):
        self.title = title
        self.artist = artist        
        self.tracks = tracks or [] 
        self.image_url = image_url
        
    @property
    def image(self):
        return image_cache.get(self.image_url)
    
    def __unicode__(self):
        return self.artist + ' - ' + self.title

class Track(object):
    def __init__(self, album, title=None, number=None, url=None, filesize=None):
        self.album = album
        self.title = title
        self.number = number
        self.url = url
        self.filesize = filesize
        self.data = None
        
    def save(self):
        if not self.data:
            raise IOError('No data to save.')
        
        if not os.access(settings.save_dir, os.W_OK):
            raise IOError('No write access to save dir.')
        
        # use the user-specified template to generate
        # the stem
        template = string.Template(settings.name_template)
        sn = template.safe_substitute(artist=self.album.artist, 
                                      title=self.title,
                                      tracknum=self.number,
                                      album=self.album.name)
        
        # combine the stem, with the base path and file extension
        # to get the fully qualified save path.
        fname = os.path.join(settings.save_dir, sn + '.mp3')
            
        # ensure we don't overwrite any files
        i = 1
        nfname = fname
        while True:
            if not os.path.isfile(nfname):
                break
            nfname = os.path.splitext(fname)[0]
            nfname = ''.join([nfname, '(', str(i), ')', '.mp3'])
            i += 1
        fname = nfname
        
        f = open(fname, 'wb')
        f.write(self.data)
        f.close()
        
    def __unicode__(self):
        return self.number + '. ' + self.title

        
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
        
    def strip_trailing_bytes(self, amz_xml):
        # strips the octet even block padding to make
        # a valid xml file. Amazon doesn't follow the padding 
        # convention specified by the DES standard, 
        # rather, they add 8 -'\x08' bytes, and enough 
        # '\x00' bytes to make the file mod(8) even. 
        # The problem is that we don't know how many '\x00' bytes 
        # there are. So, we strip bytes until we reach the first
        # xml closing tag.
        buf = StringIO(amz_xml)
        n = -1
        buf.seek(n, 2)
        while buf.read(1) != '>':
            n -= 1
            buf.seek(n, 2)    
        buf.truncate()    
        return buf.getvalue()

    def decrypt(self, amz_data):
        d_obj = DES.new(self.KEY, DES.MODE_CBC, self.IV)
        cipher = base64.b64decode(amz_data)
        xml = d_obj.decrypt(cipher)
        valid_xml = self.strip_trailing_bytes(xml)
        return valid_xml
    
    
class ParseException(Exception):
    pass


class AmzParser(object):
    
    def __init__(self):
        self.parser = None        
        self.parsed_objects = []
        self.current_track = None
        self.in_tracklist = False
        self.now_url = False
        self.now_artist = False
        self.now_album = False
        self.now_title = False
        self.now_image = False
        self.now_tracknum = False
        self.now_filesize = False   
    
    def start_element(self, name, attrs):
        if name == 'trackList':
            self.in_tracklist = True        
        if self.in_tracklist:
            if name == 'track':            
                self.current_track = defaultdict(str)
            elif name == 'location':
                self.now_url = True
            elif name == 'creator':
                self.now_artist = True
            elif name == 'album':
                self.now_album = True
            elif name == 'title':
                self.now_title = True
            elif name == 'image':
                self.now_image = True
            elif name == 'trackNum':
                self.now_tracknum = True
            elif name == 'meta':
                if attrs['rel'].endswith('fileSize'):
                    self.now_filesize = True
    
    def end_element(self, name):
        if name == 'trackList':
            self.in_tracklist = False
        if self.in_tracklist:
            if name == 'track':
                self.add_track()
            elif name == 'location':
                self.now_url = False
            elif name == 'creator':
                self.now_artist = False
            elif name == 'album':
                self.now_album = False
            elif name == 'title':
                self.now_title = False
            elif name == 'image':
                self.now_image = False
            elif name == 'trackNum':
                self.now_tracknum = False
            elif name == 'meta':
                self.now_filesize = False
    
    def character_data(self, data):        
        if self.now_url:
            self.current_track['url'] += data
        elif self.now_artist:
            self.current_track['artist'] += data
        elif self.now_album:
            self.current_track['album'] += data
        elif self.now_title:
            self.current_track['title'] += data
        elif self.now_image:
            self.current_track['image'] += data
        elif self.now_tracknum:
            self.current_track['tracknum'] += data
        elif self.now_filesize:
            self.current_track['filesize'] += data
        
    def add_track(self):
        album = self.current_track['album']
        artist = self.current_track['artist']
        # if the current track does not share the same artist 
        # and album name as any existing album, create a new album.
        for obj in self.parsed_objects:
            if isinstance(obj, Album):                
                if (obj.title == album) and (obj.artist == artist):
                    self.add_track_to_album(obj)
                    return        
        new_album = Album(title=album,
                          artist=artist,
                          image_url=self.current_track['image'])
        self.add_track_to_album(new_album)
        self.parsed_objects.append(new_album)
                    
    def add_track_to_album(self, album):
        new_track = Track(title=self.current_track['title'],
                          url=self.current_track['url'],
                          album=album,
                          number=self.current_track['tracknum'],
                          filesize=self.current_track['filesize'])
        album.tracks.append(new_track)        
     
    def create_new_parser(self):
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.character_data
        
    def parse(self, amz):
        amz_data = open(amz).read()
        decryptor = AmzDecryptor()
        xml = decryptor.decrypt(amz_data)
        self.create_new_parser()
        self.parser.Parse(xml)        
        
    def get_parsed_objects(self):
        return self.parsed_objects
    

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
        buf = StringIO()
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


