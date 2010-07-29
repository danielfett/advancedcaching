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

from __future__ import with_statement

VERSION = "0.7.0.2"
   


from geo import Coordinate
try:
    from json import loads, dumps
except (ImportError, AttributeError):
    from simplejson import loads, dumps
from sys import argv, exit
from sys import path as sys_path

import downloader
import geocaching
import gobject
import gpsreader
from os import path, mkdir, extsep, remove, walk
import provider
from threading import Thread
import cachedownloader
import fieldnotesuploader
from actors.tts import TTS
#from actors.notify import Notify
import logging

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s\t%(levelname)s\t%(name)-15s\t %(message)s',
                    )

if len(argv) == 1:
    import cli
    print cli.usage % ({'name': argv[0]})
    exit()

if '-v' in argv:
    logging.getLogger('').setLevel(logging.DEBUG)
    logging.debug("Set log level to DEBUG")

arg = argv[1].strip()
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

    
class Core(gobject.GObject):

    __gsignals__ = {
        'map-marks-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'cache-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        'fieldnotes-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'good-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'no-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'target-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'settings-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,)),
        'save-settings': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        }

    SETTINGS_DIR = path.expanduser('~/.agtl')
    CACHES_DB = path.join(SETTINGS_DIR, "caches.db")
    COOKIE_FILE = path.join(SETTINGS_DIR, "cookies.lwp")
    UPDATE_DIR = path.join(SETTINGS_DIR, 'updates')

    MAEMO_HOME = path.expanduser("~/MyDocs/.")
    MAPS_DIR = 'Maps/'

    DATA_DIR = path.expanduser('~/') if not path.exists(MAEMO_HOME) else MAEMO_HOME

    UPDATE_MODULES = [cachedownloader, fieldnotesuploader]
    
    DEFAULT_SETTINGS = {
        'download_visible': True,
        'download_notfound': True,
        'download_new': True,
        'download_nothing': False,
        'download_create_index': False,
        'download_run_after': False,
        'download_run_after_string': '',
        'download_output_dir': path.expanduser(DATA_DIR + 'geocaches/'),
        'map_position_lat': 49.7540,
        'map_position_lon': 6.66135,
        'map_follow_position': True,
        'map_zoom': 7,
        'download_resize': True,
        'download_resize_pixel': 400,
        'options_show_name': True,
        'options_username': "",
        'options_password': "",
        'last_target_lat': 50,
        'last_target_lon': 10,
        'last_target_name': 'default',
        'last_selected_geocache': '',
        'download_noimages': False,
        'download_map_path': DATA_DIR + MAPS_DIR,
        'options_hide_found': False,
        'options_show_error': True,
        'options_show_html_description': False,
        'map_providers': [
            ('OpenStreetMaps', {'remote_url': "http://128.40.168.104/mapnik/%(zoom)d/%(x)d/%(y)d.png", 'prefix': 'OpenStreetMap I'}),
            ('OpenCycleMaps', {'remote_url': 'http://andy.sandbox.cloudmade.com/tiles/cycle/%(zoom)d/%(x)d/%(y)d.png', 'prefix': 'OpenCycleMap'})

        ],
        'options_map_double_size': False,
        'options_rotate_screen': 0,
        'tts_interval' : 0
    }
            
    def __init__(self, guitype, root):
        gobject.GObject.__init__(self)
        self.current_target = None
        self.current_position = None
        self.create_recursive(self.SETTINGS_DIR)

        dataroot = path.join(root, 'data')

        self._install_updates()

        self.__read_config()
        self.connect('settings-changed', self.__on_settings_changed)
        self.connect('save-settings', self.__on_save_settings)
        self.create_recursive(self.settings['download_output_dir'])
        self.create_recursive(self.settings['download_map_path'])
                

        self.downloader = downloader.FileDownloader(self.settings['options_username'], self.settings['options_password'], self.COOKIE_FILE, cachedownloader.GeocachingComCacheDownloader.login_callback)
                
        self.pointprovider = provider.PointProvider(self.CACHES_DB, geocaching.GeocacheCoordinate, 'geocaches')

        self.gui = guitype(self, dataroot)

        
        actor_tts = TTS(self)
        actor_tts.connect('error', lambda caller, msg: self.gui.show_error(msg))
        #actor_notify = Notify(self)

        self.emit('settings-changed', self.settings, self)

 

        if '--sim' in argv:
            self.gps_thread = gpsreader.FakeGpsReader(self)
            gobject.timeout_add(1000, self.__read_gps)
            self.set_target(gpsreader.FakeGpsReader.get_target())
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

        if '--startup-only' in argv:
            return


        self.gui.show()

    ##############################################
    #
    # Misc
    #
    ##############################################

    @staticmethod
    def create_recursive(dpath):
        if dpath != '/':
            if not path.exists(dpath):
                head, tail = path.split(dpath)
                Core.create_recursive(head)
                try:
                    mkdir(dpath)
                except Exception, e:
                    logging.info("Could not create directory; " + e)
                    pass

    def optimize_data(self):
        self.pointprovider.push_filter()
        self.pointprovider.set_filter(found = True)
        old_geocaches = self.pointprovider.get_points_filter()
        self.pointprovider.pop_filter()
        for x in old_geocaches:
            images = x.get_images()
            if len(images) == 0:
                continue
            for filename, caption in images.items():
                fullpath = path.join(self.settings['download_output_dir'], filename)
                try:
                    remove(fullpath)
                except Exception:
                    logging.warning("Could not remove " + fullpath)
        self.pointprovider.remove_geocaches(old_geocaches)
        self.pointprovider.optimize()

    def get_file_sizes(self):
        folder = self.settings['download_output_dir']
        folder_size = 0
        for (p, dirs, files) in walk(folder):
          for file in files:
            filename = path.join(p, file)
            folder_size += path.getsize(filename)
        sqlite_size = path.getsize(self.CACHES_DB)
        return {'images' : folder_size, 'sqlite' : sqlite_size}

    @staticmethod
    def format_file_size(size):
        if size < 1024:
            return "%d B" % size
        elif size < 1024 * 1024:
            return "%d KiB" % (size / 1024)
        elif size < 1024 * 1024 * 1024:
            return "%d MiB" % (size / (1024 * 1024))
        else:
            return "%d GiB" % (size / (1024 * 1024 * 1024))


    ##############################################
    #
    # Handling Updates
    #
    ##############################################

    def _install_updates(self):
        updated_modules = 0
        if path.exists(self.UPDATE_DIR):
            sys_path.insert(0, self.UPDATE_DIR)
            for m in self.UPDATE_MODULES:
                modulefile = path.join(self.UPDATE_DIR, "%s%spy" % (m.__name__, extsep))
                if path.exists(modulefile):
                    v_dict = {'VERSION': -1}
                    with open(modulefile) as f:
                        for line in f:
                            if line.startswith('VERSION'):
                                exec line in v_dict
                                break
                    if v_dict['VERSION'] > m.VERSION:
                        pass#logging.info("Reloading Module '%s', current version number: %d, new version number: %d" % (m.__name__, v_dict['VERSION'], m.VERSION))
                        reload(m)
                        updated_modules += 1
                    else:
                        logging.info("Not reloading Module '%s', current version number: %d, version number of update file: %d" % (m.__name__, v_dict['VERSION'], m.VERSION))
                else:
                    logging.info("Skipping nonexistant update from" + path.join(self.UPDATE_DIR, "%s%spy" % (m.__name__, extsep)))
        return updated_modules

    def try_update(self):
        from urllib import urlretrieve
        import tempfile
        import hashlib
        from shutil import copyfile
        self.create_recursive(self.UPDATE_DIR)
        baseurl = 'http://www.danielfett.de/files/agtl-updates/%s' % VERSION
        url = "%s/updates" % baseurl
        try:
            reader = self.downloader.get_reader(url, login=False)
        except Exception, e:
            logging.exception(e)
            raise Exception("No updates were found. (Could not download index file.)")

        try:
            files = []
            for line in reader:
                md5, name = line.strip().split('  ')
                handle, temp = tempfile.mkstemp()
                files.append((md5, name, temp))
        except Exception, e:
            logging.exception(e)
            raise Exception("No updates were found. (Could not process index file.)")

        if len(files) == 0:
            raise Exception("There are no updates available.")

        for md5sum, name, temp in files:
            url = '%s/%s' % (baseurl, name)
            try:
                urlretrieve(url, temp)
            except Exception, e:
                logging.exception(e)
                raise Exception("Could not download file '%s'" % name)

            hash = hashlib.md5(open(temp).read()).hexdigest()
            if hash != md5sum:
                raise Exception("There was an error downloading the file. (MD5 sum mismatch in  %s)" % name)

        for md5sum, name, temp in files:
            file = path.join(self.UPDATE_DIR, name)
            try:
                copyfile(temp, file)
            except Exception, e:
                logging.exception(e)
                raise Exception("The update process was stopped while copying files. AGTL may run or not. If not, delete all *.py files in %s." % self.UPDATE_DIR)
            finally:
                try:
                    remove(tmpfile)
                except Exception:
                    pass

        return self._install_updates()



    ##############################################
    #
    # Settings
    #
    ##############################################

    def save_settings(self, settings, source):
        self.settings.update(settings)
        self.emit('settings-changed', settings, source)

    def __on_settings_changed(self, caller, settings, source):
        if source == self:
            return
        if 'options_username' in settings and 'options_password' in settings:
            self.downloader.update_userdata(settings['options_username'], settings['options_password'])

    def __on_save_settings(self, caller):
        settings = {
            'last_target_lat': self.current_target.lat,
            'last_target_lon': self.current_target.lon
        }
        caller.save_settings(settings, self)
                
    def __del__(self):
        self.emit('save-settings')
        self.__write_config()

    # called by gui
    def on_destroy(self):
        self.emit('save-settings')
        self.__write_config()

    # called by gui
    def on_config_changed(self, new_settings):
        self.settings = new_settings
        self.downloader.update_userdata(self.settings['options_username'], self.settings['options_password'])
        self.__write_config()



    def __read_config(self):
        filename = path.join(self.SETTINGS_DIR, 'config')
        if not path.exists(filename):
            self.settings = self.DEFAULT_SETTINGS
            return
        f = file(filename, 'r')
        string = f.read()
        self.settings = {}
        if string != '':
            tmp_settings = loads(string)
            for k, v in self.DEFAULT_SETTINGS.items():
                if k in tmp_settings != None:
                    self.settings[k] = tmp_settings[k]
                else:
                    self.settings[k] = v
        else:
            self.settings = self.DEFAULT_SETTINGS


    def __write_config(self):
        filename = path.join(self.SETTINGS_DIR, 'config')
        f = file(filename, 'w')
        f.write(dumps(self.settings, sort_keys=True, indent=4))


    ##############################################
    #
    # Target & GPS
    #
    ##############################################


    def set_target(self, coordinate):
        self.current_target = coordinate
        distance, bearing = self.__get_target_distance_bearing()
        self.emit('target-changed', coordinate, distance, bearing)
        self.emit('map-marks-changed')


    def __get_target_distance_bearing(self):
        if self.current_position != None and self.current_target != None:
            distance = self.current_position.distance_to(self.current_target)
            bearing = self.current_position.bearing_to(self.current_target)
        else:
            distance = None
            bearing = None
        return distance, bearing

    def __read_gps(self):
        fix = self.gps_thread.get_data()

        if fix.position != None:
            self.current_position = fix.position
            distance, bearing = self.__get_target_distance_bearing()
            self.emit('good-fix', fix, distance, bearing)
        else:
            self.emit('no-fix', fix, self.gps_thread.status)
        return True

    def __read_gps_cb_error(self, control, error):
        fix = gpsreader.Fix()
        msg = gpsreader.LocationGpsReader.get_error_from_code(error)
        self.emit('no-fix', fix, msg)
        return True

    def __read_gps_cb_changed(self, device):
        fix = self.gps_thread.fix_from_tuple(device.fix, device)
        # @type fix gpsreader.Fix

        if fix.position != None:
            self.current_position = fix.position
            distance, bearing = self.__get_target_distance_bearing()
            self.emit('good-fix', fix, distance, bearing)
        else:
            self.emit('no-fix', fix, 'No Fix')
        return True


    ##############################################
    #
    # Geonames & Routing
    #
    ##############################################
                                
    def get_coord_by_name(self, query):
        return self.geonames.search(query)



    def search_place(self, search):
        return self.geonames.search_all(search)

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
                from math import sqrt
                min_lat = min([x.lat for x in together])
                min_lon = min([x.lon for x in together])
                max_lat = max([x.lat for x in together])
                max_lon = max([x.lon for x in together])
                c1 = Coordinate(min_lat, min_lon)
                c2 = Coordinate(max_lat, max_lon)
                new_c1 = c1.transform(-45, r * 1000 * sqrt(2))
                new_c2 = c2.transform(-45 + 180, r * 1000 * sqrt(2))
                out.append((new_c1, new_c2))
                together = []
        logging.info("Needing %d unique queries" % len(out))
        return out

    ##############################################
    #
    # Deprecated
    #
    ##############################################

    # called by gui
    def on_cache_selected(self, cache):
        self.gui.show_cache(cache)

    ##############################################
    #
    # Filters, Searching & Pointprovider
    #
    ##############################################
                
    # called by gui
    def on_start_search_simple(self, text):
        #m = re.search(r'/([NS]?)\s*(\d{1,2})\.(\d{1,2})\D+(\d+)\s*([WE]?)\s*(\d{1,3})\.(\d{1,2})\D+(\d+)', text, re.I)
        #if m != None:
        self.__try_show_cache_by_search('%' + text + '%')

    # called by gui
    def set_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        self.emit('map-marks-changed')
                
    # called by gui
    def reset_filter(self):
        self.pointprovider.set_filter()
        self.emit('map-marks-changed')

    # called by gui
    def on_start_search_advanced(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        points = self.pointprovider.get_points_filter(location)
        self.gui.display_results_advanced(points)

    def get_points_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        self.pointprovider.push_filter()
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        points = self.pointprovider.get_points_filter(location)
        truncated = (len(points) >= self.pointprovider.MAX_RESULTS)
        self.pointprovider.pop_filter()
        return (points, truncated)


    def get_geocache_by_name(self, name):
        return self.pointprovider.get_by_name(name)

    def __try_show_cache_by_search(self, idstring):
        cache = self.pointprovider.find_by_string(idstring)
        if cache != None:
            self.gui.show_cache(cache)
            self.gui.set_center(cache)
            return True
        return False

    ##############################################
    #
    # Downloading
    #
    ##############################################

    # called by gui
    def on_download(self, location, sync=False):
        self.gui.set_download_progress(0.5, "Downloading...")
        cd = cachedownloader.GeocachingComCacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)
        if not sync:
            def same_thread(arg1, arg2):
                gobject.idle_add(self.on_download_complete, arg1, arg2)
                return False

            cd.connect("finished-overview", same_thread)
            t = Thread(target=cd.get_geocaches, args=[location])
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
        self.emit('map-marks-changed')
        if sync:
            return (caches, new_caches)
        else:
            return False

    # called on signal by downloading thread
    def on_already_downloading_error(self, something, error):
        self.gui.show_error(error)

    # called on signal by downloading thread
    def on_download_error(self, something, error):
        logging.exception(error)
        def same_thread(error):
            self.gui.hide_progress()
            self.gui.show_error("Error while downloading: '%s'" % error)
            return False
        gobject.idle_add(same_thread, error)

    # called by gui
    def on_download_cache(self, cache, sync=False):
        #
        self.gui.set_download_progress(0.5, "Downloading %s..." % cache.name)

        cd = cachedownloader.GeocachingComCacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)
        if not sync:
            def same_thread(arg1, arg2):
                gobject.idle_add(self.on_download_cache_complete, arg1, arg2)
                return False
            cd.connect("finished-single", same_thread)
            t = Thread(target=cd.update_coordinate, args=[cache])
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



    # called by gui
    def on_download_descriptions(self, location, visibleonly=False):

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
        self.update_coordinates(caches)


    def update_coordinates(self, caches):
        cd = cachedownloader.GeocachingComCacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        cd.connect("download-error", self.on_download_error)
        cd.connect("already-downloading-error", self.on_already_downloading_error)


        def same_thread(arg1, arg2):
            gobject.idle_add(self.on_download_descriptions_complete, arg1, arg2)
            return False

        def same_thread_progress (arg1, arg2, arg3, arg4):
            gobject.idle_add(self.on_download_progress, arg1, arg2, arg3, arg4)
            return False

        cd.connect('progress', same_thread_progress)
        cd.connect('finished-multiple', same_thread)

        t = Thread(target=cd.update_coordinates, args=[caches])
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
        self.emit('map-marks-changed')
        return False


    # called on signal by downloading thread
    def on_download_progress(self, something, cache_name, i, max_i):
        self.gui.set_download_progress(float(i) / float(max_i), "Downloading %s (%d of %d)..." % (cache_name, i, max_i))
        return False

    ##############################################
    #
    # Exporting
    #
    ##############################################
                
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
        
                

    ##############################################
    #
    # Fieldnotes
    #
    ##############################################


    def save_fieldnote(self, cache):
        if cache.logas == geocaching.GeocacheCoordinate.LOG_AS_FOUND:
            cache.found = 1

        elif cache.logas == geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND:
            cache.found = 0

        self.save_cache_attribute(cache, ('logas', 'logdate', 'fieldnotes'))
        self.emit('fieldnotes-changed')        

    def on_upload_fieldnotes(self):
        self.gui.set_download_progress(0.5, "Uploading Fieldnotes...")

        caches = self.pointprovider.get_new_fieldnotes()
        fn = fieldnotesuploader.FieldnotesUploader(self.downloader)
        fn.connect("upload-error", self.on_download_error)
        
        def same_thread(arg1):
            gobject.idle_add(self.on_upload_fieldnotes_finished, arg1, caches)
            return False
            
        fn.connect('finished-uploading', same_thread)
        
        for c in caches:
            fn.add_fieldnote(c)
        t = Thread(target=fn.upload)
        t.daemon = False
        t.start()
        
    def on_upload_fieldnotes_finished(self, widget, caches):
        for c in caches:
            c.logas = geocaching.GeocacheCoordinate.LOG_NO_LOG
            self.save_cache_attribute(c, 'logas')
        self.gui.hide_progress()
        self.emit('fieldnotes-changed')

    def get_new_fieldnotes_count(self):
        return self.pointprovider.get_new_fieldnotes_count()


    ##############################################
    #
    # Geocache Handling
    #
    ##############################################

    def save_cache_attribute(self, cache, attribute):
        if type(attribute) == tuple:
            for a in attribute:
                self.pointprovider.update_field(cache, a, cache.serialize_one(a), save=False)
            self.pointprovider.save()
        else:
            self.pointprovider.update_field(cache, attribute, cache.serialize_one(attribute))


    def set_alternative_position(self, cache, ap):
        cache.set_alternative_position(ap)
        self.save_cache_attribute(cache, ('alter_lat', 'alter_lon'))
        self.emit('map-marks-changed')


                
    


