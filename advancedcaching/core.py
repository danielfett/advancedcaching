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

from __future__ import with_statement

# This is also evaluated by the build scripts
VERSION='0.9.1.0'
import logging
import logging.handlers
logging.basicConfig(level=logging.WARNING,
                    format='%(relativeCreated)6d %(levelname)10s %(name)-20s %(message)s // %(filename)s:%(lineno)s',
                    )
                    

from geo import Coordinate
try:
    from json import loads, dumps
except (ImportError, AttributeError):
    from simplejson import loads, dumps
from sys import argv, exit
from sys import path as sys_path

import downloader
import geocaching
import gpsreader
from os import path, mkdir, extsep, remove, walk
import provider
from threading import Thread
import cachedownloader
from actors.tts import TTS
from re import sub
import threading
from datetime import datetime

import connection
import gobject

if len(argv) == 1:
    import cli
    print cli.usage % ({'name': argv[0]})
    exit()

if '-v' in argv or '--remote' in argv:
    import colorer
    logging.getLogger('').setLevel(logging.DEBUG)
    logging.debug("Set log level to DEBUG")
    
if '--debug-http' in argv:
    downloader.enable_http_debugging()
    
extensions = []
if '--simple' in argv:
    import simplegui
    gui = simplegui.SimpleGui
    gps = 'gpsdprovider'
elif '--desktop' in argv:
    import biggui
    gui = biggui.BigGui
elif '--qml' in argv:
    import qmlgui
    gui = qmlgui.QmlGui
    gps = 'qmllocationprovider'
elif '--hildon' in argv:
    connection.init() # is only used on the maemo platform
    import hildongui
    gui = hildongui.HildonGui
    gps = 'locationgpsprovider'
    extensions.append('geonames')
    extensions.append('tts')
else:
    import cli
    gui = cli.Cli
    gps = None
    extensions.append('geonames')
    
if '--sim' in argv:
    gps = 'simulatingprovider'
elif '--nogps' in argv:
    gps = None

logger = logging.getLogger('core')

