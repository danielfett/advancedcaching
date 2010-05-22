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
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json	 
from geocaching import GeocacheCoordinate
import datetime
import geo
import os
import threading
global Image
try:
    import Image
except:
    Image = None
    print "Not using image resize feature"
import re
import gobject


class HTMLManipulations(object):
    COMMENT_REGEX = re.compile('<!--.*?-->', re.DOTALL)
    
    @staticmethod
    def _strip_html(text, soft = False):
        if not soft:
            return re.sub(r'<[^>]*?>', '', text)
        else:
            return re.sub(r'<[^>]*?>', ' ', text)

    @staticmethod
    def _replace_br(text):
        return re.sub('<[bB][rR]\s*/?>|</?[pP]>', '\n', text)


    @staticmethod
    def _decode_htmlentities(string):
        def substitute_entity(match):
            from htmlentitydefs import name2codepoint as n2cp
            ent = match.group(3)
            if match.group(1) == "#":
                # decoding by number
                if match.group(2) == '':
                    # number is in decimal
                    return unichr(int(ent))
                elif match.group(2) == 'x':
                    # number is in hex
                    return unichr(int('0x' + ent, 16))
            else:
                # they were using a name
                cp = n2cp.get(ent)
                if cp:
                    return unichr(cp)
                else:
                    return match.group()

        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(substitute_entity, string)[0]

