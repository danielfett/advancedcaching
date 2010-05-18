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
from os import path, mkdir, extsep, remove
from threading import Thread, Semaphore, Lock
from urllib import urlretrieve
from socket import setdefaulttimeout
setdefaulttimeout(30)

def get_tile_loader(prefix, remote_url, max_zoom = 18, reverse_zoom = False, file_type = 'png'):

    class TileLoader(Thread):
        downloading = {}
        semaphore = Semaphore(40)
        lock = Lock() #download-lock
        noimage_cantload = None
        noimage_loading = None
        base_dir = ''
        gui = None
        size = 0

        PREFIX = prefix#'OSM'
        MAX_ZOOM = max_zoom#18
        FILE_TYPE = file_type#'png'
        REMOTE_URL = remote_url#"http://128.40.168.104/mapnik/%(zoom)d/%(x)d/%(y)d.png"

        TPL_LOCAL_PATH = path.join("%s", PREFIX, "%d", "%d")
        TPL_LOCAL_FILENAME = path.join("%s", "%%d%s%s" % (extsep, FILE_TYPE))

        def __init__(self, tile, zoom, undersample, x, y):
            Thread.__init__(self)
            self.daemon = False
            self.undersample = undersample
            self.tile = tile
            self.realtile = self.gui.ts.check_bounds(*tile)
            if not undersample:
                self.download_zoom = zoom
                self.display_zoom = zoom
            else:
                self.download_zoom = zoom - 1
                self.display_zoom = zoom
                self.realtile = (int(self.realtile[0]/2), int(self.realtile[1]/2))
            self.pbuf = None

            self.my_noimage = None
            self.stop = False
            #self.waitlist = []
            self.x = x
            self.y = y

            # setup paths
            self.local_path = self.TPL_LOCAL_PATH % (self.base_dir, self.download_zoom, self.realtile[0])
            self.local_filename = self.TPL_LOCAL_FILENAME % (self.local_path, self.realtile[1])
            self.remote_filename = self.REMOTE_URL % {'zoom': self.download_zoom, 'x' : self.realtile[0], 'y' : self.realtile[1]}
        '''
        def add_waitlist(l):
            self.waitlist.append(l)
        '''
        def halt(self):
            self.stop = True
            

        @staticmethod
        def create_recursive(dpath):
            if dpath != '/':
                if not path.exists(dpath):
                    head, tail = path.split(dpath)
                    TileLoader.create_recursive(head)
                    try:
                        mkdir(dpath)
                    except Exception, e:
                        # let others fail here.
                        pass


        def run(self):
            answer = True
            if not path.isfile(self.local_filename):
                self.create_recursive(self.local_path)
                gobject.idle_add(lambda: self.draw(self.get_no_image(self.noimage_loading)))
                answer = self.download(self.remote_filename, self.local_filename)
            '''            
            for x in self.waitlist:
                gobject.idle_add(x.run_again())
            '''
            # now the file hopefully exists
            if answer == True:
                self.load()
                gobject.idle_add(lambda: self.draw(self.pbuf))
            elif answer == False:
                gobject.idle_add(lambda: self.draw(self.get_no_image(self.noimage_cantload)))
                pass
            else:
                #print "nothing"
                pass

        def run_again(self):
            self.load()
            gobject.idle_add(lambda: self.draw(self.pbuf))
            return False

        def get_no_image(self, default):
            return default
            if self.my_noimage != None:
                return self.my_noimage
            size, tile = self.size, self.tile
            # we have no image available. so what do now?
            # first, check if we've the "supertile" available (zoomed out)
            supertile_zoom = self.download_zoom - 1
            supertile_x = int(tile[0]/2)
            supertile_y = int(tile[1]/2)
            supertile_path = self.TPL_LOCAL_PATH % (self.base_dir, supertile_zoom, supertile_x)
            supertile_name = self.TPL_LOCAL_FILENAME % (supertile_path, supertile_y)
            #supertile_name = path.join(TileLoader.base_dir, self.PREFIX, str(supertile_zoom), str(supertile_x), "%d%s%s" % (supertile_y, extsep, self.FILE_TYPE))
            if not self.undersample and path.exists(supertile_name):
                off_x = (tile[0]/2.0 - supertile_x) * size
                off_y = (tile[1]/2.0 - supertile_y) * size
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
            if self.stop:
                return True
            try:
                size, tile = self.size, self.tile
                if self.undersample:
                    # don't load the tile directly, but load the supertile instead
                    supertile_x = int(tile[0]/2)
                    supertile_y = int(tile[1]/2)
                    off_x = (tile[0]/2.0 - supertile_x) * size
                    off_y = (tile[1]/2.0 - supertile_y) * size
                    pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
                    if pbuf.get_width() < size or pbuf.get_height() < size:
                        raise Exception("Image too small, probably corrupted file")
                    dest = gtk.gdk.Pixbuf(pbuf.get_colorspace(), pbuf.get_has_alpha(), pbuf.get_bits_per_sample(), size, size)
                    pbuf.scale(dest, 0, 0, size, size, -off_x*2, -off_y*2, 2, 2, gtk.gdk.INTERP_HYPER)
                    self.pbuf = dest
                else:
                    self.pbuf = gtk.gdk.pixbuf_new_from_file(self.local_filename)
                    if self.pbuf.get_width() < size or self.pbuf.get_height() < size:
                        raise Exception("Image too small, probably corrupted file")
                return True
            except Exception, e:
                if tryno == 0:
                    return self.recover()
                else:
                    print e
                    print "cnl 2"
                    self.pbuf = self.noimage_cantload
                    return True

        def recover(self):
            try:
                remove(self.local_filename)
            except:
                pass
            self.download(self.remote_filename, self.local_filename)
            return self.load(1)

        def draw(self, pbuf):
            size, x, y = self.size, self.x, self.y
            if not self.stop:
                if pbuf != None:
                    self.gui.pixmap.draw_pixbuf(self.gui.xgc, pbuf, 0, 0, x, y, size, size)
                else:
                    self.gui.pixmap.draw_pixbuf(self.gui.xgc, self.noimage_cantload, 0, 0, x, y, size, size)
                
                self.gui.drawing_area.queue_draw_area(max(x, 0), max(y, 0), size, size)
            return False

        def download(self, remote, local):
            #print "downloading", remote
            #with TileLoader.lock:
                #try:
                #if remote in TileLoader.downloading:
                #    TileLoader.downloading[remote].add_waitlist(self)
            if path.exists(local):
                return True
                #TileLoader.downloading[remote] = self
                #except Exception:
                #    raise Exception

            with TileLoader.semaphore:
                try:
                    if self.stop:
                        return None
                    info = urlretrieve(remote, local)

                    if "text/html" in info[1]['Content-Type']:
                        return False
                    return True
                except Exception, e:
                    print "Download Error", e
                    return False
                #finally:
                    #try:
                    #    del TileLoader.downloading[remote]
                    #except Exception, e:
                    #    pass
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
        lat_rad = math.radians(lat_deg)
        n = 2 ** self.zoom
        xtile = int((lon_deg + 180) / 360 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return(xtile, ytile)
                
    def deg2num(self, coord):
        lat_rad = math.radians(coord.lat)
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

    def check_bounds(self, xtile, ytile):
        max_x = 2**self.zoom
        max_y = 2**self.zoom
        return (
            xtile % max_x,
            ytile % max_y
        )

