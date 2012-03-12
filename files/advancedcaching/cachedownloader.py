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


VERSION = 22
VERSION_DATE = '2012-01-30'

import logging
logger = logging.getLogger('cachedownloader')
try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json	 
from geocaching import GeocacheCoordinate
import geo
import os
import threading
import re
import gobject
from utils import HTMLManipulations
from lxml.html import fromstring, tostring

#ugly workaround...
user_token = [None]



class CacheDownloader(gobject.GObject):
    __gsignals__ = { 'finished-overview': (gobject.SIGNAL_RUN_FIRST,\
                                 gobject.TYPE_NONE,\
                                 (gobject.TYPE_PYOBJECT,)),
                    'progress' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, int, int, )),
                    'download-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'already-downloading-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'finished-single' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'finished-multiple' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'finished-uploading': (gobject.SIGNAL_RUN_FIRST,\
                                 gobject.TYPE_NONE,\
                                 ()),
                    }

    lock = threading.Lock()

    # Path and download_images are not needed if this instance is only used to upload data.
    def __init__(self, downloader, path = None, download_images = True):
        gobject.GObject.__init__(self)
        self.downloader = downloader
        self.path = path
        self.download_images = download_images
        if path != None and not os.path.exists(path):
            try:
                os.mkdir(path)
            except:
                raise Exception("Path does not exist: %s" % path)

    # Update several coordinates
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
                
    # Update a single coordinate
    def update_coordinate(self, coordinate, num_logs = 20, outfile = None):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            return
        try:
            logger.info("Downloading %s..." % (coordinate.name))
            u = self._update_coordinate(coordinate, outfile = outfile, num_logs = num_logs)
        except Exception, e:
            logger.exception(e)
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return coordinate
        CacheDownloader.lock.release()
        self.emit('finished-single', u)
        return u

    # Retrieve geocaches in the bounding box defined by location  
    def get_geocaches(self, location):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            logger.warning("Download in progress")
            return
            
        try:
            points = self._get_overview(location)
        except Exception, e:
            logger.error(e)
            self.emit('download-error', e)
            CacheDownloader.lock.release()
            return []

        self.emit('finished-overview', points)
        CacheDownloader.lock.release()
        return points
        
    # Upload one or more fieldnotes
    def upload_fieldnotes(self, geocaches, upload_as_logs = False):
        try:
            if not upload_as_logs:
                self._upload_fieldnotes(geocaches)
            else:
                self._upload_logs(geocaches)
        except Exception, e:
            self.emit('download-error', e)
            return False
        self.emit('finished-uploading')
        return True
                
        
