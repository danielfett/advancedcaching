#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2012 Daniel Fett
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
logger = logging.getLogger('qmlgui')

from PySide import QtGui
from PySide import QtDeclarative
from PySide import QtOpenGL
from PySide import QtCore
import os
import sys
import geo
geo.DEGREES = geo.DEGREES.decode('utf-8')
import re
import geocaching
import gpsreader
from os import path
from gui import Gui
#from astral import Astral

d = lambda x: x#.decode('utf-8', 'replace')

class Controller(QtCore.QObject):

    progressChanged = QtCore.Signal()
    versionChanged = QtCore.Signal()
    marksChanged = QtCore.Signal()
    
    MAX_POINTS = 200
    
    def __init__(self, view, core):
        QtCore.QObject.__init__(self)
        self.view = view
        self.core = core
        self.current_cache = None
        self.core.connect('progress', self._show_progress)
        self.core.connect('hide-progress', self._hide_progress)
        self.core.connect('cache-changed', self._cache_changed)
        self.core.connect('error', self._show_message)
        self.core.connect('map-marks-changed', self._map_marks_changed)
        self.core.connect('settings-changed', self._settings_changed)
        self.callback_gps = None
        self.c = None
        self._progress_visible = False
        self._progress = 0
        self._progress_message = ""
        self._geocache_lists = {}


    # Handle gobject signal from Core
    def _map_marks_changed(self, caller):
        self.marksChanged.emit()

    # Handle gobject signal from Core
    def _show_message(self, caller, message):
        self.view.rootObject().showMessage(str(message))

    # Handle gobject signal from Core
    def _cache_changed(self, caller, cache):
        if self.current_cache != None and self.current_cache.name == cache.name:
            self.current_cache.update(cache)

    # Handle gobject signal from Core
    def _hide_progress(self, caller):
        self._progress_visible = False
        logger.debug("Hide progress")
        self.progressChanged.emit()

    # Handle gobject signal from Core
    def _show_progress(self, caller, progress, message):
        self._progress_visible = True
        self._progress = float(progress)
        self._progress_message = str(message)
        self.progressChanged.emit()

    # Handle gobject signal from Core
    def _settings_changed(self, caller, settings, source):
        if source == self or type(source) == SettingsWrapper:
            return
        logger.debug("Got settings from %s, len() = %d, source = %s" % (caller, len(settings), source))

        if 'last_selected_geocache' in settings:
            c = self.core.pointprovider.get_by_name(settings['last_selected_geocache'])
            if c != None:
                self.geocacheSelected(GeocacheWrapper(c, self.core))
        if 'last_target_lat' in settings and 'last_target_lon' in settings:
            self.setTarget(settings['last_target_lat'], settings['last_target_lon'])


    @QtCore.Slot(QtCore.QObject)
    def geocacheDownloadDetailsClicked(self, wrapper):
        self.core.on_download_cache(wrapper._geocache)

    @QtCore.Slot(QtCore.QObject)
    def geocacheSelected(self, wrapper):
        self.current_cache = wrapper
        self.view.rootObject().setCurrentGeocache(wrapper)

        
    @QtCore.Slot(QtCore.QObject, float, float, float, float, result=bool)
    def getGeocaches(self, map, lat_start, lon_start, lat_end, lon_end):
        if self.view.rootObject() == None:
            return False
        
        points = self.core.pointprovider.get_points(geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end), self.MAX_POINTS + 1)
        
        if len(points) > self.MAX_POINTS:
            self._geocache_list = GeocacheListModel(self.core, [])
            toomany = True
        else:
            self._geocache_list = GeocacheListModel(self.core, points) 
            toomany = False
        self.view.rootObject().setGeocacheList(map, self._geocache_list)
        return toomany

    @QtCore.Slot(float, float, float, float)
    def updateGeocaches(self, lat_start, lon_start, lat_end, lon_end):
        self.core.on_download([geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end)])

    @QtCore.Slot(float, float, float, float)
    def downloadGeocaches(self, lat_start, lon_start, lat_end, lon_end):
        self.core.on_download_descriptions([geo.Coordinate(lat_start, lon_start), geo.Coordinate(lat_end, lon_end)])

    @QtCore.Slot(float, float)
    def setTarget(self, lat, lon):
        logger.debug("Setting target to %f, %f" % (lat, lon))
        self.core.set_target(geo.Coordinate(lat, lon))

    @QtCore.Slot(QtCore.QObject)
    def setAsTarget(self, coordinate):
        if type(coordinate) == GeocacheWrapper:
            c = coordinate._geocache
        elif type(coordinate) == CoordinateWrapper:
            c = coordinate._coordinate
        else:
            logger.debug("Setting Target to None")
            c = None
        self.core.set_target(c)

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
        
    @QtCore.Slot()
    def uploadFieldnotes(self):
        self.core.on_upload_fieldnotes()
        
    @QtCore.Slot(QtCore.QObject, QtCore.QObject, result = QtCore.QObject)
    def getEditWrapper(self, cache, obj):
        self.__editwrapper = CalcEditWrapper(cachewrapper = cache, source_id = obj.coordinate().source, coordinate = obj.coordinate())
        return self.__editwrapper
        
    @QtCore.Slot(QtCore.QObject, int, result = QtCore.QObject)
    def getEditWrapperByID(self, cache, id):
        self.__editwrapper = CalcEditWrapper(cachewrapper = cache, source_id = id)
        return self.__editwrapper
        
    @QtCore.Slot(QtCore.QObject, result = QtCore.QObject)
    def getAddCalcWrapper(self, cache):
        self.__editwrapper = CalcEditWrapper(cachewrapper = cache, add = CalcEditWrapper.ADD_CALC_STRING)
        return self.__editwrapper
        
    @QtCore.Slot(QtCore.QObject, result = QtCore.QObject)
    def getAddCoordinateWrapper(self, cache):
        self.__editwrapper = CalcEditWrapper(cachewrapper = cache, add = CalcEditWrapper.ADD_COORDINATE)
        return self.__editwrapper
        
    @QtCore.Slot(result = QtCore.QObject)
    def getGeocachesWithFieldnotes(self):
        self.__pointmodel = GeocacheListModel(self.core, self.core.pointprovider.get_new_fieldnotes())
        return self.__pointmodel
        
    @QtCore.Slot(result = QtCore.QObject)
    def getMarkedGeocaches(self):
        self.core.pointprovider.push_filter()
        self.core.pointprovider.set_filter(marked = True)
        self.__pointmodel = GeocacheListModel(self.core, self.core.pointprovider.get_points_filter())
        self.core.pointprovider.pop_filter()
        return self.__pointmodel

    def _progress(self):
        return self._progress

    def _progress_visible(self):
        return self._progress_visible

    def _progress_message(self):
        return self._progress_message
        
    def _core_version(self):
        import core
        return core.VERSION
        
    def _parser_version(self):
        import cachedownloader
        return cachedownloader.VERSION
        
    def _parser_date(self):
        import cachedownloader
        return cachedownloader.VERSION_DATE
        
    @QtCore.Slot()
    def tryParserUpdate(self):
        updates = self.core.try_update()
        if updates not in [None, False]:
            self._show_message(self, "%d modules upgraded. There's no need to restart AGTL." % updates)
            self.versionChanged.emit();
        else:
            self._show_message(self, "No updates available. Please try again in a few days.")

    progress = QtCore.Property(float, _progress, notify=progressChanged)
    progressVisible = QtCore.Property(bool, _progress_visible, notify=progressChanged)
    progressMessage = QtCore.Property(str, _progress_message, notify=progressChanged)
    
    coreVersion = QtCore.Property(str, _core_version, notify=versionChanged)
    parserVersion = QtCore.Property(int, _parser_version, notify=versionChanged)
    parserDate = QtCore.Property(str, _parser_date, notify=versionChanged)
    
    
