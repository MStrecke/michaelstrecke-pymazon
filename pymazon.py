#!/usr/bin/env python
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
import threading
from Crypto.Cipher import DES

# GUI stuff
import operator
try:
    from PyQt4.QtGui import (QApplication, QMainWindow, QWidget, QTableView,
                             QVBoxLayout, QPixmap, QLabel, QHBoxLayout,
                             QPushButton, QLineEdit, QFileDialog, QGridLayout,
                             QMessageBox)
                         
    from PyQt4.QtCore import (Qt, QAbstractTableModel, QVariant, pyqtSignal,
                              QString)
except ImportError:
    msg = 'The PyQt4 Libraries must be installed in order to use the gui. '
    msg += 'But the command line client can still be used.'
    raise ImportError(msg)
    

# the key and initial value for the .amz DES CBC encryption
KEY = '\x29\xAB\x9D\x18\xB2\x44\x9E\x31'
IV = '\x5E\x72\xD7\x9A\x11\xB3\x4F\xEE'


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
        self.re_url = re.compile(r'<location>.*?</location>', re.DOTALL)
        self.re_artist = re.compile(r'<creator>.*?</creator>', re.DOTALL)
        self.re_title = re.compile(r'<title>.*?</title>', re.DOTALL)
        self.re_tracknum = re.compile(r'<trackNum>.*?</trackNum>', re.DOTALL)
        self.re_album = re.compile(r'<album>.*?</album>', re.DOTALL)
        self.re_image = re.compile(r'<image>.*?</image>', re.DOTALL)
        
    def strip_tags(self, phrase):        
        tags = self.re_tag.findall(phrase)
        ltag = tags[0]
        rtag = tags[-1]        
        return phrase.replace(ltag, '').replace(rtag, '').replace('&amp;', '&')     
        
    def parse(self):
        parsed_tracks = []
        tracks = self.re_tracks.findall(self.amz)
        if not tracks:
            print tracks
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
            
            pd = {'url': url, 'artist': artist, 'title': title, 
                  'tracknum': tracknum, 'album': album, 'image': image}
                  
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
        
        
class Downloader(threading.Thread):
    def __init__(self, dir_name, track_list, callback):
        super(Downloader, self).__init__()
        self.track_list = track_list
        self.dir_name = dir_name
        self.redirects = urllib2.HTTPRedirectHandler()
        self.cookies =  urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(self.redirects, self.cookies)
        self.callback = callback
        
    def run(self):
        for track in self.track_list:
            fname = os.path.join(self.dir_name, track['title']+'.mp3')
            save_file = open(fname, 'wb')
            request = urllib2.Request(track['url'])
            url = self.opener.open(request)
            self.callback(track, 'downloading')
            mp3 = url.read()
            save_file.write(mp3)
            save_file.close()    
            self.callback(track, 'complete')
            

def parse_tracks(filename):
    f = open(filename, 'r')
    dc = Decryptor(f)
    f.close()
    prsr = AmzParser(dc.decrypt())
    parsed_tracks = prsr.parse()
    return parsed_tracks


def validate_sysargs(args):
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
    return amz_file 


#-------------------------------------------------------------------------------
# Optional PyQt4 GUI Front End
#-------------------------------------------------------------------------------
class AmzFileWidget(QWidget):
    
    newAmzFile = pyqtSignal(QString)
    
    def __init__(self, amzfile=None):
        super(AmzFileWidget, self).__init__()
        self.button = QPushButton('Load AMZ File')
        self.file_text = QLineEdit(amzfile)
        self.file_text.setReadOnly(True)
        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.file_text)
        self.setLayout(layout)       
        self.button.clicked.connect(self.onClick)       
        
    def onClick(self):
        caption = 'Choose AMZ File'
        filefilter = "Amazon MP3 Download (*.amz)"
        cdir = os.getcwd()
        f = str(QFileDialog.getOpenFileName(self, caption, cdir, filefilter))
        self.file_text.setText(f)
        self.newAmzFile.emit(f)
        

