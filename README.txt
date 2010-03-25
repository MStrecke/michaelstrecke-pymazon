 
=Pymazon=

==Summary==
This project is a python implemented downloader for the amazon mp3 store. 

The propietary Amazon downloader for Linux just, well, it's not good. 
Seriously guys, C++ and boost for a downloader!??! Not to mention there are no 
64-bit Linux builds... ugh...(But seriously, Amazon, if you're listening, 
thanks for giving the Linux community some love by making Linux releases in the 
first place. It's way more than most companies would do!)

This program uses some ideas/work from the C-based 
[http://code.google.com/p/clamz/ Clamz] project by Benjamin Moody. Thanks Ben!

The only dependency outside of the Python standard library is 
[http://www.pycrypto.org PyCrypto] (and PyQt4 >= 4.5 or PyGtk if you want to use the GUI).
----

==Installation==
**see INSTALL.txt**
----

==Use==
Currently, pymazon can be used from the command line or the GUI 
(which requires PyQt4 >= 4.5 or PyGtk).

===_GUI Interface_===
To Launch Pymazon in GUI mode:
{{{
$ pymazon 
}}}
The GUI is pretty self explanatory.
===_Command Line Interface_===
To download to current directory:
{{{
$ pymazon -c /path/to/amz/file/foo.amz
}}}
To download to alternate directory:
{{{
$ pymazon -c -d /path/to/save/dir/ /path/to/amz/file/foo.amz
}}}

If you get stuck:
{{{
$ pymazon --help
}}}
----
===_Name Templates_===
Pymazon supports name templates for the save name of the file. 

A name template is a string of the form:
{{{
${argument}whatevertextyouwant
}}}
Valid arguments include:
    title
    artist
    tracknum
    album
    
The template must include *at least* 
{{{
${title}
}}}
otherwise, Pymazon will use a default template. 

For example, suppose the current name template is 
{{{
${tracknum} - ${title}
}}}
The for a song spam.mp3 that is number 05 on the album, and a save directory of 
/ham/eggs, then the song will be written to disk as:
{{{
/ham/eggs/spam.mp3
}}}
The templates are flexible. Suppose you have a template of the form:
{{{
${artist}/${album}/${tracknum} - ${title}
}}}
and a save directory ~/Music, then every song in the .amz file will be written
to disk as:
{{{
~/Music/artist/album/tracknum - title
}}}
This is the format used by the author of Pymazon.
----
===_Configuration File_===
Pymazon supports a pymazonrc file located at ~/.pymazon/pymazonrc 
For windows users this path is the output of
{{{
>>> import os
>>> os.path.join(os.path.expanduser('~'), '.pymazon', 'pymazonrc')
}}}
You are responsible for creating this file if you want to use.

The pymazonrc file has the follwing form
{{{
[config]
name_template = ${your}/${name}/${template} - ${here}
save_dir = /path/to/default/save/dir
amz_dir = /path/to/default/amz/dir # currently has no effect
toolkit = qt4 # or gtk
num_threads = 5 # must be >= 1
}}}

Those are the only options supported by the config file. Pymazon is a fairly 
simple program.
----
==Stuff==
If you get _*Error!*_ printed to the console or status box when downloading, 
Pymazon will create a log file in the .pymazon/logs directory. 
This log will have more information about what caused 
the failure and the specifics of the track it was trying to download. 
The usual cause for errors are due to no internet connection (in which case 
you won't see album art in the GUI) or an expired .amz file 
(i.e. the Amazon download links have expired). If you get an error, and the 
link in the log file is valid (you can use it from a web browser), then please 
file a bug report and include the log as an attachment. 

Errors not related to downloading will show up as exceptions with (hopefully) 
useful error messages. 

I appreciate comments, suggestions, and bug reports.

That's about it. 

SCC