class GeocachingComCacheDownloader(CacheDownloader):
    
    MAX_REC_DEPTH = 3

    MAX_DOWNLOAD_NUM = 80


    CTIDS = {
        2:GeocacheCoordinate.TYPE_REGULAR,
        3:GeocacheCoordinate.TYPE_MULTI,
        4:GeocacheCoordinate.TYPE_VIRTUAL,
        6:GeocacheCoordinate.TYPE_EVENT,
        8:GeocacheCoordinate.TYPE_MYSTERY,
        11:GeocacheCoordinate.TYPE_WEBCAM,
        137:GeocacheCoordinate.TYPE_EARTH
    }
    
    def __init__(self, downloader, path = None, download_images = True):
        logger.info("Using new downloader.")
        CacheDownloader.__init__(self, downloader, path, download_images)
        self.downloader.allow_minified_answers = True


    def _get_overview(self, location, rec_depth = 0):
        #if user_token[0] == None:
        #    self._get_user_token()
        c1, c2 = location
        center = geo.Coordinate((c1.lat + c2.lat)/2, (c1.lon + c2.lon)/2)
        dist = center.distance_to(c1)/1000
        logger.debug("Distance is %f meters" % dist)
        if dist > 100:
            raise Exception("Please select a smaller part of the map!")
        url = 'http://www.geocaching.com/seek/nearest.aspx?lat=%f&lng=%f&dist=%f' % (center.lat, center.lon, dist)
        
        response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        t = unicode(response.read(), 'utf-8')
        doc = fromstring(t)
        bs = doc.cssselect('#ctl00_ContentBody_ResultsPanel .PageBuilderWidget b')
        if len(bs) == 0:
            raise Exception("No results?")
        count = int(bs[0].text_content())
        if count > self.MAX_DOWNLOAD_NUM:
            raise Exception("%d geocaches found, please select a smaller part of the map!" % count)
        ids = [x.text_content().split('|')[1].strip() for x in doc.cssselect(".SearchResultsTable .Merge span.small")]
        
        points = []
        for id in ids:
            coordinate = GeocacheCoordinate(-1, -1, id)
            self.emit("progress", "Description", len(points), len(ids))
            url = 'http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % coordinate.name
            response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)                
            result = self._parse_cache_page(response, coordinate, num_logs = 20, download_images = False)
            if result.lat != -1:
                points += [result]
            
        return points
        
    def _update_coordinate(self, coordinate, num_logs = 20, outfile = None):
        coordinate = coordinate.clone()
        
        
        url = 'http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % coordinate.name
        response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        if outfile != None:
            f = open(outfile, 'w')
            f.write(response.read())
            f.close()
            response = open(outfile)
            
        return self._parse_cache_page(response, coordinate, num_logs)

    
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
        
    def _get_user_token(self):
        page = self.downloader.get_reader('http://www.geocaching.com/map/default.aspx?lat=6&lng=9', login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        for line in page:
            if line.startswith('vxar uvtoken'):
                user_token[0] = re.sub('[^A-Z0-9]+', '', line.split('=')[-1])
                page.close()
                return
        logger.error("Using fallback for user token search!")
        try:
            page = self.downloader.get_reader('http://www.geocaching.com/map/default.aspx?lat=6&lng=9', login_callback = self.login_callback, check_login_callback = self.check_login_callback)
            t = page.read()
            user_token[0] = re.search('[A-Z0-9]{128}', t).group(0)
        except Exception, e:
            raise Exception("Website contents unexpected. Please check connection.")
    
    def _parse_cache_page(self, cache_page, coordinate, num_logs, download_images = True):
        logger.debug("Start parsing.")
        pg = cache_page.read()
        t = unicode(pg, 'utf-8')
        doc = fromstring(t)
        
        # Basename - Image name without path and extension
        def basename(url):
            return url.split('/')[-1].split('.')[0]
            
        # Title
        try:
            coordinate.title = doc.cssselect('meta[name="og:title"]')[0].get('content')
        except Exception, e:
            logger.error("Could find title!")
            raise e  
            
        # Type 
        try:
            t = int(basename(doc.cssselect('.cacheImage img')[0].get('src')).split('.')[0])
            coordinate.type = self.CTIDS[t] if t in self.CTIDS else GeocacheCoordinate.TYPE_UNKNOWN
        except Exception, e:
            logger.error("Could find type!")
            raise e    
        
        # Short Description - Long Desc. is added after the image handling (see below)
        try:
            coordinate.shortdesc = doc.get_element_by_id('ctl00_ContentBody_ShortDescription').text_content()
        except KeyError, e:
            # happend when no short description is available
            logger.info("No short description available")
            coordinate.shortdesc = ''

        # Coordinate - may have been updated by the user; therefore retrieve it again
        try:
            text = doc.get_element_by_id('uxLatLon').text_content()
            coord = geo.try_parse_coordinate(text)
            coordinate.lat, coordinate.lon = coord.lat, coord.lon
        except KeyError, e:
            raise Exception("Could not find uxLatLon")
        except Exception, e:
            logger.error("Could not parse this coordinate: %r" % coord_text.text_content())
            raise e
        
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
        try:
            hint = doc.get_element_by_id('div_hint')
            coordinate.hints = self._handle_hints(hint.text_content())
        except KeyError, e:
            logger.info("Hint not found!")
            coordinate.hints = ''
        
        # Owner
        try:
            coordinate.owner = doc.cssselect('#cacheDetails span.minorCacheDetails a')[0].text_content()
        except Exception, e:
            logger.error("Owner not found!")
            raise e
            
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
        try:
            desc = doc.get_element_by_id('ctl00_ContentBody_LongDescription')
        except Exception, e:
            logger.error("Description could not be found!")
            raise e
            
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
            
        if download_images:            
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
        coordinate.desc = self._extract_node_contents(desc)
        
        # Archived status
        for log in coordinate.get_logs():
            if log['type'] == GeocacheCoordinate.LOG_TYPE_ENABLED:
                break
            elif log['type'] == GeocacheCoordinate.LOG_TYPE_DISABLED:
                coordinate.status = GeocacheCoordinate.STATUS_DISABLED
                break
            elif log['type'] == GeocacheCoordinate.LOG_TYPE_ARCHIVED:
                coordinate.status = GeocacheCoordinate.STATUS_ARCHIVED
                break
        else:
            coordinate.stats = GeocacheCoordinate.STATUS_NORMAL
        
        logger.debug("End parsing.")
        return coordinate
        
        
    # Upload one or more fieldnotes
    def _upload_fieldnotes(self, geocaches):
        notes = []
        logger.info("Preparing fieldnotes (new downloader)...")
        for geocache in geocaches:
            if geocache.logdate == '':
                raise Exception("Illegal Date.")

            if geocache.logas == GeocacheCoordinate.LOG_AS_FOUND:
                log = "Found it"
            elif geocache.logas == GeocacheCoordinate.LOG_AS_NOTFOUND:
                log = "Didn't find it"
            elif geocache.logas == GeocacheCoordinate.LOG_AS_NOTE:
                log = "Write note"
            else:
                raise Exception("Illegal status: %s" % geocache.logas)

            text = geocache.fieldnotes.replace('"', "'")

            notes.append('%s,%sT10:00Z,%s,"%s"' % (geocache.name, geocache.logdate, log, text))
            
        logger.info("Uploading fieldnotes...")
        url = 'http://www.geocaching.com/my/uploadfieldnotes.aspx'
        
        # First, download webpage to get the correct viewstate value
        pg = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback).read()
        t = unicode(pg, 'utf-8')
        doc = fromstring(t)
        values = doc.forms[0].form_values()
        values += [('ctl00$ContentBody$btnUpload', 'Upload Field Note')]
        content = '\n'.join(notes)
        data = self.downloader.encode_multipart_formdata(values, [('ctl00$ContentBody$FieldNoteLoader', 'geocache_visits.txt', content)])

        response = self.downloader.get_reader(url, 
            data=data, 
            login_callback = self.login_callback, 
            check_login_callback = self.check_login_callback)

        res = response.read()
        t = unicode(res, 'utf-8')
        doc = fromstring(t)
        
        # There's no real success/no success message on the website. 
        # We therefore assume success, if this element is in the response
        if doc.get_element_by_id('ctl00_ContentBody_lnkFieldNotes', None) == None:
            raise Exception("Something went wrong while uploading the field notes.")
        else:
            logger.info("Finished upload!")
       
    # Upload one or more logs
    def _upload_logs(self, geocaches):
        notes = []
        logger.info("Preparing logs...")
        for geocache in geocaches:
            if geocache.logdate == '':
                raise Exception("Illegal Date.")

            if geocache.logas == GeocacheCoordinate.LOG_AS_FOUND:
                log = 2
            elif geocache.logas == GeocacheCoordinate.LOG_AS_NOTFOUND:
                log = 3
            elif geocache.logas == GeocacheCoordinate.LOG_AS_NOTE:
                log = 4
            else:
                raise Exception("Illegal status: %s" % geocache.logas)

            text = geocache.fieldnotes
            year, month, day = geocache.logdate.split('-')
            
            url = 'http://www.geocaching.com/seek/log.aspx?wp=%s' % geocache.name
            
            # First, download webpage to get the correct viewstate value
            pg = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback).read()
            t = unicode(pg, 'utf-8')
            doc = fromstring(t)
            doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$ddLogType'] = str(log)
            doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Day'] = str(int(day))
            doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Month'] = str(int(month))
            doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Year'] = str(int(year))
            doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$uxLogInfo'] = text
            values = dict(doc.forms[0].form_values())
            values['ctl00$ContentBody$LogBookPanel1$LogButton'] = doc.get_element_by_id('ctl00_ContentBody_LogBookPanel1_LogButton').get('value')
            logger.debug("Field values are %r" % values)
            response = self.downloader.get_reader(url, 
                values=values, 
                login_callback = self.login_callback, 
                check_login_callback = self.check_login_callback)

            res = response.read()
            t = unicode(res, 'utf-8')
            print t
            doc = fromstring(t)
            
            # There's no real success/no success message on the website. 
            # We therefore assume success, if this element is in the response
            if doc.get_element_by_id('ctl00_ContentBody_LogBookPanel1_ViewLogPanel', None) == None:
                raise Exception("Something went wrong while uploading the log.")
            else:
                logger.info("Finished upload!")
                 
    # Only return the contents of a node, not the node tag itself, as text
    def _extract_node_contents(self, el):
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
        
    # Convert stars3_5 to 35, stars4 to 4 (and so on, basename of image of star rating)
    def _handle_stars(self, stars):
        return int(stars[5])*10 + (int(stars[7]) if len(stars) > 6 else 0)
        
    def _handle_hints(self, hints):
        hints = HTMLManipulations._strip_html(HTMLManipulations._replace_br(hints)).strip()
        hints = HTMLManipulations._rot13(hints)
        hints = re.sub(r'\[([^\]]+)\]', lambda match: HTMLManipulations._rot13(match.group(0)), hints)
        return hints
        
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
        


BACKENDS = {
    'geocaching-com-new': {'class': GeocachingComCacheDownloader, 'name': 'geocaching.com', 'description': 'Backend for geocaching.com'},
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
    parser = GeocachingComCacheDownloader
    outfile = None
    if len(sys.argv) == 2: # cachedownloder.py filename
        print "Reading from file %s" % sys.argv[1]
        inp = open(sys.argv[1])
        m = GeocacheCoordinate(0, 0, 'GC1N8G6')
        a = parser(downloader.FileDownloader('dummy', 'dummy', '/tmp/cookies'), '/tmp/', True)
    elif len(sys.argv) == 3: # cachedownloader.py username password
        name, password = sys.argv[1:3]
        a = parser(downloader.FileDownloader(name, password, '/tmp/cookies'), '/tmp/', True)

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
        a = parser(downloader.FileDownloader(name, password, '/tmp/cookies'), '/tmp/', True)

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
    
    
