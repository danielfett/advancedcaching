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


VERSION = 19
VERSION_DATE = '2011-10-07'

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
import logging
logger = logging.getLogger('cachedownloader')
global Image
try:
    import Image
except:
    Image = None
    logger.info("Not using image resize feature")
import re
import gobject

#ugly workaround...
user_token = [None]


class HTMLManipulations(object):
    COMMENT_REGEX = re.compile('<!--.*?-->', re.DOTALL)
    
    @staticmethod
    def _strip_html(text, soft = False):
        if not soft:
            return re.sub(r'<[^>]*?>', '', text)
        else:
            return re.sub(r'<[^>]*?>', ' ', text)

    @staticmethod
    def strip_html_visual(text, image_replace_callback = None):
        text = text.replace("\n", " ")
        if image_replace_callback != None:
            text = re.sub(r"""(?i)<img[^>]+alt=["']?([^'"> ]+)[^>]+>""", image_replace_callback, text)
        text = re.sub(r'(?i)<(br|p)[^>]*?>', "\n", text)
        text = re.sub(r'<[^>]*?>', '', text)
        text = HTMLManipulations._decode_htmlentities(text)
        text = re.sub(r'[\n\r]+\s*[\n\r]+', '\n', text)
        return text.strip()

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
        return text.encode('rot13').decode('iso-8859-1', 'replace')

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
        logger.info("Checking download for %s" % url)
        if url in self.downloaded_images:
            return self.downloaded_images[url]
        
        ext = url.rsplit('.', 1)[1]
        if not re.match('^[a-zA-Z0-9]+$', ext):
            ext = 'img'
        filename = ''
        id = "%s-image%d.%s" % (self.current_cache.name, self.current_image, ext)

        if self.download_images:
            try:
                filename = os.path.join(self.path, id)
                logger.info("Downloading %s to %s" % (url, filename))
                f = open(filename, 'wb')
                f.write(self.downloader.get_reader(url, login=False).read())
                f.close()
                if Image != None and self.resize != None and self.resize > 0:
                    im = Image.open(filename)
                    im.thumbnail((self.resize, self.resize), Image.ANTIALIAS)
                    im.save(filename)
            except Exception, e:
                logger.exception(e)
                return None

        self.downloaded_images[url] = id
        self.current_image += 1
        return id

    def update_coordinates(self, coordinates, num_logs = 20):
        i = 0
        c = []
        if len(coordinates) > self.MAX_DOWNLOAD_NUM:
            self.emit("download-error", Exception("Downloading of more than %d descriptions is not supported." % self.MAX_DOWNLOAD_NUM))
            return
        for cache in coordinates:
            self.emit("progress", cache.name, i, len(coordinates))
            u = self.update_coordinate(cache, num_logs = num_logs)
            c.append(u)
            i += 1
        self.emit("finished-multiple", c)
        return c
                
    def update_coordinate(self, coordinate, num_logs = 20, outfile = None):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            return
        self._init_images()
        coordinate = coordinate.clone()
        self.current_cache = coordinate
        try:
            logger.info("Downloading %s..." % (coordinate.name))
            response = self._get_cache_page(coordinate.name)
            if outfile != None:
                f = open(outfile, 'w')
                f.write(response.read())
                f.close()
                response = open(outfile)
            u = self._parse_cache_page(response, coordinate, num_logs)
        except Exception, e:
            logger.exception(e)
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return self.current_cache
        CacheDownloader.lock.release()
        self.emit('finished-single', u)
        return u

                
    def get_geocaches(self, location, rec_depth = 0):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            logger.warning("Download in progress")
            return
        # don't recurse indefinitely
        if rec_depth > self.MAX_REC_DEPTH:
            raise Exception("Please select a smaller part of the map.")
            CacheDownloader.lock.release()
            return []

        try:
            content = self._get_overview(location)
        except Exception, e:
            self.emit('download-error', e)
            CacheDownloader.lock.release()
            return []
                            
        if content == None:
            return []
        try:
            points = self._parse_overview(content, location, rec_depth)
        except Exception, e:
            if rec_depth == 0:
                self.emit('download-error', e)
                CacheDownloader.lock.release()
                return []
            else:
                raise e

        self.emit('finished-overview', points)
        CacheDownloader.lock.release()
        return points
        
        
