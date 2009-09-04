#!/usr/bin/python
# -*- coding: utf-8 -*-

import math
import thread

import geo
import gobject
import gtk
import os
import threading
import urllib

class TileLoader(threading.Thread):
	downloading = []
	semaphore = threading.Semaphore(20)
	lock = thread.allocate_lock() #download-lock
	drawlock = thread.allocate_lock()
	running_threads = 0
	
	#steps:
	# - check if file exists. 
	# - NO: Download tile
	# - load pixbuf from file
	# - find target position in current pixmap (lock!)
	# - draw to pixmap (still locked!)
	# - call queue_draw
	# optional: acquire locks in all related parts of gui
	
	def __init__(self, tile, zoom, gui, base_dir, num = 0):
		threading.Thread.__init__(self)
		self.daemon = False
		self.tile = tile
		self.zoom = zoom
		self.gui = gui
		self.base_dir = base_dir
		self.pbuf = None
		self.num = num
		
	def run(self):
		self.__log("start")
		TileLoader.running_threads += 1
		filename = os.path.join("%d" % self.zoom, "%d" % self.tile[0], "%d.png" % self.tile[1])
		self.local_filename = "%s%s" % (self.base_dir, filename)
		self.remote_filename = "http://tile.openstreetmap.org/mapnik/%s" % filename
		answer = True
		if not os.path.isfile(self.local_filename):
			path_1 = "%s%d" % (self.base_dir, self.zoom)
			path_2 = "%s/%d" % (path_1, self.tile[0])
			try:
				if not os.path.exists(path_1):
					os.mkdir(path_1)
				if not os.path.exists(path_2):
					os.mkdir(path_2)
			except:
				pass
				#this may file due to threading issues. 
				# too lazy to do proper locking here
				# so just forget about the error
							
			
			if not os.path.isfile(self.local_filename):
				answer = self.download(self.remote_filename, self.local_filename)
		# now the file hopefully exists
		if not (answer == False):
			self.load()
			gobject.idle_add(self.draw)

		self.__log("prep draw")
		
	def load(self, tryno = 0):
		# load the pixbuf to memory
		try:
			self.pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
			return True
		except:
			if tryno == 0:
				return self.recover()
			else:
				# draw "empty" tile:
				self.pbuf = None
				#TileLoader.running_threads -= 1
				#if TileLoader.running_threads == 0:
					#gobject.idle_add(self.gui.draw_marks)
				return True
				
	def recover(self):
		try:
			os.remove(self.local_filename)
		except:
			pass
		self.download(self.remote_filename, self.local_filename)
		return self.load(1)
		
	def draw(self):
		acquired = False
		try:
			self.__log("draw-start")
			widget = self.gui.drawing_area
			gc = self.gui.xgc
			gc.set_function(gtk.gdk.COPY)
			gc.set_rgb_fg_color(gtk.gdk.color_parse("black"))
			# to draw "night mode": INVERT
			
			a, b, width, height = widget.get_allocation()
			size = self.gui.ts.tile_size()
			x = self.gui.map_center_x
			y = self.gui.map_center_y
			xi = int(self.gui.map_center_x)
			yi = int(self.gui.map_center_y)
			offset_x = int(self.gui.map_width/2 - (x - int(x)) * size)
			offset_y = int(self.gui.map_height/2 -(y - int(y)) * size)
			span_x = int(math.ceil(float(self.gui.map_width)/(size * 2.0)))
			span_y = int(math.ceil(float(self.gui.map_height)/(size * 2.0)))
			if self.tile[0] in range(xi - span_x, xi + span_x + 1, 1) and self.tile[1] in range(yi - span_y, yi + span_y + 1, 1) and self.zoom == self.gui.ts.zoom:
				dx = (self.tile[0] - xi) * size + offset_x
				dy = (self.tile[1] - yi) * size + offset_y
				
				#self.drawlock.acquire()
				#acquired = True
				if self.pbuf != None:
				    self.gui.pixmap.draw_pixbuf(gc, self.pbuf, 0, 0, dx, dy, size, size)
				else:
				    self.gui.pixmap.draw_rectangle(gc, True, dx, dy, size, size)
				
				widget.queue_draw_area(max(self.gui.draw_root_x + self.gui.draw_at_x  + dx, 0), max(self.gui.draw_root_y + self.gui.draw_at_y  + dy, 0), size, size)
				
				
		finally:
			if acquired:
				self.drawlock.release()
			
			TileLoader.running_threads -= 1
			self.__log("draw-end")
			#return True
			#if TileLoader.running_threads <= 0:
				#gobject.idle_add(self.gui.__draw_marks, self)
		
	def download(self, remote, local):

		self.__log("dl-start")
		self.lock.acquire()
		try:
			if (remote in self.downloading):
				return None
			if os.path.exists(local):
				return None
			self.downloading.append(remote)
		finally:
			self.lock.release()
		
		self.semaphore.acquire()
		try:
			if not self.zoom == self.gui.ts.zoom:
				return None
			webFile = urllib.urlopen(remote)
			if "text/html" in webFile.info()['Content-Type']:
				print "File not found: %s" % remote
				return False
			localFile = open(local, 'wb')
			localFile.write(webFile.read())
			webFile.close()
			localFile.close()
		except:
			pass
		finally:
			self.semaphore.release()
			self.downloading.remove(remote)
			self.__log("dl-end")
			return True


	def __log(self, string):
		a = "%d  " % self.num
		for i in range(self.num):
			a += "   "
		#print a, string
		
class TileServer():

	def __init__(self):
		self.zoom = 14
		self.max_zoom = 17
		
	def get_zoom(self):
		return self.zoom
		
	def set_zoom(self, zoom):
		if zoom < 1 or zoom > self.max_zoom:
			return
		self.zoom = zoom
		
	def tile_size(self):
		return 256
		
	def deg2tilenum(self, lat_deg, lon_deg):
		#lat_rad = lat_deg * math.pi / 180.0
		lat_rad = math.radians(lat_deg)
		n = 2 ** self.zoom
		xtile = int((lon_deg + 180) / 360 * n)
		ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
		return(xtile, ytile)
		
	def deg2num(self, coord):
		lat_rad = math.radians(coord.lat)
		#lat_rad = (coord.lat * math.pi) / 180.0
		n = 2 ** self.zoom
		xtile = (coord.lon + 180) / 360 * n
		ytile = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n
		return(xtile, ytile)
		
	def num2deg(self, xtile, ytile):
		n = 2 ** self.zoom
		lon_deg = xtile / n * 360.0 - 180.0
		lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
		lat_deg = lat_rad * 180.0 / math.pi
		return geo.Coordinate(lat_deg, lon_deg)
