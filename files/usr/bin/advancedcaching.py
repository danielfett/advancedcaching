#!/usr/bin/python
# -*- coding: utf-8 -*-

#	Copyright (C) 2009 Daniel Fett
# 	This program is free software: you can redistribute it and/or modify
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
#	Author: Daniel Fett simplecaching@fragcom.de
#



### For loading the conf file
from advancedcachinglib.geocaching import FieldnotesUploader
import os
import sys
import gtk
import gobject
import json

#import cProfile
#import pstats

sys.path.append('/usr/lib/site-python')
from advancedcachinglib import provider, openstreetmap, extListview, downloader, geo, geocaching, gpsreader


if len(sys.argv) != 2:
	print "Usage: %s --desktop (not fully implemented yet) or %s --simple" % (sys.argv[0], sys.argv[0])
	exit()
	
arg = sys.argv[1].strip()
if arg == '--simple':
	from advancedcachinglib import simplegui
	gui = simplegui.SimpleGui	
else:
	from advancedcachinglib import biggui
	gui = biggui.BigGui
	
	
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
    		'download_visible' : True,
    		'download_notfound' : True,
    		'download_new' : True,
    		'download_nothing' : False,
    		'download_create_index' : True,
    		'download_run_after' : False,
    		'download_run_after_string' : '',
    		'download_output_dir' : os.path.expanduser('~/caches/'),
    		'map_position_lat' : 49.7540,
    		'map_position_lon' : 6.66135,
    		'map_zoom' : 7,
    		'download_resize' : True,
    		'download_resize_pixel' : 400,
    		'options_show_name' : True,
    		'options_username' : "Username",
    		'options_password' : "Pass",
    		'last_target_lat' : 50,
    		'last_target_lon' : 10,
    		'last_target_name' : 'default',
		'download_noimages' : False,
		'download_map_path' : os.path.expanduser('~/Maps/OSM/'),
		'options_hide_found' : False
    	}
    	
	def __init__(self, guitype):	
		if not os.path.exists(self.SETTINGS_DIR):
			os.mkdir(self.SETTINGS_DIR)
			
		#self.standbypreventer = Standbypreventer()
		# seems to crash dbus/fso/whatever
			
		self.__read_config()
		
		#self.standbypreventer.set_status(Standbypreventer.STATUS_SCREEN_ON)
		
		self.downloader = downloader.FileDownloader(self.settings['options_username'], self.settings['options_password'])
		
		#pointprovider = LiveCacheProvider()
		self.pointprovider = provider.PointProvider("%s/caches.db" % self.SETTINGS_DIR, self.downloader, geocaching.GeocacheCoordinate, 'geocaches')
		self.userpointprovider = provider.PointProvider("%s/caches.db" % self.SETTINGS_DIR, self.downloader, geo.Coordinate, 'userpoints')
		#pointprovider = PointProvider(':memory:', self.downloader)
		#reader = GpxReader(pointprovider)
		#reader.read_file('../../file.loc')
		

		self.gui = guitype(self, self.pointprovider, self.userpointprovider)
		self.gui.write_settings(self.settings)
		
		self.gps_thread = gpsreader.GpsReader(self)
		gobject.timeout_add(1000, self.__read_gps)
		#self.downloader.upload_fieldnotes()
		self.gui.show()
		
		
		
	def __del__(self):
		self.settings = self.gui.read_settings()
		self.__write_config()
		
	#def search_value_terrain_change(self, a):
#		#print a, b, c
		#if self.search_elements['terrain']['upper'].get_adjustment().get_value() < self.search_elements['terrain']['lower'].get_adjustment().get_value():
		#	self.search_elements['terrain'][
	#def search_value_diff_change(self, widget):
		#pass
		
		

		
		
		
	# called by gui
	def on_cache_selected(self, cache):
		self.gui.show_cache(cache)
		
	# called by gui
	def on_start_search_simple(self, text):
		#m = re.search(r'/([NS]?)\s*(\d{1,2})\.(\d{1,2})\D+(\d+)\s*([WE]?)\s*(\d{1,3})\.(\d{1,2})\D+(\d+)', text, re.I)
		#if m != None:
		self.__try_show_cache_by_search('%' + text + '%')
		
	# called by gui
	def on_start_search_advanced(self, found = None, owner_search = '', name_search = '', size = None, terrain = None, diff = None, ctype = None):
		
		
		self.pointprovider.set_filter(found = found, owner_search = owner_search, name_search = name_search, size = size, terrain = terrain, diff = diff, ctype = ctype)
		points = self.pointprovider.get_points_filter()
		self.gui.display_results_advanced(points)
				

	# called by gui
	def on_destroy(self):
		self.settings = self.gui.read_settings()
		self.__write_config()

	# called by gui
	def on_download(self, location):
		cd = geocaching.CacheDownloader(self.downloader)
		caches = cd.get_geocaches(location)
		for c in caches:
			self.pointprovider.add_point(c)
		self.pointprovider.save()

	# called by gui
	def on_download_cache(self, cache):
		try:
		    cd = geocaching.CacheDownloader(self.downloader)
		    exporter = geocaching.HTMLExporter(self.downloader, self.settings['download_output_dir'], self.settings['download_noimages'])
		    full = cd.update_coordinate(cache)
		    self.pointprovider.add_point(full, True)
		    exporter.export(full)
		    self.pointprovider.save()
		except Exception as e:
			self.gui.show_error(e)
		
		
		
		
	# called by gui
	def on_download_descriptions(self, location, visibleonly = False):
		cd = geocaching.CacheDownloader(self.downloader)
		exporter = geocaching.HTMLExporter(self.downloader, self.settings['download_output_dir'], None, self.settings['download_noimages'])
		
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
			self.pointprovider.set_filter(found = found, has_details = has_details, adapt_filter = True)
			caches = self.pointprovider.get_points_filter(location)
		else:
			self.pointprovider.set_filter(found = found, has_details = has_details, adapt_filter = False)
			caches = self.pointprovider.get_points_filter()
		
		
		
		count = len(caches)
		i = 0.0
		try:
			for cache in caches:
				self.gui.set_download_progress(i/count, "Downloading %s..." % cache.name)
				while gtk.events_pending():
					gtk.main_iteration()
				full = cd.update_coordinate(cache)
				self.pointprovider.add_point(full, True)
				exporter.export(full)
				i += 1.0
				
			self.gui.set_download_progress(0, 'Finished!')
			self.gui.hide_progress()
		except Exception as e:
			self.gui.show_error(e)
		self.pointprovider.save()	
		
		self.pointprovider.pop_filter()
		
		#if self.settings['download_create_index']:
		#	all_caches = pointprovider.get_points_filter(None, None, True)
		#	exporter.write_index(all_caches)

		

			
	# called by gui
	def on_config_changed(self, new_settings):
		self.settings = new_settings
		self.downloader.update_userdata(self.settings['options_username'], self.settings['options_password'])
		self.__write_config()
		
	def on_upload_fieldnotes(self):
		caches = self.pointprovider.get_new_fieldnotes()
		fn = FieldnotesUploader(self.downloader)
		try:
			for c in caches:
				fn.add_fieldnote(c)
			fn.upload()
			
		except Exception as e:
			raise
			#self.gui.show_error(e)
		else:
			self.gui.show_success("Field notes uploaded successfully.")
			for c in caches:
				self.pointprovider.update_field(c, 'logas', geocaching.GeocacheCoordinate.LOG_NO_LOG)

		
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


	

			

		
if __name__ == "__main__":
	gtk.gdk.threads_init()
	core = Core(gui)

		