class CalcEditWrapper(QtCore.QObject):
    ADD_CALC_STRING = 0
    ADD_COORDINATE = 1
    
    def __init__(self, cachewrapper, source_id = None, coordinate = None, add = ""):
        QtCore.QObject.__init__(self)
        
        self.__before_coordinate = None
        self.__is_coordinate = False
        self.__before_name = ""
        self.__before_calc = ""
        self.__button_text = ""
        
        info = None
        # Add new Calc String to geocache
        if add == CalcEditWrapper.ADD_CALC_STRING: 
            logger.debug("Adding new calc string")
            self.__ctype = geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING
            self.__button_text = None
            self.__case = 0
        # Add new coordinate to geocache
        elif add == CalcEditWrapper.ADD_COORDINATE:
            logger.debug("Adding new user coordinate")
            self.__before_coordinate = CoordinateWrapper(geo.Coordinate(0, 0, ''))
            self.__is_coordinate = True
            self.__ctype = geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE
            self.__case = 1
        # Overwrite existing Calc String
        # Calc Strings have a string as source, e.g. "Description"
        elif type(source_id) != int:
            logger.debug("Overwriting original coordinate.")
            self.__before_calc = coordinate.orig
            self.__ctype = geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING_OVERRIDE
            self.__button_text = None
            self.__case = 2
        # Edit existing user supplied Calc String or Calc String Overwrite
        # These have integers as source
        else: 
            self.__info = cachewrapper._geocache.get_user_coordinate(source_id)
            self.__before_name = self.__info['name']
            self.__ctype = self.__info['type']
            if self.__info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING:
                logger.debug("Editing user supplied calc string.")
                self.__before_calc = self.__info['value']
                self.__button_text = 'Delete'
                self.__case = 3
            elif self.__info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING_OVERRIDE:
                logger.debug("Editing user supplied overwrite.")
                self.__before_calc = self.__info['value'][1]
                self.__button_text = 'Reset'
                self.__case = 4
            elif self.__info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE:
                c = geo.Coordinate(self.__info['value'][0], self.__info['value'][1], self.__info['name'])
                logger.debug("Editing existing user coordinate: %s" % c)
                self.__before_coordinate = CoordinateWrapper(c)
                self.__button_text = 'Delete'
                self.__is_coordinate = True
                self.__case = 5
            else:
                raise Exception("Illegal type.")
                
        self.__source_id = source_id
        self.__cachewrapper = cachewrapper
        self.__coordinate = coordinate
        
    def _before_coordinate(self):
        return self.__before_coordinate
        
    def _is_coordinate(self):
        return self.__is_coordinate
        
    def _ctype(self):
        return self.__ctype
    
    def _before_calc(self):
        return self.__before_calc
    
    def _before_name(self):
        return self.__before_name
        
    def _button_text(self):
        return self.__button_text if self.__button_text != None else ""
        
    @QtCore.Slot(str, str, result = str)
    def save(self, after_name, after_calc):
        try:
            geo.try_parse_coordinate(after_calc)
            res = "Coordinate saved."
        except Exception:
            res = "Calc string saved."
        if self.__case in [0, 3]:
            value = after_calc
            id = self.__source_id
        elif self.__case == 2:
            value = (self.__coordinate.signature, after_calc)
            id = None
        elif self.__case == 4:
            value = (self.__info['value'][0], after_calc)
            id = self.__source_id
        else:
            raise Exception("Illegal call. Case is %d. For case in (1,5) call saveCoordinate!" % self.__case)
        self.__cachewrapper._geocache.set_user_coordinate(self.__ctype, value, after_name, id)
        logger.debug("Now saving user coordinates?")
        self.__cachewrapper.save_user_coordinates()
        return res
        
    @QtCore.Slot(str, float, float, result = str)
    def saveCoordinate(self, after_name, lat, lon):
        logger.debug("lat = %r, lon = %r" % (lat, lon))
        value = (lat, lon)
        id = self.__source_id
        self.__cachewrapper._geocache.set_user_coordinate(self.__ctype, value, after_name, id)
        logger.debug("Now saving user coordinates?")
        self.__cachewrapper.save_user_coordinates()
        return "Coordinate saved"
        
    @QtCore.Slot()
    def deleteCalc(self):
        self.__cachewrapper._geocache.delete_user_coordinate(self.__source_id)
        self.__cachewrapper.save_user_coordinates()
        
    beforeCalc = QtCore.Property(str, _before_calc)
    beforeName = QtCore.Property(str, _before_name)
    beforeCoordinate = QtCore.Property(QtCore.QObject, _before_coordinate)
    isCoordinate = QtCore.Property(bool, _is_coordinate)
    buttonText = QtCore.Property(str, _button_text)
    ctype = QtCore.Property(int, _ctype)

