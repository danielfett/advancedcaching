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

 
### For the gui :-)
import gtk
import gobject
import pango
import extListview


import re

from htmlentitydefs import name2codepoint as n2cp

import math

import openstreetmap
import provider
import geo
import geocaching
import thread


class BigGui(GtkGui):
	MAP_FACTOR = 0
	CACHE_SIZE = 20
	CLICK_RADIUS = 10
	TOO_MUCH_POINTS = 400
	
	
    	SETTINGS_CHECKBOXES = [
    		'download_visible',
    		'download_notfound',
    		'download_new',
    		'download_nothing',
    		'download_create_index',
    		'download_run_after',
    		'download_resize',
    		'options_show_name'
    	]
    	SETTINGS_INPUTS = [
    		'download_run_after_string',
    		'download_output_dir',
    		'download_resize_pixel',
    		'options_username',
    		'options_password'
    	]
    	
	def __init__(self, core, pointprovider, userpointprovider):
		self.ts = ts = openstreetmap.TileServer()
		
		self.core = core
		self.pointprovider = pointprovider
		self.userpointprovider = userpointprovider
		
		self.current_cache = None
		self.dragging = False
		self.block_changes = False
		
		self.drawing_area_configured = False
		self.drag_offset_x = 0
		self.drag_offset_y = 0
		self.map_center_x, self.map_center_y = 100, 100
		self.inhibit_zoom = False
		self.draw_lock = thread.allocate_lock()
		
		global builder
		
		builder = gtk.Builder()
		builder.add_from_file("../../glade/main.glade")
		self.window = builder.get_object("window")
		
		builder.connect_signals({ "on_window_destroy" : self.destroy ,
			"on_zoomin_clicked" : self.on_zoomin_clicked ,
			"on_zoomout_clicked" : self.on_zoomout_clicked ,
			"on_download_clicked" : self.on_download_clicked,
			'save_config' : self.on_save_config,
			'on_button_download_now_clicked' : self.on_download_descriptions_clicked,
			'on_spinbutton_zoom_change_value' : self.on_zoom_changed,
			'start_search' : self.on_start_search_simple,
			'on_entry_search_key_release_event' : self.on_search_simple_key_release,
		#	'on_vscale_search_terrain_change_value' : self.search_value_terrain_change,
		#	'on_vscale_search_diff_change_value' : self.search_value_diff_change
			'on_button_advanced_search_clicked' : self.on_search_advanced_clicked,
			'on_check_search_find_no_details_toggled' : self.on_search_details_toggled
		})

		
		self.drawing_area = builder.get_object('drawingarea')
		self.drawing_area.connect("expose_event", self.expose_event)
		self.drawing_area.connect("configure_event", self.configure_event)
		self.drawing_area.connect("button_press_event", self.drag_start)
		self.drawing_area.connect("scroll_event", self.scroll)
		self.drawing_area.connect("button_release_event", self.drag_end)
		self.drawing_area.connect("motion_notify_event", self.drag)
		self.drawing_area.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.SCROLL)
		#self.drawing_area.show()
		
		
		self.zoom_adjustment = builder.get_object('spinbutton_zoom').get_adjustment()
		
		self.hpaned = builder.get_object("hpaned1")
		self.hpaned.set_position(0)
		self.cache_elements = {
			'name_downloaded':	builder.get_object('link_cache_name'),
			'name_not_downloaded': builder.get_object('button_cache_name'),
			'title': builder.get_object('label_cache_title'),
			'type': builder.get_object('label_cache_type'),
			'size': builder.get_object('label_cache_size'),
			'terrain': builder.get_object('label_cache_terrain'),
			'difficulty': builder.get_object('label_cache_difficulty'),
			'desc': builder.get_object('label_cache_desc'),
			'shortdesc': builder.get_object('label_cache_shortdesc'),
			'hints': builder.get_object('label_cache_hints'),
			'coords': builder.get_object('label_cache_coords'),
			'found': builder.get_object('check_cache_found'),
			'homepage': builder.get_object('link_cache_homepage'),
			'log': builder.get_object('link_cache_log'),
			'notebook': builder.get_object('notebook_cache')
		}
		
		self.search_elements = {
			'name' : builder.get_object('entry_search_name'),
			'owner' : builder.get_object('entry_search_owner'),
			'found' : {
				'true' : builder.get_object('radio_search_found_true'),
				'false' : builder.get_object('radio_search_found_false')
				},
			'type' : {
				'regular' : builder.get_object('check_search_type_traditional'),
				'multi' : builder.get_object('check_search_type_multi'),
				'unknown' : builder.get_object('check_search_type_unknown'),
				'virtual' : builder.get_object('check_search_type_virtual'),
				'other' : builder.get_object('check_search_type_other')
				},
			'size': {
				'1' : builder.get_object('check_search_size_1'),
				'2' : builder.get_object('check_search_size_2'),
				'3' : builder.get_object('check_search_size_3'),
				'4' : builder.get_object('check_search_size_4'),
				'5' : builder.get_object('check_search_size_other')
				},
			'terrain': {
				'lower' : builder.get_object('vscale_search_terrain_lower'),
				'upper' : builder.get_object('vscale_search_terrain_upper')
				},
			'diff': {
				'lower' : builder.get_object('vscale_search_diff_lower'),
				'upper' : builder.get_object('vscale_search_diff_upper')
				},
			'frames': {
				'type' : builder.get_object('frame_search_type'),
				'size' : builder.get_object('frame_search_size'),
				'terrain' : builder.get_object('frame_search_terrain'),
				'diff' : builder.get_object('frame_search_diff'),
			},
			'no_details': builder.get_object('check_search_no_details')
		}
		self.search_elements['terrain']['lower'].get_adjustment().set_value(1)
		self.search_elements['terrain']['upper'].get_adjustment().set_value(5)
		self.search_elements['diff']['lower'].get_adjustment().set_value(1)
		self.search_elements['diff']['upper'].get_adjustment().set_value(5)
		
		#
		# setting up TABLES
		#
		
		strings = self.pointprovider.get_titles_and_names()
		liststore = gtk.ListStore(gobject.TYPE_STRING)
		for string in strings:
			liststore.append([string])
		comp = builder.get_object('entrycompletion_search')
		entry = builder.get_object('entry_search')
		entry.set_completion(comp)
		comp.set_model(liststore)
		comp.set_text_column(0)
		self.entry_search = entry
		
		
		# Create the renderer used in the listview
		txtRdr    = gtk.CellRendererText()
		pixbufRdr = gtk.CellRendererPixbuf()
		(
			ROW_FOUND,
			ROW_TYPE,
			ROW_SIZE,
			ROW_TERRAIN,
			ROW_DIFF,
			ROW_ID,
			ROW_TITLE,
		) = range(7)
		columns = (
			('gefunden?', [(txtRdr, gobject.TYPE_STRING)], (ROW_FOUND,ROW_ID), False, True),
			('Typ', [(txtRdr, gobject.TYPE_STRING)], (ROW_TYPE,), False, True),
			('Größe', [(txtRdr, gobject.TYPE_STRING)], (ROW_SIZE,ROW_ID), False, True),
			('Terrain', [(txtRdr, gobject.TYPE_STRING)], (ROW_TERRAIN,ROW_ID), False, True),
			('Difficulty', [(txtRdr, gobject.TYPE_STRING)], (ROW_DIFF,ROW_ID), False, True),
			('ID', [(txtRdr, gobject.TYPE_STRING)], (ROW_ID,), False, True),
			('Titel', [(txtRdr, gobject.TYPE_STRING)], (ROW_TITLE,), False, True),
		)
		self.cachelist = listview = extListview.ExtListView(columns, sortable=True, useMarkup=False, canShowHideColumns=False)
		builder.get_object('scrolledwindow_search').add(listview)
		listview.connect('extlistview-button-pressed', self.on_search_cache_clicked)
		
		# Create the renderer used in the listview for user defined points
		
		txtRdr    = gtk.CellRendererText()
		pixbufRdr = gtk.CellRendererPixbuf()
		(
			ROW_COORD,
			ROW_COMMENT,
		) = range(2)
		columns = (
			('Position', [(txtRdr, gobject.TYPE_STRING)], (ROW_COORD), False, True),
			('Kommentar', [(txtRdr, gobject.TYPE_STRING)], (ROW_COMMENT,), False, True),
		)
		self.userpointlist = extListview.ExtListView(columns, sortable=True, useMarkup=False, canShowHideColumns=False)
		builder.get_object('scrolledwindow_userpoints').add(self.userpointlist)
		
		'''
	def center(coord):
		point = self.ts.deg2num(coord)
		size = self.ts.tile_size()
		p_x = (point[0] * size - self.map_center_x * size)
		p_y = (point[1] * size - self.map_center_y * size)
		'''
	
		
	def __configure_event(self, widget, event):
	
		x, y, width, height = widget.get_allocation()
		self.map_width = int(width  + 2 * width * self.MAP_FACTOR)
		self.map_height = int(height + 2 * height * self.MAP_FACTOR)
		try:
			openstreetmap.TileLoader.drawlock.acquire()
			self.pixmap = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)
		finally:
			openstreetmap.TileLoader.drawlock.release()
			
		self.xgc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
		#xgc.line_width = 3
		self.drawing_area_configured = True
		self.draw_at_x = 0
		self.draw_at_y = 0
		self.draw_root_x = int(-width * self.MAP_FACTOR)
		self.draw_root_y = int(-height * self.MAP_FACTOR)
		self.__draw_map()
		
	def __coord2point(self, coord):
		point = self.ts.deg2num(coord)
		size = self.ts.tile_size()
		
		p_x = int(point[0] * size - self.map_center_x * size + self.map_width/2)
		p_y = int(point[1] * size - self.map_center_y * size + self.map_height/2)
		return [p_x, p_y]
		
	
		
	def __decode_htmlentities(self, string):
		def substitute_entity(match):
			ent = match.group(3)
			if match.group(1) == "#":
				# decoding by number
				if match.group(2) == '':
					# number is in decimal
					return unichr(int(ent))
				elif match.group(2) == 'x':
					# number is in hex
					return unichr(int('0x'+ent, 16))
			else:
			    # they were using a name
			    cp = n2cp.get(ent)
			    if cp: 
			    	return unichr(cp)
			    else: 
			    	return match.group()

		entity_re = re.compile(r'&(#?)(x?)(\w+);')
		return entity_re.subn(substitute_entity, string)[0]
	
	def destroy(self, target):
		gtk.main_quit()	
	# called by core
	def display_results_advanced(self, caches):
		rows = []
		for r in caches:
			if r.found:
				f = 'ja'
			else:
				f = '  '
			if r.size == -1:
				s = "?"
			else:
				s = "%d" % r.size
				
			if r.difficulty == -1:
				d = "?"
			else:
				d = "%.1f" % r.difficulty
				
			if r.terrain == -1:
				t = "?"
			else:
				t = "%.1f" % r.terrain
			
			rows.append((f, r.type, s, t, d, r.name, r.title))
		self.cachelist.replaceContent(rows)		
		
	def __draw_map(self):
		if not self.drawing_area_configured:
			return False
	
		if self.map_width == 0 or self.map_height == 0:
			return
		size = self.ts.tile_size()
		xi = int(self.map_center_x)
		yi = int(self.map_center_y)
		span_x = int(math.ceil(float(self.map_width)/(size * 2.0)))
		span_y = int(math.ceil(float(self.map_height)/(size * 2.0)))
		tiles = []
		for i in range(0, span_x + 1, 1):
			for j in range(0, span_y + 1, 1):
				for dir in range(0, 4, 1):
					dir_ns = dir_ew = 1
					if dir % 2 == 1: # if dir == 1 or dir == 3
						dir_ns = -1
					if dir > 1:
						dir_ew = -1
				
					tile = (xi + (i * dir_ew), yi + (j * dir_ns))
					if not tile in tiles:
						tiles.append(tile)
						#print "Requesting ", tile, " zoom ", ts.zoom
					
						d = openstreetmap.TileLoader(tile, self.ts.zoom, self)
						d.start()

		
	def __drag(self, widget, event):
		if not self.dragging:
			return
		self.drag_offset_x = self.drag_start_x - event.x
		self.drag_offset_y = self.drag_start_y - event.y
		
	def __drag_end(self, widget, event):
		if not self.dragging:
			return
		self.dragging = False
		offset_x = (self.drag_start_x - event.x)
		offset_y = (self.drag_start_y - event.y)
		if abs(offset_x) < 3 or abs(offset_y) < 3:
			x, y = event.x, event.y
			c = self.screenpoint2coord([x, y])
			c1 = self.screenpoint2coord([x-self.CLICK_RADIUS, y-self.CLICK_RADIUS])
			c2 = self.screenpoint2coord([x+self.CLICK_RADIUS, y+self.CLICK_RADIUS])
			cache = self.pointprovider.get_nearest_point_filter(c, c1, c2)
			self.core.on_cache_selected(cache)
			return
		self.map_center_x += (offset_x / self.ts.tile_size())
		self.map_center_y += (offset_y / self.ts.tile_size())
		self.__draw_map()
		
			
	def __drag_draw(self):
		if not self.dragging:
			return False
		#if abs(self.drag_offset_x) < 3 or abs(self.drag_offset_y) < 3:
		#	return
		widget = self.drawing_area
		x, y, width, height = widget.get_allocation()
		
		widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
			self.pixmap, -self.draw_at_x + self.drag_offset_x - self.draw_root_x, -self.draw_at_y + self.drag_offset_y - self.draw_root_y, 0, 0, width, height)
		return True
	
		
	def __drag_start(self, widget, event):
		self.drag_start_x = event.x
		self.drag_start_y = event.y
		self.drag_offset_x = 0
		self.drag_offset_y = 0
		self.last_drag_offset_x = 0
		self.last_drag_offset_y = 0
		self.dragging = True
		gobject.timeout_add(50, self.drag_draw)
		
		
					
	def __draw_marks(self, thr):
		xgc = self.xgc
		"""
		position = Coordinate(49.75400, 6.66135)
		target = Coordinate(49.755900, 6.649933)
		bearing = 12
		
		p = self.coord2point(position)
		if p == False:
			return
		
		t = self.coord2point(target)
		if t == False:
			return
		
		xgc.line_width = 5		
		xgc.set_function(gtk.gdk.AND_INVERT)
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("blue"))
		self.pixmap.draw_line(xgc, p[0], p[1], t[0], t[1])
		
		xgc.line_width = 1
		length = 0.001 * (2 ** ts.zoom)
		xgc.set_function(gtk.gdk.COPY)
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("blue"))
		self.pixmap.draw_line(xgc, p[0], p[1], int(p[0] + math.cos(bearing) * length), int(p[1] + math.sin(bearing) * length))
		"""
		
		#
		# draw geocaches
		#
		
		coords = self.pointprovider.get_points_filter((self.pixmappoint2coord([0,0]), self.pixmappoint2coord([self.map_width, self.map_height])))
		draw_short = (len(coords) > self.TOO_MUCH_POINTS)

		xgc.set_function(gtk.gdk.AND)
		radius = 7
		color_default = gtk.gdk.color_parse('blue')
		color_found = gtk.gdk.color_parse('grey')
		color_regular = gtk.gdk.color_parse('green')
		color_multi = gtk.gdk.color_parse('orange')
		font = pango.FontDescription("Sans 8")
		num = 0
		for c in coords: # for each geocache
			color = color_default
			if c.found:
				color = color_found
			elif c.type == "regular":
				color = color_regular
			elif c.type == "multi":
				color = color_multi
			
			p = self.__coord2point(c)
			xgc.set_rgb_fg_color(color)
			
			xgc.line_width = 1
			self.pixmap.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
			self.pixmap.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---
			
			if draw_short:
				continue
			xgc.line_width = 3		
			self.pixmap.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)
			
			# print the name?
			if self.settings['options_show_name']:
				layout = self.drawing_area.create_pango_layout(c.name)
				layout.set_font_description(font)
				self.pixmap.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
			
			# if we have a description for this cache...
			if c.was_downloaded():
				# draw something like:
				# ----
				# ----
				# ----
				# besides the icon
				width = 6
				dist = 2
				pos_x = p[0] + radius + 3 + 1
				pos_y = p[1] + 2
				xgc.line_width = 1
				for i in range(0, 3):
					self.pixmap.draw_line(xgc, pos_x, pos_y + dist*i, pos_x + width, pos_y + dist * i)
			
			# if this cache is the active cache
			if self.current_cache != None and c.name == self.current_cache.name:
				xgc.line_width = 1		
				xgc.set_rgb_fg_color(gtk.gdk.color_parse('black'))
				radius = 8
				self.pixmap.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)
			

		# draw additional waypoints
		# --> print description!
		if self.current_cache != None and self.current_cache.waypoints != None:
			xgc.set_function(gtk.gdk.AND)
			xgc.set_rgb_fg_color(gtk.gdk.color_parse('red'))
			num = 0
			for w in self.current_cache.waypoints:
				if w['lat'] != -1 and w['lon'] != -1:
					num = num + 1
					xgc.line_width = 1
					radius = 4
					p = self.__coord2point(geo.Coordinate(w['lat'], w['lon']))
					self.pixmap.draw_line(xgc, p[0], p[1] - 3, p[0], p[1] + 4) #  |
					self.pixmap.draw_line(xgc, p[0] - 3, p[1], p[0] + 4, p[1]) # ---
					self.pixmap.draw_arc(xgc, False, p[0] - radius, p[1] - radius, radius*2, radius*2, 0, 360*64)
					layout = self.drawing_area.create_pango_layout('')
					layout.set_markup('<i>%s</i>' % (w['id']))
					layout.set_font_description(font)
					self.pixmap.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
		
			
		#
		# next, draw the user defined points
		#
		
		coords = self.userpointprovider.get_points_filter((self.pixmappoint2coord([0,0]), self.pixmappoint2coord([self.map_width, self.map_height])))

		xgc.set_function(gtk.gdk.AND)
		radius = 7
		color = gtk.gdk.color_parse('darkorchid')
		for c in coords: # for each geocache
			p = self.__coord2point(c)
			xgc.line_width = 3		
			xgc.set_rgb_fg_color(color)
			radius = 8
			self.pixmap.draw_line(xgc, p[0] - radius, p[1], p[0], p[1] + radius)
			self.pixmap.draw_line(xgc, p[0], p[1] + radius, p[0] + radius, p[1])
			self.pixmap.draw_line(xgc, p[0] + radius, p[1], p[0], p[1] - radius)
			self.pixmap.draw_line(xgc, p[0], p[1] - radius, p[0] - radius, p[1])
			xgc.line_width = 1
			self.pixmap.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
			self.pixmap.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---
			layout = self.drawing_area.create_pango_layout(c.name)
			layout.set_font_description(font)
			self.pixmap.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
		
		"""
		xgc.line_width = 2	
		radius_o = 20
		radius_i = 7
		xgc.set_function(gtk.gdk.INVERT)
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
		self.pixmap.draw_line(xgc, t[0] - radius_o, t[1], t[0] - radius_i, t[1])
		self.pixmap.draw_line(xgc, t[0] + radius_o, t[1], t[0] + radius_i, t[1])
		self.pixmap.draw_line(xgc, t[0], t[1] + radius_o, t[0], t[1] + radius_i)
		self.pixmap.draw_line(xgc, t[0], t[1] - radius_o, t[0], t[1] - radius_i)
		
		xgc.set_function(gtk.gdk.INVERT)
		self.pixmap.draw_point(xgc, t[0], t[1])
		"""
		
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
		xgc.set_function(gtk.gdk.COPY)	
		self.refresh()
		return False	
	
	def expose_event(self, widget, event):
		x , y, width, height = event.area
		try:
			openstreetmap.TileLoader.drawlock.acquire()
			widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
				self.pixmap, x, y, self.draw_root_x + self.draw_at_x  + x , self.draw_root_y + self.draw_at_y + y, -1, -1)
			# width, height hier? 
		finally:
			openstreetmap.TileLoader.drawlock.release()
		return False

	def get_visible_area(self):
		return (self.pixmappoint2coord([0,0]), self.pixmappoint2coord([self.map_width, self.map_height]))
		
		
	def on_download_descriptions_clicked(self, something):
		self.core.on_download_descriptions(self.get_visible_area())
		self.__draw_map()
		
	def on_download_clicked(self, something):
		self.core.on_download(self.get_visible_area())
		self.__draw_map()
					
	def on_save_config(self, something):
		if not self.block_changes:
			self.core.on_config_changed(self.read_settings())
		
	def on_search_advanced_clicked(self, something):
		if self.search_elements['found']['true'].get_active():
			found = True
		elif self.search_elements['found']['false'].get_active():
			found = False
		else:
			found = None
		
		owner_search = self.search_elements['owner'].get_text()
		name_search = self.search_elements['name'].get_text()
		
		if not self.search_elements['type']['other'].get_active():
			ctype = []
			for type, el in self.search_elements['type'].items():
				if el.get_active():
					ctype.append(type)
		else:
			ctype = None
			
		if not self.search_elements['no_details'].get_active():
			size = []
			for s in range(1,6):
				if self.search_elements['size'][str(s)].get_active():
					size.append(s)
				
			terrain = [self.search_elements['terrain']['lower'].get_adjustment().get_value(),
				self.search_elements['terrain']['upper'].get_adjustment().get_value()]
			diff = [self.search_elements['diff']['lower'].get_adjustment().get_value(),
				self.search_elements['diff']['upper'].get_adjustment().get_value()]
		else:
			size = terrain = diff = None
		self.core.on_start_search_advanced(found, owner_search, name_search, size, terrain, diff, ctype)

		
	def on_search_details_toggled(self, some=None):
		for k,i in self.search_elements['frames'].items():
			if k != 'type':
				i.set_sensitive(not self.search_elements['no_details'].get_active())

	def on_search_cache_clicked(self, listview, event, element):
		if event.type != gtk.gdk._2BUTTON_PRESS or element == None:
			return
		
		cachename = listview.getItem(element[0], 5)
		cache = self.pointprovider.find_by_string(cachename)
		self.core.on_cache_selected(cache)
		
		
	def on_search_key_release(self, widget, event):
		print event.keyval
		if event.keyval == 65293:  # seems to be keycode of return key
			self.core.on_start_search_simple(self.widget.get_text())
		
	def on_search_simple_key_release(self, something):
		self.core.on_start_search_simple(self.widget.get_text())
		
		
	def on_start_search_simple(self, something):
		self.core.on_start_search_simple(self.entry_search.get_text())	
			
	def on_zoom_changed(self, blub):
		if not self.inhibit_zoom:
			self.zoom()
		
	def on_zoomin_clicked(self, widget):
		self.zoom(+1)
		
	def on_zoomout_clicked(self, widget):
		self.zoom(-1)	
	
	def pixmappoint2coord(self, point):
		size = self.ts.tile_size()	
		coord = self.ts.num2deg( 
			(point[0] + self.map_center_x * size - self.map_width/2)/size,
			(point[1] + self.map_center_y * size - self.map_height/2)/size
			)
		return coord

	def read_settings(self):
		c = self.ts.num2deg(self.map_center_x, self.map_center_y)
		settings = {
			'map_position_lat' : c.lat,
			'map_position_lon' : c.lon
		}
		for x in self.SETTINGS_CHECKBOXES:
			settings[x] = builder.get_object('check_%s' % x).get_active()
		
		for x in self.SETTINGS_INPUTS:
			settings[x] = builder.get_object('input_%s' % x).get_text()
		
		self.settings = settings
		return settings
			
		
	def refresh(self):
		self.drawing_area.queue_draw()		
			
	def replace_image_tag(self, m):
		if m.group(1) != None and m.group(1).strip() != '':
			return ' [Bild: %s] ' % m.group(1).strip()
		else:
			return ' [Bild] '
			
	def screenpoint2coord(self, point):
		size = self.ts.tile_size()	
		coord = self.ts.num2deg( 
			((point[0] - self.draw_root_x - self.draw_at_x) + self.map_center_x * size - self.map_width/2)/size,
			((point[1] - self.draw_root_y - self.draw_at_y) + self.map_center_y * size - self.map_height/2)/size
			)
		return coord
	
	def scroll(self, widget, event):
		if event.direction == gtk.gdk.SCROLL_DOWN:
			self.zoom(-1)	
		else:
			self.zoom(+1)	
	def show(self):
		self.window.show_all()	
		gtk.main()
		
			
	# called by core
	def show_cache(self, cache):
		if cache == None:
			self.hpaned.set_position(0)
			return
		self.current_cache = cache
		self.hpaned.set_position(-1)
		if cache.was_downloaded():
			uri = 'file://%s/%s.html' % (self.settings['download_output_dir'], cache.name)
			self.cache_elements['name_downloaded'].set_uri(uri)
			self.cache_elements['name_downloaded'].set_label(cache.name)
			self.cache_elements['name_downloaded'].show()
			self.cache_elements['name_not_downloaded'].hide()
		else:
			self.cache_elements['name_not_downloaded'].set_label(cache.name)
			self.cache_elements['name_downloaded'].hide()
			self.cache_elements['name_not_downloaded'].show()
		self.cache_elements['title'].set_text(cache.title)
		self.cache_elements['type'].set_text("%s" % cache.type)
		self.cache_elements['size'].set_text("%d/5" % cache.size)
		self.cache_elements['terrain'].set_text("%.1f/5" % (cache.terrain/10.0))
		self.cache_elements['difficulty'].set_text("%.1f/5" % (cache.difficulty/10.0))
		
		set_page = False
		
		text_shortdesc = self.strip_html(cache.shortdesc).strip()[:600]
		if text_shortdesc == '':
			text_shortdesc = '(Keine Kurzbeschreibung vorhanden)'
		else:
			self.cache_elements['notebook'].set_current_page(0)
			set_page = True
			
		text_desc = self.strip_html(cache.desc).strip()[:600]
		if text_desc == '':
			text_desc = '(Keine Beschreibung vorhanden)'
		if not set_page:
			self.cache_elements['notebook'].set_current_page(1)
			
		text_hints = cache.hints.strip()
		if text_hints == '':
			text_hints = '(Keine Hints vorhanden)'
			
		text_coords = 'Start: %s\n' % cache
		for w in cache.waypoints:
			if not (w['lat'] == -1 and w['lon'] == -1):
				n = geo.Coordinate(w['lat'], w['lon'])
				latlon = "%s %s" % (re.sub(r' ', '', n.get_lat(geo.Coordinate.FORMAT_DM)), re.sub(r' ', '', n.get_lon(geo.Coordinate.FORMAT_DM)))
			else:
				latlon = "???"
			text_coords += "<b>%s</b> <tt>%s</tt> <i>%s</i>\n<small>%s</small>" % (w['id'], latlon, w['name'], w['comment'])
			
		self.cache_elements['desc'].set_text(text_desc)
		self.cache_elements['shortdesc'].set_text(text_shortdesc)
		self.cache_elements['hints'].set_text(text_hints)
		self.cache_elements['coords'].set_use_markup(True)
		self.cache_elements['coords'].set_text(text_coords)
		self.cache_elements['found'].set_active(cache.found)
		self.cache_elements['homepage'].set_uri('http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % cache.name)
		self.cache_elements['log'].set_uri('http://www.geocaching.com/seek/log.aspx?wp=%s' % cache.name)
		
		
	def set_center(self, coord):
		builder.get_object("notebook_all").set_current_page(0)
		self.map_center_x, self.map_center_y = self.ts.deg2num(coord)
		self.draw_at_x = 0
		self.draw_at_y = 0
		self.__draw_map()

	
	def strip_html(self, text):
		text = re.sub(r"""(?i)<img[^>]+alt=["']?([^'"> ]+)[^>]+>""", self.replace_image_tag, text)
		text = re.sub(r'<[^>]*?>', '', text)
		text = self.__decode_htmlentities(text)
		text = re.sub(r'[\n\r]+\s*[\n\r]+', '\n', text)
		return text
		
	def write_settings(self, settings):
		self.settings = settings
		self.block_changes = True
		self.set_center(geo.Coordinate(self.settings['map_position_lat'],self.settings['map_position_lon']))

		for x in self.SETTINGS_CHECKBOXES:
			if x in self.settings.keys():
				builder.get_object('check_%s' % x).set_active(self.settings[x])
			elif x in self.DEFAULT_SETTINGS.keys():
				builder.get_object('check_%s' % x).set_active(self.DEFAULT_SETTINGS[x])
	
		for x in self.SETTINGS_INPUTS:
			if x in self.settings.keys():
				builder.get_object('input_%s' % x).set_text(str(self.settings[x]))
			elif x in self.DEFAULT_SETTINGS.keys():
				builder.get_object('input_%s' % x).set_text(self.DEFAULT_SETTINGS[x])	
					
		self.block_changes = False
		
	def zoom(self, direction = None):
		size = self.ts.tile_size()
		center = self.ts.num2deg(self.map_center_x - float(self.draw_at_x)/size, self.map_center_y - float(self.draw_at_y)/size)
		if direction == None:
			newzoom = self.zoom_adjustment.get_value()
		else:
			newzoom = self.ts.get_zoom() + direction
		self.ts.set_zoom(newzoom)
		self.inhibit_zoom = True
		self.zoom_adjustment.set_value(self.ts.get_zoom())
		self.inhibit_zoom = False
		self.set_center(center)