class CacheDownloader(gobject.GObject):
    __gsignals__ = { 'finished-overview': (gobject.SIGNAL_RUN_FIRST,\
                                 gobject.TYPE_NONE,\
                                 (gobject.TYPE_PYOBJECT,)),
                    'progress' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, int, int, )),
                    'download-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'already-downloading-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'finished-single' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'finished-multiple' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    }

    lock = threading.Lock()

    @staticmethod
    def _rot13(text):
        import string
        trans = string.maketrans(
             'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM',
             'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return text.translate(trans)

    def __init__(self, downloader, path, download_images, resize = None):
        gobject.GObject.__init__(self)
        self.downloader = downloader
        self.path = path
        self.download_images = download_images
        self.resize = resize
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except:
                raise Exception("Path does not exist: %s" % path)

   

    def _init_images(self):
        self.downloaded_images = {}
        self.current_image = 0
        self.images = {}

    def _download_image(self, url):
        print "+ Checking download for %s" % url
        if url in self.downloaded_images.keys():
            return self.downloaded_images[url]
        
        ext = url.rsplit('.', 1)[1]
        if not re.match('^[a-zA-Z0-9]+$', ext):
            ext = 'img'
        filename = ''
        id = "%s-image%d.%s" % (self.current_cache.name, self.current_image, ext)

        if self.download_images:
            try:
                filename = os.path.join(self.path, id)
                print "+ Downloading %s to %s" % (url, filename)
                f = open(filename, 'wb')
                f.write(self.downloader.get_reader(url).read())
                f.close()
                if Image != None and self.resize != None and self.resize > 0:
                    im = Image.open(filename)
                    im.thumbnail((self.resize, self.resize), Image.ANTIALIAS)
                    im.save(filename)
            except Exception, e:
                print "could not download %s: %s" % (url, e)
                return None

        self.downloaded_images[url] = id
        self.current_image += 1
        return id

    def update_coordinates(self, coordinates):
        i = 0
        c = []
        if len(coordinates) > self.MAX_DOWNLOAD_NUM:
            self.emit("download-error", Exception("Downloading of more than %d descriptions is not supported." % self.MAX_DOWNLOAD_NUM))
            return
        for cache in coordinates:
            self.emit("progress", cache.name, i, len(coordinates))
            u = self.update_coordinate(cache)
            c.append(u)
            i += 1
        self.emit("finished-multiple", c)
        return c
                
    def update_coordinate(self, coordinate):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            return
        self._init_images()
        coordinate = coordinate.clone()
        self.current_cache = coordinate
        try:
            print "* Downloading %s..." % (coordinate.name)
            response = self._get_cache_page(coordinate.name)
            u = self._parse_cache_page(response, coordinate)
        except Exception, e:
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return self.current_cache
        CacheDownloader.lock.release()
        self.emit('finished-single', u)
        return u

                
    def get_geocaches(self, location, rec_depth = 0):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            print "downloading"
            return
        # don't recurse indefinitely
        if rec_depth > self.MAX_REC_DEPTH:
            self.emit('download-error', Exception("Please select a smaller part of the map."))
            CacheDownloader.lock.release()
            return []

        content = self._get_overview(location)
        if content == None:
            return []
        points = self._parse_overview(content)

        self.emit('finished-overview', points)
        CacheDownloader.lock.release()
        return points

class GeocachingComCacheDownloader(CacheDownloader):
    MAX_REC_DEPTH = 2

    MAX_DOWNLOAD_NUM = 20


    CTIDS = {
        2:GeocacheCoordinate.TYPE_REGULAR,
        3:GeocacheCoordinate.TYPE_MULTI,
        4:GeocacheCoordinate.TYPE_VIRTUAL,
        6:GeocacheCoordinate.TYPE_EVENT,
        8:GeocacheCoordinate.TYPE_MYSTERY,
        11:GeocacheCoordinate.TYPE_WEBCAM,
        137:GeocacheCoordinate.TYPE_EARTH
    }

    def _get_overview(self, location):
        c1, c2 = location
        url = 'http://www.geocaching.com/map/default.aspx?lat=49&lng=6'
        values = {'eo_cb_id':'ctl00_ContentBody_cbAjax',
            'eo_cb_param':'{"c": 1, "m": "", "d": "%f|%f|%f|%f"}' % (max(c1.lat, c2.lat), min(c1.lat, c2.lat), max(c1.lon, c2.lon), min(c1.lon, c2.lon)),
            'eo_version':'5.0.51.2'
        }

        try:
            response = self.downloader.get_reader(url, values)
            the_page = response.read()

            extractor = re.compile('<ExtraData><!\[CDATA\[(.*)\]\]>', re.DOTALL)
            match = extractor.search(the_page)
            if match == None:
                raise Exception('Could not load map of geocaches')
        except Exception, e:
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return None
        return match.group(1)

    def _parse_overview(self, content):
        text = content.replace("\\'", "'")
        a = json.loads(text.replace('\t', ' '))
        points = []
        if not 'cc' in a['cs'].keys():
            if 'count' in a['cs'].keys() and 'count' != 0:
                # let's try to download one half of the geocaches first
                mlat = (c1.lat + c2.lat)/2
                nc1 = geo.Coordinate(min(c1.lat, c2.lat), min(c1.lon, c2.lon))
                mc1 = geo.Coordinate(mlat, max(c1.lon, c2.lon))
                mc2 = geo.Coordinate(mlat, min(c1.lon, c2.lon))
                nc2 = geo.Coordinate(max(c1.lat, c2.lat), max(c1.lon, c2.lon))
                #print "recursing..."

                CacheDownloader.lock.release()
                points += self.get_geocaches((nc1, mc1), rec_depth + 1)
                points += self.get_geocaches((mc2, nc2), rec_depth + 1)
            return points
        for b in a['cs']['cc']:
            c = GeocacheCoordinate(b['lat'], b['lon'], b['gc'])
            c.title = b['nn']
            if b['ctid'] in self.CTIDS:
                c.type = self.CTIDS[b['ctid']]
            else:
                c.type = GeocacheCoordinate.TYPE_UNKNOWN

            c.found = b['f']
            if not b['ia']:
                c.status = GeocacheCoordinate.STATUS_DISABLED
            points.append(c)
        return points

        
    def _get_cache_page(self, cacheid):
        return self.downloader.get_reader('http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % cacheid)

                
    def _parse_cache_page(self, cache_page, coordinate):
        section = ''
        shortdesc = desc = hints = waypoints = images = logs = owner = ''
        for line in cache_page:
            line = line.strip()
            #line = unicode(line, errors='replace')
            if section == '' and line.startswith('<div id="doc3" class="yui-t1">'):
                section = 'head'
            elif section == 'head' and line.startswith('<span id="ctl00_ContentBody_ShortDescription">'):
                section = 'shortdesc'
            elif (section == 'head' or section == 'shortdesc') and line.startswith('<span id="ctl00_ContentBody_LongDescription">'):
                section = 'desc'
            elif (section == 'desc' or section == 'shortdesc') and line.startswith('<div class="CacheDetailNavigationWidget">'):
                section = 'after-desc'
            elif section == 'after-desc' and line.startswith('<div id="div_hint" class="HalfLeft">'):
                section = 'hints'
            elif section == 'hints' and line.startswith('</div>'):
                section = 'after-hints'
            elif (section == 'after-hints' or section == 'after-desc') and line.startswith('<div id="ctl00_ContentBody_uxlrgMap" class="fr">'):
                section = 'pre-waypoints'
            elif section == 'after-hints' and line.startswith('<p><p><strong>Additional Waypoints</strong></p></p>'):
                section = 'waypoints'
            elif section == 'waypoints' and line.startswith('</table>'):
                section = 'after-waypoints'
            elif (section == 'pre-waypoints' or section == 'after-waypoints') and line.startswith('<p><span id="ctl00_ContentBody_Images">'):
                section = 'images'
            elif section == 'images' and line.startswith('<h3>Logged Visits'):
                section = 'after-images'
            elif section == 'after-images' and line.startswith('<p><span id="ctl00_ContentBody_CacheLogs">'):
                logs = line
            print section, ':', line
            if section == 'head':
                if line.startswith('<p><strong>A cache') or line.startswith('<p><strong>An Event'):
                    owner = re.compile("by <[^>]+>([^<]+)</a>").search(line).group(1)
                elif line.startswith('<p class="NoSpacing"><strong>Size:</strong>'):
                    size = re.compile("container/([^\\.]+)\\.").search(line).group(1)
                    difficulty = re.compile('<span id="ctl00_ContentBody_Difficulty"><[^>]+alt="([0-9\\.]+) out of').search(line).group(1)
                    terrain = re.compile('<span id="ctl00_ContentBody_Terrain"><[^>]+alt="([0-9\\.]+) out of').search(line).group(1)
                elif line.startswith('<span id="ctl00_ContentBody_LatLon" style="font-weight:bold;">'):
                    coords = re.compile('lat=([0-9.-]+)&amp;lon=([0-9.-]+)&amp;').search(line)
            elif section == 'shortdesc':
                shortdesc = "%s%s\n" % (shortdesc, line)
            elif section == 'desc':
                desc = "%s%s\n" % (desc, line)
            elif section == 'hints':
                hints = "%s%s " % (hints, line)
            elif section == 'waypoints':
                waypoints = "%s%s  " % (waypoints, line)
            elif section == 'images':
                images = "%s%s " % (images, line)
    
        if owner == '':
            print "\n\n|||||||||||||||||||||||||||||||||||||||||||||||||||\n\n"
            for line in cache_page:
                print line
            print "\n\n|||||||||||||||||||||||||||||||||||||||||||||||||||\n\n"
            raise Exception("Could not parse Cache page. Maybe the format changed. Please update to latest version or contact author.")

        coordinate.owner = HTMLManipulations._decode_htmlentities(owner)
        if size == 'micro':
            coordinate.size = 1
        elif size == 'small':
            coordinate.size = 2
        elif size == 'regular':
            coordinate.size = 3
        elif size == 'large' or size == 'big':
            coordinate.size = 4
        elif size == 'not_chosen':
            coordinate.size = 5
        else:
            print "Size not known: %s" % size
            coordinate.size = 5

        coordinate.lat = float(coords.group(1))
        coordinate.lon = float(coords.group(2))
        coordinate.difficulty = 10 * float(difficulty)
        coordinate.terrain = 10 * float(terrain)
        coordinate.shortdesc = self.__treat_shortdesc(shortdesc)
        coordinate.desc = self.__treat_desc(desc)
        coordinate.hints = self.__treat_hints(hints)
        coordinate.set_waypoints(self.__treat_waypoints(waypoints))
        coordinate.set_logs(self.__treat_logs(logs))
        self.__treat_images(images)
        coordinate.set_images(self.images)
                
        return coordinate
                
    
    def __treat_hints(self, hints):
        hints = HTMLManipulations._strip_html(HTMLManipulations._replace_br(hints)).strip()
        hints = self._rot13(hints)
        hints = re.sub(r'\[([^\]]+)\]', lambda match: self._rot13(match.group(0)), hints)
        return hints

    def __treat_desc(self, desc):
        desc = self.__treat_html(desc.rsplit('\n', 5)[0])
        return desc.strip()
        
    def __treat_shortdesc(self, desc):
        if desc.strip() == '':
            return ''
        desc = self.__treat_html(desc.rsplit('\n', 3)[0])
        return desc
        
    def __treat_html(self, html):
        html = HTMLManipulations.COMMENT_REGEX.sub('', html)
        html = self.__replace_images(html)
        return html

    @staticmethod
    def __from_dm(direction, decimal, minutes):
        if direction == None or decimal == None or minutes == None:
            return -1
        if direction in "SsWw":
            sign = -1
        else:
            sign = 1
                
        return (float(decimal) + (float(minutes) / 60.0)) * sign

    def __treat_waypoints(self, data):
        
        waypoints = []
        finder = re.finditer(r'<tr class="[^"]+">\s+<td><img [^>]+></td>\s*' +
                             r'<td><img [^>]+></td>\s*' +
                             r'<td>(?P<id_prefix>[^<]+)</td>\s*' +
                             r'<td>(?P<id>[^<]+)</td>\s*' +
                             r'<td><a href=[^>]+>(?P<name>[^<]+)</a>[^<]+</td>\s*' +
                             r'<td>(\?\?\?|(?P<lat_sign>N|S) (?P<lat_d>\d+)° (?P<lat_m>[0-9\.]+) (?P<lon_sign>E|W) (?P<lon_d>\d+)° (?P<lon_m>[0-9\.]+))</td>\s*' +
                             r'<td>.*?</td>\s+</tr>\s*<tr>\s+<td>Note:</td>' +
                             r'\s*<td colspan="4">(?P<comment>.*?)</td>\s*<td>&nbsp;</td>\s*</tr> ', data, re.DOTALL)
        for m in finder:
            if m.group(1) == None:
                continue
            waypoints.append({
                             'lat': self.__from_dm(m.group('lat_sign'), m.group('lat_d'), m.group('lat_m')),
                             'lon': self.__from_dm(m.group('lon_sign'), m.group('lon_d'), m.group('lon_m')),
                             'id': "%s%s" % m.group('id_prefix', 'id'),
                             'name': HTMLManipulations._decode_htmlentities(m.group('name')),
                             'comment': HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(HTMLManipulations._replace_br(m.group('comment')), True))
                             })

        return waypoints

    def __treat_images(self, data):
        finder = re.finditer('<a href="([^"]+)" rel="lightbox" class="lnk"><img src="/images/stockholm/16x16/images.gif" />(.+?)</a><br /><br />', data)
        for m in finder:
            if m.group(1) == None:
                continue
            id = self._download_image(url = m.group(1))
            if id != None:
                self.__add_image(id, HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(m.group(2))))

    def __treat_logs(self, logs):
        lines = logs.split('<tr>') # lines 0 and 1 are useless!
        output = []
        for l in lines:
            #lines = [re.sub("\w+", ' ', HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(x, True)), '').sub('[ view this log ]') for x in lines[2:]]
            m = re.match(r"""<td[^>]+><strong><img src="http://www\.geocaching\.com/images/icons/(?:icon_(?P<icon>[a-z]+)|(?P<icon2>coord_update))\.gif" alt="" />""" +
                r"""&nbsp;(?P<month>[^ ]+) (?P<day>\d+)(, (?P<year>\d+))? by <a href[^>]+>(?P<name>[^<]+)</a></strong> \(\d+ found\)<br />(?P<text>.+)""" +
                r"""<br /><br /><small>""", l, re.DOTALL)
            if m == None:
                #print "Could not parse Log-Line:\nBEGIN\n%s\nEND\n\n This can be normal." % l
                pass
            else:
                type = m.group('icon') if m.group('icon') != None else m.group('icon2')
                month = self.__month_to_number(m.group('month'))
                day = m.group('day')
                year = m.group('year')
                if year == '' or year == None:
                    year = datetime.datetime.now().year
                finder = m.group('name')
                text = HTMLManipulations._strip_html(HTMLManipulations._replace_br(m.group('text')), True)
                output.append(dict(type=type, month=month, day=day, year=year, finder=finder, text=text))
        return output

    def __replace_images(self, data):
        return re.sub(r'''(?is)(<img[^>]+src=\n?["']?)([^ >"']+)([^>]+?/?>)''', self.__replace_image_callback, data)

    def __replace_image_callback(self, m):
        url = m.group(2)
        if not url.startswith('http://'):
            return m.group(0)
        id = self._download_image(url)
        if id == None:
            return m.group(0)
        else:
            self.__add_image(id)
            return "[[img:%s]]" % id

    def __add_image(self, id, description = ''):
        if ((id in self.images.keys() and len(description) > len(self.images[id]))
            or id not in self.images.keys()):
            self.images[id] = description

    @staticmethod
    def __month_to_number(text):
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        if text in months:
            return months.index(text) + 1
        print "Unknown month: " + text
        return 0

