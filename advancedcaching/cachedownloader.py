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

VERSION = 35
VERSION_DATE = '2013-08-27'

import logging
logger = logging.getLogger('cachedownloader')
try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json	 
from geocaching import GeocacheCoordinate
from downloader import read_from_network
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
    __gsignals__ = {
                    'progress' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, float, float, )),
                    'download-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    'already-downloading-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
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
            u = self.update_coordinate(cache, num_logs = num_logs, progress_min = i, progress_max = i+1, progress_all = len(coordinates))
            c.append(u)
            i += 1
        return c
                
    # Update a single coordinate
    def update_coordinate(self, coordinate, num_logs = 20, progress_min = 0.0, progress_max = 1.0, progress_all = 1.0):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            return
        try:
            logger.info("Downloading %s..." % (coordinate.name))
            u = self._update_coordinate(coordinate, num_logs = num_logs, progress_min = progress_min, progress_max = progress_max, progress_all = progress_all)
        except Exception, e:
            logger.exception(e)
            CacheDownloader.lock.release()
            self.emit('download-error', e)
            return coordinate
        CacheDownloader.lock.release()
        return u

    # Retrieve geocaches in the bounding box defined by location 
    def get_overview(self, location, get_geocache_callback, skip_callback = None):
        if not CacheDownloader.lock.acquire(False):
            self.emit('already-downloading-error', Exception("There's a download in progress. Please wait."))
            logger.warning("Download in progress")
            return
            
        try:
            points = self._get_overview(location, get_geocache_callback, skip_callback = skip_callback)
        except Exception, e:
            logger.exception(e)
            self.emit('download-error', e)
            CacheDownloader.lock.release()
            return []

        CacheDownloader.lock.release()
        return points
        
    # Upload one or more fieldnotes
    def upload_fieldnotes_and_logs(self, geocaches):
        try:
            success = self._upload_fieldnotes_and_logs(geocaches)
        except Exception, e:
            logger.exception(e)
            self.emit('download-error', e)
            return []
        return success
                
        