def determine_path ():
    """Borrowed from wxglade.py"""
    try:
        root = __file__
        if path.islink (root):
            root = path.realpath (root)
        return path.dirname(path.abspath (root))
    except:
        logging.error("I'm sorry, but something is wrong.")
        logging.error("There is no __file__ variable. Please contact the author.")
        exit()

                        

def start():
    Core(gui, determine_path())

def start_profile(what):
    import cProfile
    p = cProfile.Profile()
    p.run(what)
    stats = p.getstats()
    print "BY CALLS:\n------------------------------------------------------------"
    def c(x, y):
        if x.callcount < y.callcount:
            return 1
        elif x.callcount == y.callcount:
            return 0
        else:
            return -1
    stats.sort(cmp=c)
    for line in stats[:100]:
        print "%d %4f %s" % (line.callcount, line.totaltime, line.code)
        if line.calls == None:
            continue
        line.calls.sort(cmp=c)
        for line in line.calls[:10]:
            print "-- %d %4f %s" % (line.callcount, line.totaltime, line.code)

    
    print "BY TOTALTIME:\n------------------------------------------------------------"
    def c(x, y):
        if x.totaltime < y.totaltime:
            return 1
        elif x.totaltime == y.totaltime:
            return 0
        else:
            return -1
    stats.sort(cmp=c)
    for line in stats[:30]:
        print "%d %4f %s" % (line.callcount, line.totaltime, line.code)
        if line.calls == None:
            continue
        line.calls.sort(cmp=c)
        for line in line.calls[:10]:
            print "-- %d %4f %s" % (line.callcount, line.totaltime, line.code)


if '--profile' in argv:
    start = start_profile('start()')

        

if __name__ == "__main__":
    start()

