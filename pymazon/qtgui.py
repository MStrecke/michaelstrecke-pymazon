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
from PyQt4.QtCore import Qt, QAbstractTableModel, pyqtSignal, QSize, QVariant,\
                         QModelIndex, QAbstractItemModel

from pymazon import _qtgui
from pymazon import _qtfmtdialog
from pymazon.backend import AmzParser, Downloader, ImageCache
from pymazon.settings import settings


class AlbumArt(QLabel):
    '''A simple label widget to display album art.
    Automatically detects image format from the 
    img_data buffer.
    
    '''
    def __init__(self, img_data):
        super(AlbumArt, self).__init__()
        self.pm = self.create_pixmap(img_data)
        self.setPixmap(self.pm)
        self.setAutoFillBackground(True)

    def create_pixmap(self, img_data):
        pm = QPixmap()
        pm.loadFromData(img_data, None, Qt.AutoColor)
        return pm


class FormatDialog(QDialog, _qtfmtdialog.Ui_Dialog):
    ''' The dialog for specifying a custom Name format.'''
    pass


class TreeNode(object):
    def __init__(self, parent, row):
        self.parent = parent
        self.row = row
        self.subnodes = self._get_children()

    def _get_children(self):
        raise NotImplementedError()
    
    
class TreeModel(QAbstractItemModel):
    def __init__(self):
        super(QAbstractItemModel, self).__init__() 
        self.root_nodes = self._get_root_nodes()               

    def _get_root_nodes(self):
        raise NotImplementedError()

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.root_nodes[row])
        parent_node = parent.internalPointer()
        return self.createIndex(row, column, parent_node.subnodes[row])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if node.parent is None:
            return QModelIndex()
        else:
            return self.createIndex(node.parent.row, 0, node.parent)

    def reset(self):
        self.root_nodes = self._getRootNodes()
        QAbstractItemModel.reset(self)

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self.root_nodes)
        node = parent.internalPointer()
        return len(node.subnodes)    
    
 
class AmzElement(object):
    def __init__(self, obj, subelements):
        self.obj = obj
        self.subelements = subelements
        
    def data(self):
        return unicode(self.obj)
    
    
class AmzNode(TreeNode):
    def __init__(self, ref, parent, row):
        self.ref = ref
        super(AmzNode, self).__init__(parent, row)
        
    def _get_children(self):
        return [AmzNode(elem, self, idx) for idx, elem 
                in enumerate(self.ref.subelements)]
    
    
class AmzTreeModel(TreeModel):
    
    headers = ['Title', 'Status']
    
    def __init__(self, albums):
        self.albums = albums
        self.create_tree_data()
        super(AmzTreeModel, self).__init__()
        
    def create_tree_data(self):
        self.root_elements = []
        for album in self.albums:
            subelements = [AmzElement(track, []) for track in album.tracks]
            self.root_elements.append(AmzElement(album, subelements))    
    
    def _get_root_nodes(self):
        return [AmzNode(elem, None, idx) for idx, elem
                in enumerate(self.root_elements)]
    
    def columnCount(self, parent):
        return 2    
    
    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == Qt.DisplayRole and index.column() == 0:            
            return node.ref.data()
        return None   
    
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    
class ProgressBarDelegate(QStyledItemDelegate):
    
    # sizeHint doesnt seem to do anything. So
    # we modify the drawing rect directly
    #def sizeHint(self, option, index):
    #    return QSize(120, 30)
        
    def paint(self, painter, options, index):        
        opts = QStyleOptionProgressBar()
        opts.rect = options.rect        
        opts.minimum = 1
        opts.maximum = 100
        opts.textVisible = True        
        data = index.data().toPyObject()        
        if not data:            
            txt = 'Ready'
            QApplication.style().drawItemText(painter, opts.rect, 1, 
                                              opts.palette, True, txt)
        else:            
            percent, txt = data
            if percent == 100:
                txt = 'Complete!'
                QApplication.style().drawItemText(painter, opts.rect, 1, 
                                                  opts.palette, True, 
                                                  txt)
            else:
                opts.progress = percent
                opts.text = txt
                QApplication.style().drawControl(QStyle.CE_ProgressBar, opts, 
                                                 painter)        