class DirWidget(QWidget):
    def __init__(self):
        super(DirWidget, self).__init__()
        self.button = QPushButton('Save Directory')
        self.dir_text = QLineEdit(os.getcwd())
        self.dir_text.setReadOnly(True)
        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.dir_text)
        self.setLayout(layout)
        self.button.clicked.connect(self.onClick)
                
    def get_dir(self):
        return str(self.dir_text.text())
        
    def onClick(self):
        caption = 'Choose Save Directory'
        cdir = self.get_dir()
        ndir = str(QFileDialog.getExistingDirectory())
        self.dir_text.setText(ndir)
       
        
class AlbumArt(QLabel):
    def __init__(self, img_data):
        super(AlbumArt, self).__init__()
        self.pm = self.create_pixmap(img_data)
        self.setPixmap(self.pm)
        self.setAutoFillBackground(True)   
        
    def create_pixmap(self, img_data):
        pm = QPixmap()
        pm.loadFromData(img_data, None, Qt.AutoColor)
        return pm   
        
        
class TrackModel(object):
    
    unique_urls = set()
    img_map = {}
    header_map = {0:'image', 1:'tracknum', 2:'title', 3:'artist', 4:'album'}
    null_dict = {'image': '', 'tracknum': '', 'title': '', 'artist': '', 
                 'album': '',}
                 
    def __init__(self, track):
        if track is None:
            self.track = self.null_dict
        else:
            self.track = track
        self.create_image_map()
        self.status = ''
                        
    def __getitem__(self, idx):
        if idx == 5:
            return self.status
        if type(idx) == str:
            return self.track[idx]            
        key = self.header_map[idx]
        if key == 'image':
            return ''
        else:
            return self.track[key]    
               
    def __len__(self):
        return len(self.track)
        
    def set_status(self, status):
        self.status = status
        
    def get_album_art(self):
        return AlbumArt(self.img_map[self.track['image']])
        
    def create_image_map(self):
        url = self.track['image']
        if url not in self.unique_urls:
            self.unique_urls.add(url)       
            try:
                uurl = urllib2.urlopen(url)
                img_data = uurl.read()
                uurl.close()
            except (urllib2.URLError, ValueError):
                img_data = ''
            self.img_map[url] = img_data
      