class CacheCalcVarWrapper(QtCore.QObject):
    def __init__(self, cache, manager, char):
        QtCore.QObject.__init__(self)
        self.__manager = manager
        self.__char = char 
        self.__cache = cache
        v = manager.get_vars()
        if char in v:
            self.__value = v[char] 
        else:
            self.__value = ''
        logger.debug("Char is %s, Value is %s" % (self.__char, repr(self.__value)))
        
    def _value(self):
        return self.__value
        
    def _char(self):
        return self.__char
        
    def _set_value(self, v):
        self.__value = v
        logger.debug("Setting char %r to value %r (I)" % (self.__char, v))
        self.__manager.set_var(self.__char, v)
        logger.debug("Setting char %r to value %r (II)" % (self.__char, v))
        self.__cache.save_vars()
        
    changed = QtCore.Signal()    
        
    value = QtCore.Property(str, _value, _set_value, notify=changed)
    char = QtCore.Property(str, _char, notify=changed)
    
class CacheCalcCoordinateWrapper(QtCore.QObject):
    def __init__(self, cache, coordinate):
        QtCore.QObject.__init__(self)
        self.__coordinate = coordinate
        self.__cache = cache
        self.__result = None
        
    def _has_requires(self):
        return self.__coordinate.has_requires()
        
    def _calculation(self):
        if self.__coordinate.has_requires():
            return self.__coordinate.replaced_result
        return ''
        
    def _text(self):    
        if self.__coordinate.has_requires():
            t = "%s" % self.__coordinate.result if self.__coordinate.result != False else 'nix!'
        else:
            vars = self.__cache.calc.get_vars()
            req = list(self.__coordinate.requires)
            req.sort()
            t = "<i>Needs %s</i>\n" % (', '.join(("<s>%s</s>" if r in vars else "<b>%s</b>") % r for r in req))
        return t
            
    def _warnings(self):
        return (''.join("\n<b>!</b> %s" % w for w in self.__coordinate.warnings)).strip()
        
    def _source(self):
        if type(self.__coordinate.source) == int:
            source = self.__cache.get_user_coordinate(self.__coordinate.source)['name']
        else:
            source = self.__coordinate.source
        return source
        
    def _original_text(self):
        return self.__coordinate.orig
        
    def _result(self):
        if self.__result == None:
            self.__result = CoordinateWrapper(self.__coordinate.result)
        return self.__result
        
    def coordinate(self):
        return self.__coordinate
                
    changed = QtCore.Signal()
        
    hasRequires = QtCore.Property(bool, _has_requires, notify=changed)
    calculation = QtCore.Property(str, _calculation, notify=changed)
    text = QtCore.Property(str, _text, notify=changed)
    warnings = QtCore.Property(str, _warnings, notify=changed)
    source = QtCore.Property(str, _source, notify=changed)
    originalText = QtCore.Property(str, _original_text, notify=changed)
    result = QtCore.Property(QtCore.QObject, _result, notify=changed)
        
