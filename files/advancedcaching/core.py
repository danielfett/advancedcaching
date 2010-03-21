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
#        Author: Daniel Fett simplecaching@fragcom.de
#

usage = r'''Here's how to use this app:

If you want to use the gui:
%(name)s --simple
    Simple User Interface, for mobile devices such as the Openmoko Freerunner
%(name)s --desktop
    Full User Interface, for desktop usage (not implemented yet)
    
If you don't like your mouse:
%(name)s set [options]
        Change the configuration.
%(name)s import [importactions] 
        Fetch geocaches from geocaching.com and write to the internal database.
%(name)s import [importactions] do [actions]
        Fetch geocaches from geocaching.com, put them into the internal database and do whatever actions are listed.
%(name)s filter [filter-options] do [actions]
        Query the internal database for geocaches and do the desired actions.
%(name)s import [importactions] filter [filter-options] do [actions]
        Import geocaches, put them into the internal database, filter the imported geocaches and run the actions. 
%(name)s sql "SELECT * FROM geocaches WHERE ... ORDER BY ... LIMIT ..." do [actions]
        Select geocaches from local database and run the actions afterwards. Additional use of the filter is also supported. To get more information, run "%(name)s sql".
options:
        --user(name) username
        --pass(word) password
                Your geocaching.com login data. 
importactions:
        --in coord1 coord2
                Fetches the index of geocaches between the given coordinates.
                These are interpreted as the corners of a rectangle. All caches
                within the rectangle are retrieved. No details are retrieved.
        --around coord radius-in-km
                Fetches the index of geocaches at the given coordinate and radius
                kilometers around it. No details are retrieved.
        --at-route coord1 coord2 radius-in-km
                Find caches along the route from coord1 to coord2. Uses OpenRouteService
                and is not available for routes outside of europe.

filter-options:
        --in coord1 coord2
        --around coord1 radius-in-km
                See import actions.
        -f|--found
        -F|--not-found
                Filter out geocaches which have (not) been found by the user.
        -w|--was-downloaded
                caches which have full detail information available
        
        -s|--size (min|max) 1..4|micro|small|regular|huge|other
                Specify a minimum or maximum size. If min/max is not given, show
                only geocaches with the given size.
        -d|--difficulty (min|max) 1.0..5.0
        -t|--terrain (min|max) 1.0..5.0
                Filter out geocaches by difficulty or terrain.
        -T|--type type,type,...
         type: virtual|regular|unknown|multi|event
                Only show geocaches of the given type(s)
        -o|--owner owner-search-string
        -n|--name name-search-string
        -i|--id id-search-string
                Search owner, name (title) or id of the geocaches.
        --new
                Caches which were downloaded in current session. Useful to
                get alerted when new caches arrive.
actions:
        --print 
                Default action, prints tab-separated list of geocaches
        --fetch-details
                Downloads Descriptions etc. for selected geocaches
        --export-html folder
                Dumps HTML pages to given folder
        --command command
                Runs command if more than one geocache has survived the filtering.
                The placeholder %%s is replaced by a shell-escaped list of geocaches.

        Not implemented yet:
        --export-gpx folder
                Dumps geocaches into separate GPX files
        --export-single-gpx file
                Dumps selected geocaches into a single GPX file
        --draw-map zoom file
                Draws one big JPEG file with the positions of the selected geocaches
        --draw-maps zoom folder [tiles]
                Draws a small JPEG image for every geocache. 
        
Preferred format for coordinates:
    'N49 44.111 E6 29.123'
    or
    'N49.123456 E6.043212'

Instead of a coordinate, you may also query geonames.com for a place name.
Just start the string with 'q:':
    q:London
    'q:Brisbane, Australia'

'''
   


from geo import Coordinate
try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json
import sys

import downloader
import geocaching
import gobject
import gpsreader
import os
import os.path
import provider
import math
import threading

#import cProfile
#import pstats


if len(sys.argv) == 1:
    print usage % ({'name': sys.argv[0]})
    exit()
        
arg = sys.argv[1].strip()
if arg == '--simple':
    import simplegui
    gui = simplegui.SimpleGui
elif arg == '--desktop':
    import biggui
    gui = biggui.BigGui
elif arg == '--hildon':
    import hildongui
    gui = hildongui.HildonGui
else:
    import cli
    gui = cli.Cli
    


        
