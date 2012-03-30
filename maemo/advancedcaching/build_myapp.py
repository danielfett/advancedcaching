#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
import py2deb
import os
if __name__ == "__main__":
 try:
     os.chdir(os.path.dirname(sys.argv[0]))
 except:
     pass
 print
 p=py2deb.Py2deb("advancedcaching")   #This is the package name and MUST be in lowercase! (using e.g. "advancedcaching" fails miserably...)
 p.description='''AGTL, the all-in-one solution for on- and offline geocaching, makes geocaching paperless! 
It downloads geocaches including their description, hints, difficulty levels and images. No premium account needed. Searching for caches in your local db is a matter of seconds.
.
- Map view - supporting Open Street Maps and Open Cycle Maps by default, configurable for other map types, including google maps.
- GPS view - shows the distance and direction to the selected geocache.
- Cache details - all necessary details are available even in offline mode.
- Paperless geocaching features - take notes for a geocache on the go, see the hints and spoiler images, check the latest logs.
- Multicache calculation help - Let your phone do the math for you. Working for the most multi-stage geocaches, AGTL finds the coordinate calculations and let you enter the missing variables.
- Fieldnotes support - Ever came home after a long tour and asked yourself which geocaches you found? Never again: Log your find in the field and upload notes and log text when you're at home. Review them on the geocaching website and post the logs.
- Text-to-Speech-Feature! - Select a target, activate TTS and put your headphones on to enjoy completely stealth geocaching. 
- Download map tiles for selected zoom levels - for offline use.
- Advanced waypoint handling - AGTL finds waypoints in the geocache descriptions, in the list of waypoints and even in your notes. For your convenience, they're displayed on the map as well - see where you have to go next.
- Search for places - in the geonames.org database to navigate quickly.
- Sun compass - Compensates the lack of a magnetic compass.
- Instant update feature - Follow web site updates as soon as possible.
.
AGTL is Open source and in active development.'''
 
 p.author="Daniel Fett"
 p.mail="advancedcaching@fragcom.de"
 p.depends = "python2.5, python-gtk2, python-simplejson, python-location, python-hildon (>= 0.9.0-1maemo17), python-gtkhtml2, python-dbus, python-osso, python-conic, python-lxml"
 p.section="user/navigation"
 p.icon = "src/usr/share/icons/hicolor/48x48/hildon/advancedcaching.png"
 p.arch="all"                #should be all for python, any for all arch
 p.urgency="low"             #not used in maemo onl for deb os
 p.distribution="fremantle"
 p.repository="extras-devel"
 p.xsbc_bugtracker="http://github.com/webhamster/advancedcaching\nXB-Maemo-Display-Name: Advanced Geocaching Tool for Linux"
 #  p.postinstall="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your post install script
 #  p.postremove="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your post remove script
 #  p.preinstall="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your pre install script
 #  p.preremove="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your pre remove script
 version = "0.9.0.0"
 build = "0"    # for the first build of this version of your software. Increment for later re-builds of the same version of your software.
                # Text with changelog information to be displayed in the package "Details" tab of the Maemo Application Manager
 changeloginformation = """
- Fix after Website update in February
- Integrate some changes from N9 version
"""
 dir_name = "src"            #Name of the subfolder containing your package source files (e.g. usr\share\icons\hicolor\scalable\myappicon.svg, usr\lib\myapp\somelib.py). We suggest to leave it named src in all projects and will refer to that in the wiki article on maemo.org
 #Thanks to DareTheHair from talk.maemo.org for this snippet that recursively builds the file list 
 for root, dirs, files in os.walk(dir_name):
     real_dir = root[len(dir_name):]
     fake_file = []
     for f in files:
         fake_file.append(root + os.sep + f + "|" + f)
     if len(fake_file) > 0:
         p[real_dir] = fake_file
 print p
 r = p.generate(version,build,changelog=changeloginformation,tar=True,dsc=True,changes=True,build=False,src=True)
