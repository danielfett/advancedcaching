#!/usr/bin/python
# -*- coding: utf-8 -*-

#        Copyright (C) 2009 Daniel Fett
#         This program is free software: you can redistribute it and/or modify
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
#        Author: Daniel Fett advancedcaching@fragcom.de
#

try:
    from simplejson import dumps, loads
except (ImportError, AttributeError):
    from json import loads, dumps

import geo

class GeocacheCoordinate(geo.Coordinate):
    LOG_NO_LOG = 0
    LOG_AS_FOUND = 1
    LOG_AS_NOTFOUND = 2
    LOG_AS_NOTE = 3

    TYPE_REGULAR = 'regular'
    TYPE_MULTI = 'multi'
    TYPE_VIRTUAL = 'virtual'
    TYPE_EVENT = 'event'
    TYPE_MYSTERY = 'mystery'
    TYPE_WEBCAM = 'webcam'
    TYPE_UNKNOWN = 'unknown'
    TYPE_EARTH = 'earth'
    TYPES = [
        TYPE_REGULAR,
        TYPE_MULTI,
        TYPE_VIRTUAL,
        TYPE_EVENT,
        TYPE_MYSTERY,
        TYPE_WEBCAM,
        TYPE_UNKNOWN,
        TYPE_EARTH
    ]

    STATUS_NORMAL = 0
    STATUS_DISABLED = 1
    STATUS_ARCHIVED = 2
    STATUS_TEXT = ['normal', 'not available!']

    LOG_TYPE_FOUND = 'smile'
    LOG_TYPE_NOTFOUND = 'sad'
    LOG_TYPE_NOTE = 'note'
    LOG_TYPE_MAINTENANCE = 'maint'
    LOG_TYPE_PUBLISHED = 'greenlight'
    LOG_TYPE_DISABLED = 'disabled'
    LOG_TYPE_NEEDS_MAINTENANCE = 'needsmaint'
    LOG_TYPE_WILLATTEND = 'rsvp'
    LOG_TYPE_ATTENDED = 'attended'
    LOG_TYPE_UPDATE = 'coord_update'

    SIZES = ['other', 'micro', 'small', 'regular', 'big', 'other']

    TYPE_MAPPING = {
        TYPE_MULTI: 'Multi-cache',
        TYPE_REGULAR: 'Traditional Cache',
        TYPE_EARTH: 'Earthcache',
        TYPE_UNKNOWN: 'Unknown Cache',
        TYPE_EVENT: 'Event Cache',
        TYPE_WEBCAM: 'Webcam Cache',
        TYPE_VIRTUAL: 'Virtual Cache'
    }

    ATTRS = ('lat', 'lon', 'title', 'name', 'shortdesc', 'desc', 'hints', 'type', \
             'size', 'difficulty', 'terrain', 'owner', 'found', 'waypoints', \
             'images', 'notes', 'fieldnotes', 'logas', 'logdate', 'marked', \
             'logs', 'status', 'vars', 'alter_lat', 'alter_lon')


    SQLROW = {
        'lat': 'REAL',
        'lon': 'REAL',
        'name': 'TEXT PRIMARY KEY',
        'title': 'TEXT',
        'shortdesc': 'TEXT',
        'desc': 'TEXT',
        'hints': 'TEXT',
        'type': 'TEXT',
        'size': 'INTEGER',
        'difficulty': 'INTEGER',
        'terrain': 'INTEGER',
        'owner': 'TEXT',
        'found': 'INTEGER',
        'waypoints': 'text',
        'images': 'text',
        'notes': 'TEXT',
        'fieldnotes': 'TEXT',
        'logas': 'INTEGER',
        'logdate': 'TEXT',
        'marked': 'INTEGER',
        'logs': 'TEXT',
        'status': 'INTEGER',
        'vars': 'TEXT',
        'alter_lat': 'REAL',
        'alter_lon': 'REAL'
        }
    def __init__(self, lat, lon=None, name='', data=None):
        geo.Coordinate.__init__(self, lat, lon, name)
        if data != None:
            self.unserialize(data)
            return
        # NAME = GC-ID
        self.title = ''
        self.shortdesc = ''
        self.desc = ''
        self.hints = ''
        self.type = '' # regular, multi, virtual, webcam,...
        self.size = -1
        self.difficulty = -1
        self.terrain = -1
        self.owner = ''
        self.found = False
        self.waypoints = ''
        self.images = ''
        self.notes = ''
        self.fieldnotes = ''
        self.logas = self.LOG_NO_LOG
        self.logdate = ''
        self.marked = False
        self.logs = ''
        self.status = self.STATUS_NORMAL
        self.vars = ''
        self.alter_lat = 0
        self.alter_lon = 0

    def clone(self):
        n = GeocacheCoordinate(self.lat, self.lon)
        for k in self.ATTRS:
            setattr(n, k, getattr(self, k))
        return n
        
    def get_difficulty(self):
        return "%.1f" % (self.difficulty / 10.0) if self.difficulty != -1 else '?'
        
    def get_terrain(self):
        return "%.1f" % (self.terrain / 10.0) if self.difficulty != -1 else '?'

    def get_status(self):
        return self.STATUS_TEXT[self.status]

    def serialize(self):
        ret = {}
        for key in self.ATTRS:
            ret[key] = getattr(self, key)

        ret['found'] = 1 if self.found else 0
        ret['marked'] = 1 if self.marked else 0
        return ret
                
    def unserialize(self, data):
        ret = {}
        for key in self.ATTRS:
            ret[key] = data[key]

        if ret['notes'] == None:
            self.notes = ''
        if ret['fieldnotes'] == None:
            self.fieldnotes = ''
        if ret['logs'] == None:
            self.logs = ''
        if ret['vars'] == None:
            self.vars = ''
        ret['found'] = (ret['found'] == 1)
        self.__dict__ = ret
        
    def get_waypoints(self):
        if self.waypoints == None or self.waypoints == '':
            return []
        try:
            return self.saved_waypoints
        except (AttributeError):
            self.saved_waypoints = loads(self.waypoints)
            return self.saved_waypoints

    def get_vars(self):
        if self.vars == None or self.vars == '':
            return {}
        return loads(self.vars)

    def set_vars(self, vars):
        self.vars = dumps(vars)

    def get_logs(self):
        if self.logs == None or self.logs == '':
            return []
        return loads(self.logs)

    def get_images(self):
        if self.images == None or self.images == '':
            return []
        try:
            return self.saved_images
        except (AttributeError):
            self.saved_images = loads(self.images)
            return self.saved_images

    def set_waypoints(self, wps):
        self.waypoints = dumps(wps)
        try:
            del self.saved_waypoints
        except:
            pass

    def set_logs(self, ls):
        self.logs = dumps(ls)

    def set_images(self, imgs):
        self.images = dumps(imgs)
        try:
            del self.saved_images
        except:
            pass
                
    def was_downloaded(self):
        return (self.shortdesc != '' or self.desc != '')
        
    def get_bounds(self):
        minlat = maxlat = self.lat
        minlon = maxlon = self.lon
        for wpt in self.get_waypoints():
            if wpt['lat'] != -1 and wpt['lon'] != -1:
                minlat = min(minlat, wpt['lat'])
                maxlat = max(maxlat, wpt['lat'])
                minlon = min(minlon, wpt['lon'])
                maxlon = max(maxlon, wpt['lon'])

        return {'minlat': "%.5f" % minlat, 'maxlat': "%.5f" % maxlat, 'minlon': "%.5f" % minlon, 'maxlon': "%.5f" % maxlon}
    
    def get_size_string(self):
        if self.size == -1:
            return '?'
        else:
            return self.SIZES[self.size]


    def get_gs_type(self):
        if self.TYPE_MAPPING.has_key(self.type):
            return self.TYPE_MAPPING[self.type]
        else:
            return self.TYPE_MAPPING[self.TYPE_UNKNOWN]

    def set_alternative_position(self, coord):
        self.alter_lat = coord.lat
        self.alter_lon = coord.lon


    
        
