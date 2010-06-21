import pygtk
pygtk.require('2.0')
import gtk
import webbrowser

import sys
sys.path.append('/home/brucewayne/development/pymazon/hg')

from pymazon.resource import python_icon_path

class TestApp(object):
    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file('_gtk_new.glade')
        self.connect_signals(builder)       
        
        self.albumArtImage = builder.get_object('albumArtImage')
        self.nowDownloadingLabel = builder.get_object('nowDownloadingLabel')
        self.pythonPixbuf = gtk.gdk.pixbuf_new_from_file(python_icon_path)
        self.pymazon_text = '<span weight="bold" size="xx-large">Pymazon! w00t!</span>'
        self.reset_displaybar_info()        
        
        self.main_window = builder.get_object('MainWindow')        
        self.main_window.show()        
    
    def connect_signals(self, builder):
        builder.connect_signals({'on_MainWindow_destroy': gtk.main_quit})
        actionAbout = builder.get_object('actionAbout')
        actionAbout.connect('activate', self.on_actionAbout_activate)
        actionLoadFiles = builder.get_object('actionLoadFiles')
        actionLoadFiles.connect('activate', self.on_actionLoadFiles_activate)
        actionSettings = builder.get_object('actionSettings')
        actionSettings.connect('activate', self.on_actionSettings_activate)
        actionShowDownloads = builder.get_object('actionShowDownloads')
        actionShowDownloads.connect('activate', self.on_actionShowDownloads_activate)
        actionDownload = builder.get_object('actionDownload')
        actionDownload.connect('activate', self.on_actionDownload_activate)      
        actionQuit = builder.get_object('actionQuit')
        actionQuit.connect('activate', gtk.main_quit)

    def on_actionAbout_activate(self, *args):
        webbrowser.open('http://code.google.com/p/pymazon')

    def on_actionLoadFiles_activate(self, *args):
        print 'load files'

    def on_actionSettings_activate(self, *args):
        print 'preferences'

    def on_actionShowDownloads_activate(self, *args):
        print 'show downloads'

    def on_actionDownload_activate(self, *args):
        print 'download'

    def reset_displaybar_info(self):
        self.albumArtImage.set_from_pixbuf(self.pythonPixbuf)
        self.nowDownloadingLabel.set_markup(self.pymazon_text)

if __name__ == '__main__':
    app = TestApp()
    gtk.main()
