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

from pyfo import pyfo
import os
from datetime import datetime
from geocaching import GeocacheCoordinate
class Exporter():

    def export(self, coordinate, folder = None):
        if coordinate.name == '':
            raise Exception('Koordinate hat keinen Namen')
        if folder == None:
            folder = self.path
        filename = self.__get_uri(coordinate, folder)
        f = open(filename, 'w')
        f.write(self.get_text(coordinate))
        f.close()

    def __get_uri(self, coordinate, folder):
        return os.path.join(folder, "%s%s%s" % (coordinate.name, os.extsep, self.EXTENSION))

class GpxExporter(Exporter):

    EXTENSION = 'gpx'
    
    def get_text(self, c):
        result = pyfo(self.__build_gpx(c), pretty=True, prolog=True, encoding='utf-8')
        return result.encode('utf8', 'xmlcharrefreplace')

    def __build_gpx(self, c):
        return ('gpx',
            self.__build_intro(c) + self.__build_main_wp(c) + self.__build_wps(c.get_waypoints()),
            {
                'xmlns:xsi' : "http://www.w3.org/2001/XMLSchema-instance",
                'xmlns:xsd' : 'http://www.w3.org/2001/XMLSchema',
                'version' : '1.0',
                'creator' : 'AGTL Geocaching Tool',
                'xsi:schemaLocation' : "http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd http://www.groundspeak.com/cache/1/0 http://www.groundspeak.com/cache/1/0/cache.xsd",
                'xmlns' : "http://www.topografix.com/GPX/1/0"
            })

    def __build_intro(self, c):
        return [
            ('name', 'AGTL Geocache Listing'),
            ('desc', ' '),
            ('email', 'nothing@example.com'),
            ('url', 'http://www.geocaching.com'),
            ('urlname', 'Geocaching - High Tech Treasure Hunting'),
            ('time', '2010-02-27T18:31:24.4812526Z'),
            ('keywords', 'cache, geocache'),
            ('author', c.owner),
            ('bounds', None, c.get_bounds()),
            
        ]

    def __build_main_wp(self, c):
        # prepare some variables...
        available = archived = 'True'
        if c.status & GeocacheCoordinate.STATUS_DISABLED:
            available = 'False'
        if not (c.status & GeocacheCoordinate.STATUS_ARCHIVED):
            archived = 'False'

        return [('wpt',
            [
                ('time', '2010-02-27T18:31:24.4812526Z'),
                ('name', c.name),
                ('desc', "%s D%s T%s: %s" % (c.type, c.get_difficulty(), c.get_terrain(), c.title)),
                ('url', 'http://coord.info/%s' % c.name),
                ('urlname', c.name),
                ('sym', 'Geocache'),
                ('type', 'Geocache|%s' % c.get_gs_type()),
                ('groundspeak:cache', self.__build_cache_info(c), {
                    'id' : 42,
                    'available' : available,
                    'archived' : archived,
                    'xmlns:groundspeak' : "http://www.groundspeak.com/cache/1/0"
                    })
            ],
            {
                'lat' : "%.5f" % c.lat,
                'lon' : "%.5f" % c.lon
            })
        ]

    def __build_cache_info(self, c):
        if c.size == 0 or c.size == 5:
            cs = 'Not Chosen'
        elif c.size == 1:
            cs = 'Micro'
        elif c.size == 2:
            cs = 'Small'
        elif c.size == 3:
            cs = 'Regular'
        elif c.size == 4:
            cs = 'Large'
        else:
            cs = 'Not Chosen'
            
        return [
            ('groundspeak:name', c.title),
            ('groundspeak:placed_by', c.owner),
            ('groundspeak:owner', c.owner, {'id' : '42'}),
            ('groundspeak:type', c.get_gs_type()),
            ('groundspeak:container', cs),
            ('groundspeak:difficulty', c.get_difficulty()),
            ('groundspeak:terrain', c.get_terrain()),
            ('groundspeak:country', 'unknown'),
            ('groundspeak:state', 'unknown'),
            ('groundspeak:short_description', c.shortdesc, {'html' : 'True'}),
            ('groundspeak:long_description', c.desc, {'html' : 'True'}),
            ('groundspeak:encoded_hints', c.hints),
        ]

    def __build_wps(self, wps):
        out = []
        for wp in wps:
            if wp['lat'] == -1 and wp['lon'] == -1:
                continue
            out += [('wpt',
                [
                    ('time', datetime.now().strftime('%Y-%m%dT%H:%M:%S.00')),
                    ('name', wp['id']),
                    ('desc', wp['name']),
                    ('cmt', wp['comment']),
                    ('url', ''),
                    ('urlname', ''),
                    ('sym', 'Trailhead'),
                    ('type', 'Waypoint|Trailhead')
                ],
                {
                    'lat' : "%.5f" % wp['lat'],
                    'lon' : "%.5f" % wp['lon']
                })
            ]
        return out