class GeocachingComCacheDownloader(CacheDownloader):
    
    MAX_REC_DEPTH = 8

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

    @staticmethod
    def login_callback(downloader, username, password):
        url = 'https://www.geocaching.com/login/default.aspx'
        values = {'ctl00$ContentBody$tbUsername': username,
            'ctl00$ContentBody$tbPassword': password,
            'ctl00$ContentBody$cbRememberMe': 'on',
            'ctl00$ContentBody$btnSignIn': 'Login',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': ''
        }
        page = downloader.get_reader(url, values, login = False)

        for line in page:
            if 'You are logged in as' in line:
                break
            elif 'combination does not match' in line:
                raise Exception("Wrong password or username!")
        else:
            logger.info("Seems as if the language is set to something other than english")
            raise Exception("Please go to geocaching.com and set the website language to english!")

    @staticmethod
    def check_login_callback(downloader):
        url = 'http://www.geocaching.com/seek/nearest.aspx'
        page = downloader.get_reader(url, login = False)
        
        for line in page:
            if 'Hello, ' in line:
                logger.info("Seems as we're still logged in")
                page.close()
                return True
            elif 'Welcome, Visitor!' in line:
                logger.info("Nope, not logged in anymore")
                page.close()
                return False

    def _get_overview(self, location):
        if user_token[0] == None:
            self._get_user_token()
        c1, c2 = location
        url = 'http://www.geocaching.com/map/default.aspx/MapAction?lat=9&lng=6'
        data = ('application/json', '{"dto":{"data":{"c":1,"m":"","d":"%f|%f|%f|%f"},"ut":"%s"}}' % (max(c1.lat, c2.lat), min(c1.lat, c2.lat), max(c1.lon, c2.lon), min(c1.lon, c2.lon), user_token[0]))

        try:
            response = self.downloader.get_reader(url, data = data, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
            the_page = response.read()

        except Exception, e:
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return None
        return the_page
        
    def _get_user_token(self):
        page = self.downloader.get_reader('http://www.geocaching.com/map/default.aspx?lat=6&lng=9', login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        for line in page:
            if line.startswith('var uvtoken'):
                user_token[0] = re.compile("userToken[ =]+'([^']+)'").search(line).group(1)
                print user_token
                page.close()
                return
        raise Exception("Website contents unexpected. Please check connection.")
        

    def _parse_overview(self, content, location, rec_depth = 0):
        c1, c2 = location
        #text = content.replace('\\"', '"')
        #text = text.replace('\t', ' ')
        full = json.loads(content)
        a = json.loads(full['d'])
        points = []
        if not 'cc' in a['cs']:
            if 'count' in a['cs'] and 'count' != 0:
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
                CacheDownloader.lock.acquire(False)
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
        return self.downloader.get_reader('http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % cacheid, login_callback = self.login_callback, check_login_callback = self.check_login_callback)

                
    def _parse_cache_page(self, cache_page, coordinate, num_logs):
        prev_section = ''
        shortdesc = desc = coords = hints = waypoints = images = logs = owner = head = attribute_line = warning_line = ''
        logger.debug("Start parsing...")
        S_NONE, S_HEAD, S_AFTER_HEAD, S_SHORTDESC, S_DESC, S_AFTER_DESC, S_HINTS, S_AFTER_HINTS, S_PRE_WAYPOINTS, S_WAYPOINTS, S_AFTER_WAYPOINTS, S_IMAGES, S_AFTER_IMAGES, S_TOKEN = range(14)
        section = S_NONE
        for line in cache_page:
            line = line.strip()
            
            if section == S_NONE: 
                if line.startswith('<meta name="og:site_name" '):
                    section = S_HEAD
            elif section == S_HEAD:
                if line.startswith('<form name="aspnetForm"'):
                    section = S_AFTER_HEAD
            elif section == S_AFTER_HEAD:
                if line.startswith('<span id="ctl00_ContentBody_ShortDescription">'):
                    section = S_SHORTDESC
                elif line.startswith('<span id="ctl00_ContentBody_LongDescription">'):
                    section = S_DESC
            elif section == S_SHORTDESC:
                if line.startswith('<span id="ctl00_ContentBody_LongDescription">'):
                    section = S_DESC
                elif line.startswith('Additional Hints'):
                    section = S_AFTER_DESC
            elif section == S_DESC:
                if line.startswith('Additional Hints'):
                    section = S_AFTER_DESC
            elif section == S_AFTER_DESC:
                if line.startswith('<div id="div_hint"'):
                    section = S_HINTS
                elif line.startswith('<div class="CacheDetailNavigationWidget">'):
                    section = S_PRE_WAYPOINTS
            elif section == S_HINTS:
                if line.startswith("<div id='dk'"):
                    section = S_AFTER_HINTS
            elif section == S_AFTER_HINTS:
                if line.startswith('<div class="CacheDetailNavigationWidget">'):
                    section = S_PRE_WAYPOINTS
            elif section == S_PRE_WAYPOINTS:
                if line.startswith('<span id="ctl00_ContentBody_MapLinks_MapLinks">'):
                    section = S_IMAGES
                if line.startswith('<table class="Table" id="ctl00_ContentBody_Waypoints">'):
                    section = S_WAYPOINTS
            elif section == S_WAYPOINTS:
                if line.startswith('</tbody> </table>'):
                    section = S_AFTER_WAYPOINTS
            elif section == S_AFTER_WAYPOINTS:
                if line.startswith('<span id="ctl00_ContentBody_MapLinks_MapLinks">'):
                    section = S_IMAGES
            elif section == S_IMAGES:
                if line.startswith('<div class="InformationWidget'):
                    section = S_AFTER_IMAGES            
            elif section == S_AFTER_IMAGES:
                if line.startswith('userToken = '):
                    section = S_TOKEN
                

            if section != prev_section:
                logger.debug("Now in Section '%s', with line %s" % (section, line[:20:]))
            prev_section = section

            if section == S_HEAD:
                head = "%s%s\n" % (head, line)
            elif section == S_SHORTDESC:
                shortdesc = "%s%s\n" % (shortdesc, line)
            elif section == S_DESC:
                desc = "%s%s\n" % (desc, line)
            elif section == S_HINTS:
                hints = "%s%s " % (hints, line)
            elif section == S_WAYPOINTS:
                waypoints = "%s%s  " % (waypoints, line)
            elif section == S_IMAGES:
                images = "%s%s " % (images, line)
            elif section == S_TOKEN:
                usertoken = line.replace("userToken = '", '').replace("';", '').strip()
                logger.debug("usertoken is %s" % usertoken)
                break
            elif section == S_AFTER_HINTS and attribute_line == '' and line.startswith("<img src=\"/images/attributes"):
                attribute_line = line
            elif section == S_AFTER_HEAD and warning_line == '' and line.startswith('<p class="OldWarning NoBottomSpacing">'):
                warning_line = line
            elif section == S_AFTER_HEAD and coords == '' and line.startswith('<a id="ctl00_ContentBody_lnkConversions"'):
                coords = line
                
        logger.debug('finished parsing, converting...')
        head = unicode(head, 'utf-8', errors='replace')
        shortdesc = unicode(shortdesc, 'utf-8', errors='replace')
        desc = unicode(desc, 'utf-8', errors='replace')
        hints = unicode(hints, 'utf-8', errors='replace')
        waypoints = unicode(waypoints, 'utf-8', errors='replace')
        images = unicode(images, 'utf-8', errors='replace')
        attribute_line = unicode(attribute_line, 'utf-8', errors='replace')
        logger.debug('finished converting, reading...')
        if 'archived' in warning_line:
            coordinate.status = GeocacheCoordinate.STATUS_ARCHIVED
            logger.debug("Cache status is ARCHIVED")
        elif 'temporarily unavailable' in warning_line:
            coordinate.status = GeocacheCoordinate.STATUS_DISABLED
            logger.debug("Cache status is DISABLED")
        else:
            # Do not change existing status - it may be more accurate.
            pass
            
        coordinate.size, coordinate.difficulty, coordinate.terrain, coordinate.owner, coordinate.lat, coordinate.lon = self.__parse_head(head, coords)
        coordinate.shortdesc = self.__treat_shortdesc(shortdesc)
        coordinate.desc = self.__treat_desc(desc)
        coordinate.hints = self.__treat_hints(hints)
        coordinate.set_waypoints(self.__treat_waypoints(waypoints))
        coordinate.set_logs(self._get_logs(usertoken, num_logs))
        coordinate.attributes = self.__treat_attributes(attribute_line)
        self.__treat_images(images)
        coordinate.set_images(self.images)
        logger.debug('finished reading.')
        return coordinate

    def _get_logs(self, usertoken, count):
        logger.debug("Retrieving %d logs..." % count)
        logs = self.downloader.get_reader('http://www.geocaching.com/seek/geocache.logbook?tkn=%s&idx=1&num=%d&decrypt=true' % (usertoken, count), login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        return self._parse_logs_json(logs.read())

    def _parse_logs_json(self, logs):
        try:
            r = json.loads(logs)
        except Exception, e:
            logger.exception('Could not json-parse logs!')
        if not 'status' in r or r['status'] != 'success':
            logger.error('Could not read logs, status is "%s"' % r['status'])
        data = r['data']

        output = []
        for l in data:
            tpe = l['LogTypeImage'].replace('.gif', '').replace('icon_', '')
            date = l['Visited']
            finder = "%s (found %s)" % (l['UserName'], l['GeocacheFindCount'])
            text = HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(HTMLManipulations._replace_br(l['LogText'])))
            output.append(dict(type=tpe, date=date, finder=finder, text=text))
        logger.debug("Read %d log entries" % len(output))
        return output
                
    def __parse_head(self, head, coords):
        size_diff_terr = re.compile('was created by (?P<owner>.+?) on .+? a (?P<size>[a-zA-Z ]+) size geocache, with difficulty of (?P<diff>[0-9.]+?), terrain of (?P<terr>[0-9.]+?). ').search(head)
        sizestring = size_diff_terr.group('size').lower()
        if sizestring == 'micro':
            size = 1
        elif sizestring == 'small':
            size = 2
        elif sizestring == 'regular':
            size = 3
        elif sizestring == 'large' or sizestring == 'big':
            size = 4
        elif sizestring == 'not chosen' or sizestring == 'other' or sizestring == 'virtual':
            size = 5
        else:
            logger.warning("Size not known: %s" % sizestring)
            size = 5
        diff = float(size_diff_terr.group('diff'))*10
        terr = float(size_diff_terr.group('terr'))*10
        owner = HTMLManipulations._decode_htmlentities(size_diff_terr.group('owner'))
        coords = re.compile('lat=([0-9.-]+)&amp;lon=([0-9.-]+)&amp;').search(coords)
        lat = float(coords.group(1))
        lon = float(coords.group(2))
        return size, diff, terr, owner, lat, lon
        
    def __treat_attributes(self, line):
        finder = re.finditer('<img[^>]+?title="([^"]+?)"', line)
        attributes = []
        for m in finder:
            if m.group(1) != "blank":
                attributes += [m.group(1)]
        logger.debug("Attributes are: %r" % attributes)
        return ','.join(attributes)
    
    def __treat_hints(self, hints):
        hints = HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(HTMLManipulations._replace_br(hints))).strip()
        hints = self._rot13(hints)
        hints = re.sub(r'\[([^\]]+)\]', lambda match: self._rot13(match.group(0)), hints)
        hints = hints.replace('&aofc;', '').strip()
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
        logger.debug('Waypoints: %s' % data)
        data.replace('</td>', '')
        data.replace('</tr>', '')
        lines = data.split('<tr')
        waypoints = []
        for line in lines:
            tds = re.split('<td[^>]*>', line)
            logger.debug('TDs: %s' % repr(tds))
            if len(tds) <= 1:
                continue
            elif len(tds) > 4:
                id = ''.join(HTMLManipulations._strip_html(x).strip() for x in tds[4:6])
                name = HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(tds[6])).strip()
            
                m = re.compile(ur'''(\?\?\?|(?P<lat_sign>N|S) (?P<lat_d>\d+?)° (?P<lat_m>[0-9\.]+?) (?P<lon_sign>E|W) (?P<lon_d>\d+?)° (?P<lon_m>[0-9\.]+?))''').search(tds[7])
                lat = self.__from_dm(m.group('lat_sign'), m.group('lat_d'), m.group('lat_m'))
                lon = self.__from_dm(m.group('lon_sign'), m.group('lon_d'), m.group('lon_m'))
            else:
                comment = HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(HTMLManipulations._replace_br(tds[3]))).strip()
                waypoints.append({'lat':lat, 'lon':lon, 'id':id, 'name':name, 'comment':comment})
        return waypoints

    def __treat_images(self, data):
        finder = re.finditer('<a href="([^"]+?)"[^>]*?rel="lightbox"[^>]*?>.+?<span>(.+?)</span>', data)
        for m in finder:
            if m.group(1) == None:
                continue
            id = self._download_image(url = m.group(1))
            if id != None:
                self.__add_image(id, HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(m.group(2))))
    def __replace_images(self, data):
        return re.sub(ur'''(?is)(<img[^>]+src=\n?["']?)([^ >"']+)([^>]+?/?>)''', self.__replace_image_callback, data)

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
        if ((id in self.images and len(description) > len(self.images[id]))
            or id not in self.images):
            self.images[id] = description