class Core(gobject.GObject):

    __gsignals__ = {
        'map-marks-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'cache-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        'fieldnotes-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'good-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'no-fix': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'target-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        'settings-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, )),
        'save-settings': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'error': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        'progress': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, )),
        'hide-progress': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        }

    SETTINGS_DIR = path.expanduser(path.join('~', '.agtl'))
    CACHES_DB = path.join(SETTINGS_DIR, "caches.db")
    COOKIE_FILE = path.join(SETTINGS_DIR, "cookies.lwp")
    UPDATE_DIR = path.join(SETTINGS_DIR, 'updates')

    MAEMO_HOME = path.expanduser(path.join('~', 'MyDocs', '.'))
    MAPS_DIR = path.join('Maps', '')

    DATA_DIR = path.expanduser(path.join('~', '')) if not path.exists(MAEMO_HOME) else MAEMO_HOME

    UPDATE_MODULES = [cachedownloader]
    
    updating_lock = threading.Lock()
    _geocache_by_name_event = threading.Event()
    
    DEFAULT_SETTINGS = {
        'download_visible': True,
        'download_notfound': True,
        'download_new': True,
        'download_nothing': False,
        'download_create_index': False,
        'download_run_after': False,
        'download_run_after_string': '',
        'download_output_dir': path.expanduser(path.join(DATA_DIR, '.geocaches', '')),
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
            ('OpenStreetMaps', {'remote_url': "http://tile.openstreetmap.org/%(zoom)d/%(x)d/%(y)d.png", 'prefix': 'OpenStreetMap I', 'max_zoom': 18}),
            ('OpenCycleMaps', {'remote_url': 'http://a.tile.opencyclemap.org/cycle/%(zoom)d/%(x)d/%(y)d.png', 'prefix': 'OpenCycleMap', 'max_zoom': 18}),
        ],
        'options_map_double_size': False,
        'options_rotate_screen': 0,
        'tts_interval': 0,
        'options_default_log_text' : 'TFTC!\n\nLogged at %X from my %(machine)s using AGTL.',
        'options_auto_update': True,
        'download_num_logs': 20,
        'options_night_view_mode': 0,
        'debug_log_to_http': False,
        'options_backend': 'geocaching-com-new',
        'options_redownload_after': 14,
    }
            
    def __init__(self, guitype, gpstype, extensions):
        """
        Initialize the application.
        
        guitype -- Python type of the gui which is to be used.
        gpstype -- String indicating the desired GPS access method.
        extensions -- List of strings indicating desired extensions.
        """
        gobject.GObject.__init__(self)
        self.current_target = None
        self.current_position = None
        self.auto_update_checked = False
        self.create_recursive(self.SETTINGS_DIR)

        # self.cachedownloader is populated in settings handling.
        self.cachedownloader = None
        self._install_updates()

        self.__read_config()
        
        # Check tile URLs for outdated URLs after Openstreetmap URL change
        for name, details in self.settings['map_providers']:
            prev = details['remote_url']
            details['remote_url'] = sub(r'//(.*).openstreetmap.org/([a-z]*/)?', '//tile.openstreetmap.org/', prev)
            if prev != details['remote_url']:
                logger.info("Replaced url '%s' with '%s' because Openstreetmaps changed their URLs." % (prev, details['remote_url']))
        
        self.connect('settings-changed', self.__on_settings_changed)
        self.connect('save-settings', self.__on_save_settings)
        self.create_recursive(self.settings['download_output_dir'])
        self.create_recursive(self.settings['download_map_path'])
        
        self.downloader = downloader.FileDownloader(self.settings['options_username'], self.settings['options_password'], self.COOKIE_FILE)
                
        self.pointprovider = provider.PointProvider(self.CACHES_DB, geocaching.GeocacheCoordinate)

        self.gui = guitype(self)
        
        
        if ('debug_log_to_http' in self.settings and self.settings['debug_log_to_http']) or '--remote' in argv:
            http_handler = logging.handlers.HTTPHandler("danielfett.de", "http://www.danielfett.de/files/collect.php")
            buffering_handler = logging.handlers.MemoryHandler(100, target = http_handler)
            logging.getLogger('').addHandler(buffering_handler)
            logging.getLogger('').setLevel(logging.DEBUG)
            logging.debug("Remote logging activated!")
            # Now reset the setting to default
            self.settings['debug_log_to_http'] = False
        
        
        self.emit('settings-changed', self.settings, self)
        self.emit('fieldnotes-changed')  

        self.__setup_gps(gps)
            
        if 'geonames' in extensions:
            import geonames
            self.geonames = geonames.Geonames(self.downloader)
            
        if 'tts' in extensions:
            from actors.notify import Notify
            actor_tts = TTS(self)
            actor_tts.connect('error', lambda caller, msg: self.emit('error', msg))
            actor_notify = Notify(self)

        if '--startup-only' in argv:
            return

        self.gui.show()
        if not '--profile' in argv:
            exit()

    ##############################################
    #
    # Misc, File and Path operations
    #
    ##############################################

    @staticmethod
    def create_recursive(dpath):
        """
        Create dpath and all parent directories if necessary
        
        """
        if dpath != '/':
            if not path.exists(dpath):
                head, tail = path.split(dpath)
                Core.create_recursive(head)
                try:
                    mkdir(dpath)
                except Exception, e:
                    logging.info("Could not create directory; %s" % e)
                    pass

    def optimize_data(self):
        """
        Clean up database and file system.
        
        Removes found geocaches and their images from the database or filesystem, respectively.
        """
        self.pointprovider.push_filter()
        self.pointprovider.set_filter(found=True)
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
        """
        Return the accumulated size of the images in the download output directory (i.e., the images).
        
        """
        folder = self.settings['download_output_dir']
        folder_size = 0
        for (p, dirs, files) in walk(folder):
            for file in files:
                filename = path.join(p, file)
                folder_size += path.getsize(filename)
        sqlite_size = path.getsize(self.CACHES_DB)
        return {'images': folder_size, 'sqlite': sqlite_size}

    @staticmethod
    def format_file_size(size):
        """
        Format a file size to a human readable string.
        
        """
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
        """
        Installs updated modules. 
        
        Checks the updates directory for new versions of one of the modules listed in self.UPDATE_MODULES and reloads the modules. Version check is performed by comparing the VERSION variable stored in the module.
        """
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
                        else:
                            logger.error("Could not find VERSION string in file %s!" % modulefile) 
                            continue
                    if v_dict['VERSION'] > m.VERSION:
                        logging.info("Reloading Module '%s', current version number: %d, new version number: %d" % (m.__name__, v_dict['VERSION'], m.VERSION))
                        reload(m)
                        if m == cachedownloader and self.cachedownloader != None:
                            self.__install_cachedownloader()
                        updated_modules += 1
                    else:
                        logging.info("Not reloading Module '%s', current version number: %d, version number of update file: %d" % (m.__name__, m.VERSION, v_dict['VERSION']))
                else:
                    logging.info("Skipping nonexistant update from" + path.join(self.UPDATE_DIR, "%s%spy" % (m.__name__, extsep)))
        return updated_modules

    def try_update(self, silent = False):
        """
        Retrieve and install updates.
        
        This method connects to danielfett.de and tries to retrieve an md5sums file containing references to updated files for this AGTL version. If available, downloads the files and checks their md5sums before copying them to the updates folder. Calls self._install_updates afterwards to reload updated modules.
        silent -- If possible, suppress errors. Useful for auto-updating.

        """
        if connection.offline:
            if not silent:
                self.emit('error', Exception("Can't update in offline mode."))
            return False
            
        class NoUpdateException(Exception):
            pass
            
            
        from urllib import urlretrieve
        from urllib2 import HTTPError
        import tempfile
        import hashlib
        from shutil import copyfile
        self.create_recursive(self.UPDATE_DIR)
        baseurl = 'http://www.danielfett.de/files/agtl-updates/%s' % VERSION
        url = "%s/updates" % baseurl
        self.emit('progress', 0.5, "Checking for updates...")
        try:
            try:
                reader = self.downloader.get_reader(url, login=False)
            except HTTPError, e:
                raise NoUpdateException("No updates available.")
            except Exception, e:
                logging.exception(e)
                raise Exception("Could not connect to update server.")

            try:
                files = []
                for line in reader:
                    md5, name = line.strip().split('  ')
                    handle, temp = tempfile.mkstemp()
                    files.append((md5, name, temp))
            except Exception, e:
                logging.exception(e)
                raise NoUpdateException("No updates were found. (Could not process index file.)")

            if len(files) == 0:
                raise NoUpdateException("No updates available.")

            for md5sum, name, temp in files:
                url = '%s/%s' % (baseurl, name)
                try:
                    urlretrieve(url, temp)
                except Exception, e:
                    logging.exception(e)
                    raise Exception("Could not download file '%s'" % name)

                hash = hashlib.md5(open(temp).read()).hexdigest()
                if hash != md5sum:
                    raise Exception("There was an error downloading the file. (MD5 sum mismatch in %s)" % name)

            for md5sum, name, temp in files:
                file = path.join(self.UPDATE_DIR, name)
                try:
                    copyfile(temp, file)
                except Exception, e:
                    logging.exception(e)
                    raise Exception("The update process was stopped while copying files. AGTL may run or not. If not, delete all *.py files in %s." % self.UPDATE_DIR)
                finally:
                    try:
                        remove(temp)
                    except Exception:
                        pass
                        
        except NoUpdateException, e:
            self.emit('hide-progress')
            return self._install_updates()
        except Exception, e:
            self.emit('error', e)
            return None

        self.emit('hide-progress')
        return self._install_updates()



    ##############################################
    #
    # Settings
    #
    ##############################################

    def save_settings(self, settings, source):
        '''
        This should be called to update the settings throughout all components.
        
        When settings need to be changed, for example when the GUI updates the username, other components need to be notified. This method updates the settings and notifies the other components (including the core).
        settings -- Subset of settings dictionary which is to be updated.
        source -- Calling class instance, for example a HildonGui instance. This is passed on so that the triggering component can suppress reactions to its own updates.
        '''
        logger.debug("Got settings update from %s" % source)
        
        self.settings.update(settings)
        self.emit('settings-changed', settings, source)


    def __on_settings_changed(self, caller, settings, source):
        '''
        This is called when settings have changed.
        
        This method is connected to the settings-changed signal and indicates that someone has changed the settings. The new settings need to be applied, e.g., to the cachedownloader.
        settings -- contains only the updated parts of the settings dictionary.
        '''
        logger.debug("Settings where changed by %s." % source)
        
        if 'options_backend' in settings or 'download_output_dir' in settings or 'download_noimages' in settings:
            self.__install_cachedownloader()
            
        if source == self:
            return
        if 'options_username' in settings:
            self.downloader.update_userdata(username = settings['options_username'])
        if 'options_password' in settings:
            self.downloader.update_userdata(password = settings['options_password'])

    def __on_save_settings(self, caller):
        """
        This is called when settings shall be saved, calling save_settings afterwards.
        
        The save-settings signal is emitted whenever the application is about to be destroyed. Therefore, we need to save some settings.
        """
        logger.debug("Assembling update for settings, on behalf of %s" % caller)
        if self.current_target != None:
            settings = {
                'last_target_lat': self.current_target.lat,
                'last_target_lon': self.current_target.lon
            }
            caller.save_settings(settings, self)
    
    def __del__(self):
        logger.debug("Somebody is trying to kill me, saving the settings.")
        self.emit('save-settings')
        self.__write_config()

    def prepare_for_disposal(self):
        """
        This is called by the GUI when it is about to be killed.
        
        """
        logger.debug("Somebody is being killed, saving the settings.")
        self.emit('save-settings')
        self.__write_config()


    def __read_config(self):
        filename = path.join(self.SETTINGS_DIR, 'config')
        logger.debug("Loading config from %s" % filename)
        if not path.exists(filename):
            logger.error("Did not find settings file (%s), loading default settings." % filename)
            self.settings = self.DEFAULT_SETTINGS
            return
        with file(filename, 'r') as f:
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
        logger.debug("Writing settings to %s" % filename)
        try:
            with file(filename, 'w') as f:
                config = dumps(self.settings, sort_keys=True, indent=4)
                f.write(config)
        except IOError, e:
            logger.error("Can not write to config file (%s):" % filename)
            logger.exception(e)

    def __install_cachedownloader(self):
        logger.debug("Installing new cachedownloader")
        if self.cachedownloader != None:
            logger.debug("Disconnecting old signals.")
            for handler in self.__cachedownloader_signal_handlers:
                self.cachedownloader.disconnect(handler)
        self.__cachedownloader_signal_handlers = []
        self.cachedownloader = cachedownloader.get(self.settings['options_backend'], self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        a = self.cachedownloader.connect("download-error", self.on_download_error)
        b = self.cachedownloader.connect("already-downloading-error", self.on_already_downloading_error)
        c = self.cachedownloader.connect('progress', self.on_download_progress)
        self.__cachedownloader_signal_handlers = [a, b, c]

    ##############################################
    #
    # Target & GPS
    #
    ##############################################


    def set_target(self, coordinate):
        """
        Sets the new target coordinate.
        
        Updates target distance and target bearing afterwards and emits target-changed signal.
        """
        self.current_target = coordinate
        distance, bearing = self.__get_target_distance_bearing()
        self.emit('target-changed', coordinate, distance, bearing)

    def __get_target_distance_bearing(self):
        if self.current_position != None and self.current_target != None:
            distance = self.current_position.distance_to(self.current_target)
            bearing = self.current_position.bearing_to(self.current_target)
        else:
            distance = None
            bearing = None
        return distance, bearing
        
    def __setup_gps(self, gps):
        """
        Setup GPS provider according to the constant in gps.
        
        """
        if gps == 'simulatingprovider':
            self.gps_thread = gpsreader.FakeGpsReader(self)
            gobject.timeout_add(1000, self.__read_gps)
            self.set_target(gpsreader.FakeGpsReader.get_target())
        elif gps == None:
            self.gps_thread = gpsreader.FakeGpsReader(self)
            self.set_target(gpsreader.FakeGpsReader.get_target())
        elif gps == 'gpsdprovider':
            self.gps_thread = gpsreader.GpsReader()
            gobject.timeout_add(1000, lambda: self.__read_gps(self.gps_thread.get_data()))
        elif gps == 'locationgpsprovider':
            self.gps_thread = gpsreader.LocationGpsReader(self.__read_gps)
            gobject.idle_add(self.gps_thread.start)
        elif gps == 'qmllocationprovider':
            self.gui.get_gps(self.__read_gps)
            self.gps_thread = None
            
    def __read_gps(self, fix):
        """
        This callback method is called by the gpsreader to process a new fix.
        
        """
        if fix.position != None:
            self.current_position = fix.position
            distance, bearing = self.__get_target_distance_bearing()
            logger.debug("Sending good fix for fix %r" % fix)
            self.emit('good-fix', fix, distance, bearing)
        else:
            logger.debug("Sending bad fix for fix %r" % fix)
            self.emit('no-fix', fix, self.gps_thread.status if self.gps_thread != None else "")
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
    # Filters, Searching & Pointprovider
    #
    ##############################################
                
    def set_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None):
        """
        Sets a new filter for the pointprovider. 
        
        Is mainly used to filter the map display. (Currently only in hildongui_plugins)
        
        """
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        self.emit('map-marks-changed')
                
    def reset_filter(self):
        """
        Resets the filter for the pointprovider. 
        
        (Currently only in hildongui_plugins)
        
        """
        self.pointprovider.set_filter()
        self.emit('map-marks-changed')

    def get_points_filter(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location=None, marked=None, preserve_filter = False):
        """
        Performs a search according to the given criteria and returns the geocaches. Also returns information on whether the result was truncated due to the maximum number of search results configured in pointprovider.
        preserve_filter -- Apply the filter and keep it active after this method. If set to False, the filtering remains unchanged after the method call.
        
        """
        if not preserve_filter:
            self.pointprovider.push_filter()
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked=marked)
        points = self.pointprovider.get_points_filter(location)
        truncated = (len(points) >= self.pointprovider.MAX_RESULTS)
        if not preserve_filter:
            self.pointprovider.pop_filter()
        return (points, truncated)


    def get_geocache_by_name(self, name):
        """
        Return a geocache by its ID.
        
        """
        return self.pointprovider.get_by_name(name)

    ##############################################
    #
    # Downloading
    #
    ##############################################
    
    def _download_upload_helper(self, action, then, *args, **kwargs):
        with Core.updating_lock:
            self._check_auto_update()
            # Problem: self.cachedownloader may change in between. What to do?
            # One solution: Use eval to get the function name
            res = eval(action)(*args, **kwargs)
            gobject.idle_add(then, res)

    def _check_auto_update(self):
        if 'options_auto_update' in self.settings and self.settings['options_auto_update'] and not self.auto_update_checked:
            self.emit('progress', 0.1, "Checking for Updates...")
            updates = self.try_update(silent = True)
            if updates not in [None, False]:
                logger.info("Parser update installed.")
        self.auto_update_checked = True

    def download_overview(self, location, sync=False, skip_callback = None):
        """
        Downloads an *overview* of geocaches within the boundaries given in location.
        
        location -- Geographic boundaries (see cachedownloader.get_overview for details)
        sync -- Perform actions synchronized, i.e., don't use threads.
        skip_callback -- A callback function which gets the geocache id and its found status as input. If it returns true, the geocache's details are not downloaded.
        """
        if not sync:                
            t = Thread(target=self._download_upload_helper, args=['self.cachedownloader.get_overview', self._download_overview_complete, location, self.get_geocache_by_name_async, skip_callback])
            t.daemon = True
            t.start()
            return False
        else:
            return self._download_overview_complete(self.cachedownloader.get_overview(location, self.get_geocache_by_name, skip_callback), True)

    def _download_overview_complete(self, caches, sync=False):
        """
        Called upon completion of the download of all geocaches within a boundary.
        
        caches -- Updated geocache information.
        sync -- Perform actions synchronized, i.e., don't use threads.
        """
        new_caches = []
        for c in caches:
            self.emit('cache-changed', c)
            point_new = self.pointprovider.add_point(c)
            if point_new:
                new_caches.append(c)
        self.pointprovider.save()
        
        for c in caches:
            self.emit('cache-changed', c)
            
        self.emit('hide-progress')
        self.emit('map-marks-changed')
        if sync:
            return (caches, new_caches)
        else:
            return False

    def download_cache_details(self, cache, sync=False):
        """
        Download or update *detailed* information for a specific geocache.
        
        location -- Geographic boundaries (see cachedownloader.get_overview for details)
        sync -- Perform actions synchronized, i.e., don't use threads.
        
        """
        if not sync:                
            t = Thread(target=self._download_upload_helper, args=['self.cachedownloader.update_coordinate', self._download_cache_details_complete, cache, self.settings['download_num_logs']])
            t.daemon = True
            t.start()
            #t.join()
            return False
        else:
            full = self.cachedownloader.update_coordinate(cache, self.settings['download_num_logs'])
            return self._download_cache_details_complete(full, sync)

    def _download_cache_details_complete(self, cache, sync = False):
        """
        Called when a single geocache was successfully downloaded.

        """
        self.pointprovider.add_point(cache, True)
        self.pointprovider.save()
        self.emit('hide-progress')
        self.emit('cache-changed', cache)
        if not sync:
            return False
        else:
            return cache


    def download_cache_details_map(self, location, visibleonly=False):
        """
        Download *details* for all geocaches within a specific location.
        
        location -- Geographic boundaries (see cachedownloader.get_overview for details)
        sync -- Perform actions synchronized, i.e., don't use threads.
        
        """
    
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
        self.download_cache_details_list(caches)

    def download_cache_details_list(self, caches, sync=False):
        """
        Download/update *detailed* information for a list of geocaches.
        
        caches -- List of geocaches
        
        """
        if not sync:
            t = Thread(target=self._download_upload_helper, args=['self.cachedownloader.update_coordinates', self._download_cache_details_list_complete, caches, self.settings['download_num_logs']])
            t.daemon = True
            t.start()
            return False
        else:
            return self._download_cache_details_list_complete(self.cachedownloader.update_coordinates(caches))
        
    def _download_cache_details_list_complete(self, caches):
        """
        Called when details for a list of geocaches were downloaded.
        
        caches -- List of geocaches
        
        """
        for c in caches:
            self.pointprovider.add_point(c, True)
        self.pointprovider.save()
        self.emit('hide-progress')
        for c in caches:
            self.emit('cache-changed', c)
        self.emit('map-marks-changed')
        return False

    def on_download_progress(self, something, text, i, max_i):
        """
        Signal handler which is called when the downloading process has made progress.
        
        something -- not used
        text -- Text describing the current work item
        i -- Progress in relation to max_i
        max_i -- Expected maximum value of i (Actual displayed progress fraction is i/max_i)
        
        """
        logger.debug("Progress: %f of %f" % (i, max_i))
        self.emit('progress', float(i) / float(max_i), "%s..." % text)
        return False

    def on_already_downloading_error(self, something, error):
        """
        Signal handler which is called when the downloading thread cannot download because someone else is still downloading.
        
        """
        self.emit('error', error)
        
    def on_download_error(self, something, error):
        """
        Signal handler which is called when an error happened during a download (or upload).
        
        """
        extra_message = "Error:\n%s" % error
        logging.exception(error)
        self.emit('hide-progress')
        self.emit('error', extra_message)
    
    def default_download_skip_callback(self, geocache, found):
        """
        This is a default callback for skip_callback in download_overview. 
        
        This callback is called after the cachedownloader fetched a list of geocaches which are in a certain area and before it actually downloads the geocache's details. If the callback returns True, the cachedownloader will skip downloading details. It reads the settings and acts accordingly.
        
        geocache -- is None or the geocache which was fetched from the database before its details were updated
        found -- the (new) found status, as read from the web page
        
        """
        if self.settings['download_notfound'] and found:
            logger.debug("Geocache is marked as found, skipping!")
            return True
        if geocache == None or geocache.get_updated() == None: 
            logger.debug("Geocache %r was not in the database or had no update timestamp." % geocache)
            return False # When the geocache is not in the database or when it was downloaded before we introduced timestamps, don't skip!
        if self.settings['options_redownload_after'] > 0:
            diff = datetime.now() - geocache.get_updated() 
            if diff.days >= self.settings['options_redownload_after']:
                logger.debug("Geocache %s was not updated for %d days. It's time!" % (geocache.name, diff.days))
                return False
            logger.debug("Geocache %s was not updated for %d days. That's fine." % (geocache.name, diff.days))
            return True
        return False
        
    def get_geocache_by_name_async(self, id):
        self._geocache_by_name_event.clear()
        gobject.idle_add(self._get_geocache_by_name_async_idle, id, priority=gobject.PRIORITY_HIGH)
        res = self._geocache_by_name_event.wait(1)
        if res == False:
            logger.error("Screw it!")
            return None
        return self._geocache_by_name_result
        
    def _get_geocache_by_name_async_idle(self, id):
        self._geocache_by_name_result = self.get_geocache_by_name(id)
        self._geocache_by_name_event.set()

    ##############################################
    #
    # Exporting
    #
    ##############################################
                
    def export_cache(self, cache, format, folder):
        """
        Export descriptions of geocaches. Not maintained at the moment.
        
        """
        from exporter import GpxExporter
        if (format == 'gpx'):
            exporter = GpxExporter()
        else:
            raise Exception("Format currently not supported: %s" % format)

        self.emit('progress', 0.5, "Exporting %s..." % cache.name)
        try:
            exporter.export(cache, folder)
        except Exception, e:
            self.emit('error', e)
        finally:
            self.emit('hide-progress')
        

    ##############################################
    #
    # Fieldnotes
    #
    ##############################################

    def save_fieldnote(self, cache):
        """
        Save the fieldnote information for a geocache to the database.
        
        """
        if cache.logas == geocaching.GeocacheCoordinate.LOG_AS_FOUND:
            cache.found = 1

        elif cache.logas == geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND:
            cache.found = 0

        self.save_cache_attribute(cache, ('logas', 'logdate', 'fieldnotes', 'found'))
        self.emit('fieldnotes-changed')        

    def upload_fieldnotes(self):
        """
        Upload fieldnotes to the web site. 
        
        """
        caches = self.pointprovider.get_new_fieldnotes()
        
        t = Thread(target=self._download_upload_helper, args=['self.cachedownloader.upload_fieldnotes', self._upload_fieldnotes_complete, caches])
        t.daemon = True
        t.start()
        
    def _upload_fieldnotes_complete(self, caches):
        """
        Called when uploading of fieldnotes is complete.
        
        Resets the fieldnotes which were uploaded to "NO LOG".
        """
        for c in caches:
            c.logas = geocaching.GeocacheCoordinate.LOG_NO_LOG
            self.save_cache_attribute(c, 'logas')
            self.emit('cache-changed', c)
        self.emit('hide-progress')
        self.emit('fieldnotes-changed')

    def get_new_fieldnotes_count(self):
        """
        Return the number of pending fieldnotes.
        
        """
        return self.pointprovider.get_new_fieldnotes_count()


    ##############################################
    #
    # Geocache Handling
    #
    ##############################################

    def save_cache_attribute(self, cache, attribute):
        """
        Save the attribute of a geocache to the database.
        
        """
        if type(attribute) == tuple:
            for a in attribute:
                self.pointprovider.update_field(cache, a, cache.serialize_one(a), save=False)
            self.pointprovider.save()
        else:
            self.pointprovider.update_field(cache, attribute, cache.serialize_one(attribute))

    def set_alternative_position(self, cache, ap):
        """
        Sets the alternative position for a geocaches.
        
        An alternative position is a user-chosen geographic location for a geocache which differs from the original location. This is, for example, used for solved mystery geocaches.
        """
        cache.set_alternative_position(ap)
        self.save_cache_attribute(cache, ('alter_lat', 'alter_lon'))
        self.emit('map-marks-changed')


def start():
    """
    Start the application.
    
    """
    gobject.threads_init()
    Core(gui, gps, extensions)

def start_profile(what):
    """
    Uses cprofile to profile the method calls in the application. For developing only.
    
    """
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

if __name__ == "__main__":
    if '--profile' in argv:
        start_profile('start()')
    else:
        start()

