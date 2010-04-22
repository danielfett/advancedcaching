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
import math
import geo
import os
import datetime
import threading
global Image
try:
    import Image
except:
    Image = None
    print "Not using image resize feature"
import re
import gobject



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
        'marked' : 'INTEGER',
        'logs' : 'TEXT',
        'status' : 'INTEGER',
        'vars' : 'TEXT',
        'alter_lat' : 'REAL',
        'alter_lon' : 'REAL'
        }
    def __init__(self, lat, lon, name=''):
        geo.Coordinate.__init__(self, lat, lon, name)
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
        self.log_as = self.LOG_NO_LOG
        self.log_date = ''
        self.marked = False
        self.logs = ''
        self.status = self.STATUS_NORMAL
        self.vars = ''
        self.alter_lat = 0
        self.alter_lon = 0

    def clone(self):
        n = GeocacheCoordinate(self.lat, self.lon)
        for k in ('title', 'name', 'shortdesc', 'desc', 'hints', 'type', \
            'size', 'difficulty', 'terrain', 'owner', 'found', 'waypoints', \
            'images', 'notes', 'fieldnotes', 'log_as', 'log_date', 'marked', \
            'logs', 'status', 'vars', 'alter_lat', 'alter_lon'):
            setattr(n, k, getattr(self, k))
        return n
        
    def get_difficulty(self):
        return "%.1f" % (self.difficulty / 10.0) if self.difficulty != -1 else '?'
        
    def get_terrain(self):
        return "%.1f" % (self.terrain / 10.0) if self.difficulty != -1 else '?'

    def get_status(self):
        return self.STATUS_TEXT[self.status]

    def serialize(self):

        if self.found:
            found = 1
        else:
            found = 0
        if self.marked:
            marked = 1
        else:
            marked = 0
        return {
            'lat': self.lat,
            'lon': self.lon,
            'name': self.name,
            'title': self.title,
            'shortdesc': self.shortdesc,
            'desc': self.desc,
            'hints': self.hints,
            'type': self.type,
            'size': self.size,
            'difficulty': self.difficulty,
            'terrain': self.terrain,
            'owner': self.owner,
            'found': found,
            'waypoints': self.waypoints,
            'images': self.images,
            'notes': self.notes,
            'fieldnotes': self.fieldnotes,
            'logas': self.log_as,
            'logdate': self.log_date,
            'marked' : marked,
            'logs' : self.logs,
            'status' : self.status,
            'vars' : self.vars,
            'alter_lat' : self.alter_lat,
            'alter_lon' : self.alter_lon,
        }
                
    def unserialize(self, data):
        self.lat = data['lat']
        self.lon = data['lon']
        self.name = data['name']
        self.title = data['title']
        self.shortdesc = data['shortdesc']
        self.desc = data['desc']
        self.hints = data['hints']
        self.type = data['type']
        self.size = int(data['size'])
        self.difficulty = float(data['difficulty'])
        self.terrain = float(data['terrain'])
        self.owner = data['owner']
        self.found = (data['found'] == 1)
        self.waypoints = data['waypoints']
        self.images = data['images']
        if data['notes'] == None:
            self.notes = ''
        else:
            self.notes = data['notes']
        if data['fieldnotes'] == None:
            self.fieldnotes = ''
        else:
            self.fieldnotes = data['fieldnotes']
        self.log_as = data['logas']
        self.log_date = data['logdate']
        self.marked = (data['marked'] == 1)
        if data['logs'] == None:
            self.logs = ''
        else:
            self.logs = data['logs']
        if data['vars'] == None:
            self.vars = ''
        else:
            self.vars = data['vars']
        self.status = data['status']
        self.alter_lat = data['alter_lat']
        self.alter_lon = data['alter_lon']

    def get_waypoints(self):
        if self.waypoints == None or self.waypoints == '':
            return []
        return json.loads(self.waypoints)

    def get_vars(self):
        if self.vars == None or self.vars == '':
            return {}
        return json.loads(self.vars)

    def set_vars(self, vars):
        self.vars = json.dumps(vars)

    def get_logs(self):
        if self.logs == None or self.logs == '':
            return []
        return json.loads(self.logs)

    def get_images(self):
        if self.images == None or self.images == '':
            return []
        return json.loads(self.images)

    def set_waypoints(self, wps):
        self.waypoints = json.dumps(wps)

    def set_logs(self, ls):
        self.logs = json.dumps(ls)

    def set_images(self, imgs):
        self.images = json.dumps(imgs)
                
                
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

        return {'minlat' : "%.5f" % minlat, 'maxlat' : "%.5f" % maxlat, 'minlon' : "%.5f" % minlon, 'maxlon' : "%.5f" % maxlon}
    
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

