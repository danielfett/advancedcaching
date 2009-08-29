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
import gc
import extListview
import json


import re

from htmlentitydefs import name2codepoint as n2cp

import math

import openstreetmap
import provider
import geo
import geocaching
import thread


class GtkGui():

	def __init__(self):
		self.ts = ts = openstreetmap.TileServer()
		
		self.core = core
		self.pointprovider = pointprovider
		self.userpointprovider = userpointprovider
		
		self.format = geo.Coordinate.FORMAT_DM
		
		self.current_cache = None
		
		self.current_target = None
		self.gps_data = None
		self.gps_has_fix = False
		self.gps_last_position = None
		self.drawing_area_configured = False
		
		
		# Create the renderer used in the listview
		txtRdr	= gtk.CellRendererText()
		(
			ROW_TYPE,
			ROW_SIZE,
			ROW_TERRAIN,
			ROW_DIFF,
			ROW_ID,
			ROW_TITLE,
		) = range(6)
		columns = (
			('typ', [(txtRdr, gobject.TYPE_STRING)], (ROW_TYPE,), False, True),
			('size', [(txtRdr, gobject.TYPE_STRING)], (ROW_SIZE,ROW_ID), False, True),
			('ter', [(txtRdr, gobject.TYPE_STRING)], (ROW_TERRAIN,ROW_ID), False, True),
			('dif', [(txtRdr, gobject.TYPE_STRING)], (ROW_DIFF,ROW_ID), False, True),
			('ID', [(txtRdr, gobject.TYPE_STRING)], (ROW_ID,), False, True),
			('name', [(txtRdr, gobject.TYPE_STRING)], (ROW_TITLE,), False, True),
		)
		self.cachelist = listview = extListview.ExtListView(columns, sortable=True, useMarkup=False, canShowHideColumns=False)
		xml.get_widget('scrolledwindow_search').add(listview)
		listview.connect('extlistview-button-pressed', self.on_search_cache_clicked)
		
		
		# Create the renderer used in the listview for coordinates
		
		txtRdr	= gtk.CellRendererText()
		pixbufRdr = gtk.CellRendererPixbuf()
		(
			COL_COORD_ID,
			COL_COORD_LATLON,
			COL_COORD_NAME,
			COL_COORD_COMMENT,
		) = range(4)
		columns = (
			('id', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_ID), False, True),
			('pos', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_LATLON), False, True),
			('name', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_NAME), False, True),
			('comment', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_COMMENT,), False, True),
		)
		self.coordlist = extListview.ExtListView(columns, sortable=True, useMarkup=False, canShowHideColumns=False)
		xml.get_widget('scrolledwindow_coordlist').add(self.coordlist)
		self.coordlist.connect('extlistview-button-pressed', self.on_waypoint_clicked)
		
		
		
	def coord2point(self, coord):
		point = self.ts.deg2num(coord)
		size = self.ts.tile_size()
		
		p_x = int(point[0] * size - self.map_center_x * size + self.map_width/2)
		p_y = int(point[1] * size - self.map_center_y * size + self.map_height/2)
		return [p_x, p_y]
		
		
	def decode_htmlentities(self, string):
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
		
	def configure_event(self, widget, event):
	
		x, y, width, height = widget.get_allocation()
		self.map_width = int(width  + 2 * width * self.MAP_FACTOR)
		self.map_height = int(height + 2 * height * self.MAP_FACTOR)
		try:
			openstreetmap.TileLoader.drawlock.acquire()
			self.pixmap = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)
		finally:
			openstreetmap.TileLoader.drawlock.release()
			
		self.pixmap_marks = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)
		self.xgc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
		#xgc.line_width = 3
		self.drawing_area_configured = True
		self.draw_at_x = 0
		self.draw_at_y = 0
		self.draw_root_x = int(-width * self.MAP_FACTOR)
		self.draw_root_y = int(-height * self.MAP_FACTOR)
		self.draw_map()
		
		
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
			
			rows.append((r.type, s, t, d, r.name, r.title))
		self.cachelist.replaceContent(rows)
		
		
	def drag(self, widget, event):
		if not self.dragging:
			return
		self.drag_offset_x = self.drag_start_x - event.x
		self.drag_offset_y = self.drag_start_y - event.y
		
	def drag_end(self, widget, event):
		if not self.dragging:
			return
		self.dragging = False
		offset_x = (self.drag_start_x - event.x)
		offset_y = (self.drag_start_y - event.y)
		self.map_center_x += (offset_x / self.ts.tile_size())
		self.map_center_y += (offset_y / self.ts.tile_size())
		if offset_x**2 + offset_y ** 2 < self.CLICK_RADIUS ** 2:
			self.draw_at_x -= offset_x
			self.draw_at_y -= offset_y
			x, y = event.x, event.y
			c = self.screenpoint2coord([x, y])
			c1 = self.screenpoint2coord([x-self.CLICK_RADIUS, y-self.CLICK_RADIUS])
			c2 = self.screenpoint2coord([x+self.CLICK_RADIUS, y+self.CLICK_RADIUS])
			cache = self.pointprovider.get_nearest_point_filter(c, c1, c2)
			self.core.on_cache_selected(cache)
			return
		self.draw_at_x = self.draw_at_y = 0
		self.draw_map()
		
			
	def drag_draw(self):
		if not self.dragging:
			return False
		#if abs(self.drag_offset_x) < 3 or abs(self.drag_offset_y) < 3:
		#	return
		widget = self.drawing_area
		x, y, width, height = widget.get_allocation()
		gc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
		gc.set_function(gtk.gdk.COPY)
		widget.window.draw_drawable(gc,
			self.pixmap, -self.draw_at_x + self.drag_offset_x - self.draw_root_x, -self.draw_at_y + self.drag_offset_y - self.draw_root_y, 0, 0, width, height)
		return True
	
		
	def drag_start(self, widget, event):
		self.drag_start_x = event.x
		self.drag_start_y = event.y
		self.drag_offset_x = 0
		self.drag_offset_y = 0
		self.last_drag_offset_x = 0
		self.last_drag_offset_y = 0
		self.dragging = True
		gobject.timeout_add(100, self.drag_draw)
		
		
	def draw_map(self):
		if not self.drawing_area_configured:
			return False
	
		if self.map_width == 0 or self.map_height == 0:
			return
		self.draw_marks()
		
		self.xgc.set_function(gtk.gdk.COPY)
		self.xgc.set_rgb_fg_color(gtk.gdk.color_parse('white'))
		self.pixmap.draw_rectangle(self.xgc, True, 0, 0, self.map_width, self.map_height)
			
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

					
	def draw_marks(self, thr = None):
		
		xgc = self.xgc
		xgc.set_function(gtk.gdk.COPY)
		self.xgc.set_rgb_fg_color(gtk.gdk.color_parse('white'))
		self.pixmap_marks.draw_rectangle(self.xgc, True, 0, 0, self.map_width, self.map_height)
		
		#
		# draw geocaches
		#
		
		coords = self.pointprovider.get_points_filter((self.pixmappoint2coord([0,0]), self.pixmappoint2coord([self.map_width, self.map_height])))
		draw_short = (len(coords) > self.TOO_MUCH_POINTS)

		xgc.set_function(gtk.gdk.COPY)
		color_default = gtk.gdk.color_parse('blue')
		color_found = gtk.gdk.color_parse('grey')
		color_regular = gtk.gdk.color_parse('green')
		color_multi = gtk.gdk.color_parse('orange')
		font = pango.FontDescription(self.CACHE_DRAW_FONT)
		num = 0
		for c in coords: # for each geocache
			radius = self.CACHE_DRAW_SIZE
			color = color_default
			if c.found:
				color = color_found
			elif c.type == "regular":
				color = color_regular
			elif c.type == "multi":
				color = color_multi
			
			p = self.coord2point(c)
			xgc.set_rgb_fg_color(color)
			
			
			if draw_short:
				radius = radius/2.0
				
			xgc.line_width = 3		
			self.pixmap_marks.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)
			if draw_short:
				continue
				
			
			xgc.line_width = 1
			self.pixmap_marks.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
			self.pixmap_marks.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---
			
			# print the name?
			if self.settings['options_show_name']:
				layout = self.drawing_area.create_pango_layout(c.name)
				layout.set_font_description(font)
				self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
			
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
					self.pixmap_marks.draw_line(xgc, pos_x, pos_y + dist*i, pos_x + width, pos_y + dist * i)
			
			# if this cache is the active cache
			if self.current_cache != None and c.name == self.current_cache.name:
				xgc.line_width = 1		
				xgc.set_rgb_fg_color(gtk.gdk.color_parse('red'))
				radius = 8
				self.pixmap_marks.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)
			

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
					p = self.coord2point(geo.Coordinate(w['lat'], w['lon']))
					self.pixmap_marks.draw_line(xgc, p[0], p[1] - 3, p[0], p[1] + 4) #  |
					self.pixmap_marks.draw_line(xgc, p[0] - 3, p[1], p[0] + 4, p[1]) # ---
					self.pixmap_marks.draw_arc(xgc, False, p[0] - radius, p[1] - radius, radius*2, radius*2, 0, 360*64)
					layout = self.drawing_area.create_pango_layout('')
					layout.set_markup('<i>%s</i>' % (w['id']))
					layout.set_font_description(font)
					self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
		
			
		#
		# next, draw the user defined points
		#
		"""
		coords = self.userpointprovider.get_points_filter((self.pixmap_markspoint2coord([0,0]), self.pixmap_markspoint2coord([self.map_width, self.map_height])))

		xgc.set_function(gtk.gdk.AND)
		radius = 7
		color = gtk.gdk.color_parse('darkorchid')
		for c in coords: # for each geocache
			p = self.coord2point(c)
			xgc.line_width = 3		
			xgc.set_rgb_fg_color(color)
			radius = 8
			self.pixmap_marks.draw_line(xgc, p[0] - radius, p[1], p[0], p[1] + radius)
			self.pixmap_marks.draw_line(xgc, p[0], p[1] + radius, p[0] + radius, p[1])
			self.pixmap_marks.draw_line(xgc, p[0] + radius, p[1], p[0], p[1] - radius)
			self.pixmap_marks.draw_line(xgc, p[0], p[1] - radius, p[0] - radius, p[1])
			xgc.line_width = 1
			self.pixmap_marks.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
			self.pixmap_marks.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---
			layout = self.drawing_area.create_pango_layout(c.name)
			layout.set_font_description(font)
			self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
		
		"""
		#
		# and now for our current data!
		#
		
		
		
		# if we have a target, draw it
		if self.current_target != None:
			t = self.coord2point(self.current_target)
			if t != False:
			
	
				xgc.line_width = 2	
				radius_o = 10
				radius_i = 3
				xgc.set_function(gtk.gdk.INVERT)
				xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
				self.pixmap_marks.draw_line(xgc, t[0] - radius_o, t[1], t[0] - radius_i, t[1])
				self.pixmap_marks.draw_line(xgc, t[0] + radius_o, t[1], t[0] + radius_i, t[1])
				self.pixmap_marks.draw_line(xgc, t[0], t[1] + radius_o, t[0], t[1] + radius_i)
				self.pixmap_marks.draw_line(xgc, t[0], t[1] - radius_o, t[0], t[1] - radius_i)
		else:
			t = False
		
		
		
		if self.gps_data != None and self.gps_data['position'] != None:
			# if we have a position, draw a black cross
			p = self.coord2point(self.gps_data['position'])
			if p != False:
				
		
				xgc.line_width = 2	
				radius_o = 20
				radius_i = 7
				xgc.set_function(gtk.gdk.COPY)
				xgc.set_rgb_fg_color(gtk.gdk.color_parse("red"))
				
				# \  /
				#
				# /  \
				self.pixmap_marks.draw_line(xgc, p[0] - radius_o, p[1] - radius_o, p[0] - radius_i, p[1] - radius_i)
				self.pixmap_marks.draw_line(xgc, p[0] + radius_o, p[1] + radius_o, p[0] + radius_i, p[1] + radius_i)
				self.pixmap_marks.draw_line(xgc, p[0] + radius_o, p[1] - radius_o, p[0] + radius_i, p[1] - radius_i)
				self.pixmap_marks.draw_line(xgc, p[0] - radius_o, p[1] + radius_o, p[0] - radius_i, p[1] + radius_i)
				self.pixmap_marks.draw_point(xgc, p[0], p[1])
		
				
				# if we have a bearing, draw it.
				if self.gps_data['bearing'] != None:
					bearing = self.gps_data['bearing']
			
					xgc.line_width = 1
					length = 10
					xgc.set_function(gtk.gdk.COPY)
					xgc.set_rgb_fg_color(gtk.gdk.color_parse("blue"))
					self.pixmap_marks.draw_line(xgc, p[0], p[1], int(p[0] + math.cos(bearing) * length), int(p[1] + math.sin(bearing) * length))
				
				# and a line between target and position if we have both
				if t != False:
					xgc.line_width = 5		
					xgc.set_function(gtk.gdk.AND_INVERT)
					xgc.set_rgb_fg_color(gtk.gdk.color_parse("blue"))
					self.pixmap_marks.draw_line(xgc, p[0], p[1], t[0], t[1])
				
			
		
		xgc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
		xgc.set_function(gtk.gdk.COPY)	
		#self.refresh()
		return False	
	
	def expose_event(self, widget, event):
		x , y, width, height = event.area
		try:
			openstreetmap.TileLoader.drawlock.acquire()
			gc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
			gc.set_function(gtk.gdk.COPY)
			widget.window.draw_drawable(gc,
				self.pixmap, x, y, self.draw_root_x + self.draw_at_x  + x , self.draw_root_y + self.draw_at_y + y, -1, -1)
			gc.set_function(gtk.gdk.EQUIV)
			widget.window.draw_drawable(gc,
				self.pixmap_marks, x, y, self.draw_root_x + self.draw_at_x  + x , self.draw_root_y + self.draw_at_y + y, -1, -1)
		finally:
			openstreetmap.TileLoader.drawlock.release()
		return False
		
	def get_visible_area(self):
		return (self.pixmappoint2coord([0,0]), self.pixmappoint2coord([self.map_width, self.map_height]))
		
	def load_images(self):
		if self.current_cache == None:
			self.update_cache_image(reset = True)
			return
		try:
			files = os.listdir(self.settings['download_output_dir'])
			images = []
			for f in files:
				if f.startswith('%s-image' % self.current_cache.name):
					images.append(os.path.join(self.settings['download_output_dir'], f))
				
			self.images = images
		except Exception as e:
			print "Could not prepare images: %s" % e
		self.update_cache_image(reset = True)
		
	def on_download_descriptions_clicked(self, something):
		self.core.on_download_descriptions(self.get_visible_area())
		self.draw_map()	
		
	def on_download_clicked(self, something):
		self.core.on_download(self.get_visible_area())
		self.draw_map()	
		
	def on_download_cache_clicked(self, something):
		self.core.on_download_cache(self.current_cache)
		self.show_cache(self.current_cache)
	
	def on_image_next_clicked(self, something):
		if len(self.images) == 0:
			self.update_cache_image(reset = True)
			return
		self.image_no += 1
		self.image_no %= len(self.images)
		self.update_cache_image()
		
	
	def on_image_zoom_clicked(self, something):
		self.image_zoomed = not self.image_zoomed
		self.update_cache_image()
		
	def on_save_config(self, something):
		if not self.block_changes:
			self.core.on_config_changed(self.read_settings())
		
	def on_zoom_changed(self, blub):
		if not self.inhibit_zoom:
			self.zoom()
		
	def on_zoomin_clicked(self, widget):
		self.zoom(+1)
		
	def on_zoomout_clicked(self, widget):
		self.zoom(-1)	
		
		
	def update_cache_image(self, reset = False):
		if reset:
			self.image_cache.set_from_stock(gtk.STOCK_GO_FORWARD, -1)
			return
		try:
			mw, mh = self.scrolledwindow_image.get_allocation().width - 10, self.scrolledwindow_image.get_allocation().height - 10
			if self.current_cache == None or len(self.images) <= self.image_no:
				self.image_cache.set_from_stock(gtk.STOCK_GO_FORWARD, -1)
				return
			filename = os.path.join(self.settings['download_output_dir'], self.images[self.image_no])
			if not os.path.exists(filename):
				print "File does not exist: %s:" % filename
				self.image_cache.set_from_stock(gtk.STOCK_GO_FORWARD, -1)
				return
			
			pb = gtk.gdk.pixbuf_new_from_file(filename)
		
			if not self.image_zoomed:
				scale = 1.0
				w = float(pb.get_width())
				h = float(pb.get_height())
				if w > mw:
					factor = mw/w
					w = w * factor
					h = h * factor
				if h > mh:
					factor = mh/h
					w = w * factor
					h = h * factor
				pb = pb.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
		
			
			self.image_cache.set_from_pixbuf(pb)
		except Exception as e:
			print "Error loading image: %s" % e
			
			
	
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
		if self.current_target != None:
			settings['last_target_lat'] = self.current_target.lat
			settings['last_target_lon'] = self.current_target.lon
			settings['last_target_name'] = self.current_target.name
			
		for x in self.SETTINGS_CHECKBOXES:
			settings[x] = xml.get_widget('check_%s' % x).get_active()
		
		for x in self.SETTINGS_INPUTS:
			settings[x] = xml.get_widget('input_%s' % x).get_text()
		
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
	
		
	def set_center(self, coord):
		#xml.get_widget("notebook_all").set_current_page(0)
		self.map_center_x, self.map_center_y = self.ts.deg2num(coord)
		self.draw_at_x = 0
		self.draw_at_y = 0
		self.draw_map()
		
	#called by core
	def set_download_progress(self, fraction, text):
		self.progressbar.set_text(text)
		self.progressbar.set_fraction(fraction)	
		
		
		
	def show(self):
		self.window.show_all()	
		gtk.main()
		
		
