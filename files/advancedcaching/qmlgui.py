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
import gpsreader
from os import path
from gui import Gui
from astral import Astral

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
        self.core.connect('map-marks-changed', self.map_marks_changed)
        self.callback_gps = None

    marksChanged = QtCore.Signal()

    def map_marks_changed(self, caller):
        self.marksChanged.emit()

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
        self.view.rootObject().setCurrentGeocache(wrapper, CoordinateListModel(self.core, x), wrapper._logs())

    @QtCore.Slot(QtCore.QObject, float, float, float, float)
    def mapViewChanged(self, map, lat_start, lon_start, lat_end, lon_end):
        #logger.debug("Map view changed to %f-%f, %f-%f." % (lat_start, lon_start, lat_end, lon_end))
        if self.view.rootObject() != None:
            self.view.rootObject().setGeocacheList(map, GeocacheListModel(self.core, lat_start, lon_start, lat_end, lon_end))

    @QtCore.Slot(float, float, float, float)
    def updateGeocaches(self, lat_start, lon_start, lat_end, lon_end):
        self.core.on_download([geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end)])

    @QtCore.Slot(float, float)
    def setTarget(self, lat, lon):
        logger.debug("Setting target to %f, %f" % (lat, lon))
        self.core.set_target(geo.Coordinate(lat, lon))

    @QtCore.Slot(QtCore.QObject)
    def setAsTarget(self, coordinate):
        self.core.set_target(coordinate._coordinate)

    @QtCore.Slot(bool, float, float, bool, float, bool, float, float, QtCore.QObject)
    def positionChanged(self, valid, lat, lon, altvalid, alt, speedvalid, speed, error, timestamp):
        if self.callback_gps == None:
            logger.debug("No GPS callback registered")
            return
        if valid:
            p = geo.Coordinate(lat, lon)
        else:
            p = None
        logger.debug("TS is %r" % timestamp)
        a = gpsreader.Fix(position = p,
            altitude = alt if altvalid else None,
            bearing = None,
            speed = speed if speedvalid else None,
            sats = 0,
            sats_known = 0,
            dgps = False,
            quality = 0,
            error = error,
            error_bearing = 0,
            timestamp = timestamp)
        logger.debug("Position changed, new fix is %r" % a)
        self.callback_gps(a)


    def _distance_unit(self):
        return "m"

    def _coordinate_format(self):
        return "DM"

    changed = QtCore.Signal()

    distanceUnit = QtCore.Property(str, _distance_unit, notify=changed)
    coordinateFormat = QtCore.Property(str, _coordinate_format, notify=changed)

class FixWrapper(QtCore.QObject):

    def __init__(self, fix):
        QtCore.QObject.__init__(self)
        self.data = fix

    changed = QtCore.Signal()
    
    def update(self, fix):
        self.data = fix
        logger.debug("Fix updated with data from %r" % fix)
        self.changed.emit()

    def _lat(self):
        if self.data.position != None:
            return self.data.position.lat
        else:
            return -1

    def _lon(self):
        if self.data.position != None:
            return self.data.position.lon
        else:
            return -1

    def _altitude(self):
        return self.data.altitude if self.data.altitude != None else 0

    def _speed(self):
        return self.data.speed if self.data.altitude != None else 0

    def _error(self):
        return float(self.data.error)

    def _valid(self):
        return (self.data.position != None)

    def _altitude_valid(self):
        return self.data.altitude != None

    def _speed_valid(self):
        return self.data.speed != None

    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    altitude = QtCore.Property(float, _altitude, notify=changed)
    speed = QtCore.Property(float, _speed, notify=changed)
    error = QtCore.Property(float, _error, notify=changed)
    valid = QtCore.Property(bool, _valid, notify=changed)
    speedValid = QtCore.Property(bool, _speed_valid, notify=changed)
    altitudeValid = QtCore.Property(bool, _altitude_valid, notify=changed)


class GPSDataWrapper(QtCore.QObject):

    changed = QtCore.Signal()
    changed_target = QtCore.Signal()
    changed_distance_bearing = QtCore.Signal()

    def __init__(self, core):
        QtCore.QObject.__init__(self)
        self.core = core
        self.core.connect('good-fix', self._on_good_fix)
        self.core.connect('no-fix', self._on_no_fix)
        self.core.connect('target-changed', self._on_target_changed)
        self.gps_data = FixWrapper(gpsreader.Fix())
        self.gps_last_good_fix = FixWrapper(gpsreader.Fix())
        self.gps_target_distance = -1.0
        self.gps_target_bearing = -1.0
        self.gps_status = ''
        self._target_valid = False
        self._target = CoordinateWrapper(geo.Coordinate(0, 0))
        self.astral = Astral()


    def _on_good_fix(self, core, gps_data, distance, bearing):
        logger.debug("Received good fix")
        self.gps_data.update(gps_data)
        self.gps_last_good_fix.update(gps_data)
        self.gps_has_fix = True
        self.gps_target_distance = distance
        self.gps_target_bearing = bearing

        self.changed_distance_bearing.emit()
        self.changed.emit()

    def _on_no_fix(self, caller, gps_data, status):
        self.gps_data.update(gps_data)
        self.gps_has_fix = False
        self.gps_status = status

        self.changed_distance_bearing.emit()
        self.changed.emit()

    def _on_target_changed(self, caller, target, distance, bearing):
        self._target_valid = True
        self._target = CoordinateWrapper(target)
        self.gps_target_distance = distance
        self.gps_target_bearing = bearing
        self.changed_distance_bearing.emit()
        self.changed_target.emit()
        logger.debug("Target is now set to %r" % target)