"""
class GpxReader():
        def __init__(self, pointprovider):
                self.pointprovider = pointprovider
                
        def read_file(self, filename):
                lat = lon = -1
                uid = name = comment = description = url = cachetype = ''
                found = intag = False
                locline = re.compile('<wpt lat="(\d+\.\d+)" lon="(\d+\.\d+)"')
                if os.path.exists(filename):
                        for line in open(filename, 'r'):
                                line = line.strip()
                                if line.startswith('<wpt'):
                                        match = locline.match(line)
                                        lat = float(match.group(1))
                                        lon = float(match.group(2))
                                        intag = True
                                elif line.startswith('<name>') and intag and lat != -1 and lon != -1:
                                        name = line.rpartition('</name>')[0][6:]
                                        currentcoord = GeocacheCoordinate(lat, lon, name)
                                elif line.startswith('<cmt>') and intag:
                                        currentcoord.title = line.rpartition('</cmt>')[0][5:]
                                elif line.startswith('<desc>') and intag:
                                        currentcoord.desc = line.rpartition('</desc>')[0][6:]
                                elif line.startswith('<sym>') and intag:
                                        typestring = line.rpartition('</sym>')[0][5:].split('-')
                                        currentcoord.type = typestring[-1]
                                        if typestring[1] == 'ifound':
                                                currentcoord.found = True
                                                #found = False                                                                                                
                                elif line.startswith('</wpt>') and intag:
                                        self.pointprovider.add_point(currentcoord)
                                        currentcoord = None
                                        lat = lon = -1
                                        uid = name = comment = description = url = cachetype = ''
                                        found = intag = False
"""