class GeocachingComCacheDownloader(CacheDownloader):
    
    MAX_REC_DEPTH = 3

    MAX_DOWNLOAD_NUM = 800

    CTIDS = {
        2:GeocacheCoordinate.TYPE_REGULAR,
        3:GeocacheCoordinate.TYPE_MULTI,
        4:GeocacheCoordinate.TYPE_VIRTUAL,
        6:GeocacheCoordinate.TYPE_EVENT,
        8:GeocacheCoordinate.TYPE_MYSTERY,
        11:GeocacheCoordinate.TYPE_WEBCAM,
        137:GeocacheCoordinate.TYPE_EARTH
    }
    
    TRANS_FIELDNOTE_TYPE = {
        GeocacheCoordinate.LOG_AS_FOUND: "Found it",
        GeocacheCoordinate.LOG_AS_NOTFOUND: "Didn't find it",
        GeocacheCoordinate.LOG_AS_NOTE: "Write note"
    }
        
       
    TRANS_LOG_TYPE = {
        GeocacheCoordinate.LOG_AS_FOUND: 2,
        GeocacheCoordinate.LOG_AS_NOTFOUND: 3,
        GeocacheCoordinate.LOG_AS_NOTE: 4
    }
    
    # URL for log pages; fetches 10 logs by default
    LOGBOOK_URL = 'http://www.geocaching.com/seek/geocache.logbook?tkn=%s&idx=%d&num=10&decrypt=true'
    OVERVIEW_URL = 'http://www.geocaching.com/seek/nearest.aspx?lat=%f&lng=%f&dist=%f'
    PRINT_PREVIEW_URL_FULLNAME = 'http://www.geocaching.com/geocache/%s'
    SEEK_URL = "http://www.geocaching.com/seek/%s"
    DETAILS_URL = 'http://www.geocaching.com/seek/cache_details.aspx?wp=%s'
    LOGIN_URL = 'https://www.geocaching.com/login/default.aspx'
    NEAREST_URL = 'http://www.geocaching.com/seek/nearest.aspx'
    USER_TOKEN_URL = 'http://www.geocaching.com/map/default.aspx?lat=6&lng=9'
    UPLOAD_FIELDNOTES_URL = 'http://www.geocaching.com/my/uploadfieldnotes.aspx'
    UPLOAD_LOG_URL = 'http://www.geocaching.com/seek/log.aspx?wp=%s'
    
    def __init__(self, downloader, path = None, download_images = True):
        CacheDownloader.__init__(self, downloader, path, download_images)
        self.downloader.allow_minified_answers = True

    def _parse(self, text):
        try:
            t = unicode(text, 'utf-8')
            doc = fromstring(t)
        except Exception, e:
            logger.exception(e)
            from lxml.html.soupparser import fromstring as fromstring_soup
            doc = fromstring_soup(text)
        return doc

    def _get_overview(self, location, get_geocache_callback, skip_callback = None):
        c1, c2 = location
        center = geo.Coordinate((c1.lat + c2.lat)/2, (c1.lon + c2.lon)/2)
        dist = (center.distance_to(c1)/1000)/2
        logger.debug("Distance is %f meters" % dist)
        if dist > 100:
            raise Exception("Please select a smaller part of the map!")
        url = self.OVERVIEW_URL % (center.lat, center.lon, dist)
        
        self.emit("progress", "Fetching list", 0, 1)
        response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
        if response == None:
            logger.warning("Got None from downloader")

        cont = True
        wpts = []
        page_last = 0 # Stores the "old" value of the page counter; If it doesn't increment, abort!
        while cont:
            # Count the number of results and pages
            if response == None:
                logger.warning("_get_overview: Error: response is None:"+str(e))
            else:
                text = read_from_network(response)
                if text != None:
                    doc = self._parse(text)
                    bs = doc.cssselect('#ctl00_ContentBody_ResultsPanel .PageBuilderWidget b')
                    if len(bs) == 0:
                        raise Exception("There are no geocaches in this area.")
                    count = int(bs[0].text_content())
                    page_current = int(bs[1].text_content())
                    if page_current == page_last:
                        raise Exception("Current page has the same number as the last page; aborting!")
                        break
                    page_last = page_current
                    page_max = int(bs[2].text_content())
                    logger.info("We are at page %d of %d, total %d geocaches" % (page_current, page_max, count))
                    if count > self.MAX_DOWNLOAD_NUM:
                        raise Exception("%d geocaches found, please select a smaller part of the map!" % count)
                
                
                    # Extract waypoint information from the page
                    w = [(
                        # Get the GUID from the link
                        # Actually, this is not the GUID anymore...
                        x.getparent().getchildren()[0].get('href').split('/')[-1],
                        # See whether this cache was found or not
                        'TertiaryRow' in x.getparent().getparent().get('class'),
                        # Get the GCID from the text
                        x.text_content().split('|')[1].strip()
                        ) for x in doc.cssselect(".SearchResultsTable .Merge .small")]
                    wpts += w

                
            cont = False  
            # There are more pages...
            if page_current < page_max:
                from urllib import urlencode
                doc.forms[0].fields['__EVENTTARGET'] = 'ctl00$ContentBody$pgrTop$ctl08'
                # Quick hack. Nicer solution would be to remove the element.
                v = [x for x in doc.forms[0].form_values() if x[0] != 'ctl00$ContentBody$chkAll']
                values = urlencode(v)
                action = self.SEEK_URL % doc.forms[0].action
                logger.info("Retrieving next page!")
                self.emit("progress", "Fetching list (%d of %d)" % (page_current + 1, page_max), page_current, page_max)
                response = self.downloader.get_reader(action, data=('application/x-www-form-urlencoded', values), login_callback = self.login_callback, check_login_callback = self.check_login_callback)
                
                cont = True
        
        # Now, split wpts into three groups:
        points_that_need_downloading = [] # Geocaches that need to be downloaded
        points_finished = []              # Geocaches that only need to be updated in the database
        # and Geocaches which don't need any update (they will be removed)
        for fullname, found, id in wpts:
            # Check if geocache exists in DB
            coordinate = get_geocache_callback(id)
            
            if coordinate == None:
                # If the coordinate was not in the DB
                if skip_callback != None and skip_callback(None, found):
                    # Skip it, for example when it is marked as found
                    logger.info("Skipping %s. It was not in the DB." % id)
                    continue
                # Else always download
                points_that_need_downloading.append((fullname, found, id, GeocacheCoordinate(-1, -1, id)))
                logger.info("Downloading %s. It was not in the DB." % id)
                continue
            
            if coordinate.found != found:
                coordinate.found = found
                needs_update = True
            else:
                needs_update = False
                
            if skip_callback != None and skip_callback(coordinate, found):
                if not needs_update:
                    logger.info("Skipping %s. It was in the DB, but its found status was correct." % id)
                    continue
                # If the coordinate is to be skipped, put it into points_finished anyway
                # because the found status was updated
                points_finished.append(coordinate)
                logger.info("Updating %s. It was in the DB, but its found status was not correct." % id)
                continue
            logger.info("Downloading %s. It was in the DB, but it was not to be skipped." % id)
            points_that_need_downloading.append((fullname, found, id, coordinate))
                    
        
        # Download the geocaches using the print preview 

        i = 0
        for fullname, found, id, coordinate in points_that_need_downloading:
            i += 1
            coordinate.found = found
            logger.debug("Coordinate %s, found=%r" % (coordinate.name, found))
            self.emit("progress", "Geocache %d of %d" % (i, len(points_that_need_downloading)), i, len(points_that_need_downloading))
            logger.info("Downloading %s..." % id)
            url = self.PRINT_PREVIEW_URL_FULLNAME % fullname
            response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)                
            result = self.__parse_cache_page(response, coordinate, 10, progress_min = i, progress_max = i+1, progress_all = len(points_that_need_downloading), download_images = False)
            if result != None and result.lat != -1:
                points_finished.append(result)
                
        return points_finished
        
    def _update_coordinate(self, coordinate, num_logs = 20, progress_min = 0.0, progress_max = 1.0, progress_all = 1.0):
        coordinate = coordinate.clone()
        
        logger.debug("_update_coordinate, pmin = %f, pmax = %f." % (progress_min, progress_max))
        
        # Progress should be displayed in the range between progress_min and progress_max. 
        self.emit('progress', "Downloading %s" % coordinate.name, progress_min, progress_all)
        
        url = self.DETAILS_URL % coordinate.name
        response = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
            
        return self.__parse_cache_page(response, coordinate, num_logs, progress_min = progress_min, progress_max = progress_max, progress_all = progress_all)

    
    @staticmethod
    def check_login_callback(downloader):
        login_request = downloader.get_reader(GeocachingComCacheDownloader.NEAREST_URL, login = False)
        page = read_from_network(login_request)
        if page == None:
            return False

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
        values = {'ctl00$ContentBody$tbUsername': username,
            'ctl00$ContentBody$tbPassword': password,
            'ctl00$ContentBody$cbRememberMe': 'on',
            'ctl00$ContentBody$btnSignIn': 'Login',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': ''
        }
        request = downloader.get_reader(GeocachingComCacheDownloader.LOGIN_URL, values, login = False)
        page = read_from_network(request)
        if page == None:
            return False

        t = unicode(page, 'utf-8')
        doc = fromstring(t)
        
        if doc.get_element_by_id('ctl00_liNavProfile', None) == None:
            raise Exception("Wrong username or password!")
        elif doc.get_element_by_id('ctl00_liNavJoin', None) == None:
            logger.info("Great success.")
            return True
        raise Exception("Name/Password MAY be correct, but I encountered unexpected data while logging in.")
        
    def __parse_cache_page(self, cache_page, coordinate, num_logs, download_images = True, progress_min = 0.0, progress_max = 1.0, progress_all = 1.0):
        logger.debug("Start parsing, pmin = %f, pmax = %f." % (progress_min, progress_max))
        if cache_page == None:
            logger.warning("Can't parse this cache, it is None")
            return
        pg = read_from_network(cache_page)
        if pg == None:
            return False

        t = unicode(pg, 'utf-8')
        doc = fromstring(t)
                
        # Basename - Image name without path and extension
        def basename(url):
            return url.split('/')[-1].split('.')[0]

        #check for premium-only cache
        try:
            doc.get_element_by_id('ctl00_ContentBody_basicMemberMsg') #Premium user will not get this
            logger.info("PREMIUM ONLY cache (and not premium account), skip it totally")
            return
        except Exception, e:
            None
            #print "normal cache, can continue"


        # Title
        try:
            coordinate.title = doc.cssselect('meta[name="og:title"]')[0].get('content')
        except Exception, e:
            logger.error("Could not find title - cache is probably unpublished!")
            raise Exception("Geocache not found.")
            
        # Type 
        try:
            t = int(basename(doc.cssselect('.cacheImage img')[0].get('src')).split('.')[0])
            coordinate.type = self.CTIDS[t] if t in self.CTIDS else GeocacheCoordinate.TYPE_UNKNOWN
        except Exception, e:
            logger.error("Could not find type!")
            raise e    
            
        # Website
        try:
            coordinate.websitelink = doc.get_element_by_id('ctl00_ContentBody_uxCacheUrl').get('href')
        except KeyError, e:
            logger.info("No website link found, skipping.")
            coordinate.websitelink = ''
        
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
            logger.error("Could not parse this coordinate: %r" % text)
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
            coordinate.difficulty, coordinate.terrain = [self._handle_stars(basename(x.get('src'))) for x in doc.cssselect('.CacheStarLabels img')]
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
            coordinate.owner = doc.cssselect('#cacheDetails .minorCacheDetails a')[0].text_content()
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
                w = {}
        coordinate.set_waypoints(waypoints)
        
        # User token and Logs
        userToken = ''
        new_set_of_logs = []
        for x in doc.cssselect('script'):
            if not x.text:
                continue
            s = x.text.strip()
            if not s.startswith('//<![CDATA['):
                continue
            for line in s.split('\n'):
                if line.startswith('userToken'):
                    userToken = re.sub("(?s).*userToken = '", '', line)
                    userToken = re.sub("(?s)'.*", '', userToken)
                    logger.debug("userToken: %s" % userToken)
                    break
                if line.startswith('initialLogs'):
                    new_set_of_logs, dummy = self._parse_logs_json(line[13:])

        if userToken == '':
            logger.error('User token is empty before retrieving logs!')
                        
        
        self.emit('progress', 'Fetching logs', progress_min + 0.2 * (progress_max - progress_min), progress_all)
        
        #Ask first page of logs. And same time number of pages
        logs = self.downloader.get_reader(
            self.LOGBOOK_URL % (userToken, 1),
            login_callback = self.login_callback, 
            check_login_callback = self.check_login_callback)
        new_set_of_logs.extend(self._parse_logs_json(read_from_network(logs)))

        #First page is already handled, so counter starts from 2
        counter = 2
        while len(new_set_of_logs) < num_logs:
            # We want progress to be between 0.3 and 0.5 times of our own range.
            # Our own range is progress_min -> progress_max
            # Log range is 0.3 to 0.5
            progress_internal = 0.3 + (float(len(new_set_of_logs))/float(num_logs)) * 0.2
            logger.debug("- Progress internal is %f" % progress_internal)
            logger.debug("- Progress is %f of %f" % (progress_min + progress_internal * (progress_max - progress_min), progress_all))
            self.emit('progress', "Logs (%d)" % counter, progress_min + progress_internal * (progress_max - progress_min), progress_all)
            logs = self.downloader.get_reader(
                self.LOGBOOK_URL % (userToken, counter),
                login_callback = self.login_callback, 
                check_login_callback = self.check_login_callback)
            new_set_of_logs.extend(self._parse_logs_json(read_from_network(logs)))

            counter += 1
            
            # Bail out if we don't download any logs.
            if counter > num_logs:
                logger.error("Downloading logs did not really work.")
                logger.warning("cache=" +str(coordinate.serialize()))
                break

        coordinate.set_logs(new_set_of_logs)

        # Attributes
        if not coordinate.attributes:
            logger.warn("No attributes set for this geocache yet.")
            try:
                attr_xml = doc.cssselect('.CacheDetailNavigationWidget.TopSpacing.BottomSpacing .WidgetBody img')
                attributes = self._parse_attributes_from_doc(attr_xml)
                coordinate.clear_attributes()
                for x in attributes: 
                    coordinate.add_attribute(x)
            except IndexError:
                # There are no attributes
                logger.info("Attributes not found!")
            except Exception, e:
                logger.error("Could not find/parse attributes")
                raise e
        
        # Image Handling

        images = {}
        # Called when an image was found.
        # Returns a unique filename for the given URL
        def found_image(url, title):
            # First, only use the large geocaching.com images
            if url.startswith('http://img.geocaching.com/cache/') and not url.startswith('http://img.geocaching.com/cache/large/'):
                url = url.replace('http://img.geocaching.com/cache/', 'http://img.geocaching.com/cache/large/')
            
            # Then, check if this URL is known        
            if url in images:
                # If it is, take the longest available title
                if len(images[url]['title']) < title:
                    images[url]['title'] = title
                # Return the previously calculated filename
                # Obviously, it points to the image from the same URL
                return images[url]['filename']
            
            # If this URL is encountered for the first time, calculate the filename
            if '.' in url: #this is the normal case (filename has dot)
                ext = url.rsplit('.', 1)[1]    #this will be out of range if no dot in filename
            else:   #there are filenames without dot and extension
                ext = "img"
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
                if attribute is not 'src': #only handle src-fields, it could be e.g. ImageMap
                    break

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
            
        counter = 0
        if download_images:            
            # Download images
            num = len(images)
            for url, data in images.items():
                # We want progress to be between 0.5 and 1.0 times of our own range.
                # Our own range is progress_min -> progress_max
                # Log range is 0.5 to 1.0
                progress_internal = 0.5 + (counter/float(num)) * 0.5
                self.emit('progress', "Images (%d/%d)" % (counter + 1, num), progress_min + progress_internal * (progress_max - progress_min), progress_all)
                # Prepend local path to filename
                filename = os.path.join(self.path, data['filename'])
                logger.info("Downloading %s to %s" % (url, filename))
                
                # Download file
                #Some images (e.g. smileys) have path without domain name
                if url.startswith("/"):
                    url = "http://www.geocaching.com"+url  #Needs rethinking when agtl supports different domains/services.

                #some images (e.g. attribute-icons) have path without domain name
                if url.startswith("../"):
                    url = "http://www.geocaching.com"+url[2:]  #Needs rethinking when agtl supports different domains/services.

                try:
                    f = open(filename, 'wb')
                    f.write(read_from_network(self.downloader.get_reader(url, login = False)))
                    f.close()
                except Exception, e:
                    #logger.exception(e)
                    logger.error("Failed to download image from URL '%s': '%s'" % (url,e))
                counter += 1
                
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
            
        # And finally, set last updated time
        coordinate.touch_updated()
        
        logger.debug("End parsing.")
        return coordinate
        
    # This parses the print preview of a geocache
    # It currently omits images, waypoints and logs.
    def __parse_cache_page_print(self, cache_page, coordinate, num_logs):
        logger.debug("Start parsing.")
        pg = read_from_network(cache_page)
        if pg == None:
           return None

        t = unicode(pg, 'utf-8')
        doc = fromstring(t)
        
        # Basename - Image name without path and extension
        def basename(url):
            return url.split('/')[-1].split('.')[0]
            
        # Title, ID and Owner
        try:
            text = doc.cssselect('title')[0].text_content()
            part1, part2 = text.split(') ', 1)
            coordinate.id = part1[1:]
            coordinate.title, coordinate.owner = part2.rsplit(' by ', 1)
        except Exception, e:
            logger.error("Could not find title, id or owner!")
            logger.exception(e)
            raise e  
            
        # Type 
        #try:
        t = int(basename(doc.cssselect('#Content h2 img')[0].get('src')).split('.')[0])
        coordinate.type = self.CTIDS[t] if t in self.CTIDS else GeocacheCoordinate.TYPE_UNKNOWN
        #except Exception, e:
        #    logger.error("Could not find type - probably premium cache!")
        #    return None
        
        # Short Description - Long Desc. is added after the image handling (see below)
        try:
            coordinate.shortdesc = doc.cssselect('#Content .sortables .item-content')[1].text_content().strip()
        except KeyError, e:
            # happend when no short description is available
            logger.info("No short description available")
            logger.exception(e)
            coordinate.shortdesc = ''

        # Coordinate - may have been updated by the user; therefore retrieve it again
        try:
            text = doc.cssselect('.LatLong.Meta')[0].text_content()
            coord = geo.try_parse_coordinate(text)
            coordinate.lat, coordinate.lon = coord.lat, coord.lon
        except KeyError, e:
            logger.exception(e)
            raise Exception("Could not find uxLatLon")
        except Exception, e:
            logger.error("Could not parse this coordinate: %r" % text)
            logger.exception(e)
            raise e
        
        # Size 
        try:
            # src is URL to image of the cache size
            # src.split('/')[-1].split('.')[0] is the basename minus extension
            coordinate.size = self._handle_size(basename(doc.cssselect('.Third .Meta img')[0].get('src')))
        except Exception, e:
            logger.error("Could not find/parse size string")
            logger.exception(e)
            raise e
            
        # Terrain/Difficulty
        try:
            coordinate.difficulty, coordinate.terrain = [self._handle_stars(basename(x.get('src'))) for x in doc.cssselect('.Third .Meta img')[1:]]
        except Exception, e:
            logger.error("Could not find/parse star ratings")
            logger.exception(e)
            
        # Hint(s)
        try:
            hint = self._extract_node_contents(doc.cssselect('#uxEncryptedHint')[0])
            coordinate.hints = self._handle_hints(hint, encrypted = False)
        except IndexError, e:
            logger.info("Hint not found!")
            coordinate.hints = ''
            
        # Attributes
        try:
            attr_xml = doc.cssselect('#Content .sortables .item-content')[5].cssselect('img')
            attributes = self._parse_attributes_from_doc(attr_xml)
            logger.debug("Found the following attributes: %r" % attributes)
            coordinate.clear_attributes()
            for x in attributes: 
                coordinate.add_attribute(x)
        except IndexError:
            # There are no attributes
            logger.info("Attributes not found!")
        except Exception, e:
            logger.exception(e)
            logger.error("Could not find/parse attributes")
            raise e
                

        # Extract description...
        try:
            desc = doc.cssselect('#Content .sortables .item-content')[2]
            coordinate.desc = self._extract_node_contents(desc).strip()
        except Exception, e:
            logger.error("Description could not be found!")
            logger.exception(e)
            raise e

        # Waypoints
        waypoints = []
        w = {}
        for x in doc.cssselect('#Content .sortables .item-content tr.BorderBottom'):
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
                w = {}
        coordinate.set_waypoints(waypoints)

        # And finally, set last updated time
        coordinate.touch_updated()

        logger.debug("End parsing.")
        return coordinate
        
    

    def _parse_attributes_from_doc(self, imgs):
        """
        Takes a document tree representing the attribute images as input and parses the attributes. Downloads any attribute images which are not in the file system yet.
        
        """
        attributes = []
        for x in imgs:
            if x.get('title') == 'blank':
                continue

            attrib = x.get('src')[19:] #strip text '/images/attributes/'
            logger.debug("attrib is %r, self.path is %r" % (attrib, self.path))
            # Prepend local path to filename, and check if we have it already
            filename = os.path.join(self.path, attrib)
            if os.path.isfile(filename):
                logger.info("%s exists already, don't reload " % filename)
            else:
                # Download file
                url="http://www.geocaching.com/images/attributes/%s" % attrib
                logger.info("Downloading %s to %s" % (url, filename))

                try:
                    f = open(filename, 'wb')
                    f.write(read_from_network(self.downloader.get_reader(url, login = False)))
                    f.close()
                except Exception, e:
                    logger.exception(e)
                    logger.error("Failed to download image from URL %s" % url)

            # store filename without path to the comma separated string
            attributes.append(attrib)
        return attributes
        
    def _upload_fieldnotes_and_logs(self, geocaches):
        '''
        Upload all fieldnotes and logs of the geocaches given in the first argument and return a list of geocaches, for which uploading worked.
        
        '''
        upload_fieldnotes = []
        upload_logs = []
        for geocache in geocaches:
            if geocache.upload_as == GeocacheCoordinate.UPLOAD_AS_LOG:
                upload_logs.append(geocache)
            else:
                upload_fieldnotes.append(geocache)
                
                
        logger.info("Will try to upload %d fieldnotes and %d logs." % (len(upload_fieldnotes), len(upload_logs)))
        
        success_fieldnotes = self.__upload_fieldnotes(upload_fieldnotes)
        success_logs = self.__upload_logs(upload_logs)
        
        before = len(geocaches)
        after = len(success_fieldnotes) + len(success_logs)
        
        if after == 0 and before != 0:
            self.emit("download-error", Exception("Uploading of fieldnotes and logs failed."))
        elif after < before:
            self.emit("download-error", Exception("Uploading failed for some fieldnotes or logs."))
        
        return success_fieldnotes + success_logs
                        
        
    # Upload one or more fieldnotes
    def __upload_fieldnotes(self, geocaches):
        notes = []
        if len(geocaches) == 0:
            return []
        logger.info("Preparing fieldnotes (new downloader)...")
        try:
            for geocache in geocaches:
                name, logdate, logtype, fieldnotes = geocache.name, geocache.logdate, geocache.logas, geocache.fieldnotes
                if logdate == '':
                    raise Exception("Illegal Date.")
                
                try:
                    logtype_trans = self.TRANS_FIELDNOTE_TYPE[logtype]
                except KeyError, e:
                    raise Exception("Illegal status: %s" % logtype)

                text = fieldnotes.replace('"', "'")

                notes.append('%s,%sT10:00Z,%s,"%s"' % (name, logdate, logtype_trans, text))
                
            logger.info("Uploading fieldnotes...")
            
            self.emit('progress', "Uploading Fieldnotes (Step 1 of 2)", 0, 2)
            
            # First, download webpage to get the correct viewstate value
            cache_page = self.downloader.get_reader(self.UPLOAD_FIELDNOTES_URL, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
            pg = read_from_network(cache_page)
            if pg == None:
                logger.error("network error")
                return
            t = unicode(pg, 'utf-8')
            doc = fromstring(t)
            # Sometimes this field is not available
            if 'ctl00$ContentBody$chkSuppressDate' in doc.forms[0].fields:
                doc.forms[0].fields['ctl00$ContentBody$chkSuppressDate'] = ''
            values = doc.forms[0].form_values()
            values += [('ctl00$ContentBody$btnUpload', 'Upload Field Note')]
            content = '\r\n'.join(notes).encode("UTF-16")
            
            data = self.downloader.encode_multipart_formdata(values, [('ctl00$ContentBody$FieldNoteLoader', 'geocache_visits.txt', content)])
            self.emit('progress', "Uploading Fieldnotes (Step 2 of 2)", 1, 2)
            response = self.downloader.get_reader(self.UPLOAD_FIELDNOTES_URL, 
                data = data, 
                login_callback = self.login_callback, 
                check_login_callback = self.check_login_callback)

            res = read_from_network(response)
            if res == None:
                logger.error("network error")
                return

            t = unicode(res, 'utf-8')
            doc = fromstring(t)
            
            # There's no real success/no success message on the website. 
            # We therefore assume success, if this element is in the response
            if doc.get_element_by_id('ctl00_ContentBody_lnkFieldNotes', None) == None:
                raise Exception("Something went wrong while uploading the field notes.")
            else:
                logger.info("Finished upload!")
            return geocaches
        except Exception, e:
            logger.exception(e)
        
            
       
    # Upload one or more logs
    def __upload_logs(self, geocaches):
        if len(geocaches) == 0:
            return []
        success = []
        logger.info("Preparing logs...")
        i = 0
        for geocache in geocaches:
            try:
                name, logdate, logtype, fieldnotes = geocache.name, geocache.logdate, geocache.logas, geocache.fieldnotes
                
                if logdate == '':
                    raise Exception("Illegal Date.")

                try:
                    logtype_trans = self.TRANS_LOG_TYPE[logtype]
                except KeyError, e:
                    raise Exception("Illegal status: %s" % logtype)
                
                year, month, day = logdate.split('-')
                
                url = self.UPLOAD_LOG_URL % name
                
                # First, download webpage to get the correct viewstate value
                self.emit('progress', "Uploading Logs (%d of %d)..." % (i, len(geocaches)), i + 1, len(geocaches))
                cache_page = self.downloader.get_reader(url, login_callback = self.login_callback, check_login_callback = self.check_login_callback)
                pg = read_from_network(cache_page)
                if pg == None:
                    return success #it is list of successfully
                t = unicode(pg, 'utf-8')
                doc = fromstring(t)
                doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$ddLogType'] = str(logtype_trans)
                doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Day'] = str(int(day))
                doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Month'] = str(int(month))
                doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$DateTimeLogged$Year'] = str(int(year))
                doc.forms[0].fields['ctl00$ContentBody$LogBookPanel1$uxLogInfo'] = fieldnotes
                values = dict(doc.forms[0].form_values())
                values['ctl00$ContentBody$LogBookPanel1$LogButton'] = doc.get_element_by_id('ctl00_ContentBody_LogBookPanel1_LogButton').get('value')
                
                # Now, manually re-encoding the text
                # Normally, get_reader (below) expects unicode-encoded values, but lxml (above) does not allow that.
                values['ctl00$ContentBody$LogBookPanel1$uxLogInfo'] = values['ctl00$ContentBody$LogBookPanel1$uxLogInfo'].encode('utf-8')
                
                response = self.downloader.get_reader(url, 
                    values = values, 
                    login_callback = self.login_callback, 
                    check_login_callback = self.check_login_callback)

                res = read_from_network(response)
                if res == None:
                    return success #it is list of successfully
                t = unicode(res, 'utf-8')
                doc = fromstring(t)
                
                # There's no real success/no success message on the website. 
                # We therefore assume success, if this element is in the response
                if doc.get_element_by_id('ctl00_ContentBody_LogBookPanel1_ViewLogPanel', None) == None:
                    raise Exception("Something went wrong while uploading the log.")
                else:
                    logger.info("Finished upload!")
                i += 1
                success.append(geocache)
            except Exception, e:
                logger.exception(e)
        return success
            
                 
    # Only return the contents of a node, not the node tag itself, as text
    def _extract_node_contents(self, el):
        # Alternative solution for this would be:
        #element = unicode(tostring(el, encoding='utf-8', method='html'), 'utf-8')
        #out = re.sub('^<[^>]+>', '', element)
        #out = re.sub('<[^>]+>$', '', out)
        #return out
        return (el.text if el.text != None else '') + ''.join(unicode(tostring(x, encoding='utf-8', method='html'), 'utf-8') for x in el)
        
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
        
    def _handle_hints(self, hints, encrypted = True):
        hints = HTMLManipulations._strip_html(HTMLManipulations._replace_br(hints)).strip()
        if encrypted:
            hints = HTMLManipulations._rot13(hints)
            hints = re.sub(r'\[([^\]]+)\]', lambda match: HTMLManipulations._rot13(match.group(0)), hints)
        return hints
        
    def _parse_logs_json(self, logs):
        logger.debug("Start json logs parsing")
        #print logs
        try:
            r = json.loads(logs)
        except Exception, e:
            logger.exception('Could not json-parse logs!')
            raise e
        if not 'status' in r or r['status'] != 'success':
            logger.error('Could not read logs, status is "%s"' % r['status'])
        data = r['data']
        output = []
        for l in data:
            tpe = l['LogType']
            icon = l['LogTypeImage']
            date = l['Visited']
            finder = "%s (found %s)" % (l['UserName'], l['GeocacheFindCount'])
            text = HTMLManipulations._decode_htmlentities(HTMLManipulations._strip_html(HTMLManipulations._replace_br(l['LogText'])))
            output.append(dict(type=tpe, typeicon=icon, date=date, finder=finder, text=text))
        logger.debug("Read %d log entries" % len(output))
        
        total_page = r['pageInfo']['totalPages']
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
    if len(sys.argv) != 3: 
        logger.error("Please provide username and password on the command line.")
        sys.exit(2)

    name, password = sys.argv[1:3]
    a = parser(downloader.FileDownloader(name, password, '/tmp/cookies'), '/tmp/', True)

    logger.info("Using Username %s" % name)

    def pcache(c):
        logger.info("--------------------\nName: '%s'\nTitle: '%s'\nType: %s" % (c.name, c.title, c.type))
    
    def dummy_callback(x):
        return None
    coords = a.get_overview((geo.Coordinate(49.3513,6.583), geo.Coordinate(49.352,6.584)), dummy_callback)
    logger.info("Found %d coordinates" % len(coords))
    for x in coords:
        pcache(x)
        if x.name == 'GC1N8G6':
            if x.type != GeocacheCoordinate.TYPE_REGULAR or x.title != 'Druidenpfad':
                sys.exit("Wrong type or title (Type is %d, Title is '%s')" % (x.type, x.title))
            m = x
            break
        
    else:
        logger.error("Didn't find my own geocache :-(")
        sys.exit(-1)
        
    res = a.update_coordinate(m, num_logs = 20)

    c = res
    
    errors = 0
    if c.owner != 'webhamster':
        logger.error("Owner doesn't match ('%s', expected webhamster)" % c.owner)
        errors += 1
    if c.title != 'Druidenpfad':
        logger.error( "Title doesn't match ('%s', expected 'Druidenpfad')" % c.title)
        errors += 1
    if c.get_terrain() != '3.0':
        logger.error("Terrain doesn't match (%s, expected 3.0) " % c.get_terrain())
        errors += 1
    if c.get_difficulty() != '2.0':
        logger.error("Diff. doesn't match (%s, expected 2.0)" % c.get_difficulty())
        errors += 1
    if len(c.desc) < 1760:
        logger.error("Length of text doesn't match (%d, expected at least %d chars)" % (len(c.desc), 1760))
        errors += 1
    if len(c.shortdesc) < 160:
        logger.error("Length of short description doesn't match (%d, expected at least %d chars)" % (len(c.shortdesc), 200))
        errors += 1
    if len(c.get_waypoints()) != 4:
        logger.error("Expected 4 waypoints, got %d" % len(c.get_waypoints()))
        errors += 1
    if len(c.hints) < 80 or len(c.hints) > 90:
        # Hint text length depends on whether HTML is contained, how linebreaks are converted, etc.
        logger.error("Expected 80-90 characters of hints, got %d" % len(c.hints))
        errors += 1
    if len(c.attributes) < 20:
        logger.error("Expected 20 characters of attributes, got %d: '%s'" % (len(c.attributes), c.attributes))
        errors += 1
        
    link = 'http://wandern-plus.de/saarland/rehlingen-siersburg/weg_2_info.html'
    if c.websitelink != link:
        logger.error("Expected website link to be '%s', found '%s'." % (link, c.websitelink))
        errors += 1
    
    if len(c.get_logs()) < 2:
        logger.error("Expected at least 2 logs, got %d" % len(c.get_logs()))
        errors += 1
        
    logger.info(u"Owner:%r (type %r)\nTitle:%r (type %r)\nTerrain:%r\nDifficulty:%r\nDescription:%r (type %r)\nShortdesc:%r (type %r)\nHints:%r (type %r)\nLogs: %r\nAttributes: %r" % (c.owner, type(c.owner), c.title, type(c.title), c.get_terrain(), c.get_difficulty(), c.desc[:200], type(c.desc), c.shortdesc, type(c.shortdesc), c.hints, type(c.hints), c.get_logs()[:3], c.attributes))
    logger.info(c.get_waypoints())
    
    if errors > 0:
        sys.exit("Found %d error(s)." % errors)
        
    logger.info("Seems to be okay.")
    sys.exit(0)
    
    