class CacheCalcVarList(QtCore.QAbstractListModel):
    COLUMNS = ('vars',)

    def __init__(self, cache, manager):
        QtCore.QAbstractListModel.__init__(self)
        self.setRoleNames(dict(enumerate(CacheCalcVarList.COLUMNS)))
        self.__cache = cache
        self.__manager = manager
        # List of objects of CacheCalcVarWrappers
        self.__var_wrappers = []
        # Mapping from chars to wrapper objects
        self.__var_wrapper_mapping = {}
        self._init_vars()
        logger.debug("Cache calc list initiated with %d vars from %d vars" % (len(self.__var_wrappers), len(self.__manager.get_vars())))
        
    def _init_vars(self):
        self.__new_var_wrappers = []
        self.__new_var_wrapper_mapping = {}
        req = list(self.__manager.requires)
        req.sort()
        for char in req:
            if char in self.__var_wrapper_mapping:
                self.__new_var_wrappers += [self.__var_wrappers[self.__var_wrapper_mapping[char]]]
            else:
                n = len(self.__new_var_wrappers)
                self.__new_var_wrappers += [CacheCalcVarWrapper(self.__cache, self.__manager, char)]
                self.__new_var_wrapper_mapping[char] = n
        self.__var_wrappers = self.__new_var_wrappers
        self.__var_wrapper_mapping = self.__new_var_wrapper_mapping
        
        self.dataChanged.emit(self.createIndex(0,0), self.createIndex(len(self.__var_wrappers),0))

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__var_wrappers)

    def data(self, index, role):
        if index.isValid() and role == CacheCalcVarList.COLUMNS.index('vars'):
            return self.__var_wrappers[index.row()]
        return None

class MapTypeWrapper(QtCore.QObject):
    def __init__(self, name, url):
        QtCore.QObject.__init__(self)
        self._data_name = name
        self._data_url = url

    def _name(self):
        return self._data_name

    def _url(self):
        return self._data_url

    changed = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    url = QtCore.Property(str, _url, notify=changed)
    
    

class MapTypesList(QtCore.QAbstractListModel):
    COLUMNS = ('maptype',)

    def __init__(self, maptypes):
        QtCore.QAbstractListModel.__init__(self)
        self.setRoleNames(dict(enumerate(MapTypesList.COLUMNS)))
        #self._maptypes = [{'name': name, 'url': data['remote_url']} for name, data in maptypes]
        self._maptypes = [MapTypeWrapper(name, data['remote_url']) for name, data in maptypes]
        logger.debug("Creating new maptypes list with %d entries" % len(self._maptypes))


    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._maptypes)

    def data(self, index, role):
        if index.isValid() and role == MapTypesList.COLUMNS.index('maptype'):
            return self._maptypes[index.row()]
        return None

    def get_data_at(self, i):
        return self._maptypes[i] if i < len(self._maptypes) else None
        
    def get_index_of(self, t):
        try:
            return self._maptypes.index(t)
        except ValueError:
            logger.debug("Map type not found: %r" % t)
            return None

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
        return self.data.speed if self.data.speed != None else 0

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
        self.gps_target_distance = None
        self.gps_target_bearing = None
        self.gps_has_fix = False
        self.gps_status = ''
        self._target_valid = False
        self._target = CoordinateWrapper(geo.Coordinate(0, 0))
        #self.astral = Astral()


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
        self._target_valid = (target != None)
        self._target = CoordinateWrapper(target) if target != None else CoordinateWrapper(geo.Coordinate(0, 0))
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

    def _gps_target_bearing(self):
        try:
            return float(self.gps_target_bearing)
        except TypeError:
            return 0

    def _gps_status(self):
        return self.gps_status
            

    data = QtCore.Property(QtCore.QObject, _gps_data, notify=changed)
    lastGoodFix = QtCore.Property(QtCore.QObject, _gps_last_good_fix, notify=changed)
    hasFix = QtCore.Property(bool, _gps_has_fix, notify=changed)
    targetValid = QtCore.Property(bool, _target_valid, notify=changed_target)
    target = QtCore.Property(QtCore.QObject, _target, notify=changed_target)
    targetDistanceValid = QtCore.Property(bool, _gps_target_distance_valid, notify=changed_distance_bearing)
    targetDistance = QtCore.Property(float, _gps_target_distance, notify=changed_distance_bearing)
    targetBearing = QtCore.Property(float, _gps_target_bearing, notify=changed_distance_bearing)
    status = QtCore.Property(str, _gps_status, notify=changed)





