#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2010 Daniel Fett
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#   Author: Daniel Fett agtl@danielfett.de
#   Jabber: fett.daniel@jaber.ccc.de
#   Bugtracker and GIT Repository: http://github.com/webhamster/advancedcaching
#

import logging
logger = logging.getLogger('qtgui')

from PySide import QtGui
from PySide import QtDeclarative
from PySide import QtOpenGL
from PySide import QtCore
import os
import sys
import geo
import re
from os import path
from gui import Gui

d = lambda x: x.decode('utf-8', 'replace')

class Controller(QtCore.QObject):
    def __init__(self, view, core):
        QtCore.QObject.__init__(self)
        self.view = view
        self.core = core
        self.current_cache = None
        self.core.connect('progress', self.show_progress)
        self.core.connect('hide-progress', self.hide_progress)
        self.core.connect('cache-changed', self.cache_changed)
        self.core.connect('error', self.show_message)

    def show_message(self, caller, message):
        self.view.rootObject().showMessage(message)

    def cache_changed(self, caller, cache):
        if self.current_cache != None and self.current_cache.name == cache.name:
            self.current_cache._geocache = cache
            self.current_cache.changed.emit()

    def hide_progress(self, caller):
        self.view.rootObject().hideProgress()

    def show_progress(self, caller, progress, message):
        self.view.rootObject().showProgress(progress, message)

    @QtCore.Slot(QtCore.QObject)
    def geocacheDownloadDetailsClicked(self, wrapper):
        self.core.on_download_cache(wrapper._geocache)

    @QtCore.Slot(QtCore.QObject)
    def geocacheSelected(self, wrapper):
        self.current_cache = wrapper
        x = [CoordinateWrapper(x) for x in wrapper._geocache.get_collected_coordinates(format = geo.Coordinate.FORMAT_DM).values()]
        self.view.rootObject().setCurrentGeocache(wrapper, CoordinateListModel(self.core, x))

    @QtCore.Slot(float, float, float, float)
    def mapViewChanged(self, lat_start, lon_start, lat_end, lon_end):
        #logger.debug("Map view changed to %f-%f, %f-%f." % (lat_start, lon_start, lat_end, lon_end))
        self.view.rootObject().setGeocacheList(GeocacheListModel(self.core, lat_start, lon_start, lat_end, lon_end))

class SettingsWrapper(QtCore.QObject):
    def __init__(self, core):
        QtCore.QObject.__init__(self)
        self.core = core

    changed = QtCore.Signal()

    def _username(self):
        return self.core.settings['options_username']

    def _password(self):
        return self.core.settings['options_password']

    def _setUsername(self, u):
        self.core.settings['options_username'] = u
        self.core.emit('settings-changed', self.core.settings, self)
        self.changed.emit()

    def _setPassword(self, p):
        logger.debug("Password is '%s'" % p)
        self.core.settings['options_password'] = p
        self.core.emit('settings-changed', self.core.settings, self)
        self.changed.emit()

    username = QtCore.Property(str, _username, _setUsername, notify=changed)
    password = QtCore.Property(str, _password, _setPassword, notify=changed)

class CoordinateWrapper(QtCore.QObject):
    def __init__(self, coordinate):
        QtCore.QObject.__init__(self)
        self._coordinate = coordinate

    def _name(self):
        return self._coordinate.name

    def _lat(self):
        return self._coordinate.lat

    def _lon(self):
        return self._coordinate.lon

    def _display_text(self):
        return self._coordinate.display_text

    def _comment(self):
        return self._coordinate.comment

    def _user_coordinate_id(self):
        return self._coordinate.user_coordinate_id

    changed = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    display_text = QtCore.Property(unicode, _display_text, notify=changed)
    comment = QtCore.Property(unicode, _comment, notify=changed)
    user_coordinate_id = QtCore.Property(unicode, _user_coordinate_id, notify=changed)

