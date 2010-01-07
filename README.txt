 
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
[http://www.pycrypto.org PyCrypto] (and PyQt4 >= 4.5 if you want to use the GUI).
----

==Installation==
**see INSTALL.txt**
----

==Use==
Currently, pymazon can be used from the command line or the GUI 
(which requires PyQt4 >= 4.5).

===_Command Line Interface_===
To download to current directory:
{{{
$ pymazon /path/to/amz/file/foo.amz
}}}
To download to alternate directory:
{{{
$ pymazon /path/to/amz/file/foo.amz -d /path/to/save/dir/
}}}
===_GUI Interface_===
To Launch Pymazon in GUI mode:
{{{
$ pymazon -g
}}}
The GUI is pretty self explanatory.

If you get stuck:
{{{
$ pymazon --help
}}}
----
==Stuff==
If you get _*Error!*_ printed to the console or status box when downloading, 
Pymazon will create a log file in the current working directory called 
pymazon_error_log.txt. This log will have more information about what caused 
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