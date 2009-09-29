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
%(name)s --full
    Full User Interface, for desktop usage (not implemented yet)
    
If you don't like your mouse:
%(name)s post-note geocache-id --(found|not-found|note) text
        Post fieldnote for given geocache. If text is not given, it is read from the standard input (stdio).
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

importactions:
        --fetch-index coord1 coord2
        --fetch-index-radius coord1 radius

filter-options:
        --in coord1 coord2
        -f|--found
        -F|--not-found 
        -w|--was-downloaded
        
        -s|--size (min|max) 1..4|micro|small|regular|huge|other
        -d|--difficulty (min|max) 1.0..5.0
        -t|--terrain (min|max) 1.0..5.0
        -T|--type type,type,...
         type: virtual|regular|unknown|multi|event
        -o|--owner owner-search-string
        -n|--name name-search-string
        -i|--id id-search-string
        
actions:
        --print 
                Default action, prints tab-separated mlist of geocaches
        --fetch-details
                Downloads Descriptions etc. for selected geocaches
        --export-html folder
                Dumps HTML pages to given folder
        --export-gpx folder
                Dumps geocaches into separate GPX files
        --export-single-gpx file
                Dumps selected geocaches into a single GPX file
        --draw-map zoom file
                Draws one big JPEG file with the positions of the selected geocaches
        --draw-maps zoom folder [tiles]
                Draws a small JPEG image for every geocache. 
        
Preferred format for coordinates:
    N49 44.111 E6 29.123
    or
    N49.123456 E6.043212