class GeocacheWrapper(QtCore.QObject):
    def __init__(self, geocache, core):
        QtCore.QObject.__init__(self)
        self._geocache = geocache
        self.core = core
        
    def _name(self):
        return self._geocache.name

    def _title(self):
        return d(self._geocache.title)

    def _lat(self):
        return self._geocache.lat

    def _lon(self):
        return self._geocache.lon

    def _shortdesc(self):
        return self._geocache.shortdesc

    def _desc(self):
        if self._geocache.desc != '' and self._geocache.shortdesc != '':
            showdesc = "<b>%s</b><br />%s" % (self._geocache.shortdesc, self._geocache.desc)
        elif self._geocache.desc == '' and self._geocache.shortdesc == '':
            showdesc = "<i>No description available</i>"
        elif self._geocache.desc == '':
            showdesc = self._geocache.shortdesc
        else:
            showdesc = self._geocache.desc
        showdesc = d(showdesc)
        showdesc = re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: "<img src='%s' />" % self.get_path_to_image(a.group(1)), showdesc)
        return showdesc


    def get_path_to_image(self, image):
        return path.join(self.core.settings['download_output_dir'], image)

    def _type(self):
        return self._geocache.type

    def _size(self):
        return self._geocache.size

    def _difficulty(self):
        return (self._geocache.difficulty/10.0)

    def _terrain(self):
        return (self._geocache.terrain/10.0)

    def _owner(self):
        return self._geocache.owner

    def _found(self):
        return self._geocache.found

    #def _waypoints(self):
    #    return self._geocache.owner

    def _images(self):
        return self._geocache.get_images()

    def _status(self):
        return self._geocache.status


    changed = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    title = QtCore.Property(unicode, _title, notify=changed)
    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    desc = QtCore.Property(str, _desc, notify=changed)
    shortdesc = QtCore.Property(str, _shortdesc, notify=changed)
    type = QtCore.Property(str, _type, notify=changed)
    size = QtCore.Property(int, _size, notify=changed)
    difficulty = QtCore.Property(float, _difficulty, notify=changed)
    terrain = QtCore.Property(float, _terrain, notify=changed)
    owner = QtCore.Property(str, _owner, notify=changed)
    found = QtCore.Property(bool, _found, notify=changed)
    images = QtCore.Property(QtCore.QObject, _images, notify=changed)
    status = QtCore.Property(int, _status, notify=changed)
    #coordinates = QtCore.Property("QVariant", _coordinates, notify=changed)

class GeocacheListModel(QtCore.QAbstractListModel):
    COLUMNS = ('geocache',)

    def __init__(self, core, lat_start, lon_start, lat_end, lon_end):
        QtCore.QAbstractListModel.__init__(self)
        self._geocaches = [GeocacheWrapper(x, core) for x in core.pointprovider.get_points(geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end))[0:100]]
        self.setRoleNames(dict(enumerate(GeocacheListModel.COLUMNS)))

        logger.debug("Loaded %d geocaches" % len(self._geocaches))

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._geocaches)

    def data(self, index, role):
        if index.isValid() and role == GeocacheListModel.COLUMNS.index('geocache'):
            return self._geocaches[index.row()]
        return None

class CoordinateListModel(QtCore.QAbstractListModel):
    COLUMNS = ('coordinate',)

    def __init__(self, core, coordinates = []):
        QtCore.QAbstractListModel.__init__(self)
        #self._geocaches = [GeocacheWrapper(x, core) for x in core.pointprovider.get_points(geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end))[0:100]]
        self._coordinates = coordinates
        self.setRoleNames(dict(enumerate(CoordinateListModel.COLUMNS)))

    def add_many(self, coordinates):
        self._coordinates += coordinates

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._coordinates)

    def data(self, index, role):
        if index.isValid() and role == CoordinateListModel.COLUMNS.index('coordinate'):
            return self._coordinates[index.row()]
        return None

class QmlGui(Gui):

    USES = ['geonames']

    def __init__(self, core, dataroot, parent=None):
        self.app = QtGui.QApplication(sys.argv)
        self.core = core
        self.view = QtDeclarative.QDeclarativeView()
        self.view.statusChanged.connect(self._status_changed)
        glw = QtOpenGL.QGLWidget()
        self.view.setViewport(glw)
        
        controller = Controller(self.view, self.core)
        settings = SettingsWrapper(self.core)
        #geocacheList = GeocacheListModel(self.core)

        rc = self.view.rootContext()
        rc.setContextProperty('controller', controller)
        rc.setContextProperty('settings', settings)
        #rc.setContextProperty('geocacheList', geocacheList)
        #rc.setContextProperty('geocacheList', 42)

        self.view.setSource(os.path.join('qml','main.qml'))
        


    def show(self):
        self.view.showFullScreen()
        self.app.exec_()
        self.core.on_destroy()

    def _status_changed(self, error):
        logger.error(self.view.errors())
