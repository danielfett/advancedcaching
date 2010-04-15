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

import math
import geo
import gobject
import gtk
import os
import threading
import urllib
import socket
socket.setdefaulttimeout(30)


def get_tile_loader(prefix, remote_url, max_zoom = 18, reverse_zoom = False, file_type = 'png'):

    class TileLoader(threading.Thread):
        downloading = []
        semaphore = threading.Semaphore(40)
        lock = threading.Lock() #download-lock
        noimage_cantload = None
        noimage_loading = None

        PREFIX = prefix#'OSM'
        MAX_ZOOM = max_zoom#18
        FILE_TYPE = file_type#'png'
        REMOTE_URL = remote_url#"http://128.40.168.104/mapnik/%(zoom)d/%(x)d/%(y)d.png"

        def __init__(self, tile, zoom, gui, base_dir, noimage_cantload, noimage_loading, num=0):
            threading.Thread.__init__(self)
            self.daemon = False
            self.tile = tile
            self.zoom = zoom
            self.gui = gui
            self.base_dir = base_dir
            self.pbuf = None
            self.num = num
            self.noimage_cantload = noimage_cantload
            self.noimage_loading = noimage_loading
            self.set_paths()
            self.my_noimage = None

        def set_paths(self):
            self.local_path = os.path.join(self.base_dir, self.PREFIX, str(self.zoom), str(self.tile[0]))
            self.local_filename =  os.path.join(self.local_path, "%d%s%s" % (self.tile[1], os.extsep, self.FILE_TYPE))
            self.remote_filename = self.REMOTE_URL % {'zoom': self.zoom, 'x' : self.tile[0], 'y' : self.tile[1]}

        @staticmethod
        def create_recursive(path):
            if path != '/':
                if not os.path.exists(path):
                    head, tail = os.path.split(path)
                    TileLoader.create_recursive(head)
                    try:
                        os.mkdir(path)
                    except Exception, e:
                        # let others fail here.
                        pass


        def run(self):
            answer = True
            if not os.path.isfile(self.local_filename):
                self.create_recursive(self.local_path)
                gobject.idle_add(lambda: self.draw(self.get_no_image(TileLoader.noimage_loading)))
                answer = self.download(self.remote_filename, self.local_filename)
            # now the file hopefully exists
            if answer == True:
                self.load()
                gobject.idle_add(lambda: self.draw(self.pbuf))
            elif answer == False:
                gobject.idle_add(lambda: self.draw(self.get_no_image(TileLoader.noimage_cantload)))
            else:
                #print "nothing"
                pass


        def get_no_image(self, default):
            if self.my_noimage != None:
                return self.my_noimage
            size = self.gui.ts.tile_size()
            # we have no image available. so what do now?
            # first, check if we've the "supertile" available (zoomed out)
            supertile_zoom = self.zoom - 1
            supertile_x = int(self.tile[0]/2)
            supertile_y = int(self.tile[1]/2)
            supertile_name = os.path.join(self.base_dir, str(supertile_zoom), str(supertile_x), "%d%s%s" % (supertile_y, os.extsep, self.FILE_TYPE))
            if os.path.exists(supertile_name):
                off_x = (self.tile[0]/2.0 - supertile_x) * size
                off_y = (self.tile[1]/2.0 - supertile_y) * size
                pbuf = gtk.gdk.pixbuf_new_from_file(supertile_name)
                dest = gtk.gdk.Pixbuf(pbuf.get_colorspace(), pbuf.get_has_alpha(), pbuf.get_bits_per_sample(), size, size)
                pbuf.scale(dest, 0, 0, 256, 256, -off_x*2, -off_y*2, 2, 2, gtk.gdk.INTERP_BILINEAR)
                self.my_noimage = dest
                return dest
            else:
                self.my_noimage = default
                return default

        def load(self, tryno=0):
            # load the pixbuf to memory
            try:
                self.pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
                if self.pbuf.get_width() < self.gui.ts.tile_size() or self.pbuf.get_height() < self.gui.ts.tile_size():
                    raise Exception("Image too small, probably corrupted file")
                return True
            except Exception, e:
                if tryno == 0:
                    return self.recover()
                else:
                    print e
                    self.pbuf = TileLoader.noimage_cantload
                    return True

        def recover(self):
            try:
                os.remove(self.local_filename)
            except:
                pass
            self.download(self.remote_filename, self.local_filename)
            return self.load(1)

        def draw(self, pbuf):
            #gc.set_function(gtk.gdk.COPY)
            #gc.set_rgb_fg_color(self.COLOR_BG)
            # to draw "night mode": INVERT

            size = self.gui.ts.tile_size()
            x = self.gui.map_center_x
            y = self.gui.map_center_y
            xi = int(self.gui.map_center_x)
            yi = int(self.gui.map_center_y)
            span_x = int(math.ceil(float(self.gui.map_width) / (size * 2.0)))
            span_y = int(math.ceil(float(self.gui.map_height) / (size * 2.0)))
            if self.tile[0] in xrange(xi - span_x, xi + span_x + 1, 1) and self.tile[1] in xrange(yi - span_y, yi + span_y + 1, 1) and self.zoom == self.gui.ts.zoom:

                offset_x = int(self.gui.map_width / 2 - (x - int(x)) * size)
                offset_y = int(self.gui.map_height / 2 -(y - int(y)) * size)
                dx = (self.tile[0] - xi) * size + offset_x
                dy = (self.tile[1] - yi) * size + offset_y

                gc = self.gui.xgc

                if pbuf != None:
                    self.gui.pixmap.draw_pixbuf(gc, pbuf, 0, 0, dx, dy, size, size)
                else:
                    self.gui.pixmap.draw_pixbuf(gc, self.noimage_cantload, 0, 0, dx, dy, size, size)

                self.gui.drawing_area.queue_draw_area(max(self.gui.draw_root_x + self.gui.draw_at_x  + dx, 0), max(self.gui.draw_root_y + self.gui.draw_at_y  + dy, 0), size, size)


        def download(self, remote, local):
            #print "downloading", remote
            with TileLoader.lock:
                try:
                    if remote in TileLoader.downloading:
                        return None
                    if os.path.exists(local):
                        return None
                    TileLoader.downloading.append(remote)
                except Exception:
                    pass

            with TileLoader.semaphore:
                try:
                    if not self.zoom == self.gui.ts.zoom:
                        return None
                    info = urllib.urlretrieve(remote, local)

                    if "text/html" in info[1]['Content-Type']:
                        return False
                    return True
                except Exception, e:
                    print "Download Error", e
                    return False
                finally:
                    TileLoader.downloading.remove(remote)
    return TileLoader

                
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

    @staticmethod
    def tile_size():
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


