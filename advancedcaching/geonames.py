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
from urllib import quote

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json

from advancedcaching import geo

logger = logging.getLogger('geonames')


class Geonames():
    URL = '''http://ws.geonames.org/searchJSON?formatted=true&q=%(query)s&maxRows=%(max_rows)d&style=short'''
    URL_STREETS = 'http://ws.geonames.org/findNearestIntersectionOSMJSON?formatted=true&lat=%f&lng=%f&style=short'

    ORS_URL = 'http://data.giub.uni-bonn.de/openrouteservice/php/OpenLSRS_DetermineRoute.php'
    ORS_DATA = 'Start=%f,%f&End=%f,%f&Via=&lang=de&distunit=KM&routepref=Fastest&avoidAreas=&useTMC=false&noMotorways=false&noTollways=false&instructions=true'

    MAX_NODES = 1000
    DIST_FACTOR = 1.3

    def __init__(self, downloader):
        self.downloader = downloader

    @staticmethod
    def my_quote(input):
        if isinstance(input, unicode):
            return quote(input.encode('utf-8'))
        return quote(input)

    def search(self, search, nearest_street=False):
        logger.info("Trying to search geonames for %s" % search)
        qurl = self.URL % {'query': self.my_quote(search), 'max_rows': 1}
        logger.debug("Query URL: %s" % qurl)
        page = self.downloader.get_reader(url=qurl, login=False).read()
        values = json.loads(page)
        if int(values['totalResultsCount']) == 0:
            raise Exception('No Record found for query "%s"' % search)
        res = values['geonames'][0]
        c = geo.Coordinate(float(res['lat']), float(res['lng']), search)


        logger.info("Using %s for query '%s'" % (c, search))
        return c

    def search_all(self, search, max_results=15, name_string="%(name)s, %(countryCode)s"):
        logger.info("Trying to search geonames for %s" % search)
        qurl = self.URL % {'query': self.my_quote(search), 'max_rows': max_results}
        logger.debug("Query URL: %s" % qurl)
        page = self.downloader.get_reader(url=qurl, login=False).read()
        logger.debug("Result:\n%s\n" % page)
        values = json.loads(page)
        return [geo.Coordinate(float(res['lat']), float(res['lng']), name_string % res) for res in values['geonames'] if 'countryCode' in res]

    def find_nearest_intersection(self, c):
        logger.info("trying to find nearest street...")
        url = self.URL_STREETS % (c.lat, c.lon)
        page = self.downloader.get_reader(url, login=False).read()
        values = json.loads(page)
        if (len(values) == 0):
            logger.warning("Could NOT find nearest intersection to %s, using this" % c)
            return c
        intersection = values['intersection']
        c = geo.Coordinate(float(intersection['lat']), float(intersection['lng']))
        logger.info("Using nearest intersection at %s" % c)
        return c


    def find_route(self, c1, c2, min_distance):
        page = self.downloader.get_reader(url=self.ORS_URL, values=self.ORS_DATA % (c1.lon, c1.lat, c2.lon, c2.lat), login=False).read()
        import xml.dom.minidom
        from xml.dom.minidom import Node
        doc = xml.dom.minidom.parseString(page)
        # @type doc xml.dom.minidom.Document
        errors = doc.getElementsByTagName('xls:Error')
        if len(errors) > 0:
            if errors[0].getAttribute('locationPath') == 'PathFinder - getPath()':
                raise Exception("Could not find route. Please try another street as start or endpoint. The server said: ''%s''\n" % errors[0].getAttribute('message'))
            raise Exception("Could not find route. The server said: ''%s''\n" % errors[0].getAttribute('message'))
        segments = doc.getElementsByTagName('gml:LineString')
        route_points = []

        # min_distance is in km, we need m
        mdist = (min_distance * 1000.0) / self.DIST_FACTOR

        for s in segments:
            for p in s.childNodes:
                if p.nodeType != Node.ELEMENT_NODE:
                    continue
                lon, tmp, lat = p.childNodes[0].data.partition(' ')
                c = geo.Coordinate(float(lat), float(lon))
                stop = False
                for o in route_points:
                    if c.distance_to(o) < mdist:
                        stop = True
                        break
                if not stop:
                    route_points.append(c)

                if len(route_points) > self.MAX_NODES:
                    raise Exception("Too many waypoints! Try a bigger radius.")
        logger.info("Using the following Waypoints:")
        return route_points