class FieldnotesUploader(gobject.GObject):
    __gsignals__ = { 'finished-uploading': (gobject.SIGNAL_RUN_FIRST,\
                                 gobject.TYPE_NONE,\
                                 ()),
                    'upload-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    }
    #lock = threading.Lock()
    URL = 'http://www.geocaching.com/my/uploadfieldnotes.aspx'
    
    def __init__(self, downloader):
        gobject.GObject.__init__(self)
        self.downloader = downloader
        self.notes = []

    def add_fieldnote(self, geocache):
        if geocache.log_date == '':
            raise Exception("Illegal Date.")

        if geocache.log_as == GeocacheCoordinate.LOG_AS_FOUND:
            log = "Found it"
        elif geocache.log_as == GeocacheCoordinate.LOG_AS_NOTFOUND:
            log = "Didn't find it"
        elif geocache.log_as == GeocacheCoordinate.LOG_AS_NOTE:
            log = "Write note"
        else:
            raise Exception("Illegal status: %s" % self.log_as)

        text = geocache.fieldnotes.replace('"', "'")

        self.notes.append('%s,%sT10:00Z,%s,"%s"' % (geocache.name, geocache.log_date, log, text))

    def upload(self):
        try:
            print "+ Uploading fieldnotes..."
            page = self.downloader.get_reader(self.URL).read()
            m = re.search('<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="([^"]+)" />', page)
            if m == None:
                raise Exception("Could not download fieldnotes page.")
            viewstate = m.group(1)
            text = "\r\n".join(self.notes).encode("UTF-16")
            response = self.downloader.get_reader(self.URL,
                                                  data=self.downloader.encode_multipart_formdata(
                                                    [('ctl00$ContentBody$btnUpload', 'Upload Field Note'), ('ctl00$ContentBody$chkSuppressDate', ''), ('__VIEWSTATE', viewstate)],
                                                    [('ctl00$ContentBody$fuFieldNote', 'geocache_visits.txt', text)]
                                                  ))

            res = response.read()
            if not "successfully uploaded" in res:
                raise Exception("Something went wrong while uploading the field notes.")
            else:
                self.emit('finished-uploading')
        except Exception, e:
            self.emit('upload-error', e)
        

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
                                 
    MAX_REC_DEPTH = 2

    MAX_DOWNLOAD_NUM = 20
    
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
        
    @staticmethod
    def __rot13(text):
        import string
        trans = string.maketrans(
                                 'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM',
                                 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return text.translate(trans)

    @staticmethod
    def __strip_html(text, soft = False):
        if not soft:
            return re.sub(r'<[^>]*?>', '', text)
        else:
            return re.sub(r'<[^>]*?>', ' ', text)

    @staticmethod
    def __replace_br(text):
        return re.sub('<[bB][rR]\s*/?>|</?[pP]>', '\n', text)

    def __treat_hints(self, hints):
        hints = self.__strip_html(self.__replace_br(hints)).strip()
        hints = self.__rot13(hints)
        hints = re.sub(r'\[([^\]]+)\]', lambda match: self.__rot13(match.group(0)), hints)
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
        strip_comments = re.compile('<!--.*?-->', re.DOTALL)
        html = strip_comments.sub('', html)
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
                             r'<td></td>\s+</tr>\s*<tr>\s+<td>Note:</td>' +
                             r'\s*<td colspan="4">(?P<comment>.*?)</td>\s*<td>&nbsp;</td>\s*</tr> ', data, re.DOTALL)
        for m in finder:
            if m.group(1) == None:
                continue
            waypoints.append({
                             'lat': self.__from_dm(m.group('lat_sign'), m.group('lat_d'), m.group('lat_m')),
                             'lon': self.__from_dm(m.group('lon_sign'), m.group('lon_d'), m.group('lon_m')),
                             'id': "%s%s" % m.group('id_prefix', 'id'),
                             'name': self.__decode_htmlentities(m.group('name')),
                             'comment': self.__decode_htmlentities(self.__strip_html(self.__replace_br(m.group('comment')), True))
                             })

        return waypoints

    def __treat_images(self, data):
        finder = re.finditer('<a href="([^"]+)" rel="lightbox" class="lnk"><img src="/images/stockholm/16x16/images.gif" />(.+?)</a><br /><br />', data)
        for m in finder:
            if m.group(1) == None:
                continue
            id = self.__download_image(url = m.group(1))
            if id != None:
                self.__add_image(id, self.__decode_htmlentities(self.__strip_html(m.group(2))))

    def __replace_images(self, data):
        return re.sub(r'''(?is)(<img[^>]+src=\n?["']?)([^ >"']+)([^>]+?/?>)''', self.__replace_image_callback, data)

    def __replace_image_callback(self, m):
        url = m.group(2)
        if not url.startswith('http://'):
            return m.group(0)
        id = self.__download_image(url)
        if id == None:
            return m.group(0)
        else:
            self.__add_image(id)
            return "[[img:%s]]" % id

    def __treat_logs(self, logs):
        lines = logs.split('<tr>') # lines 0 and 1 are useless!
        output = []
        for l in lines:
            #lines = [re.sub("\w+", ' ', self.__decode_htmlentities(self.__strip_html(x, True)), '').sub('[ view this log ]') for x in lines[2:]]
            m = re.match(r"""<td[^>]+><strong><img src="http://www\.geocaching\.com/images/icons/icon_([a-z]+)\.gif" alt="" />""" +
                r"""&nbsp;([^ ]+) (\d+)(, (\d+))? by <a href[^>]+>([^<]+)</a></strong> \(\d+ found\)<br />(.+)""" +
                r"""<br /><br /><small>""", l, re.DOTALL)
            if m == None:
                #print "Could not parse Log-Line:\nBEGIN\n%s\nEND\n\n This can be normal." % l
                pass
            else:
                type = m.group(1)
                month = self.__month_to_number(m.group(2))
                day = m.group(3)
                year = m.group(5)
                if year == '' or year == None:
                    year = datetime.datetime.now().year
                finder = m.group(6)
                text = self.__strip_html(self.__replace_br(m.group(7)), True)
                output.append(dict(type=type, month=month, day=day, year=year, finder=finder, text=text))
        return output

    def __month_to_number(self, text):
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        if text in months:
            return months.index(text) + 1
        print "Unknown month: " + text
        return 0

    def __download_image(self, url):
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

    def __add_image(self, id, description = ''):
        if ((id in self.images.keys() and len(description) > len(self.images[id]))
            or id not in self.images.keys()):
            self.images[id] = description

    @staticmethod
    def __decode_htmlentities(string):
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
        self.downloaded_images = {}
        self.current_image = 0
        self.images = {}
        coordinate = coordinate.clone()
        self.current_cache = coordinate
        try:
            print "* Downloading %s..." % (coordinate.name)
            response = self.__get_cache_page(coordinate.name)
            u = self.__parse_cache_page(response, coordinate)
        except Exception, e:
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return self.current_cache
        CacheDownloader.lock.release()
        self.emit('finished-single', u)
        return u
        
    def __get_cache_page(self, cacheid):
        return self.downloader.get_reader('http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % cacheid)
                
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
            return []
        text = match.group(1).replace("\\'", "'")
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
            if b['ctid'] == 2:
                c.type = GeocacheCoordinate.TYPE_REGULAR
            elif b['ctid'] == 3:
                c.type = GeocacheCoordinate.TYPE_MULTI
            elif b['ctid'] == 4:
                c.type = GeocacheCoordinate.TYPE_VIRTUAL
            elif b['ctid'] == 6:
                c.type = GeocacheCoordinate.TYPE_EVENT
            elif b['ctid'] == 8:
                c.type = GeocacheCoordinate.TYPE_MYSTERY
            elif b['ctid'] == 11:
                c.type = GeocacheCoordinate.TYPE_WEBCAM
            elif b['ctid'] == 137:
                c.type = GeocacheCoordinate.TYPE_EARTH
            else:
                c.type = GeocacheCoordinate.TYPE_UNKNOWN
            c.found = b['f']
            if not b['ia']:
                c.status = GeocacheCoordinate.STATUS_DISABLED
            points.append(c)
        print 'end'
        self.emit('finished-overview', points)
        CacheDownloader.lock.release()
        return points
                
    def __parse_cache_page(self, cache_page, coordinate):
        indesc = inshortdesc = inwaypoints = inhints = False
        inhead = True
        shortdesc = desc = hints = waypoints = images = logs = owner = ''
        for line in cache_page:
            line = line.strip()
            #line = unicode(line, errors='replace')
        
            if line.startswith('<span id="ctl00_ContentBody_ShortDescription">'):
                inhead = False
                inshortdesc = True
            elif line.startswith('<span id="ctl00_ContentBody_LongDescription">'):
                inhead = False
                inshortdesc = False
                indesc = True
            elif line.startswith('<div class="CacheDetailNavigationWidget">'):
                inhead = False
                inshortdesc = False
                indesc = False
            elif line.startswith('<div id="div_hint" class="HalfLeft">'):
                inhead = False
                inshortdesc = False
                indesc = False
                inhints = True
            elif inhints and line.startswith('</div>'):
                inhints = False
            elif line.startswith('<div id="ctl00_ContentBody_uxlrgMap" class="fr"> '):
                inhead = False
                inshortdesc = False
                indesc = False
            elif line.startswith('<p><p><strong>Additional Waypoints</strong></p></p>'):
                inhead = False
                inshortdesc = False
                indesc = False
                inwaypoints = True
            elif line.startswith('</table>') and inwaypoints:
                inwaypoints = False
            elif line.startswith('<p><span id="ctl00_ContentBody_Images">'):
                images = line
            elif line.startswith('<span id="ctl00_ContentBody_LatLon" style="font-weight:bold;">'):
                coords = re.compile('lat=([0-9.-]+)&amp;lon=([0-9.-]+)&amp;').search(line)
            elif line.startswith('<p><span id="ctl00_ContentBody_CacheLogs">'):
                logs = line
            if inhead:
                if line.startswith('<p><strong>A cache') or line.startswith('<p><strong>An Event'):
                    owner = re.compile("by <[^>]+>([^<]+)</a>").search(line).group(1)
                elif line.startswith('<p class="NoSpacing"><strong>Size:</strong>'):
                    size = re.compile("container/([^\\.]+)\\.").search(line).group(1)
                    difficulty = re.compile('<span id="ctl00_ContentBody_Difficulty"><[^>]+alt="([0-9\\.]+) out of').search(line).group(1)
                    terrain = re.compile('<span id="ctl00_ContentBody_Terrain"><[^>]+alt="([0-9\\.]+) out of').search(line).group(1)
#                elif line.startswith('<a id="lnkPrintFriendly" class="lnk" href="cdpf.aspx?guid'):
#                    guid = re.compile('.*cdpf\\.aspx\?guid=([a-z0-9-]+)"').match(line).group(1)
            if inshortdesc:
                shortdesc += "%s\n" % line
                
            if indesc:
                desc += "%s\n" % line
                
            if inhints:
                hints += line + " "
                
            if inwaypoints:
                waypoints += "%s  " % line
    
        if owner == '':
            print "\n\n|||||||||||||||||||||||||||||||||||||||||||||||||||\n\n"
            for line in cache_page:
                print line
            print "\n\n|||||||||||||||||||||||||||||||||||||||||||||||||||\n\n"
            raise Exception("Could not parse Cache page. Maybe the format changed. Please update to latest version or contact author.")

        coordinate.owner = self.__decode_htmlentities(owner)
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