class Standbypreventer():
    STATUS_NONE = 0
    STATUS_ALIVE = 1
    STATUS_SCREEN_ON = 2

    def __init__(self):
        self.requested_status = self.STATUS_NONE
                
    def __del__(self):
        self.__unrequest_all()
                
    def set_status(self, status):
        if status != self.requested_status:
            self.__unrequest_all()
            self.__request(status)
        
    def __unrequest_all(self):
        if self.requested_status == self.STATUS_ALIVE:
            self.__try_run('dbus-send --system --type=method_call --dest=org.shr.ophonekitd.Usage /org/shr/ophonekitd/Usage org.shr.ophonekitd.Usage.ReleaseResource string:CPU')
        elif self.requested_status == self.STATUS_SCREEN_ON:
            self.__try_run('dbus-send --system --type=method_call --dest=org.shr.ophonekitd.Usage /org/shr/ophonekitd/Usage org.shr.ophonekitd.Usage.ReleaseResource string:Display')
                        
    def __request(self, status):
        if status == self.STATUS_ALIVE:
            self.__try_run('dbus-send --system --type=method_call --dest=org.shr.ophonekitd.Usage /org/shr/ophonekitd/Usage org.shr.ophonekitd.Usage.RequestResource string:CPU')
        elif status == self.STATUS_SCREEN_ON:
            self.__try_run('dbus-send --system --type=method_call --dest=org.shr.ophonekitd.Usage /org/shr/ophonekitd/Usage org.shr.ophonekitd.Usage.RequestResource string:Display')
                        
    def __try_run(self, command):
        try:
            os.system(command)
        except Exception, e:
            print "Could not prevent Standby: %s" % e