def test(name, password):
    import downloader

    def pcache(c):
        print "--------------------\nName: '%s'\nTitle: '%s'\nType: %s" % (c.name, c.title, c.type)
    
    a = GeocachingComCacheDownloader(downloader.FileDownloader(name, password, '/tmp/cookies'), '/tmp/', True)
    coords = a.get_geocaches((geo.Coordinate(49.3513,6.583), geo.Coordinate(49.352,6.584)))
    print "# Found %d coordinates" % len(coords)
    for x in coords:
        pcache(x)
        if x.name == 'GC1N8G6':
            if x.type != GeocacheCoordinate.TYPE_REGULAR or x.title != 'Druidenpfad':
                print "# Wrong type or title"
                return False
            m = x
            break
        
    else:
        print "# Didn't find my own geocache :-("
    res = a.update_coordinates([m])
    print res
    c = res[0]
    if c.owner != 'webhamster':
        print "Owner doesn't match ('%s', expected webhamster)" % c.owner
    if c.title != 'Druidenpfad':
        print "Title doesn't match ('%s', expected 'Druidenpfad')" % c.title
    if c.get_terrain() != '3.0':
        print "Terrain doesn't match (%s, expected %s) " % c.get_terrain()
    if c.get_difficulty() != '2.0':
        print "Diff. doesn't match (%s, expected 2.0)" % c.get_difficulty()
    if len(c.desc) != 1980:
        print "Length of text doesn't match (%d, expected %d" % (len(c.desc), 1980)
    if len(c.shortdesc) != 238:
        print "Length of short description doesn't match (%d, expected %d" % (len(c.shortdesc), 238)
    if len(c.get_waypoints()) != 4:
        print "Expected 4 waypoints, got %d" % c.get_waypoints()
    if len(c.hints) != 83:
        print "Expected 83 characters of hints, got %d" % len(c.hints)
    
    if len(c.get_logs()) < 2:
        print "Expected at least 2 logs, got %d" % len(c.get_logs())

