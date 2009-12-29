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
import os, sys, operator, urllib2

from PyQt4.QtGui import (QApplication, QMainWindow, QWidget, 
                         QTableView, QVBoxLayout, QPixmap, QLabel, 
                         QHBoxLayout, QPushButton, QLineEdit, 
                         QFileDialog, QGridLayout, QMessageBox)                         
from PyQt4.QtCore import (Qt, QAbstractTableModel, QVariant, 
                          pyqtSignal, QString)
                          
from pymazon.pymazonbackend import parse_tracks, Downloader


#-------------------------------------------------------------------------------
# Optional Pymazon PyQt4 GUI Front End
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
        if f:
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
                     
    def __init__(self, track):
        self.track = track
        if track is None:
            self.null_track = True
        else:
            for attr, value in track.iteritems():
                setattr(self, attr, value)
            self.null_track = False
        self.create_image_map()
        self.status = ''
                        
    def __getitem__(self, attr):
        if self.null_track:
            return ''        
        else:
            return getattr(self, attr)    
    
    def __str__(self):
        return str(self.track)
        
    def set_status(self, status):
        self.status = status
        
    def get_album_art(self):
        return AlbumArt(self.img_map[self['image']])
        
    def create_image_map(self):
        url = self['image']
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
    header_map = {'Art':'image', 'Track #':'tracknum', 'Title':'title',
                  'Artist':'artist', 'Album':'album', 
                  'Download Status':'status'}
        
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
        return len(self.header)
    
    def data(self, idx, role):
        if not idx.isValid(): 
            return None 
        elif role != Qt.DisplayRole: 
            return None
        key = self.header_map[self.header[idx.column()]]
        if key=='image':
            return ''
        return self.t_data[idx.row()][key]
        
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
            idx = self.model.header.index('Art')
            midx = self.model.createIndex(i, idx)
            aa = self.model.get_album_art(i)
            self.setIndexWidget(midx, aa)            
         
    def refresh(self):
        self.show_album_art()
        self.set_sizing()
        
    def set_new_model(self, model):
        self.model = model
        self.setModel(model)
        self.refresh()
               
        
class MainWidget(QWidget):
    
    dl_messages = {0: 'Connecting...', 1:'Downloading...',
                   2: 'Complete!', 3:'Error!'}
                   
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
        
        self.downloader = None       
        
    def new_amz(self, amz_file):
        self.table_model = TrackTableModel(amz_file)
        self.table.set_new_model(self.table_model)
    
    def downloader_callback(self, track, status):
        if status == 4:
            self.downloader = None
            self.dl_button.setEnabled(True)
        else:
            msg = self.dl_messages[status]
            self.table_model.set_download_status(track, msg)
    
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
            
        self.downloader = Downloader(save_dir, tracks, self.downloader_callback)
        self.downloader.start()
        self.dl_button.setEnabled(False)
        
    def onClose(self):
        if self.downloader:
            self.downloader.kill()
        
        
class MainWindow(QMainWindow):
    def __init__(self, amz_file=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Pymazon')
        self.widget = MainWidget(amz_file)
        self.setCentralWidget(self.widget)
        self.setMinimumSize(640, 480)
        
    def closeEvent(self, event):
        self.widget.onClose()
        event.accept()
    
        