#!/usr/bin/python
# -*- coding: utf-8 -*-

#    Copyright (C) 2009 Daniel Fett
#     This program is free software: you can redistribute it and/or modify
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
#    Author: Daniel Fett advancedcaching@fragcom.de
#

import math
import re

try:
    import location
except (ImportError):
    pass


def try_parse_coordinate(text):
    
    text = text.strip()
    # got some problems with the degree symbol in regexes.
    text = text.replace('°', ' ')
    #                         1        2          3           4            5         6            7           8
    match = re.match(ur'''(?i)^([NS+-]?)\s?(\d\d?\d?)[ °]{0,2}(\d\d?\d?)[., ](\d+)['\s,]+([EOW+-]?)\s?(\d{1,3})[ °]{0,2}(\d\d?\d?)[., ](\d+)?[\s']*$''', text)
    if match != None:
        c = Coordinate(0, 0)
        if match.group(1) in 'sS-':
            sign_lat = -1
        else:   
            sign_lat = 1
        if match.group(5) in 'wW-':
            sign_lon = -1
        else:   
            sign_lon = 1
        
        c.from_dm(sign_lat * int(match.group(2)), 
            sign_lat * float("%s.%s" % (match.group(3), match.group(4))),
            sign_lon * int(match.group(6)),
            sign_lon * float("%s.%s" % (match.group(7), match.group(8)))
            )
        return c
    
    #                         1        2           3         4         5             6
    match = re.match(ur'''(?i)^([NS+-]?)\s?(\d\d?)[., ](\d+)[°']?[\s,]+([EOW+-]?)\s?(\d{1,3})[., ](\d+)['°]?\s*$''', text)
    
    if match != None:
        c = Coordinate(0, 0)
        if match.group(1) in 'sS-':
            sign_lat = -1
        else:   
            sign_lat = 1
        if match.group(4) in 'wW-':
            sign_lon = -1
        else:   
            sign_lon = 1
                
        # not using math magic here: this is more error-free :-)
        c.lat = sign_lat * float("%s.%s" % (match.group(2), match.group(3)))
        c.lon = sign_lon * float("%s.%s" % (match.group(5), match.group(6)))
        return c
    
    raise Exception("Could not parse this input as a coordinate: '%s'\nExample Input: N49 44.111 E6 12.123" % text)

def search_coordinates(text):

    text = text.strip()
    # got some problems with the degree symbol in regexes.
    text = text.replace('°', ' ')
    #

    output = []

    matches = re.finditer(ur'''(?i)([NS+-]?)\s?(\d\d?\d?)[ °]{1,2}(\d\d?\d?)[., ](\d+)['\s,]+([EOW+-]?)\s?(\d{1,3})[ °]{1,2}(\d\d?\d?)[., ](\d+)?[\s']*''', text)
    for match in matches:
        c = Coordinate(0, 0)
        if match.group(1) in 'sS-':
            sign_lat = -1
        else:
            sign_lat = 1
        if match.group(5) in 'wW-':
            sign_lon = -1
        else:
            sign_lon = 1

        c.from_dm(sign_lat * int(match.group(2)),
            sign_lat * float("%s.%s" % (match.group(3), match.group(4))),
            sign_lon * int(match.group(6)),
            sign_lon * float("%s.%s" % (match.group(7), match.group(8)))
            )
        output.append(c)

    #                         1        2           3         4         5             6
    matches = re.finditer(ur'''(?i)([NS+-]?)\s?(\d\d?)[.,](\d+)[°']?[\s,]+([EOW+-]?)\s?(\d{1,3})[.,](\d+)['°]?\s*''', text)
    for match in matches:
        c = Coordinate(0, 0)
        if match.group(1) in 'sS-':
            sign_lat = -1
        else:
            sign_lat = 1
        if match.group(4) in 'wW-':
            sign_lon = -1
        else:
            sign_lon = 1

        # not using math magic here: this is more error-free :-)
        c.lat = sign_lat * float("%s.%s" % (match.group(2), match.group(3)))
        c.lon = sign_lon * float("%s.%s" % (match.group(5), match.group(6)))

        output.append(c)
    return output

