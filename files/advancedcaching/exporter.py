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



class HTMLExporter():
    def __init__(self, downloader, path):
        self.downloader = downloader
        self.path = path
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except:
                raise

    def export(self, coordinate, folder = None):
        if coordinate.name == '':
            raise Exception('Koordinate hat keinen Namen')
        if folder == None:
            folder = self.path
        filename = self.__get_uri(coordinate, folder)
        f = open(filename, 'w')
        self.__write_html(f, coordinate)
        f.close()
        self.__copy_images(coordinate, folder)

    def __copy_images(self, coordinate, folder):
        for image, description in coordinate.get_images().items():
            src = os.path.realpath(os.path.join(self.path, image))
            dst = os.path.realpath(os.path.join(folder, image))
            if not src == dst and not os.path.exists(dst) and os.path.exists(src):
                import shutil
                shutil.copy(src, dst)

    def __get_uri(self, coordinate, folder):
        return os.path.join(folder, "%s%shtml" % (coordinate.name, os.extsep))

    def write_index(self, caches):
        b = [{'n': c.name, 't': c.title} for c in caches]
        caches = json.dumps(b)
        f = open(os.path.join(self.path, "index.html"), 'w')
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')
        f.write(' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
        f.write('<html xmlns="http://www.w3.org/1999/xhtml"> <head>')
        f.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
        f.write(' <title>Geocache suchen</title> <script type="text/javascript">\n')
        f.write(' var caches = %s;' % caches)
        f.write("""function refresh() {
            s = document.getElementById('search'); t = s.value.toLowerCase(); ht = '';
                   if (t.length > 2) { for (var c in caches) {
                                   if (caches[c]['t'].toLowerCase().indexOf(t) != -1 || caches[c]['n'].toLowerCase().indexOf(t) != -1) {
                                           ht = ht + "<a href='" + caches[c]['n'] + ".html'>" + caches[c]['n'] + "|" + caches[c]['t'] + "<br>";
                                   } }
                   } else { ht = "(Bitte mehr als 2 Zeichen eingeben)"; }
                   document.getElementById('res').innerHTML = ht; }
                  </script>
                 </head> <body>
                  <fieldset><legend>Geocache suchen</legend>
                  <input type="text" name="search" id="search" onkeyup="refresh()" />
                  </fieldset>
                  <fieldset><legend>Ergebnisse</legend>
                  <div id="res">Bitte Suchbegriff eingeben!</div>
                  </fieldset>  </body> </html>
                """)
        f.close()



    def __write_html(self, f, coordinate):
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')
        f.write(' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
        f.write('<html xmlns="http://www.w3.org/1999/xhtml">\n <head>\n')
        f.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
        self.__write_header(f, coordinate)
        f.write(' </head>\n <body>\n')
        self.__write_body(f, coordinate)
        f.write(' </body>\n</html>\n')

    def __write_header(self, f, coordinate):
        f.write('  <title>%s|%s</title>\n' % (coordinate.name, coordinate.title))

    def __write_body(self, f, coordinate):
        f.write('  <h2>%s|%s</h2>\n' % (coordinate.name, coordinate.title))
        f.write('  <fieldset><legend>Daten</legend>\n')
        f.write('   <div style="display:inline-block;"><b>Size:</b> %s/5</div><br />\n' % coordinate.size)
        f.write('   <div style="display:inline-block;"><b>Difficulty:</b> %.1f/5</div><br />\n' % (coordinate.difficulty / 10))
        f.write('   <div style="display:inline-block;"><b>Terrain:</b> %.1f/5</div><br />\n' % (coordinate.terrain / 10))
        f.write('  </fieldset>\n')
        f.write('  <fieldset><legend>Koordinaten</legend>\n')
        f.write('   <div style="display:inline-block;"><b>MAIN:</b> <code>%s %s</code></div><br />\n' % (coordinate.get_lat(geo.Coordinate.FORMAT_DM), coordinate.get_lon(geo.Coordinate.FORMAT_DM)))
        if len(coordinate.get_waypoints()) > 0:
            f.write('   <table>\n')
            for w in coordinate.get_waypoints():
                if not (w['lat'] == -1 and w['lon'] == -1):
                    n = geo.Coordinate(w['lat'], w['lon'])
                    latlon = "%s %s" % (n.get_lat(geo.Coordinate.FORMAT_DM), n.get_lon(geo.Coordinate.FORMAT_DM))
                else:
                    latlon = "???"
                f.write('    <tr style="background-color:#bbf"><th>%s</th><td><code>%s</code></td></tr>\n' % (w['name'], latlon))
                f.write('    <tr style="background-color:#ddd"><td colspan="2">%s</tr>\n' % w['comment'])
            f.write('   </table>\n')
        f.write('  </fieldset>')
        f.write('  <fieldset><legend>Cachebeschreibung</legend>\n')
        f.write(self.__replace_images(coordinate.desc, coordinate))
        f.write('  </fieldset>')
        if len(coordinate.get_images()) > 0:
            f.write('  <fieldset><legend>Bilder</legend>\n')
            for image, description in coordinate.get_images().items():
                f.write('   <em>%s:</em><br />\n' % description)
                f.write('   <img src="%s" />\n' % image)
                f.write('   <hr />\n')
            f.write('  </fieldset>')

    def __replace_images(self, text, coordinate):
        return re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: self.__replace_image_callback(a, coordinate), text)

    def __replace_image_callback(self, match, coordinate):
        if match.group(1) in coordinate.get_images():
            return '<img src="%s" />' % match.group(1)
        else:
            return ' [image not found -- please re-download geocache description] '