class SettingsWrapper(QtCore.QObject):
    def __init__(self, core):
        QtCore.QObject.__init__(self)
        self.core = core
        self.core.connect('settings-changed', self._settings_changed)
        self.core.connect('save-settings', self._save_settings)
        self.settings = {}
        self._map_types_list = MapTypesList(self.core.settings['map_providers'])

    settingsChanged = QtCore.Signal()

    def _setting(self, s, t):
        x = t(self.settings[s]) if s in self.settings else 0
        return x

    def _set_setting(self, s, t, notify = True):
        logger.debug("Setting %s is now: %r" % (s, t))
        self.settings[s] = t
        if notify:
            self.settingsChanged.emit()
        else:
            logger.debug("Not notifying about %s settings change" % s)

    # Handle gobject signal from Core
    def _save_settings(self, caller):
        caller.save_settings(self.settings, self)

    # Handle gobject signal from Core
    def _settings_changed(self, caller, settings, source):
        if source == self:
            return
        logger.debug("Settings object got settings from %s, len() = %d, source = %s" % (caller, len(settings), source))
        self.settings.update(settings)

        if 'map_providers' in settings:
            self._map_types_list = MapTypesList(settings['map_providers'])
        if 'map_type' in settings:
            self._current_map_type = self._map_types_list.get_data_at(settings['map_type'])
            
        #if 'last_target_lat' in settings:
        #    self.setTarget(settings['last_target_lat'], settings['last_target_lon'])

        self.settingsChanged.emit()



    def _distance_unit(self):
        return "m"

    def _coordinate_format(self):
        return "DM"

    def _get_current_map_type(self):
        if 'map_type' in self.settings:
            return self._map_types_list.get_data_at(self.settings['map_type'])
        else:
            return self._map_types_list.get_data_at(0)
        
    def _set_current_map_type(self, map_type):
        self.settings['map_type'] = self._map_types_list.get_index_of(map_type)
        self.settingsChanged.emit()

    def _map_types(self):
        return self._map_types_list

    def createSetting(name, type, signal, inputNotify = True):
        return QtCore.Property(type, lambda x: x._setting(name, type), lambda x, m: x._set_setting(name, m, inputNotify), notify=signal)

    mapPositionLat = createSetting('map_position_lat', float, settingsChanged, False)
    mapPositionLon = createSetting('map_position_lon', float, settingsChanged, False)
    mapZoom = createSetting('map_zoom', int, settingsChanged, False)
    optionsUsername = createSetting('options_username', str, settingsChanged)
    optionsPassword = createSetting('options_password', str, settingsChanged)
    lastSelectedGeocache = createSetting('last_selected_geocache', str, settingsChanged, False)
    optionsMapRotation = createSetting('options_maprotation', bool, settingsChanged)
    optionsHideFound = createSetting('options_hide_found', bool, settingsChanged)
    optionsShowPositionError = createSetting('options_show_position_error', bool, settingsChanged)
    optionsNightViewMode = createSetting('options_night_view_mode', int, settingsChanged)
    downloadNumLogs = createSetting('download_num_logs', int, settingsChanged)
    optionsAutoUpdate = createSetting('options_auto_update', bool, settingsChanged)
    debugLogToHTTP = createSetting('debug_log_to_http', bool, settingsChanged)

    currentMapType = QtCore.Property(QtCore.QObject, _get_current_map_type, _set_current_map_type, notify=settingsChanged)
    mapTypes = QtCore.Property(QtCore.QObject, _map_types, notify=settingsChanged)
    distanceUnit = QtCore.Property(str, _distance_unit, notify=settingsChanged)
    coordinateFormat = QtCore.Property(str, _coordinate_format, notify=settingsChanged)


class CoordinateWrapper(QtCore.QObject):
    def __init__(self, coordinate, geocache = None):
        QtCore.QObject.__init__(self)
        self._coordinate = coordinate
        self._geocache = geocache
        self._is_valid = coordinate != None and coordinate != False and (self._coordinate.lat != -1 or self._coordinate.lon != -1) and self._coordinate.lat != None
        if self._is_valid:
            try:
                float(self._coordinate.lat)
                float(self._coordinate.lon)
            except ValueError:
                self._is_valid = false

    def _name(self):
        return self._coordinate.name

    def _lat(self):
        return self._coordinate.lat if self._is_valid else -1

    def _lon(self):
        return self._coordinate.lon if self._is_valid else -1

    def _display_text(self):
        return d(self._coordinate.display_text)

    def _comment(self):
        return d(self._coordinate.comment)

    def _user_coordinate_id(self):
        return self._coordinate.user_coordinate_id if self._coordinate.user_coordinate_id != None else -1
        #self._user_coordinate = CacheCalcCoordinateWrapper(self._geocache, self._geocache.get_user_coordinate(self._coordinate.user_coordinate_id))
        #return self._user_coordinate

    def _is_valid_coordinate(self):
        return self._is_valid

    changed = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    display_text = QtCore.Property(str, _display_text, notify=changed)
    comment = QtCore.Property(str, _comment, notify=changed)
    userCoordinateID = QtCore.Property(int, _user_coordinate_id, notify=changed)
    valid = QtCore.Property(bool, _is_valid_coordinate, notify=changed)