from lxml.html import fromstring, tostring
        
class NewGeocachingComCacheDownloader(GeocachingComCacheDownloader):
        
    @staticmethod
    def check_login_callback(downloader):
        url = 'http://www.geocaching.com/seek/nearest.aspx'
        page = downloader.get_reader(url, login = False).read()

        t = unicode(page, 'utf-8')
        doc = fromstring(t)
        if len(doc.cssselect('.NotSignedInText')) > 0:
            logger.info("Probably not signed in anymore.")
            return False
        elif len(doc.cssselect('.SignedInText')) > 0:
            logger.info("Probably still signed in.")
            return True
        logger.exception("Could not reliably determine logged in status, assuming No")
        return False
        
    @staticmethod
    def login_callback(downloader, username, password):
        url = 'https://www.geocaching.com/login/default.aspx'
        values = {'ctl00$ContentBody$tbUsername': username,
            'ctl00$ContentBody$tbPassword': password,
            'ctl00$ContentBody$cbRememberMe': 'on',
            'ctl00$ContentBody$btnSignIn': 'Login',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': ''
        }
        page = downloader.get_reader(url, values, login = False).read()

        t = unicode(page, 'utf-8')
        doc = fromstring(t)
        
        if doc.get_element_by_id('ctl00_ContentBody_ErrorText', None) != None:
            raise Exception("Wrong username or password!")
        if len(doc.cssselect('.Success')) > 0:
            logger.info("Great success.")
            return True
        raise Exception("Name/Password MAY be correct, but I encountered unexpected data while logging in.")
            
                
    def _parse_cache_page(self, cache_page, coordinate, num_logs):
        logger.debug("Start parsing.")
        pg = cache_page.read()
        t = unicode(pg, 'utf-8')
        doc = fromstring(t)
        
        # Basename - Image name without path and extension
        def basename(url):
            return url.split('/')[-1].split('.')[0]
        
        # Short Description - Long Desc. is added after the image handling (see below)
        coordinate.shortdesc = doc.get_element_by_id('ctl00_ContentBody_ShortDescription').text_content()#self._extract_node_contents(doc.get_element_by_id('ctl00_ContentBody_ShortDescription'), 'Short Description')

        # Coordinate - may have been updated by the user; therefore retrieve it again
        coord_text = doc.get_element_by_id('uxLatLon')
        if coord_text == None:
            raise Exception("Could not find uxLatLon")
        try:
            coord = geo.try_parse_coordinate(coord_text.text_content())
        except Exception, e:
            logger.error("Could not parse this coordinate: %r" % coord_text.text_content())
            raise e
        coordinate.lat, coordinate.lon = coord.lat, coord.lon
        
        # Size 
        try:
            # src is URL to image of the cache size
            # src.split('/')[-1].split('.')[0] is the basename minus extension
            coordinate.size = self._handle_size(basename(doc.cssselect('.CacheSize p span img')[0].get('src')))
        except Exception, e:
            logger.error("Could not find/parse size string")
            raise e
            
        # Terrain/Difficulty
        try:
            coordinate.difficulty, coordinate.terrain = [self._handle_stars(basename(x.get('src'))) for x in doc.cssselect('.CacheStarImgs span img')]
        except Exception, e:
            logger.error("Could not find/parse star ratings")
            
        # Hint(s)
        hint = doc.get_element_by_id('div_hint')
        if hint == None:
            raise Exception("Hint not found.")
        coordinate.hints = self._handle_hints(hint.text_content())
        
        # Owner
        coordinate.owner = doc.cssselect('#cacheDetails span.minorCacheDetails a')[0].text_content()
            
        # Waypoints
        waypoints = []
        w = {}
        for x in doc.cssselect('#ctl00_ContentBody_Waypoints tr.BorderBottom'):
            if len(x) > 6: #chosen between 8 (data line) and 3 (description line)
                w['id'] = ''.join([x[3].text_content().strip(), x[4].text_content().strip()])
                w['name'] = x[5].text_content().strip()
                try:
                    coord = geo.try_parse_coordinate(x[6].text_content().strip())
                    w['lat'], w['lon'] = coord.lat, coord.lon 
                except Exception, e:
                    w['lat'], w['lon'] = -1, -1
            else:
                w['comment'] = x[2].text_content().strip()
                waypoints += [w]
        coordinate.set_waypoints(waypoints)
        
        # User token and Logs
        for x in doc.cssselect('script'):
            if not x.text:
                continue
            s = x.text.strip()
            if s.startswith('//<![CDATA[\r\ninitalLogs'):
                logs = s.replace('//<![CDATA[\r\ninitalLogs = ', '')
                logs = re.sub('(?s)};\s*//]]>', '}', logs)
                coordinate.set_logs(self._parse_logs_json(logs))
            # User Token is not currently in use
            #elif s.startswith('//<![CDATA[\r\nvar uvtoken'):
            #    userToken = re.sub("(?s).*userToken = '", '', s)
            #    userToken = re.sub("(?s)'.*", '', userToken)
            #    print userToken
            
        # Attributes
        try:
            coordinate.attributes = ','.join([x.get('title') for x in doc.cssselect('.CacheDetailNavigationWidget.BottomSpacing .WidgetBody img') if x.get('title') != 'blank'])
        except Exception, e:
            logger.error("Could not find/parse attributes")
            raise e
        
        # Image Handling

        images = {}
        # Called when an image was found.
        # Returns a unique filename for the given URL
        def found_image(url, title):
            # First, check if this URL is known        
            if url in images:
                # If it is, take the longest available title
                if len(images[url]['title']) < title:
                    images[url]['title'] = title
                # Return the previously calculated filename
                # Obviously, it points to the image from the same URL
                return images[url]['filename']
            
            # If this URL is encountered for the first time, calculate the filename
            ext = url.rsplit('.', 1)[1]
            if not re.match('^[a-zA-Z0-9]+$', ext):
                ext = 'img'
            filename = "%s-image%d.%s" % (coordinate.name, len(images), ext)
            images[url] = {'filename': filename, 'title': title}
            return filename
        
        # Find Images in the additional image section
        for x in doc.cssselect('a[rel=lightbox]'):
            found_image(x.get('href'), x.text_content().strip())
            
        # Search images in Description and replace them by a special placeholder
        # First, extract description...
        desc = doc.get_element_by_id('ctl00_ContentBody_LongDescription')
        if desc == None:
            raise Exception("Description could not be found!")
            
        # Next, search image elements and replace them
        for element, attribute, link, pos in desc.iterlinks():
            if element.tag == 'img':
                replace_id = found_image(link, element.get('alt') or element.get('title') or '')
                replacement = '[[img:%s]]' % replace_id
                for parent in desc.getiterator():
                    for index, child in enumerate(parent):
                        if child == element:
                            if parent[index-1].tail == None:
                                parent[index-1].tail = replacement
                            else:
                                parent[index-1].tail += replacement
                            del parent[index]
            
            
        # Download images
        for url, data in images.items():
            # Prepend local path to filename
            filename = os.path.join(self.path, data['filename'])
            logger.info("Downloading %s to %s" % (url, filename))
            
            # Download file
            try:
                f = open(filename, 'wb')
                f.write(self.downloader.get_reader(url, login = False).read())
                f.close()
            except Exception, e:
                logger.exception(e)
                logger.error("Failed to download image from URL %s" % url)
                
        # And save Images to coordinate
        images_save = dict([x['filename'], x['title']] for x in images.values())
        coordinate.set_images(images_save)
                
        # Long description
        coordinate.desc = self._extract_node_contents(desc, 'Description')
        
        # Archived status
        for log in coordinate.get_logs():
            if log['type'] == GeocacheCoordinate.LOG_TYPE_ENABLED:
                break
            elif log['type'] == GeocacheCoordinate.LOG_TYPE_DISABLED:
                coordinate.status = STATUS_DISABLED
                break
            elif log['type'] == GeocacheCoordinate.LOG_TYPE_ARCHIVED:
                coordinate.status = STATUS_ARCHIVED
                break
        else:
            coordinate.stats = GeocacheCoordinate.STATUS_NORMAL
        
        logger.debug("End parsing.")
        return coordinate
            
    # Only return the contents of a node, not the node tag itself, as text
    def _extract_node_contents(self, el, name):
        if el == None:
            raise Exception("Could not find Element: %s" % name)
        return ''.join(unicode(tostring(x, encoding='utf-8', method='html'), 'utf-8') for x in el)
        
    # Handle size string from basename of the according image
    def _handle_size(self, sizestring):
        if sizestring == 'micro':
            size = 1
        elif sizestring == 'small':
            size = 2
        elif sizestring == 'regular':
            size = 3
        elif sizestring == 'large' or sizestring == 'big':
            size = 4
        else:   
            size = 5
        return size
        
    # Convert stars3_5 to 35, stars4 to 4 (basename of image to star rating)
    def _handle_stars(self, stars):
        return int(stars[5])*10 + (int(stars[7]) if len(stars) > 6 else 0)
        
    def _handle_hints(self, hints):
        hints = HTMLManipulations._strip_html(HTMLManipulations._replace_br(hints)).strip()
        hints = self._rot13(hints)
        hints = re.sub(r'\[([^\]]+)\]', lambda match: self._rot13(match.group(0)), hints)
        return hints