class TrackTableModel(QAbstractTableModel):
    
    header = ['Art', 'Track #', 'Title', 'Artist', 'Album', 'Download Status']
        
    def __init__(self, amz_file=None, parent=None, *args):
        super(TrackTableModel, self).__init__(parent, *args)
        self.amz_file = amz_file
        self.t_data = []
        self.has_tracks = False
        self.create_table_data()        
            
    def create_table_data(self):
        if self.amz_file is None:
            self.t_data = [TrackModel(None)]
        else:
            parsed_tracks = parse_tracks(self.amz_file)
            self.t_data = [TrackModel(pt) for pt in parsed_tracks]
            self.has_tracks = True
                        
    def rowCount(self, parent):
        return len(self.t_data)
    
    def columnCount(self, parent):
        return len(self.t_data[0])
    
    def data(self, idx, role):
        if not idx.isValid(): 
            return None 
        elif role != Qt.DisplayRole: 
            return None         
        return self.t_data[idx.row()][idx.column()]
        
    def headerData(self, idx, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[idx]
        else:
            return None
    
    def get_album_art(self, idx):
        return self.t_data[idx].get_album_art()
        
    def set_download_status(self, track, status):
        self.layoutAboutToBeChanged.emit()
        track.set_status(status)
        self.layoutChanged.emit()
        
    def get_tracks(self):
        if not self.has_tracks:
            return None
        else:
            return self.t_data
        
        
class TrackTable(QTableView):
    def __init__(self, model):
        super(TrackTable, self).__init__()
        self.set_new_model(model)
        
    def set_sizing(self):        
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.horizontalHeader().setStretchLastSection(True)
        
    def show_album_art(self):        
        for i in range(len(self.model.t_data)):            
            idx = self.model.createIndex(i, 0)
            aa = self.model.get_album_art(i)
            self.setIndexWidget(idx, aa)            
         
    def refresh(self):
        self.show_album_art()
        self.set_sizing()
        
    def set_new_model(self, model):
        self.model = model
        self.setModel(model)
        self.refresh()
               
        
class MainWidget(QWidget):
    def __init__(self, amz_file=None):
        super(MainWidget, self).__init__()        
        
        self.amz_widget = AmzFileWidget(amz_file)
        self.amz_widget.newAmzFile.connect(self.new_amz)
        
        self.dir_widget = DirWidget()
        
        self.dl_button = QPushButton('Download')
        self.dl_button.clicked.connect(self.download_tracks)
        
        self.table_model = TrackTableModel(amz_file)
        self.table = TrackTable(self.table_model)
                
        layout = QGridLayout()
        layout.addWidget(self.amz_widget, 0, 0,)
        layout.addWidget(self.dir_widget, 1, 0,)
        layout.addWidget(self.dl_button, 0, 3, 2, 1)
        layout.addWidget(self.table, 2, 0, 1, 5)
        
        self.setLayout(layout)       
    
    def new_amz(self, amz_file):
        self.table_model = TrackTableModel(amz_file)
        self.table.set_new_model(self.table_model)
    
    def update_download_status(self, track, status):
        if status == 'downloading':
            self.table_model.set_download_status(track, 'Downloading...')
        elif status == 'complete':
            self.table_model.set_download_status(track, 'Complete!')
        else:
            pass
    
    def download_tracks(self):
        save_dir = self.dir_widget.get_dir()
        if not os.access(save_dir, os.W_OK):
            msg = 'No write access to save directory. '
            msg += 'Choose a new directory with write privileges.'
            d = QMessageBox()
            d.setText(msg)
            d.exec_()
            return
        tracks = self.table_model.get_tracks()
        if not tracks:
            msg = 'No tracks loaded. Select a valid amz file.'
            d = QMessageBox()
            d.setText(msg)
            d.exec_()
            return
            
        downloader = Downloader(save_dir, tracks, self.update_download_status)
        downloader.start()
         
        
class MainWindow(QMainWindow):
    def __init__(self, args=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Pymazon')
        if args:
            amz_file = validate_sysargs(args)
        else:
            amz_file = None
        self.widget = MainWidget(amz_file)
        self.setCentralWidget(self.widget)
        self.setMinimumSize(640, 480)  
    
    
if __name__=='__main__':    
    parser = OptionParser()    
    parser.add_option('-d', '--dir', dest='save_dir', 
                      help='Directory in which to save the downloads', 
                      default=os.getcwd())
    parser.add_option('-g', '--gui', dest='gui', 
                      help='Launch the program in GUI mode',
                      action='store_true', default=False)
                      
    (options, args) = parser.parse_args()
    
    if options.gui:
        app = QApplication([])
        win = MainWindow(args)
        win.show()
        app.exec_()    
    else:        
        amz_file = validate_sysargs(args)
        save_dir = options.save_dir   
        if not os.access(save_dir, os.W_OK):
            raise RuntimeError('Unable to write to target directory. Ensure the directory exits and write permission is granted.')
            sys.exit()
            
        def dl_printer(track, status):
            if status == 'downloading':
                print('Downloading track %s by %s on album %s. ' 
                      % (track['title'], track['artist'], track['album']))
            elif status == 'complete':
                print 'Complete!\n'
            else:
                pass
            
        parsed_tracks = parse_tracks(amz_file)        
        dl = Downloader(save_dir, parsed_tracks, dl_printer)
        dl.start()
        dl.join()
        print 'Downloads Complete!'