#    def _sun_angle_valid(self):
#        return self.astral.get_sun_azimuth_from_fix(self.gps_last_good_fix) != None
#

    def _target(self):
        return self._target

    def _target_valid(self):
        return self._target_valid

    def _gps_data(self):
        return self.gps_data

    def _gps_last_good_fix(self):
        return self.gps_last_good_fix

    def _gps_has_fix(self):
        return self.gps_has_fix

    def _gps_target_distance_valid(self):
        return self.gps_target_distance != None

    def _gps_target_distance(self):
        logger.debug("Target distance is %r" % self.gps_target_distance)
        return float(self.gps_target_distance) if self._gps_target_distance_valid()  else 0

    def _gps_status(self):
        return self.gps_status

    data = QtCore.Property(QtCore.QObject, _gps_data, notify=changed)
    lastGoodFix = QtCore.Property(QtCore.QObject, _gps_last_good_fix, notify=changed)
    hasFix = QtCore.Property(bool, _gps_has_fix, notify=changed)
    targetValid = QtCore.Property(bool, _target_valid, notify=changed_target)
    target = QtCore.Property(QtCore.QObject, _target, notify=changed_target)
    targetDistanceValid = QtCore.Property(bool, _gps_target_distance_valid, notify=changed_target)
    targetDistance = QtCore.Property(float, _gps_target_distance, notify=changed_distance_bearing)
    status = QtCore.Property(str, _gps_status, notify=changed)


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
        return d(self._coordinate.display_text)

    def _comment(self):
        return d(self._coordinate.comment)

    def _user_coordinate_id(self):
        return self._coordinate.user_coordinate_id

    changed = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    display_text = QtCore.Property(str, _display_text, notify=changed)
    comment = QtCore.Property(str, _comment, notify=changed)
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
        showdesc = showdesc
        showdesc = re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: "<img src='%s' />" % self.get_path_to_image(a.group(1)), showdesc)
        return showdesc

    def _logs(self):
        return LogsListModel(self._geocache.logs)

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
    #logs = QtCore.Property(QtCore.QObject, _logs, notify=changed)
    #coordinates = QtCore.Property("QVariant", _coordinates, notify=changed)

class GeocacheListModel(QtCore.QAbstractListModel):
    COLUMNS = ('geocache',)

    def __init__(self, core, lat_start, lon_start, lat_end, lon_end):
        QtCore.QAbstractListModel.__init__(self)
        self._geocaches = [GeocacheWrapper(x, core) for x in core.pointprovider.get_points(geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end))[0:100]]
        self.setRoleNames(dict(enumerate(GeocacheListModel.COLUMNS)))

        logger.debug("Loaded %d geocaches for %f-%f %f-%f" % (len(self._geocaches), lat_start, lon_start, lat_end, lon_end))

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



class LogsListModel(QtCore.QAbstractListModel):
    COLUMNS = ('logs',)

    def __init__(self, core, logs = []):
        QtCore.QAbstractListModel.__init__(self)
        self._logs = [LogWrapper(x) for x in logs]
        self._logs = logs
        self.setRoleNames(dict(enumerate(LogsListModel.COLUMNS)))


    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._logs)

    def data(self, index, role):
        if index.isValid() and role == LogsListModel.COLUMNS.index('logs'):
            return self._logs[index.row()]
        return None

class LogWrapper(QtCore.QObject):
    changed = QtCore.Signal()
    def __init__(self, log):
        QtCore.QObject.__init__(self)
        self._log = log

    def _type(self):

        if self._log['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_FOUND:
            t = 'FOUND'
        elif self._log['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_NOTFOUND:
            t = 'NOT FOUND'
        elif self._log['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_NOTE:
            t = 'NOTE'
        elif self._log['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_MAINTENANCE:
            t = 'MAINTENANCE'
        else:
            t = self._log['type'].upper()
        return t

    def _finder(self):
        return self._log['finder']

    def _year(self):
        return self._log['year']

    def _month(self):
        return self._log['month']

    def _day(self):
        return self._log['day']

    def _text(self):
        return self._log['text']

    type = QtCore.Property(str, _type, notify=changed)
    finder = QtCore.Property(str, _finder, notify=changed)
    year = QtCore.Property(int, _year, notify=changed)
    month = QtCore.Property(int, _month, notify=changed)
    day = QtCore.Property(int, _day, notify=changed)
    text = QtCore.Property(str, _text, notify=changed)
    

class QmlGui(Gui):

    USES = ['geonames', 'qmllocationprovider']

    def __init__(self, core, dataroot, parent=None):
        self.app = QtGui.QApplication(sys.argv)
        self.core = core
        self.view = QtDeclarative.QDeclarativeView()
        self.view.statusChanged.connect(self._status_changed)
        glw = QtOpenGL.QGLWidget()
        self.view.setViewport(glw)
        
        self.controller = Controller(self.view, self.core)
        settings = SettingsWrapper(self.core)
        #geocacheList = GeocacheListModel(self.core)

        rc = self.view.rootContext()
        rc.setContextProperty('controller', self.controller)
        rc.setContextProperty('settings', settings)
        rc.setContextProperty('gps', GPSDataWrapper(self.core))
        #rc.setContextProperty('geocacheList', geocacheList)
        #rc.setContextProperty('geocacheList', 42)

        self.view.setSource(os.path.join('qml','main.qml'))

    def get_gps(self, callback):
        self.controller.callback_gps = callback

    def show(self):
        self.view.showFullScreen()
        self.app.exec_()
        self.core.on_destroy()

    def _status_changed(self, error):
        logger.error(self.view.errors())
