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

import logging
logger = logging.getLogger('openstreetmap')

from os import path, mkdir, extsep, remove
from threading import Semaphore
from urllib import urlretrieve
from socket import setdefaulttimeout
import connection
setdefaulttimeout(30)
   
    
CONCURRENT_THREADS = 20




    

def get_tile_loader(prefix, remote_url, max_zoom = 18, reverse_zoom = False, file_type = 'png', size = 256):
    class TileLoader():
        downloading = {}
        semaphore = Semaphore(CONCURRENT_THREADS)
        noimage_cantload = None
        noimage_loading = None
        base_dir = ''
        
        PREFIX = prefix
        MAX_ZOOM = max_zoom
        FILE_TYPE = file_type
        REMOTE_URL = remote_url
        TILE_SIZE = size

        TPL_LOCAL_PATH = path.join("%s", PREFIX, "%d", "%d")
        TPL_LOCAL_FILENAME = path.join("%s", "%%d%s%s" % (extsep, FILE_TYPE))

        def __init__(self, id_string, tile, zoom, undersample = False, x = 0, y = 0, callback_draw = None, callback_load = None):
            self.id_string = id_string
            self.undersample = undersample
            self.tile = tile
            #self.download_tile = self.gui.ts.check_bounds(*tile)
            self.download_tile = tile
            if not undersample:
                self.download_zoom = zoom
                self.display_zoom = zoom
            else:
                self.download_zoom = zoom - 1
                self.display_zoom = zoom
                self.download_tile = (int(self.download_tile[0]/2), int(self.download_tile[1]/2))
            self.pbuf = None
            self.callback_draw = callback_draw
            self.callback_load = callback_load

            self.my_noimage = None
            self.stop = False
            self.x = x
            self.y = y

            # setup paths
            self.local_path = self.TPL_LOCAL_PATH % (self.base_dir, self.download_zoom, self.download_tile[0])
            self.local_filename = self.TPL_LOCAL_FILENAME % (self.local_path, self.download_tile[1])
            self.remote_filename = self.REMOTE_URL % {'zoom': self.download_zoom, 'x' : self.download_tile[0], 'y' : self.download_tile[1]}
            

        def halt(self):
            self.stop = True
            

        @staticmethod
        def create_recursive(dpath):
            if not path.exists(dpath):
                head, tail = path.split(dpath)
                TileLoader.create_recursive(head)
                try:
                    mkdir(dpath)
                except Exception:
                    # let others fail here.
                    pass


        def run(self):
            needs_download = True
            if not path.isfile(self.local_filename):
                self.create_recursive(self.local_path)
                self.draw(self.get_no_image(self.noimage_loading))
                needs_download = self.__download(self.remote_filename, self.local_filename)

            # now the file hopefully exists
            if needs_download == True:
                self.load()
                self.draw(self.pbuf)
            elif needs_download == False:
                self.draw(self.get_no_image(self.noimage_cantload))
            else:
                # Do nothing here, as the thread was told to stop
                pass

        def run_again(self):
            self.load()
            self.draw(self.pbuf)
            return False

        def get_no_image(self, default):
            return (default, None)
            
        def load(self, tryno=0):                
            # load the pixbuf to memory
            if self.stop:
                return True
            try:
                size, tile = self.TILE_SIZE, self.tile
                if self.undersample:
                    # don't load the tile directly, but load the supertile instead
                    supertile_x = int(tile[0]/2)
                    supertile_y = int(tile[1]/2)
                    off_x = (tile[0]/2.0 - supertile_x) * size
                    off_y = (tile[1]/2.0 - supertile_y) * size
                    surface = self.callback_load(self.local_filename)
                    
                    self.pbuf = (surface, (off_x, off_y))
                else:
                    surface = self.callback_load(self.local_filename)
                    self.pbuf = (surface, None)
                return True
            except Exception, e:
                if tryno == 0:
                    return self.recover()
                else:
                    logger.exception("Exception while loading map tile: %s" % e)
                    self.pbuf = (self.noimage_cantload, None)
                    return True

        def recover(self):
            try:
                remove(self.local_filename)
            except Exception, e:
                logger.critical("Exception occured while removing file: %s" % e)
            self.__download(self.remote_filename, self.local_filename)
            return self.load(1)

        def draw(self, pbuf):
            if not self.stop:
                return self.callback_draw(self.id_string, pbuf[0], self.x, self.y, pbuf[1])
            return False


        def __download(self, remote, local):
            if path.exists(local):
                return True
            if connection.offline:
                return False
            with TileLoader.semaphore:
                try:
                    if self.stop:
                        return None
                    info = urlretrieve(remote, local)

                    if "text/html" in info[1]['Content-Type']:
                        return False
                    return True
                except Exception, e:
                    logger.error("Download error")
                    logger.exception(e)
                    return False

        def download_tile_only(self):
            if not path.isfile(self.local_filename):
                self.create_recursive(self.local_path)
            return self.__download(self.remote_filename, self.local_filename)

    return TileLoader