class MainWindow(QMainWindow, _qtgui.Ui_MainWindow):    

    dl_messages = {0: 'Connecting...', 1:'Downloading...',
                   2: 'Complete!', 3:'Error!'}

    def __init__(self, amz_file, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.image_cache = ImageCache()
        self.downloader = None
        
        self.amz_button.clicked.connect(self.new_amz)
        self.dir_button.clicked.connect(self.new_dir)
        self.dl_button.clicked.connect(self.download_tracks)        

        self.dir_lineedit.setText(settings.save_dir)
        self.setup_fmt_box()
        
        if amz_file:
            self.load_new_amz_file(amz_file)        
        
    def setup_fmt_box(self):
        # setup the format box
        self.custom_fmt = 'Custom...'
        fmt_strings = [settings.name_template,
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
            if not fmt:
                self.fmt_box.setCurrentIndex(0)
                return
            else:
                # two calls to setCurrentIndex are required because
                # insertItems triggers a currentIndexChanged signal.
                # As such, we cant be on `Custom...` when the event is called
                # or we'll enter an endless loop of dialog boxes.
                # Likewise, once we insert the item, we need to reset the
                # focus to that item.
                self.fmt_box.setCurrentIndex(0)
                self.fmt_box.insertItem(0, fmt)
                self.fmt_box.setCurrentIndex(0)
        settings.name_template = fmt

    def _new_custom_fmt(self):
        dialog = FormatDialog()
        dialog.setupUi(dialog)
        dialog.exec_()
        return str(dialog.lineEdit.text())

    def set_tree_sizing(self):
        self.treeView.setColumnWidth(0, 200)
        self.treeView.setColumnWidth(1, 100)
        #self.treeView.resizeColumnToContents(0)
        #self.treeView.resizeRowsToContents()
        #self.tableView.horizontalHeader().setStretchLastSection(True)

    def new_amz(self):
        caption = 'Choose AMZ File'
        filefilter = "Amazon MP3 Download (*.amz)"
        f = str(QFileDialog.getOpenFileName(self, caption, '', filefilter))
        if f:
            self.amz_lineedit.setText(f)
            self.load_new_amz_file(f)

    def new_dir(self):
        caption = 'Choose Save Directory'
        ndir = str(QFileDialog.getExistingDirectory(None, caption,
                                                    settings.save_dir))
        if ndir:
            settings.save_dir = ndir
            self.dir_lineedit.setText(ndir)

    def downloader_callback(self, track, status, *args):
        if status == 4:
            self.downloader = None
            self.dl_button.setEnabled(True)
            self.amz_button.setEnabled(True)
            self.dir_button.setEnabled(True)        
        else:
            msg = self.dl_messages[status]
            if args:
                perc = args[0]
            else:
                if msg == 'Complete!': # this is ugly
                    perc = 100
                else:
                    perc = None
            self.table_model.set_progress(track, perc, msg)

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
        self.downloader = Downloader(save_dir, tracks, self.downloader_callback)
        self.downloader.start()
        self.dl_button.setEnabled(False)
        self.amz_button.setEnabled(False)
        self.dir_button.setEnabled(False)

    def load_new_amz_file(self, amz_file):
        parser = AmzParser()
        parser.parse(amz_file)
        albums = parser.get_parsed_objects()        
        self.tree_model = AmzTreeModel(albums)        
        self.treeView.setModel(self.tree_model)
        #self.show_album_art()        
        self.pbardelegate = ProgressBarDelegate()
        self.treeView.setItemDelegateForColumn(1, self.pbardelegate)
        self.set_tree_sizing()

    def show_album_art(self):
        table = self.table_model.get_table()
        for i in range(len(table)):
            idx = self.table_model.header.index('Artwork')
            midx = self.table_model.createIndex(i, idx)
            url = table[i].image
            jpg = self.image_cache.get(url)
            art = AlbumArt(jpg)
            self.tableView.setIndexWidget(midx, art)
            
    def closeEvent(self, evt):
        if self.downloader:
            self.downloader.kill()
        evt.accept()
            