class Coordinate(object):
    SQLROW = {'lat': 'REAL', 'lon': 'REAL', 'name': 'TEXT'}
    
    RADIUS_EARTH = 6371000.0
    
    FORMAT_D = 0
    FORMAT_DM = 1
    re_to_dm_array = re.compile('^(\d?)(\d)(\d) (\d)(\d)\.(\d)(\d)(\d)$')
    re_to_d_array = re.compile('^(\d?)(\d)(\d).(\d)(\d)(\d)(\d)(\d)$')
    
    def __init__(self, lat, lon, name="No Name"):
        self.lat = lat
        self.lon = lon
        self.name = name
        try:
            location
            self.distance_to = self.distance_to_liblocation
        except Exception:
            self.distance_to = self.distance_to_manual
            
    def from_d(self, lat, lon):
        self.lat = lat
        self.lon = lon
            
    def from_dm(self, latdd, latmm, londd, lonmm):
        self.lat = latdd + (latmm / 60)
        self.lon = londd + (lonmm / 60)
            
    def from_dm_array(self, sign_lat, lat, sign_lon, lon):
        lat += [0, 0, 0, 0, 0, 0]
        lon += [0, 0, 0, 0, 0, 0, 0]
        self.from_dm(sign_lat * (lat[0] * 10 + lat[1]),
                   sign_lat * float(str(lat[2]) + str(lat[3]) + "." + str(lat[4]) + str(lat[5]) + str(lat[6])),
                   sign_lon * (lon[0] * 100 + lon[1] * 10 + lon[2]),
                   sign_lon * float(str(lon[3]) + str(lon[4]) + "." + str(lon[5]) + str(lon[6]) + str(lon[7])))

    def from_d_array(self, sign_lat, lat, sign_lon, lon):
        self.lat = int(sign_lat) * float("%d%d.%d%d%d%d%d" % tuple(lat))
        self.lon = int(sign_lon) * float("%d%d%d.%d%d%d%d%d" % tuple(lon))
                
    def to_dm_array(self):
        [[lat_d, lat_m], [lon_d, lon_m]] = self.to_dm()
            
        d_lat = self.re_to_dm_array.search("%02d %06.3f" % (abs(lat_d), abs(lat_m)))
        d_lon = self.re_to_dm_array.search("%03d %06.3f" % (abs(lon_d), abs(lon_m)))
        return [
            [d_lat.group(i) for i in xrange (2, 9)],
            [d_lon.group(i) for i in xrange (1, 9)]
            ]

    def to_d_array(self):

        d_lat = self.re_to_d_array.search("%08.5f" % abs(self.lat))
        d_lon = self.re_to_d_array.search("%09.5f" % abs(self.lon))
        return [
            [d_lat.group(i) for i in xrange (2, 7)],
            [d_lon.group(i) for i in xrange (1, 7)]
            ]
            
    def to_dm(self):
        lat = abs(self.lat)
        lon = abs(self.lon)
        return [[int(math.floor(lat)), (lat - math.floor(lat)) * 60],
            [int(math.floor(lon)), (lon - math.floor(lon)) * 60]]
    
    def bearing_to(self, target):
        lat1 = math.radians(self.lat)
        lat2 = math.radians(target.lat)
        #lon1 = math.radians(self.lon)
        #lon2 = math.radians(target.lon)
        
        dlon = math.radians(target.lon - self.lon);
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(y, x))
        return (360 + bearing) % 360
        
    def transform(self, bearing, distance):
        # expect distance in meters and bearing in degrees
        rlat1 = math.radians(self.lat)
        rlon1 = math.radians(self.lon)
        rbearing = math.radians(bearing)
        rdistance = distance / self.RADIUS_EARTH # normalize linear distance to radian angle

        rlat = math.asin( math.sin(rlat1) * math.cos(rdistance) + math.cos(rlat1) * math.sin(rdistance) * math.cos(rbearing) )

        if math.cos(rlat) == 0 or abs(math.cos(rlat)) < 0.00001: # Endpoint a pole
            rlon=rlon1
        else:
            rlon = ( (rlon1 - math.asin( math.sin(rbearing)* math.sin(rdistance) / math.cos(rlat) ) + math.pi ) % (2*math.pi) ) - math.pi

        lat = math.degrees(rlat)
        lon = math.degrees(rlon)
        return Coordinate(lat, lon, self.name)
    

    def get_lat(self, format):
        l = abs(self.lat)
        if self.lat > 0:
            c = 'N'
        else:
            c = 'S'
        if format == self.FORMAT_D:
            return "%s %.5f°" % (c, l)
        elif format == self.FORMAT_DM:
            return "%s %d° %06.3f'" % (c, math.floor(l), (l - math.floor(l)) * 60)

    def get_lon(self, format):
        l = abs(self.lon)
        if self.lon > 0:
            c = 'E'
        else:
            c = 'W'
        if format == self.FORMAT_D:
            return "%s %.5f°" % (c, l)
        elif format == self.FORMAT_DM:
            return "%s %d° %06.3f'" % (c, math.floor(l), (l - math.floor(l)) * 60)

    def get_latlon(self, format = 1): # that is FORMAT_DM
        return "%s %s" % (self.get_lat(format), self.get_lon(format))

    def distance_to_manual (self, target):
        dlat = math.pow(math.sin(math.radians(target.lat-self.lat) / 2), 2)
        dlon = math.pow(math.sin(math.radians(target.lon-self.lon) / 2), 2)
        a = dlat + math.cos(math.radians(self.lat)) * math.cos(math.radians(target.lat)) * dlon;
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a));
        return self.RADIUS_EARTH * c;

    def distance_to_liblocation(self, target):
        return location.distance_between(self.lat, self.lon, target.lat, target.lon) * 1000


    def __str__(self):
        return self.get_latlon()
        
    def serialize(self):

        return {'lat': self.lat, 'lon': self.lon, 'name': self.name}
        
    def unserialize(self, data):
        self.lat = data['lat']
        self.lon = data['lon']
        self.name = data['name']
        