class CoordinateListModel(QtCore.QAbstractListModel):
    COLUMNS = ('coordinate',)

    def __init__(self, core, coordinates = []):
        QtCore.QAbstractListModel.__init__(self)
        self._coordinates = coordinates
        self.setRoleNames(dict(enumerate(CoordinateListModel.COLUMNS)))

    def update(self, new):
        self._coordinates = new
        QtCore.QAbstractListModel.dataChanged(self)
        logger.warning("data changed!")

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._coordinates)

    def data(self, index, role):
        if index.isValid() and role == CoordinateListModel.COLUMNS.index('coordinate'):
            return self._coordinates[index.row()]
        return None
        
    changed = QtCore.Signal()
    length = QtCore.Property(int, rowCount, notify=changed)
        

class ImageListModel(QtCore.QAbstractListModel):
    COLUMNS = ('image',)

    def __init__(self, images = []):
        QtCore.QAbstractListModel.__init__(self)
        self._images = images
        self.setRoleNames(dict(enumerate(ImageListModel.COLUMNS)))

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._images)

    def data(self, index, role):
        if index.isValid() and role == ImageListModel.COLUMNS.index('image'):
            logger.debug("Image retrieved: %r and has url '%s'"  % (self._images[index.row()], self._images[index.row()]._url()))
            return self._images[index.row()]
        return None
        
    changed = QtCore.Signal()
    
    length = QtCore.Property(int, rowCount, notify=changed)

class ImageWrapper(QtCore.QObject):
    
    def __init__(self, imageUrl, imageName):
        QtCore.QObject.__init__(self)
        self.__url = imageUrl
        self.__name = imageName
        
    def _url(self):
        return self.__url
        
    def _name(self):
        return self.__name
        
    changed = QtCore.Signal()
        
    url = QtCore.Property(str, _url, notify=changed)
    name = QtCore.Property(str, _name, notify=changed)


