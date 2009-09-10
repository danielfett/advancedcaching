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
import cStringIO

class TileLoader(threading.Thread):
    downloading = []
    semaphore = threading.Semaphore(5)
    lock = thread.allocate_lock()
    cachelock = thread.allocate_lock()
    running_threads = 0

    # we use a LRU cache here
    cache = {}
    cache_contents = []

    # use 5 MBs of cache. 15.000 is the average size
    # of one tile.
    CACHE_SIZE = (5*1024*1024)/15000

    #steps:
    # - check if file exists.
    # - NO: Download tile
    # - load pixbuf from file
    # - find target position in current pixmap (lock!)
    # - draw to pixmap (still locked!)
    # - call queue_draw
    # optional: acquire locks in all related parts of gui
	
    def __init__(self, tile, zoom, gui, base_dir, num=0):
	threading.Thread.__init__(self)
	self.daemon = False
	self.tile = tile
	self.zoom = zoom
	self.gui = gui
	self.base_dir = base_dir
	self.pbuf = None
	self.num = num
	self.cached_file = None

    def get_cached(self, key, retrievefunction):
	#print TileLoader.cache
	#print TileLoader.cache_contents
	# @type cache dict
	if key in TileLoader.cache.keys():
	    res = TileLoader.cache[key]
	    # @type cache_contents list
	    TileLoader.cache_contents.remove(key)
	    TileLoader.cache_contents.append(key)
	    #print "auscache"
	else:
	    res = retrievefunction()
	    if res == None:
		return None
	    if len(TileLoader.cache_contents) == self.CACHE_SIZE:
		out = TileLoader.cache_contents.pop(0)
		del TileLoader.cache[out]
		#print "killing", out
	    TileLoader.cache[key] = res
	    TileLoader.cache_contents.append(key)
	return res

		
    def run(self):
	self.local_filename = os.path.join(self.base_dir, str(self.zoom), str(self.tile[0]), "%d.png" % self.tile[1])
	self.remote_filename = "http://tile.openstreetmap.org/mapnik/%d/%d/%d.png" % (self.zoom, self.tile[0], self.tile[1])
	#self.remote_filename = "http://andy.sandbox.cloudmade.com/tiles/cycle/%d/%d/%d.png" % (self.zoom, self.tile[0], self.tile[1])
	self.load()

		
    def load(self):
	tiledata = self.get_cached("%s/%s/%s" % (self.zoom, self.tile[0], self.tile[1]), self.read_file)
	if tiledata == None:
	    path_1 = os.path.join(self.base_dir, str(self.zoom))
	    path_2 = os.path.join(path_1, str(self.tile[0]))
	    try:
		if not os.path.exists(path_1):
		    os.mkdir(path_1)
		if not os.path.exists(path_2):
		    os.mkdir(path_2)
	    except:
		pass
		# this may fail due to threading issues.
		# too lazy to do proper locking here
		# so just forget about the error


	    tiledata = self.download(self.remote_filename, self.local_filename)
	
	if tiledata != None:
	    pbl = gtk.gdk.PixbufLoader()
	    pbl.write(tiledata.getvalue())
	    self.pbuf = pbl.get_pixbuf()
	    if self.pbuf == None:
		print "Isnone: ", self.local_filename
	    pbl.close()
	    #self.pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
	    gobject.idle_add(self.draw)
	return True

    def read_file(self):
	# @type file file
	file = None
	try:
	    file = open(self.local_filename, 'rb')
	    return cStringIO.StringIO(file.read())
	except Exception as e:
	    print e
	    return None
	finally:
	    if file != None:
		file.close()
	
    '''
    def recover(self):
	try:
	    os.remove(self.local_filename)
	except:
	    pass
	self.download(self.remote_filename, self.local_filename)
	return self.load(1)
    '''
    def draw(self):
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
	offset_x = int(self.gui.map_width / 2 - (x - int(x)) * size)
	offset_y = int(self.gui.map_height / 2 -(y - int(y)) * size)
	span_x = int(math.ceil(float(self.gui.map_width) / (size * 2.0)))
	span_y = int(math.ceil(float(self.gui.map_height) / (size * 2.0)))
	if self.tile[0] in xrange(xi - span_x, xi + span_x + 1, 1) and self.tile[1] in xrange(yi - span_y, yi + span_y + 1, 1) and self.zoom == self.gui.ts.zoom:
	    dx = (self.tile[0] - xi) * size + offset_x
	    dy = (self.tile[1] - yi) * size + offset_y

	    if self.pbuf != None:
		self.gui.pixmap.draw_pixbuf(gc, self.pbuf, 0, 0, dx, dy, size, size)
	    else:
		self.gui.pixmap.draw_rectangle(gc, True, dx, dy, size, size)

	    widget.queue_draw_area(max(self.gui.draw_root_x + self.gui.draw_at_x  + dx, 0), max(self.gui.draw_root_y + self.gui.draw_at_y  + dy, 0), size, size)


    def download(self, remote, local):
	file = None
	'''
	TileLoader.lock.acquire()
	try:
	    if (remote in TileLoader.downloading):
		return None
	    if os.path.exists(local):
		return None
	    TileLoader.downloading.append(remote)
	except Exception as e:
	    print e
	finally:
	    TileLoader.lock.release()
	'''
	#TileLoader.semaphore.acquire()
	try:
	    if not self.zoom == self.gui.ts.zoom:
		return None
	    webFile = urllib.urlopen(remote)
	    if "text/html" in webFile.info()['Content-Type']:
		print "File not found: %s" % remote
		return False
	    localFile = open(local, 'wb')
	    file = webFile.read()
	    webFile.close()
	    localFile.write(file)
	    localFile.close()
	except Exception as e:
	    print e
	finally:
	    #TileLoader.semaphore.release()
	    #TileLoader.downloading.remove(remote)
	    if file != None:
		return cStringIO.StringIO(file)

		
class TileServer():

    def __init__(self):
	self.zoom = 14
	self.max_zoom = 18
		
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
