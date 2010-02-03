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
from PyQt4.QtGui import *
from PyQt4.QtCore import Qt, QAbstractTableModel, pyqtSignal, QSize
from _pymazon_qt import Ui_MainWindow
import qt_fmt_dialog
from pymazon.pymazonbackend import parse_tracks, Downloader, ImageCache, \
                                   get_save_templ, set_save_templ


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
        
        
class FormatDialog(QDialog, qt_fmt_dialog.Ui_Dialog):
    pass        
        
        
class ProgressBar(QProgressBar):
    def __init__(self, parent=None):
        QProgressBar.__init__(self, parent)
        self.setMaximum(100)
        self.setMinimum(0)
        #sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        #self.setSizePolicy(sp)
        self.msg = ''        
        
    def text(self):
        return self.msg   
        
    def setText(self, txt):
        self.msg = str(txt)
        self.update()
        
    
class TrackTableModel(QAbstractTableModel):
    
    header = ['Album Art', 'Track #', 'Title', 'Artist', 'Album', 'Download Status']
    header_map = {'Album Art':'image', 'Track #':'tracknum', 'Title':'title',
                  'Artist':'artist', 'Album':'album', 
                  'Download Status':'status'}   
        
    def __init__(self, amz_file=None, parent=None, *args):
        super(TrackTableModel, self).__init__(parent, *args)
        self.amz_file = amz_file
        self.t_data = []        
        self.create_table_data()              
        
    def create_table_data(self):
        if self.amz_file is None:
            return
        else:
            self.t_data = parse_tracks(self.amz_file)            
                
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
        return getattr(self.t_data[idx.row()], key)
        
    def headerData(self, idx, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[idx]
        else:
            return None    
        
    def get_table(self):
        return self.t_data    


class MainWindow(QMainWindow, Ui_MainWindow):
    
    # we need a signal to update the progress bars
    # or we segfaults due to the downloader threads
    # trying to mess with pixel buffers
    dlProgress = pyqtSignal(ProgressBar, int)
    
    dl_messages = {0: 'Connecting...', 1:'Downloading...',
                   2: 'Complete!', 3:'Error!'}
    
    def __init__(self, amz_file, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)       
        self.image_cache = ImageCache()
        
        self.amz_button.clicked.connect(self.new_amz)
        self.dir_button.clicked.connect(self.new_dir)
        self.dl_button.clicked.connect(self.download_tracks)
        self.dlProgress.connect(self.update_progress_bar)
        
        self.setup_fmt_box()
        self.load_new_amz_file(amz_file)       
    
    def setup_fmt_box(self):
        # setup the format box
        self.custom_fmt = 'Custom...'
        fmt_strings = [get_save_templ(),
                            '${title}',
                            '${tracknum} - ${artist} - ${title}',
                            '${artist} - ${title}',
                            self.custom_fmt]
        # add back the default if the user config overrode it
        if '${tracknum} - ${title}' not in fmt_strings:
            fmt_strings.insert(1, '${tracknum} - ${title}')
        self.fmt_box.addItems(fmt_strings)
        self.fmt_box.currentIndexChanged.connect(self._new_fmt)
     
    def _new_fmt(self, idx):
        fmt = str(self.fmt_box.currentText())
        if fmt == self.custom_fmt:
            fmt = self._new_custom_fmt()
            self.fmt_box.addItem(fmt)
            idx = self.fmt_box.findText(fmt)
            self.fmt_box.setCurrentIndex(idx)
        set_save_templ(fmt)
            
    def _new_custom_fmt(self):
        dialog = FormatDialog()
        dialog.setupUi(dialog)
        dialog.exec_()
         
    def set_table_sizing(self):
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        self.tableView.horizontalHeader().setStretchLastSection(True)
        
    def new_amz(self):
        caption = 'Choose AMZ File'
        filefilter = "Amazon MP3 Download (*.amz)"        
        f = str(QFileDialog.getOpenFileName(self, caption, '', filefilter))
        if f:
            self.amz_lineedit.setText(f)
            self.load_new_amz_file(f)
    
    def new_dir(self):
        caption = 'Choose Save Directory'        
        ndir = str(QFileDialog.getExistingDirectory(None, caption))
        if ndir:
            self.dir_lineedit.setText(ndir)
    
    def downloader_callback(self, track, status, *args):
        if status == 4:
            self.downloader = None
            self.dl_button.setEnabled(True)
            self.amz_button.setEnabled(True)
            self.dir_button.setEnabled(True)
        else:            
            msg = self.dl_messages[status]
            pbar = self.progress_map[track]            
            if args:
                perc = args[0]               
                self.dlProgress.emit(pbar, perc)
                msg += '%s%%' % perc
                pbar.setText(msg)
            else:
                pbar.setText(msg)            
            
    def download_tracks(self):
        save_dir = str(self.dir_lineedit.text())
        if not os.access(save_dir, os.W_OK):
            msg = 'No write access to save directory. '
            msg += 'Choose a new directory with write privileges.'
            d = QMessageBox()
            d.setText(msg)
            d.exec_()
            return
        tracks = self.table_model.get_table()        
        if not tracks:
            msg = 'No tracks loaded. Select a valid amz file.'
            d = QMessageBox()
            d.setText(msg)
            d.exec_()
            return            
        self.downloader = Downloader(save_dir, tracks, self.downloader_callback,
                                     num_threads=5)
        self.downloader.start()
        self.dl_button.setEnabled(False)
        self.amz_button.setEnabled(False)
        self.dir_button.setEnabled(False)
    
    def update_progress_bar(self, pbar, value):
        pbar.setValue(value)
        
    def load_new_amz_file(self, amz_file):        
        self.table_model = TrackTableModel(amz_file)
        self.tableView.setModel(self.table_model)        
        self.show_album_art()
        self.set_progress_bars()
        self.set_table_sizing()
        
    def show_album_art(self):
        table = self.table_model.get_table()
        for i in range(len(table)):
            idx = self.table_model.header.index('Album Art')
            midx = self.table_model.createIndex(i, idx)
            url = table[i].image
            jpg = self.image_cache.get(url)
            art = AlbumArt(jpg)            
            self.tableView.setIndexWidget(midx, art)
            
    def set_progress_bars(self):
        table = self.table_model.get_table()
        self.progress_map = {}
        for i in range(len(table)):
            track = table[i]
            idx = self.table_model.header.index('Download Status')
            midx = self.table_model.createIndex(i, idx)
            progress_bar = ProgressBar()
            self.progress_map[track] = progress_bar
            self.tableView.setIndexWidget(midx, progress_bar)
            
        
    