class Core(gobject.GObject):

    __gsignals__ = {
        'map-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'cache-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        'fieldnotes-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'good-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        'no-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        }

    SETTINGS_DIR = os.path.expanduser('~/.agtl')
    CACHES_DB = os.path.join(SETTINGS_DIR, "caches.db")
    COOKIE_FILE = os.path.join(SETTINGS_DIR, "cookies.lwp")

    MAEMO_HOME = os.path.expanduser("~/MyDocs/.")
    MAPS_DIR = 'Maps/'

    DATA_DIR = os.path.expanduser('~/') if not os.path.exists(MAEMO_HOME) else MAEMO_HOME
    
    DEFAULT_SETTINGS = {
        'download_visible': True,
        'download_notfound': True,
        'download_new': True,
        'download_nothing': False,
        'download_create_index': False,
        'download_run_after': False,
        'download_run_after_string': '',
        'download_output_dir': os.path.expanduser(DATA_DIR + 'geocaches/'),
        'map_position_lat': 49.7540,
        'map_position_lon': 6.66135,
        'map_zoom': 7,
        'download_resize': True,
        'download_resize_pixel': 400,
        'options_show_name': True,
        'options_username': "",
        'options_password': "",
        'last_target_lat': 50,
        'last_target_lon': 10,
        'last_target_name': 'default',
        'download_noimages': False,
        'download_map_path': DATA_DIR + MAPS_DIR,
        'options_hide_found': False,
        'options_show_error' : True,
        'map_providers': [
            ('OpenStreetMaps', {'remote_url' : "http://128.40.168.104/mapnik/%(zoom)d/%(x)d/%(y)d.png", 'prefix' : 'OpenStreetMap I'}),
            ('OpenCycleMaps', {'remote_url' : 'http://andy.sandbox.cloudmade.com/tiles/cycle/%(zoom)d/%(x)d/%(y)d.png', 'prefix' : 'OpenCycleMap'})

        ]
    }
            
    def __init__(self, guitype, root):
        gobject.GObject.__init__(self)
        self.create_recursive(self.SETTINGS_DIR)

        dataroot = os.path.join(root, 'data')
        
        #self.standbypreventer = Standbypreventer()
        # seems to crash dbus/fso/whatever
                        
        self.__read_config()
        self.create_recursive(self.settings['download_output_dir'])
        self.create_recursive(self.settings['download_map_path'])
                
        #self.standbypreventer.set_status(Standbypreventer.STATUS_SCREEN_ON)
                
        self.downloader = downloader.FileDownloader(self.settings['options_username'], self.settings['options_password'], self.COOKIE_FILE)
                
        #pointprovider = LiveCacheProvider()
        self.pointprovider = provider.PointProvider(self.CACHES_DB, self.downloader, geocaching.GeocacheCoordinate, 'geocaches')
        #self.userpointprovider = provider.PointProvider("%s/caches.db" % self.SETTINGS_DIR, self.downloader, geo.Coordinate, 'userpoints')
        self.userpointprovider = None
        #pointprovider = PointProvider(':memory:', self.downloader)
        #reader = GpxReader(pointprovider)
        #reader.read_file('../../file.loc')
        self.gui = guitype(self, self.pointprovider, self.userpointprovider, dataroot)
        self.gui.write_settings(self.settings)

        if '--sim' in sys.argv:
            self.gps_thread = gpsreader.FakeGpsReader(self)
            gobject.timeout_add(1000, self.__read_gps)
            self.gui.set_target(gpsreader.FakeGpsReader.get_target())
        elif 'gpsprovider' in self.gui.USES:
            self.gps_thread = gpsreader.GpsReader()
            #self.gps_thread = gpsreader.FakeGpsReader(self)
            gobject.timeout_add(1000, self.__read_gps)
        elif 'locationgpsprovider' in self.gui.USES:
            self.gps_thread = gpsreader.LocationGpsReader(self.__read_gps_cb_error, self.__read_gps_cb_changed)
            gobject.idle_add(self.gps_thread.start)  
        if 'geonames' in self.gui.USES:
            import geonames
            self.geonames = geonames.Geonames(self.downloader)
        self.gui.show()

    @staticmethod
    def create_recursive(path):
        if path != '/':
            if not os.path.exists(path):
                head, tail = os.path.split(path)
                Core.create_recursive(head)
                try:
                    os.mkdir(path)
                except Exception:
                    # let others fail here.
                    pass

                
    def __del__(self):
        self.settings = self.gui.read_settings()
        self.__write_config()
                                
    def get_coord_by_name(self, query):
        return self.geonames.search(query)

    def get_route(self, c1, c2, r):
        c1 = self.geonames.find_nearest_intersection(c1)
        c2 = self.geonames.find_nearest_intersection(c2)
        route = self.geonames.find_route(c1, c2, r)
        out = []
        together = []
        TOL = 15
        MAX_TOGETHER = 20
        for i in range(len(route)):
            if len(together) == 0:
                together = [route[i]] 
            if (i < len(route) - 1):
                brg = route[i].bearing_to(route[i + 1])
                
            if len(together) < MAX_TOGETHER \
                and (i < len(route) - 1) \
                and (abs(brg - 90) < TOL
                     or abs(brg + 90) < TOL
                     or abs(brg) < TOL
                     or abs (brg - 180) < TOL) \
                and route[i].distance_to(route[i + 1]) < (r * 1000 * 2):
                    together.append(route[i + 1])
            else:
                min_lat = min([x.lat for x in together])
                min_lon = min([x.lon for x in together])
                max_lat = max([x.lat for x in together])
                max_lon = max([x.lon for x in together])
                c1 = Coordinate(min_lat, min_lon)
                c2 = Coordinate(max_lat, max_lon)
                new_c1 = c1.transform(-45, r * 1000 * math.sqrt(2))
                new_c2 = c2.transform(-45 + 180, r * 1000 * math.sqrt(2))
                out.append((new_c1, new_c2))
                together = []
        print "* Needing %d unique queries" % len(out)
        return out

    # called by gui
    def on_cache_selected(self, cache):
        self.gui.show_cache(cache)
                
    # called by gui
    def on_start_search_simple(self, text):
        #m = re.search(r'/([NS]?)\s*(\d{1,2})\.(\d{1,2})\D+(\d+)\s*([WE]?)\s*(\d{1,3})\.(\d{1,2})\D+(\d+)', text, re.I)
        #if m != None:
        self.__try_show_cache_by_search('%' + text + '%')

    # called by gui
    def set_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        self.emit('map-changed')
                
    # called by gui
    def reset_filter(self):
        self.pointprovider.set_filter()
        self.emit('map-changed')

    # called by gui
    def on_start_search_advanced(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        points = self.pointprovider.get_points_filter(location)
        self.gui.display_results_advanced(points)

    def get_points_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.push_filter()
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        return self.pointprovider.get_points_filter(location)


    # called by gui
    def on_destroy(self):
        self.settings = self.gui.read_settings()
        self.__write_config()

    # called by gui
    def on_download(self, location, sync=False):
        self.gui.set_download_progress(0.5, "Downloading...")
        cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)
        if not sync:
            def same_thread(arg1, arg2):
                gobject.idle_add(self.on_download_complete, arg1, arg2)
                return False

            cd.connect("finished-overview", same_thread)
            t = threading.Thread(target=cd.get_geocaches, args=[location])
            t.daemon = False
            t.start()
            return False
        else:
            return self.on_download_complete(None, cd.get_geocaches(location))

    # called on signal by downloading thread
    def on_download_complete(self, something, caches, sync=False):
        new_caches = []
        for c in caches:
            point_new = self.pointprovider.add_point(c)
            if point_new:
                new_caches.append(c)
        self.pointprovider.save()
        self.gui.hide_progress()
        self.emit('map-changed')
        if sync:
            return (caches, new_caches)
        else:
            return False

    # called on signal by downloading thread
    def on_already_downloading_error(self, something, error):
        self.gui.show_error(error)

    # called on signal by downloading thread
    def on_download_error(self, something, error):
        print error
        self.gui.hide_progress()
        self.gui.show_error(error)

    # called by gui
    def on_download_cache(self, cache, sync=False):
        #
        self.gui.set_download_progress(0.5, "Downloading %s..." % cache.name)

        cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)
        if not sync:
            def same_thread(arg1, arg2):
                gobject.idle_add(self.on_download_cache_complete, arg1, arg2)
                return False
            cd.connect("finished-single", same_thread)
            t = threading.Thread(target=cd.update_coordinate, args=[cache])
            t.daemon = False
            t.start()
            #t.join()
            return False
        else:
            full = cd.update_coordinate(cache)
            return full

    # called on signal by downloading thread
    def on_download_cache_complete(self, something, cache):
        self.pointprovider.add_point(cache, True)
        self.pointprovider.save()
        self.gui.hide_progress()
        self.emit('cache-changed', cache)
        return False
                
    def on_export_cache(self, cache, format, folder):
        from exporter import GpxExporter
        if (format == 'gpx'):
            exporter = GpxExporter()
        else:
            raise Exception("Format currently not supported: %s" % format)

        self.gui.set_download_progress(0.5, "Exporting %s..." % cache.name)
        try:
            exporter.export(cache, folder)
        except Exception, e:
            self.gui.show_error(e)
        finally:
            self.gui.hide_progress()
        
                
                
                
    # called by gui
    def on_download_descriptions(self, location, visibleonly=False):
        cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)
        
        #exporter = geocaching.HTMLExporter(self.downloader, self.settings['download_output_dir'])
                
        self.pointprovider.push_filter()
                        
        if self.settings['download_notfound'] or visibleonly:
            found = False
        else:
            found = None
                        
        if self.settings['download_new'] or visibleonly:
            has_details = False
        elif self.settings['download_nothing']:
            has_details = True
        else:
            has_details = None
                
                
        if self.settings['download_visible'] or visibleonly:
            self.pointprovider.set_filter(found=found, has_details=has_details, adapt_filter=True)
            caches = self.pointprovider.get_points_filter(location)
        else:
            self.pointprovider.set_filter(found=found, has_details=has_details, adapt_filter=False)
            caches = self.pointprovider.get_points_filter()

        self.pointprovider.pop_filter()

        def same_thread(arg1, arg2):
            gobject.idle_add(self.on_download_descriptions_complete, arg1, arg2)
            return False
        
        def same_thread_progress (arg1, arg2, arg3, arg4):
            gobject.idle_add(self.on_download_progress, arg1, arg2, arg3, arg4)
            return False

        cd.connect('progress', self.on_download_progress)
        cd.connect('finished-multiple', same_thread)

        t = threading.Thread(target=cd.update_coordinates, args=[caches])
        t.daemon = False
        t.start()


    # called on signal by downloading thread
    def on_download_descriptions_complete(self, something, caches):
        for c in caches:
            self.pointprovider.add_point(c, True)
        self.pointprovider.save()
        self.gui.hide_progress()
        for c in caches:
            self.emit('cache-changed', c)
        self.emit('map-changed')
        return False


    # called on signal by downloading thread
    def on_download_progress(self, something, cache_name, i, max_i):
        self.gui.set_download_progress(float(i) / float(max_i), "Downloading %s (%d of %d)..." % (cache_name, i, max_i))
        return False
    
    # called by gui
    def on_config_changed(self, new_settings):
        self.settings = new_settings
        self.downloader.update_userdata(self.settings['options_username'], self.settings['options_password'])
        self.__write_config()


    def on_notes_changed(self, cache, new_notes):
        self.pointprovider.update_field(cache, 'notes', new_notes)

    def on_fieldnotes_changed(self, cache, new_notes):
        self.pointprovider.update_field(cache, 'fieldnotes', new_notes)

    def write_fieldnote(self, cache, logas, logdate, fieldnotes):
        self.pointprovider.update_field(cache, 'logas', logas)
        self.pointprovider.update_field(cache, 'logdate', logdate)
        self.pointprovider.update_field(cache, 'fieldnotes', fieldnotes)
        self.emit('fieldnotes-changed')
        
        if logas == geocaching.GeocacheCoordinate.LOG_AS_FOUND:
            self.pointprovider.update_field(cache, 'found', '1')
            cache.found = 1

        elif logas == geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND:
            self.pointprovider.update_field(cache, 'found', '0')
            cache.found = 0
        

    def on_upload_fieldnotes(self):
        self.gui.set_download_progress(0.5, "Uploading Fieldnotes...")

        caches = self.pointprovider.get_new_fieldnotes()
        fn = geocaching.FieldnotesUploader(self.downloader)
        fn.connect("upload-error", self.on_download_error)
        
        def same_thread(arg1):
            gobject.idle_add(self.on_upload_fieldnotes_finished, arg1, caches)
            return False
            
        fn.connect('finished-uploading', same_thread)
        
        for c in caches:
            fn.add_fieldnote(c)
        t = threading.Thread(target=fn.upload)
        t.daemon = False
        t.start()
        
    def on_upload_fieldnotes_finished(self, widget, caches):
        for c in caches:
            self.pointprovider.update_field(c, 'logas', geocaching.GeocacheCoordinate.LOG_NO_LOG)
        self.gui.hide_progress()
        self.emit('fieldnotes-changed')

    def get_new_fieldnotes_count(self):
        return self.pointprovider.get_new_fieldnotes_count()

    def set_cache_calc_vars(self, cache, vars):
        self.pointprovider.update_field(cache, 'vars', vars)

    #called by gui
    def on_userdata_changed(self, username, password):
        self.downloader.update_userdata(username, password)
                
    def __read_gps(self):
        fix = self.gps_thread.get_data()
        if fix.position != None:
            self.gui.on_good_fix(fix)
            self.emit('good-fix', fix)
        else:
            self.gui.on_no_fix(fix, self.gps_thread.status)
            self.emit('no-fix', fix)
        return True

    def __read_gps_cb_error(self, control, error):
        fix = gpsreader.Fix()
        msg = gpsreader.LocationGpsReader.get_error_from_code(error)
        self.gui.on_no_fix(fix, msg)
        self.emit('no-fix', fix)
        return True

    def __read_gps_cb_changed(self, device):
        fix = gpsreader.Fix.from_tuple(device.fix, device)
        # @type fix gpsreader.Fix
        if fix.position != None:
            self.gui.on_good_fix(fix)
            self.emit('good-fix', fix)
        else:
            self.gui.on_no_fix(fix, 'No fix')
            self.emit('no-fix', fix)
        return True
                
    def __read_config(self):
        filename = os.path.join(self.SETTINGS_DIR, 'config')
        if not os.path.exists(filename):
            self.settings = self.DEFAULT_SETTINGS
            return
        f = file(filename, 'r')
        string = f.read()
        self.settings = {}
        if string != '':
            tmp_settings = json.loads(string)
            for k, v in self.DEFAULT_SETTINGS.items():
                if k in tmp_settings.keys() != None:
                    self.settings[k] = tmp_settings[k]
                else:
                    self.settings[k] = v
        else:
            self.settings = self.DEFAULT_SETTINGS
                
                
                
    def __try_show_cache_by_search(self, idstring):
        cache = self.pointprovider.find_by_string(idstring)
        if cache != None:
            self.gui.show_cache(cache)
            self.gui.set_center(cache)
            return True
        return False
                
    def __write_config(self):
        filename = os.path.join(self.SETTINGS_DIR, 'config')
        f = file(filename, 'w')
        f.write(json.dumps(self.settings, sort_keys=True, indent=4))


def determine_path ():
    """Borrowed from wxglade.py"""
    try:
        root = __file__
        if os.path.islink (root):
            root = os.path.realpath (root)
        return os.path.dirname(os.path.abspath (root))
    except:
        print "I'm sorry, but something is wrong."
        print "There is no __file__ variable. Please contact the author."
        sys.exit()

                        
def start():
    Core(gui, determine_path())

if __name__ == "__main__":
    start()

