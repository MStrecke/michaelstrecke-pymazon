import pygtk
pygtk.require('2.0')
import gobject
import gtk
import webbrowser
import os
import sys
sys.path.append('/home/brucewayne/development/pymazon/hg')

from pymazon.resource import python_icon_path
from pymazon.gtk.tree_model import TreeModel
from pymazon.core.parser import AmzParser
from pymazon.core.settings import settings
from pymazon.core.downloader import Downloader


gtk.gdk.threads_init()


class ProgressRenderer(gtk.CellRendererProgress):
    def do_render(self, window, widget, background_area, area, expose_area, flags):       
        gtk.CellRendererProgress.do_render(self, window, widget, 
                                       background_area, area,
                                       expose_area, flags)     


gobject.type_register(ProgressRenderer)


class MainWindow(gobject.GObject):    
    def __init__(self):
        glade_fpath = os.path.join(os.path.split(__file__)[0], '_ui.glade')
        builder = gtk.Builder()
        builder.add_from_file(glade_fpath)
        self.connect_signals(builder)       
        
        self.albumArtImage = builder.get_object('albumArtImage')
        self.nowDownloadingLabel = builder.get_object('nowDownloadingLabel')
        self.pythonPixbuf = gtk.gdk.pixbuf_new_from_file(python_icon_path)
        self.pymazon_text = '<span weight="bold" size="xx-large">Pymazon! w00t!</span>'
        self.reset_displaybar_info()        
        
        self.main_window = builder.get_object('MainWindow')        
        self.main_window.show()        

        self.treeView = builder.get_object('treeView')
        self.tree_model = None        
   
        
        self.pbarRenderer = ProgressRenderer()       
        self.colStatus = builder.get_object('colStatus')
        self.colStatus.clear()
        self.colStatus.pack_start(self.pbarRenderer, True)
        self.colStatus.add_attribute(self.pbarRenderer, 'value', 1)
        self.colStatus.add_attribute(self.pbarRenderer, 'text', 2)
        
        self.downloader = None
        
        
    def connect_signals(self, builder):
        builder.connect_signals({'on_MainWindow_destroy': self.on_destroy})
        self.actionAbout = builder.get_object('actionAbout')
        self.actionAbout.connect('activate', self.on_actionAbout_activate)
        self.actionLoadFiles = builder.get_object('actionLoadFiles')
        self.actionLoadFiles.connect('activate', self.on_actionLoadFiles_activate)
        self.actionSettings = builder.get_object('actionSettings')
        self.actionSettings.connect('activate', self.on_actionSettings_activate)
        self.actionShowDownloads = builder.get_object('actionShowDownloads')
        self.actionShowDownloads.connect('activate', self.on_actionShowDownloads_activate)
        self.actionDownload = builder.get_object('actionDownload')
        self.actionDownload.connect('activate', self.on_actionDownload_activate)      
        self.actionQuit = builder.get_object('actionQuit')
        self.actionQuit.connect('activate', self.on_destroy)
        

    def on_actionAbout_activate(self, *args):
        webbrowser.open('http://code.google.com/p/pymazon')

    def on_actionLoadFiles_activate(self, *args):
        self.new_amz()

    def on_actionSettings_activate(self, *args):
        print 'preferences'

    def on_actionShowDownloads_activate(self, *args):
        webbrowser.open(settings.save_dir)

    def on_actionDownload_activate(self, *args):
        self.download_tracks()

    def on_destroy(self, *arg):
        if self.downloader:
            self.downloader.kill()
        gtk.main_quit()

    def reset_displaybar_info(self):
        self.albumArtImage.set_from_pixbuf(self.pythonPixbuf)
        self.nowDownloadingLabel.set_markup(self.pymazon_text)

    def new_amz(self):
        caption = 'Choose AMZ File'
        filefilter = gtk.FileFilter()        
        filefilter.add_pattern('*.amz')        
        dialog = gtk.FileChooserDialog(caption, self.main_window,                                       
                                       buttons=(gtk.STOCK_CANCEL,
                                                gtk.RESPONSE_REJECT,
                                                gtk.STOCK_OK,
                                                gtk.RESPONSE_ACCEPT))
        dialog.set_select_multiple(True)
        dialog.set_filter(filefilter)
        res = dialog.run()
        files = dialog.get_filenames()
        dialog.destroy()
        if res == gtk.RESPONSE_REJECT:
            return
        if files:
            self.load_new_amz_files(files)

    def load_new_amz_files(self, amz_files):
        parser = AmzParser()
        for f in amz_files:
            parser.parse(f)
        objects = parser.get_parsed_objects()        
        self.tree_model = TreeModel(objects)        
        self.treeView.set_model(self.tree_model)
        self.treeView.expand_all()

    def download_tracks(self):
        self.num_threads = 1        
        if not self.tree_model:
            return
        save_dir = settings.save_dir               
        if not os.access(save_dir, os.W_OK):
            print 'here'
            msg = 'No write access to save directory. '
            msg += 'Choose a new directory with write privileges.'
            dialog = gtk.MessageDialog(self.main_window, 
                                       buttons=gtk.BUTTONS_OK)
            dialog.set_markup(msg)
            dialog.run()
            dialog.destroy()
            return        
        self.downloader = Downloader(self.tree_model, self.update_cb, 
                                     self.finished_cb)
        self.actionDownload.set_sensitive(False)
        self.actionSettings.set_sensitive(False)
        self.actionLoadFiles.set_sensitive(False)        
        self.downloader.start()            

    def update_cb(self, node):
        self.tree_model.update_node(node)
    
    def finished_cb(self):
        self.downloader = None
        self.reset_displaybar_info()
        self.actionDownload.set_sensitive(True)
        self.actionSettings.set_sensitive(True)
        self.actionLoadFiles.set_sensitive(True)


if __name__ == '__main__':
    app = MainWindow()
    gtk.gdk.threads_enter()    
    gtk.main()
    gtk.gdk.threads_leave()