class GeocacheWrapper(QtCore.QObject):
    def __init__(self, geocache, core):
        QtCore.QObject.__init__(self)
        self._geocache = geocache
        self.core = core
        self._coordinate_list = None
        self._logs_list = None
        self._image_list = None
        self._var_list = None
        self._calc_coordinate_list = None
        
    GEOCACHE_CACHE = {}
        
    @staticmethod
    def get(geocache, core):
        if geocache.name not in GeocacheWrapper.GEOCACHE_CACHE:
            logger.debug("Not in cache: %s" % geocache.name)
            GeocacheWrapper.GEOCACHE_CACHE[geocache.name] = GeocacheWrapper(geocache, core)
        else:
            GeocacheWrapper.GEOCACHE_CACHE[geocache.name].update(geocache)
        return GeocacheWrapper.GEOCACHE_CACHE[geocache.name]

    def update(self, geocache):
        self._geocache = geocache
        self._coordinate_list = None
        self._logs_list = None
        self._image_list = None
        self._var_list = None
        self._calc_coordinate_list = None
        self.changed.emit()
        self.coordsChanged.emit()
        
    def _name(self):
        return self._geocache.name

    def _title(self):
        return self._geocache.title

    def _lat(self):
        return self._geocache.lat

    def _lon(self):
        return self._geocache.lon

    def _shortdesc(self):
        return self._geocache.shortdesc
        
    def _stripped_shortdesc(self):
        from utils import HTMLManipulations
        return HTMLManipulations.strip_html_visual(self._geocache.shortdesc)

    def _desc(self):
        if self._geocache.desc != '' and self._geocache.shortdesc != '':
            showdesc = "<b>%s</b><br />%s" % (self._geocache.shortdesc, self._geocache.desc)
        elif self._geocache.desc == '' and self._geocache.shortdesc == '':
            showdesc = "<i>No description available</i>"
        elif self._geocache.desc == '':
            showdesc = self._geocache.shortdesc
        else:
            showdesc = self._geocache.desc
        showdesc = re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: "<img src='%s' />" % self.get_path_to_image(a.group(1)), showdesc)
        return showdesc

    def _logs(self):
        if self._logs_list == None:
            logs = self._geocache.get_logs()
            self._logs_list = LogsListModel(self.core, logs)
            logger.debug("Creating logs list... logs: %d" % self._logs_list.rowCount())
        return self._logs_list

    def _logs_count(self):
        return self._logs().rowCount()

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

    def _hints(self):
        return self._geocache.hints
        
    def _url(self):
        return "http://coord.info/%s" % self._geocache.name

    def _coordinates(self):
        logger.debug("Preparing coordinate list...")
        if self._coordinate_list == None:
            if self._geocache.calc == None:
                self._geocache.start_calc()
            z = [CoordinateWrapper(x, self._geocache) for x in self._geocache.get_collected_coordinates(format = geo.Coordinate.FORMAT_DM, skip_calc = True).values()]
            self._coordinate_list = CoordinateListModel(self.core, z)
        return self._coordinate_list

    def _coordinates_count(self):
        return self._coordinates().rowCount()

    def _images(self):
        if self._image_list == None:
            l = [ImageWrapper(self.get_path_to_image(x), y) for (x, y) in self._geocache.get_images().items()]
            self._image_list = ImageListModel(l)
        return self._image_list

    def _status(self):
        return self._geocache.status

    def _has_details(self):
        return self._geocache.was_downloaded()
        
    def _logas(self):
        try:
            return int(self._geocache.logas)
        except ValueError:
            return 0
        
    def _fieldnotes(self):
        return self._geocache.fieldnotes
        
    def _marked(self):
        return self._geocache.marked
        
    def _set_marked(self, marked):
        self._geocache.marked = marked
        self.core.save_cache_attribute(self._geocache, 'marked')
        self.changed.emit()
        
    def _var_list(self):
        if self._var_list == None:
            if self._geocache.calc == None:
                self._geocache.start_calc()
            self._var_list = CacheCalcVarList(self, self._geocache.calc)
        return self._var_list
        
    def save_vars(self):
        logger.debug("Saving cache vars.")
        self.core.save_cache_attribute(self._geocache, 'vars')
        self._calc_coordinate_list = None
        self.coordsChanged.emit()
        
    def save_user_coordinates(self):
        logger.debug("Saving user coordinates.")
        self.core.save_cache_attribute(self._geocache, 'user_coordinates')
        self._calc_coordinate_list = None
        self._coordinate_list = None
        self._geocache.stop_calc()
        self._var_list = None
        self.coordsChanged.emit()
        
    def _calc_coordinates(self):
        if self._calc_coordinate_list == None:
            if self._geocache.calc == None:
                self._geocache.start_calc()
            l = [CacheCalcCoordinateWrapper(self._geocache, x) for x in self._geocache.calc.coords]
            self._calc_coordinate_list = CoordinateListModel(self.core, l)
        return self._calc_coordinate_list
            
    
    @QtCore.Slot(str, str)
    def setFieldnote(self, logas, text):
        from time import gmtime
        from time import strftime
        logger.debug("Setting fieldnote, logas=%r, text=%r" % (logas, text))
        self._geocache.logas = logas
        self._geocache.fieldnotes = text
        self._geocache.logdate = strftime('%Y-%m-%d', gmtime())
        self.core.save_fieldnote(self._geocache)
        self.changed.emit()

    changed = QtCore.Signal()
    coordsChanged = QtCore.Signal()

    name = QtCore.Property(str, _name, notify=changed)
    title = QtCore.Property(unicode, _title, notify=changed)
    lat = QtCore.Property(float, _lat, notify=changed)
    lon = QtCore.Property(float, _lon, notify=changed)
    desc = QtCore.Property(str, _desc, notify=changed)
    shortdesc = QtCore.Property(str, _shortdesc, notify=changed)
    strippedShortdesc = QtCore.Property(str, _stripped_shortdesc, notify=changed)
    type = QtCore.Property(str, _type, notify=changed)
    url = QtCore.Property(str, _url, notify=changed)
    size = QtCore.Property(int, _size, notify=changed)
    difficulty = QtCore.Property(float, _difficulty, notify=changed)
    terrain = QtCore.Property(float, _terrain, notify=changed)
    owner = QtCore.Property(str, _owner, notify=changed)
    found = QtCore.Property(bool, _found, notify=changed)
    images = QtCore.Property(QtCore.QObject, _images, notify=changed)
    status = QtCore.Property(int, _status, notify=changed)
    marked = QtCore.Property(bool, _marked, _set_marked, notify=changed)
    logs = QtCore.Property(QtCore.QObject, _logs, notify=changed)
    logsCount = QtCore.Property(int, _logs_count, notify=changed)
    coordinates = QtCore.Property(QtCore.QObject, _coordinates, notify=coordsChanged)
    coordinatesCount = QtCore.Property(int, _coordinates_count, notify=coordsChanged)
    hasDetails = QtCore.Property(bool, _has_details, notify=changed)
    hints = QtCore.Property(str, _hints, notify=changed)
    logas = QtCore.Property(int, _logas, notify=changed)
    fieldnotes = QtCore.Property(str, _fieldnotes, notify=changed)
    varList = QtCore.Property(QtCore.QObject, _var_list, notify=coordsChanged)
    calcCoordinates = QtCore.Property(QtCore.QObject, _calc_coordinates, notify=coordsChanged)

