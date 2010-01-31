"""
Pymazon - A Python based downloader for the Amazon.com MP3 store
Copyright (c) 2009 Steven C. Colbert

`pymazongtk.py' by Raymond Myers, using tiny bits from Steven C. Colbert.

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

import gtk, gobject
from pymazon.pymazonbackend import parse_tracks, Downloader, ImageCache, \
                                   set_save_templ, get_save_templ


class AlbumArt(object):
    def __init__(self):
        self.cache = ImageCache()
        
    def get(self, url):
        jpg = self.cache.get(url)
        loader = gtk.gdk.PixbufLoader()
        #loader.set_size(64,64) # << Lock the size to 64x64, because we can.
        loader.write(jpg)
        loader.close()
        return loader.get_pixbuf()


# GtkBuilder seems to mess up the horizontal sizing for the Progress bar 
# renderer, and GTK in general is too greedy when it comes to vertical sizing.
class MyProgressRenderer(gtk.CellRendererProgress):    
    
    def do_render(self, window, widget, background_area, area, expose_area, flags):
        # Don't draw when the 'text' is '--':
        if self.get_property("text") == "--": 
            return
        
        # Calculate the new height of the progress bar:
        new_height = min(area.height, 24)
        diff = area.height - new_height
        
        # Apply the new height into the bar, and center vertically:
        new_area = gtk.gdk.Rectangle(area.x, (area.y+diff/2), area.width, new_height)
        gtk.CellRendererProgress.do_render(self, window, widget, background_area, new_area, expose_area, flags)
        
        # Solid black outline, because we can. :)
        # I don't think that jives with the rest of the program's look and feel - SCC
        #color = widget.style.fg[gtk.STATE_NORMAL]
        #gc = gtk.gdk.GC(window, foreground=color)
        #window.draw_rectangle(gc, False, new_area.x, new_area.y, new_area.width-1, new_area.height-1)
    

gobject.type_register(MyProgressRenderer)


class MainWindow:

    # The pymazon.gtk file is in the same directory as this file:
    BUILDER_FILE_PATH = os.path.join(os.path.dirname(__file__), "pymazon.gtk")
    
    # The messages for the download progress
    messages = ['Connecting...', 'Downloading...', 'Complete!', 'Error!']

    def __init__(self, amz_file=None):
        self.b = gtk.Builder()
        self.b.add_from_file(MainWindow.BUILDER_FILE_PATH)
        
        self.window       = self.b.get_object("Window")
        self.button       = self.b.get_object("Download")
        self.model        = self.b.get_object("InfoModel")        
        self.filechooser  = self.b.get_object("FileChooser")
        self.dirchooser   = self.b.get_object("DirectoryChooser")
        self.colstatus    = self.b.get_object("ColStatus")
        self.formatlist   = self.b.get_object("FormatStrings")
        self.formatdialog = self.b.get_object("FormatDialog")
        self.formatentry  = self.b.get_object("FormatEntry")
        self.model_map = {}
        self.oldformat = 0

        self.set_filter()
        
        # The progress renderer isn't done justice with GtkBuilder. :)
        renderer = MyProgressRenderer()
        self.colstatus.clear()
        self.colstatus.pack_start(renderer, True)
        self.colstatus.add_attribute(renderer, 'value', 6)
        self.colstatus.add_attribute(renderer, 'text',  5)        

        self.window.connect("delete-event", gtk.main_quit)
        self.filechooser.connect("file-set", self.load_file)
        self.button.connect("clicked", self.start_download)
        self.formatlist.connect("changed", self.new_format)
        self.formatentry.connect("icon-release", self.reset_string)
        
        self.button.set_sensitive(False) # No file yet.
        self.parsed = None
        self.art  = AlbumArt()
        
        # setup the format store
        self.fmt_strings = [get_save_templ(),
                            '${title}',
                            '${tracknum} - ${artist} - ${title}',
                            '${artist} - ${title}',
                            'Custom...']
        # add back the default if the user config overrode it
        if '${tracknum} - ${title}' not in self.fmt_strings:
            self.fmt_strings.insert(1, '${tracknum} - ${title}')
        self.fmt_store = gtk.ListStore(gobject.TYPE_STRING)
        for fmt in self.fmt_strings:
            self.fmt_store.append([fmt])
        self.formatlist.set_model(self.fmt_store)        
        
        # If we were given it, set the filename:
        # (doesn't work for some reason...
        #if amz_file:
        #    self.filechooser.select_filename(amz_file)
        #    self.load_file(self.filechooser)    
    
    def reset_string(self, *ignored_options):
    	self.formatentry.set_text("${tracknum} - ${title}")
    
    def new_format(self, combobox):
    	selected = self.formatlist.get_active()
    	if self.fmt_store[selected][0] == 'Custom...':
    		self.other_option()
    	else:
    		self.oldformat = selected
    		set_save_templ(self.fmt_store[selected][0])
    
    def other_option(self):
        code = self.formatdialog.run()
        self.formatdialog.hide()
        
        # If 'code' is 1, then 'ok' was clicked. otherwise, we cancel:
        if code == 1:
            text = self.formatentry.get_text()
            
            if r"${title}" not in text:
                win = gtk.MessageDialog(parent=self.window, type=gtk.MESSAGE_ERROR,
                    buttons=gtk.BUTTONS_OK,
                    message_format="Format strings need to have ${title} in them.")
                win.run()
                win.hide()
                # Try again:
                self.other_option()
                return
            
            # Set the new format string:
            set_save_templ(text)
            if text not in self.fmt_strings:
                self.fmt_store.append([text])
                self.fmt_strings.append(text)
            self.formatlist.set_active(self.fmt_strings.index(text))
            return
        
        # Else, the old option needs to be reinstated:
        self.formatlist.set_active(self.oldformat)
        
    def set_filter(self):
        self.filefilter = gtk.FileFilter()
        self.filefilter.add_pattern("*.amz")
        self.filechooser.set_filter(self.filefilter)    
    
    def refresh_list(self):
        self.model.clear()
        self.model_map = {}

        i = 0
        for item in self.parsed:
            # The url is put in there, so that we can find it again later...
            self.model.append([self.art.get(item.image), int(item.tracknum),
                               item.title, item.artist, item.album, "--", 0,
                               item.url])
            row_ref = gtk.TreeRowReference(self.model, i)
            self.model_map[item] = row_ref
            i += 1 
            
    def load_file(self, button):
        filename = button.get_filename()        
        self.parsed = parse_tracks(filename) if filename else []
        self.refresh_list()
        if len(self.parsed) > 0: self.button.set_sensitive(True)
        
        # Due to a bug in GTK, the filter gets reset after use. Reset:
        self.set_filter()    
    
    def set_sensitivity(self, b):
        self.button.set_sensitive(b)
        self.filechooser.set_sensitive(b)
        self.dirchooser.set_sensitive(b)    
        self.formatlist.set_sensitive(b)
        
    def start_download(self, button):
        save_dir = self.dirchooser.get_filename()
        self.downloader = Downloader(save_dir, self.parsed, self.downloader_callback, num_threads=5)
        self.downloader.start()
        self.set_sensitivity(False)    
    
    def set_dl_info(self, track, message, percent):        
        row_path = self.model_map[track].get_path()
        row = self.model[row_path]
        row[5], row[6] = message, percent    
    
    def downloader_callback(self, track, status, *args):        
        
        if status == 4:
            self.downloader = None
            self.set_sensitivity(True)
        
        else:
            msg = self.messages[status]
            if args:
                percent = args[0]
                msg += ('%s%%' % percent)
            else:
                # Pick a value for percent: 0 if connecting, 100 if complete. 
                percent = 0 if status == 0 else 100
            
            self.set_dl_info(track, msg, percent)    
    
    def start(self):
        gtk.gdk.threads_init()
        self.window.show()        
        gtk.gdk.threads_enter()
        gtk.main()
        gtk.gdk.threads_leave()