BACKENDS = {
    'geocaching-com-new': {'class': NewGeocachingComCacheDownloader, 'name': 'geocaching.com (new)', 'description': 'New backend for geocaching.com'},
    'geocaching-com-old': {'class': GeocachingComCacheDownloader, 'name': 'geocaching.com (legacy)', 'description': 'Old backend for geocaching.com, not maintained'},
    }

def get(name, *args, **kwargs):
    if name in BACKENDS:
        return BACKENDS[name]['class'](*args, **kwargs)
    else:
        raise Exception("Backend not found: %s" % name)


if __name__ == '__main__':
    import sys
    import downloader
    import colorer
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG,
                    format='%(relativeCreated)6d %(levelname)10s %(name)-20s %(message)s',
                    )
    parser = NewGeocachingComCacheDownloader
    outfile = None
    if len(sys.argv) == 2: # cachedownloder.py filename
        print "Reading from file %s" % sys.argv[1]
        inp = open(sys.argv[1])
        m = GeocacheCoordinate(0, 0, 'GC1N8G6')
        a = parser(downloader.FileDownloader('dummy', 'dummy', '/tmp/cookies'), '/tmp/', True)
    elif len(sys.argv) == 3: # cachedownloader.py username password
        name, password = sys.argv[1:3]
        a = parser(downloader.FileDownloader(name, password, '/tmp/cookies', parser.login_callback, parser.check_login_callback), '/tmp/', True)

        print "Using Username %s" % name

        def pcache(c):
            print "--------------------\nName: '%s'\nTitle: '%s'\nType: %s" % (c.name, c.title, c.type)
        
        coords = a.get_geocaches((geo.Coordinate(49.3513,6.583), geo.Coordinate(49.352,6.584)))
        print "# Found %d coordinates" % len(coords)
        for x in coords:
            pcache(x)
            if x.name == 'GC1N8G6':
                if x.type != GeocacheCoordinate.TYPE_REGULAR or x.title != 'Druidenpfad':
                    print "# Wrong type or title"
                    sys.exit()
                m = x
                break
            
        else:
            print "# Didn't find my own geocache :-("
            m = GeocacheCoordinate(0, 0, 'GC1N8G6')
    elif len(sys.argv) == 4: # cachedownloader.py geocache username password
        geocache, name, password = sys.argv[1:4]
        a = parser(downloader.FileDownloader(name, password, '/tmp/cookies', GeocachingComCacheDownloader.login_callback), '/tmp/', True)

        print "Using Username %s" % name
        m = GeocacheCoordinate(0, 0, geocache)
    else:
        logger.error("I don't know what you want to do...")
        sys.exit()
    res = a.update_coordinate(m, num_logs = 20, outfile = "/tmp/geocache.tmp")
    print res
    c = res
    
    if c.owner != 'webhamster':
        logger.error("Owner doesn't match ('%s', expected webhamster)" % c.owner)
    if c.title != 'Druidenpfad':
        logger.error( "Title doesn't match ('%s', expected 'Druidenpfad')" % c.title)
    if c.get_terrain() != '3.0':
        logger.error("Terrain doesn't match (%s, expected 3.0) " % c.get_terrain())
    if c.get_difficulty() != '2.0':
        logger.error("Diff. doesn't match (%s, expected 2.0)" % c.get_difficulty())
    if len(c.desc) < 1760:
        logger.error("Length of text doesn't match (%d, expected at least %d chars)" % (len(c.desc), 1760))
    if len(c.shortdesc) < 160:
        logger.error("Length of short description doesn't match (%d, expected at least %d chars)" % (len(c.shortdesc), 200))
    if len(c.get_waypoints()) != 4:
        logger.error("Expected 4 waypoints, got %d" % len(c.get_waypoints()))
    if len(c.hints) != 83:
        logger.error("Expected 83 characters of hints, got %d" % len(c.hints))
    
    if len(c.get_logs()) < 2:
        logger.error("Expected at least 2 logs, got %d" % len(c.get_logs()))
    print u"Owner:%r (type %r)\nTitle:%r (type %r)\nTerrain:%r\nDifficulty:%r\nDescription:%r (type %r)\nShortdesc:%r (type %r)\nHints:%r (type %r)\nLogs: %r" % (c.owner, type(c.owner), c.title, type(c.title), c.get_terrain(), c.get_difficulty(), c.desc[:200], type(c.desc), c.shortdesc, type(c.shortdesc), c.hints, type(c.hints), c.get_logs()[:3])
    print c.get_waypoints()
    
