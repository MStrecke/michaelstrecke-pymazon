"""
Pymazon - A Python based downloader for the Amazon.com MP3 store
Copyright (c) 2010 Steven C. Colbert

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

from collections import defaultdict
from xml.parsers import expat

from pymazon.core.decryptor import AmzDecryptor
from pymazon.core.item_model import Album, OtherMedia, Track

"""
XML structure of AMZ file         (as of Oct. 2012)

<playlist>
   ...
  <trackList>
    <track>
      <location>http://...</location>
      <creator>...</creator>
      <album>...</album>
      <title>...</title>
      <image>http://.....</image>
      <duration>####</duration>
      <trackNum>##</trackNum>
      <meta rel="http://.../dmusic/ASIN">....</meta>
      <meta rel="http://.../dmusic/productTypeName">DOWNLOADABLE_MUSIC_TRACK</meta>
      <meta rel="http://.../dmusic/customerId">....</meta>
      <meta rel="http://.../dmusic/primaryGenre">...</meta>
      <meta rel="http://.../dmusic/discNum">2</meta>
      <meta rel="http://.../dmusic/albumASIN">...</meta>
      <meta rel="http://.../dmusic/albumPrimaryArtist">...</meta>
      <meta rel="http://.../dmusic/trackType">mp3</meta>
    </track>
  </trackList>
</playlist>

Note:
- The image tag is optional.
- The image track is part of a track - not an album (in pymazon, the
  image_url is part of an album!)

The parser builds a list named 'parsed_objects', which looks like this:

parsed_objects ---+-- Album
                  |     |
                  |     +---- Track
                  |     |
                  |     +---- Track
                  |     |
                  |     +---- OtherMedia (not MP3s - only if needed)
                  |     |           |
                  |     |           +--- non mp3 track
                  |     |           |
                  |     |           +--- non mp3 track
                  |     |           |
                  |     |            ...
                  |     ...
                  |
                  +-- Album
                  |     |
                  |     +---- Track
                  |     |
                  ...   ...

The "Album"s are created as needed (one for each new combination of
album title and artist name).


"""

class ParseException(Exception):
    pass

class AmzParser(object):
    def __init__(self):
        self.parser = None              # Parser
        self.parsed_objects = []        # list of albums
        self.current_track = None

        # We are using the expat parser. That means, we have to
        # keep track of the current node ourself
        self.in_tracklist = False
        self.in_extension = False
        self.now_url = False
        self.now_artist = False
        self.now_album = False
        self.now_title = False
        self.now_image = False
        self.now_tracknum = False
        self.now_filesize = False
        self.now_tracktype = False
        self.now_genre = False
        self.now_discnum = False
        self.now_albumartist = False
        self.now_ASIN = False
        self.now_albumASIN = False

    def start_element(self, name, attrs):
        # we encountered the opening tag <name attr>

        if name == "extension":
            self.in_extension = True

        if self.in_extension:               # do nothing while in extension
            return

        if name == 'trackList':
            self.in_tracklist = True

        if self.in_tracklist:
            if name == 'track':
                self.current_track = defaultdict(str)   # empty dict
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
                elif attrs['rel'].endswith('trackType'):
                    self.now_tracktype = True
                elif attrs['rel'].endswith('primaryGenre'):
                    self.now_genre = True
                elif attrs['rel'].endswith('albumPrimaryArtist'):
                    self.now_albumartist = True
                elif attrs['rel'].endswith('discNum'):
                    self.now_discnum = True
                elif attrs['rel'].endswith('/ASIN'):
                    self.now_ASIN = True
                elif attrs['rel'].endswith('/albumASIN'):
                    self.now_albumASIN = True

    def end_element(self, name):
        # end tags </name> found

        if name == "extension":
            self.in_extension = False

        if self.in_extension:           # do nothing while in extension
            return

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
                if self.now_filesize:
                    self.now_filesize = False
                elif self.now_tracktype:
                    self.now_tracktype = False
                elif self.now_discnum:
                    self.now_discnum = False
                elif self.now_genre:
                    self.now_genre = False
                elif self.now_albumartist:
                    self.now_albumartist = False
                elif self.now_albumASIN:
                    self.now_albumASIN = False
                elif self.now_ASIN:
                    self.now_ASIN = False

    def character_data(self, data):
        # text between tags

        if self.in_extension:           # do nothing while in extension
            return

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
            self.current_track['tracknum'] += ('0' + data if len(data) == 1 else data)
        elif self.now_filesize:
            self.current_track['filesize'] += data
        elif self.now_tracktype:
            self.current_track['tracktype'] += data
        elif self.now_discnum:
            self.current_track['discnum'] += ('0' + data if len(data) == 1 else data)
        elif self.now_genre:
            self.current_track['genre'] += data
        elif self.now_albumartist:
            self.current_track['albumartist'] += data
        elif self.now_ASIN:
            self.current_track['ASIN'] += data
        elif self.now_albumASIN:
            self.current_track['albumASIN'] += data


    def add_track(self):
        # this routine is called with the closing tag </track>
        # it scans the objects added so far (parsed_objects) for a suitable
        # album. If it does not find one, it creates one.

        album = self.current_track['album']
        album_artist = self.current_track['albumartist']
        # if the current track does not share the same artist
        # and album name as any existing album, create a new album.
        for obj in self.parsed_objects:
            if isinstance(obj, Album):
                if (obj.title == album) and (obj.artist == album_artist):
                    self.add_track_to_album(obj)
                    return

        new_album = Album(title=album,
                          artist=album_artist,
                          image_url=self.current_track['image'])
        self.add_track_to_album(new_album)
        self.parsed_objects.append(new_album)

    def add_track_to_album(self, album):
        # create a new Track to be added to the album
        new_track = Track(title=self.current_track['title'],
                          artist=self.current_track['artist'],
                          url=self.current_track['url'],
                          album=album,
                          genre=self.current_track['genre'],
                          discnum=self.current_track['discnum'],
                          number=self.current_track['tracknum'],
                          filesize=self.current_track['filesize'],
                          extension=self.current_track['tracktype'],
                          ASIN=self.current_track['ASIN'],
                          albumASIN=self.current_track['albumASIN']
                          )

        if new_track.extension not in ['mp3']:
            # if not an MP3
            # scan the tracks of the ALBUM for an OtherMedia entry, and add it there
            for track in album.tracks:
                if isinstance(track, OtherMedia):
                    track.tracks.append(new_track)
                    return
                else:
                    pass

            # if there wasn't an OtherMedia entry,
            # create one and add this track
            other_media = OtherMedia(tracks=[new_track])
            album.tracks.append(other_media)
        else:
            album.tracks.append(new_track)

    def create_new_parser(self):
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.character_data

    def parse(self, amz):
        # read, decrypt, and parse amz file
        amz_data = open(amz).read()
        decryptor = AmzDecryptor()
        xml = decryptor.decrypt(amz_data)
        self.create_new_parser()
        self.parser.Parse(xml)

    def get_parsed_objects(self):
        return self.parsed_objects