class GeocacheListModel(QtCore.QAbstractListModel):
    COLUMNS = ('geocache',)
    
    SORT_BY_PROXIMITY = 0
    SORT_BY_NAME = 1
    SORT_BY_TYPE = 2
    SORT_BY_FOUND = 3
    
    def __init__(self, core, points = []):
        QtCore.QAbstractListModel.__init__(self)
        self.setRoleNames(dict(enumerate(GeocacheListModel.COLUMNS)))
        self.core = core
        #self._geocaches = [GeocacheWrapper(x, self.core) for x in points]
        self._geocaches = [GeocacheWrapper.get(x, self.core) for x in points]
        
    def update(self, points):
        oldlen = len(self._geocaches)
        self._geocaches = [GeocacheWrapper(x, self.core) for x in points]
        #QtCore.QAbstractListModel.dataChanged(self)
        newlen = len(self._geocaches)
        
        self.dataChanged.emit(self.createIndex(0,0), self.createIndex(newlen,0))
        if oldlen < newlen:
            self.rowsInserted.emit(QtCore.QModelIndex(), oldlen -1, newlen - 1)
        elif oldlen > newlen:
            self.rowsRemoved.emit(QtCore.QModelIndex(), newlen -1, oldlen - 1)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._geocaches)

    def data(self, index, role):
        #if index.isValid() and role == GeocacheListModel.COLUMNS.index('geocache'):
        return self._geocaches[index.row()]
        #return None
        
    @QtCore.Slot(int, QtCore.QObject)
    def sort(self, by, gpsWrapper):
        if by == self.SORT_BY_PROXIMITY:
            def key(f):
                if gpsWrapper.gps_last_good_fix._valid():
                    return f._geocache.distance_to(geo.Coordinate(gpsWrapper.gps_last_good_fix._lat(), gpsWrapper.gps_last_good_fix._lon()))
                return None
        elif by == self.SORT_BY_NAME:
            key = lambda f: f._title()
        elif by == self.SORT_BY_TYPE:
            key = lambda f: f._type() + ("b" if f._found() else "a")
        elif by == self.SORT_BY_FOUND:
            key = lambda f: ("b" if f._found() else "a") + f._type()
        self._geocaches.sort(key = key)
        self.dataChanged.emit(self.createIndex(0,0), self.createIndex(len(self._geocaches),0))
        
    @QtCore.Slot(bool)
    def markAll(self, mark):
        for i in self._geocaches:
            i._set_marked(mark)
            
    @QtCore.Slot()
    def downloadDetails(self):
        self.core.update_coordinates([x._geocache for x in self._geocaches]);

class LogsListModel(QtCore.QAbstractListModel):
    COLUMNS = ('log',)

    def __init__(self, core, logs = []):
        QtCore.QAbstractListModel.__init__(self)
        self._logs = [LogWrapper(x) for x in logs]
        self.setRoleNames(dict(enumerate(LogsListModel.COLUMNS)))


    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._logs)

    def data(self, index, role):
        if index.isValid() and role == LogsListModel.COLUMNS.index('log'):
            return self._logs[index.row()]
        return None

class LogWrapper(QtCore.QObject):
    ICONS = {
        geocaching.GeocacheCoordinate.LOG_TYPE_FOUND: 'emoticon_grin',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTFOUND: 'cross',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTE: 'comment',
        geocaching.GeocacheCoordinate.LOG_TYPE_MAINTENANCE: 'wrench',
        geocaching.GeocacheCoordinate.LOG_TYPE_PUBLISHED: 'accept',
        geocaching.GeocacheCoordinate.LOG_TYPE_DISABLED: 'delete',
        geocaching.GeocacheCoordinate.LOG_TYPE_NEEDS_MAINTENANCE: 'error',
        geocaching.GeocacheCoordinate.LOG_TYPE_WILLATTEND: 'calendar_edit',
        geocaching.GeocacheCoordinate.LOG_TYPE_ATTENDED: 'group',
        geocaching.GeocacheCoordinate.LOG_TYPE_UPDATE: 'asterisk_yellow',
    }
    
    changed = QtCore.Signal()
    def __init__(self, log):
        QtCore.QObject.__init__(self)
        self._log = log

    def _type(self):
        logger.debug('type')
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

    def _date(self):
        if 'year' in self._log:
            return "%s-%s-%s" % (self._log['year'], self._log['month'], self._log['day'])
        else:
            return self._log['date']

    def _text(self):
        return self._log['text']

    def _icon_basename(self):
        r = self.ICONS[self._log['type']] if self._log['type'] in self.ICONS else ""
        return r

    type = QtCore.Property(str, _type, notify=changed)
    finder = QtCore.Property(str, _finder, notify=changed)
    date = QtCore.Property(str, _date, notify=changed)
    text = QtCore.Property(str, _text, notify=changed)
    iconBasename = QtCore.Property(str, _icon_basename, notify=changed)
    
    

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