'''


import json
import sys

import downloader
import geocaching
import gobject
import gpsreader
import os
import provider

#import cProfile
#import pstats


if len(sys.argv) == 1:
    print usage % ({'name' : sys.argv[0]})
    exit()
        
arg = sys.argv[1].strip()
if arg == '--simple':
    import simplegui
    gui = simplegui.SimpleGui
elif arg == '--desktop':
    import biggui
    gui = biggui.BigGui
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
        except Exception as e:
            print "Could not prevent Standby: %s" % e

class Core():
    SETTINGS_DIR = os.path.expanduser('~/.agtl')
    DEFAULT_SETTINGS = {
        'download_visible': True,
        'download_notfound': True,
        'download_new': True,
        'download_nothing': False,
        'download_create_index': True,
        'download_run_after': False,
        'download_run_after_string': '',
        'download_output_dir': os.path.expanduser('~/caches/'),
        'map_position_lat': 49.7540,
        'map_position_lon': 6.66135,
        'map_zoom': 7,
        'download_resize': True,
        'download_resize_pixel': 400,
        'options_show_name': True,
        'options_username': "Username",
        'options_password': "Pass",
        'last_target_lat': 50,
        'last_target_lon': 10,
        'last_target_name': 'default',
        'download_noimages': False,
        'download_map_path': os.path.expanduser('~/Maps/OSM/'),
        'options_hide_found': False
    }
            
    def __init__(self, guitype, root):
        if not os.path.exists(self.SETTINGS_DIR):
            os.mkdir(self.SETTINGS_DIR)


        dataroot = os.path.join(root, 'data')
        
        #self.standbypreventer = Standbypreventer()
        # seems to crash dbus/fso/whatever
                        
        self.__read_config()
                
        #self.standbypreventer.set_status(Standbypreventer.STATUS_SCREEN_ON)
                
        self.downloader = downloader.FileDownloader(self.settings['options_username'], self.settings['options_password'])
                
        #pointprovider = LiveCacheProvider()
        self.pointprovider = provider.PointProvider("%s/caches.db" % self.SETTINGS_DIR, self.downloader, geocaching.GeocacheCoordinate, 'geocaches')
        #self.userpointprovider = provider.PointProvider("%s/caches.db" % self.SETTINGS_DIR, self.downloader, geo.Coordinate, 'userpoints')
        self.userpointprovider = None
        #pointprovider = PointProvider(':memory:', self.downloader)
        #reader = GpxReader(pointprovider)
        #reader.read_file('../../file.loc')
        
        self.gui = guitype(self, self.pointprovider, self.userpointprovider, dataroot)
        self.gui.write_settings(self.settings)
                
        self.gps_thread = gpsreader.GpsReader(self)
        gobject.timeout_add(1000, self.__read_gps)
        
        self.gui.show()
                
                
                
    def __del__(self):
        self.settings = self.gui.read_settings()
        self.__write_config()
                                
                
                
    # called by gui
    def on_cache_selected(self, cache):
        self.gui.show_cache(cache)
                
    # called by gui
    def on_start_search_simple(self, text):
        #m = re.search(r'/([NS]?)\s*(\d{1,2})\.(\d{1,2})\D+(\d+)\s*([WE]?)\s*(\d{1,3})\.(\d{1,2})\D+(\d+)', text, re.I)
        #if m != None:
        self.__try_show_cache_by_search('%' + text + '%')
                
    # called by gui
    def on_start_search_advanced(self, found=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, location = None, marked = None):
                
                
        self.pointprovider.set_filter(found=found, owner_search=owner_search, name_search=name_search, size=size, terrain=terrain, diff=diff, ctype=ctype, marked = marked)
        points = self.pointprovider.get_points_filter(location)
        self.gui.display_results_advanced(points, len(points) > self.pointprovider.MAX_RESULTS)
                                

    # called by gui
    def on_destroy(self):
        self.settings = self.gui.read_settings()
        self.__write_config()

    # called by gui
    def on_download(self, location):
        cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
        try:
            caches = cd.get_geocaches(location)
        except Exception as e:
            self.gui.show_error(e)
            print e
            return []
        else:
            for c in caches:
                self.pointprovider.add_point(c)
            self.pointprovider.save()
            return caches

    # called by gui
    def on_download_cache(self, cache):
        self.gui.set_download_progress(0.5, "Downloading %s..." % cache.name)

        try:
            cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
            full = cd.update_coordinate(cache)
            self.pointprovider.add_point(full, True)
            self.pointprovider.save()
        except Exception as e:
                self.gui.show_error(e)
                return cache
        finally:
                self.gui.hide_progress()
        return full
                
    def on_export_cache(self, cache, folder = None):
        self.gui.set_download_progress(0.5, "Exporting %s..." % cache.name)
        try:
            exporter = geocaching.HTMLExporter(self.downloader, self.settings['download_output_dir'])
            exporter.export(cache, folder)
        except Exception as e:
                self.gui.show_error(e)
        finally:
                self.gui.hide_progress()
        
                
                
                
    # called by gui
    def on_download_descriptions(self, location, visibleonly=False):
        cd = geocaching.CacheDownloader(self.downloader, self.settings['download_output_dir'], not self.settings['download_noimages'])
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
                
                
                
        count = len(caches)
        i = 0.0
        try:
            for cache in caches:
                self.gui.set_download_progress(i / count, "Downloading %s..." % cache.name)
                full = cd.update_coordinate(cache)
                self.pointprovider.add_point(full, True)
                #exporter.export(full)
                i += 1.0
                                
        except Exception as e:
            self.gui.show_error(e)
        finally:
            self.gui.hide_progress()
            self.pointprovider.pop_filter()
        self.pointprovider.save()
                
                
        #if self.settings['download_create_index']:
        #        all_caches = pointprovider.get_points_filter(None, None, True)
        #        exporter.write_index(all_caches)

                

                        
    # called by gui
    def on_config_changed(self, new_settings):
        self.settings = new_settings
        self.downloader.update_userdata(self.settings['options_username'], self.settings['options_password'])
        self.__write_config()


    def on_notes_changed(self, cache, new_notes):
        self.pointprovider.update_field(cache, 'notes', new_notes)

    def on_fieldnotes_changed(self, cache, new_notes):
        self.pointprovider.update_field(cache, 'fieldnotes', new_notes)

                
    def on_upload_fieldnotes(self):
        self.gui.set_download_progress(0.5, "Uploading Fieldnotes...")

        caches = self.pointprovider.get_new_fieldnotes()
        fn = geocaching.FieldnotesUploader(self.downloader)
        try:
            for c in caches:
                fn.add_fieldnote(c)
            fn.upload()
                        
        except Exception as e:
            self.gui.show_error(e)
        else:
            #self.gui.show_success("Field notes uploaded successfully.")
            for c in caches:
                self.pointprovider.update_field(c, 'logas', geocaching.GeocacheCoordinate.LOG_NO_LOG)
        finally:
            self.gui.hide_progress()
                
    def __read_gps(self):
        gps_data = self.gps_thread.get_data()
        if (gps_data['position'] != None):
            self.gui.on_good_fix(gps_data)
        else:
            self.gui.on_no_fix(gps_data, self.gps_thread.status)
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
                    self.settings[k] = self.DEFAULT_SETTINGS[k]
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

