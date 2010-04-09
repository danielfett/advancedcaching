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
 p.description="Paperless (offline) geocaching.\n AGTL downloads cache locations in the area visible on the map including their description, hints, difficulty levels and images. Searching for caches in your local db is a matter of seconds. The currently selected cache is shown on the map (and also all the others if you want) and there's a traditional compass-like view that show the direction to the cache."
 p.author="Daniel Fett"
 p.mail="advancedcaching@fragcom.de"
 p.depends = "python2.5, python-gtk2, python-simplejson, python-location, python-hildon (>= 0.9.0-1maemo15)"
 p.section="user/navigation"
 p.icon = "src/usr/share/icons/hicolor/48x48/hildon/advancedcaching.png"
 p.arch="all"                #should be all for python, any for all arch
 p.urgency="low"             #not used in maemo onl for deb os
 p.distribution="fremantle"
 p.repository="extras-devel"
 p.xsbc_bugtracker="http://github.com/webhamster/advancedcaching"
 #  p.postinstall="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your post install script
 #  p.postremove="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your post remove script
 #  p.preinstall="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your pre install script
 #  p.preremove="""#!/bin/sh
 #  chmod +x /usr/bin/advancedcaching.py""" #Set here your pre remove script
 version = "0.5.2"
 build = "0"############# for the first build of this version of your software. Increment for later re-builds of the same version of your software.
                             #Text with changelog information to be displayed in the package "Details" tab of the Maemo Application Manager
 changeloginformation = """
Changes from 0.5.1:
 * Fixed downloading of geocaches
 * Added various features:
   - Type a coordinate into the "notes" field and it is selectable in the "coords" tab
   - Calculated coordinates are listed there, too
 * Fixed a lot of bugs
Changes from 0.5.2:
 * Bug fix release for 0.5.1
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
