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
import socket

socket.setdefaulttimeout(10)
socket.settimeout(10)

class TileLoader(threading.Thread):
    downloading = []
    semaphore = threading.Semaphore(40)
    lock = thread.allocate_lock() #download-lock
    drawlock = thread.allocate_lock()
    running_threads = 0
    noimage = None
        
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
               
    def run(self):
        self.__log("start")
        TileLoader.running_threads += 1
        self.local_filename = os.path.join(self.base_dir, str(self.zoom), str(self.tile[0]), "%d.png" % self.tile[1])
        self.remote_filename = "http://tile.openstreetmap.org/mapnik/%d/%d/%d.png" % (self.zoom, self.tile[0], self.tile[1])
        #self.remote_filename = "http://andy.sandbox.cloudmade.com/tiles/cycle/%d/%d/%d.png" % (self.zoom, self.tile[0], self.tile[1])
        answer = True
        if not os.path.isfile(self.local_filename):
            print "Datei existiert nicht: '%s' " % self.local_filename
            path_1 = "%s%d" % (self.base_dir, self.zoom)
            path_2 = "%s/%d" % (path_1, self.tile[0])
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
                                                        
                        
            answer = self.download(self.remote_filename, self.local_filename)
        # now the file hopefully exists
        if answer == True:
            print "loading"
            self.load()
            gobject.idle_add(self.draw)
        elif answer == False:
            print "loading default"
            self.pbuf = TileLoader.noimage
            gobject.idle_add(self.draw)
        else:
            print "nothing"
            

        self.__log("prep draw")
                
    def load(self, tryno=0):
        # load the pixbuf to memory
        try:
            self.pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
            if self.pbuf.get_width() < self.gui.ts.tile_size() or self.pbuf.get_height() < self.gui.ts.tile_size():
            	raise Exception("Image too small, probably corrupted file")
            return True
        except Exception as e:
            if tryno == 0:
                return self.recover()
            else:
                print e
                self.pbuf = TileLoader.noimage
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
            offset_x = int(self.gui.map_width / 2 - (x - int(x)) * size)
            offset_y = int(self.gui.map_height / 2 -(y - int(y)) * size)
            span_x = int(math.ceil(float(self.gui.map_width) / (size * 2.0)))
            span_y = int(math.ceil(float(self.gui.map_height) / (size * 2.0)))
            if self.tile[0] in xrange(xi - span_x, xi + span_x + 1, 1) and self.tile[1] in xrange(yi - span_y, yi + span_y + 1, 1) and self.zoom == self.gui.ts.zoom:
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
            #if acquired:
            #    self.drawlock.release()
             self.__log("draw-end")
            #return True
            #if TileLoader.running_threads <= 0:
                #gobject.idle_add(self.gui.__draw_marks, self)
                
    def download(self, remote, local):
        print "lade runter", remote
        acquired = False
        self.__log("dl-start")
        
        TileLoader.lock.acquire()
        try:
            if remote in TileLoader.downloading:
                print 'lädt schon: %s' % remote
                return None
            if os.path.exists(local):
                print 'ex schon: %s' % remote
                return None
            TileLoader.downloading.append(remote)
        finally:
            TileLoader.lock.release()
            
        #TileLoader.semaphore.acquire()
        #acquired = True
        try:
            if not self.zoom == self.gui.ts.zoom:
                return None
            info = urllib.urlretrieve(remote, local)    
            print "feddisch!"
            if "text/html" in info[1]['Content-Type']:
                print "File not found: %s" % remote
                return False
            return True
        except Exception as e:
        	print "Download Error", e
        	return False
        finally:
            if acquired:
            	TileLoader.semaphore.release()
            TileLoader.downloading.remove(remote)
            self.__log("dl-end")
            
            
    def __log(self, string):
        a = "%d  " % self.num
        for i in xrange(self.num):
            a += "   "
        #print a, string
                
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
