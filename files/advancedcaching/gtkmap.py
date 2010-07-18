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

import math

import cairo
import gobject
import geo
import gtk
import openstreetmap
import pango
import cairo
import math
import geo
import threadpool

import logging
logger = logging.getLogger('gtkmap')

class MapLayer():
    def __init__(self):
        self.result = None

    def draw(self):
        pass

    def clicked_screen(self, screenpoint):
        pass

    def clicked_coordinate(self, center, topleft, bottomright):
        pass

class OsdLayer(MapLayer):

    MESSAGE_DRAW_FONT = pango.FontDescription("Sans 5")
    MESSAGE_DRAW_COLOR = gtk.gdk.color_parse('black')
    COLOR_OSD_SECONDARY = gtk.gdk.color_parse("white")
    COLOR_OSD_MAIN = gtk.gdk.color_parse("black")

    @staticmethod
    def set_layout(message_draw_font, message_draw_color):
        OsdLayer.MESSAGE_DRAW_FONT = message_draw_font
        OsdLayer.MESSAGE_DRAW_COLOR = message_draw_color

    def draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map.map_width, self.map.map_height)
        cr = gtk.gdk.CairoContext(cairo.Context(surface))

        # message

        cr.set_line_width(2)
        if self.map.osd_message != None:
            cr.set_source_color(self.MESSAGE_DRAW_COLOR)
            layout = self.map.create_pango_layout(self.map.osd_message)
            layout.set_font_description(self.MESSAGE_DRAW_FONT)
            cr.move_to(20, 20)
            cr.show_layout(layout)

        # scale bar

        position = (20, self.map.map_height - 28)

        center = self.map.get_center()
        mpp = self.map.get_meters_per_pixel(center.lat)
        avglength = self.map.map_width / 5
        first_length_meters = mpp * avglength
        final_length_meters = round(first_length_meters, int(-math.floor(math.log(first_length_meters, 10) + 0.00001)))
        final_length_pixels = final_length_meters / mpp
        cr.move_to(position[0], position[1] + 10)
        cr.line_to(position[0] + final_length_pixels, position[1] + 10)
        cr.set_line_width(5)
        cr.set_source_color(self.COLOR_OSD_SECONDARY)
        cr.stroke_preserve()
        cr.set_line_width(3)
        cr.set_source_color(self.COLOR_OSD_MAIN)
        cr.stroke_preserve()

        cr.set_source_color(self.MESSAGE_DRAW_COLOR)
        if final_length_meters < 10000:
            msg = "%d m" % final_length_meters
        else:
            msg = "%d km" % (final_length_meters/1000)
        layout = self.map.create_pango_layout(msg)
        layout.set_font_description(self.MESSAGE_DRAW_FONT)
        cr.move_to(position[0], position[1] - 15)
        cr.show_layout(layout)


        self.result = surface


class Map(gtk.DrawingArea):

    MAP_FACTOR = 0
    RADIUS_EARTH = 6371000.0

    MIN_DRAG_REDRAW_DISTANCE = 5
    DRAG_RECHECK_SPEED = 20
    CLICK_RADIUS = 20

    LAZY_SET_CENTER_DIFFERENCE = 0.1 # * screen (width|height)

    @staticmethod
    def set_config(map_providers, map_path, placeholder_cantload, placeholder_loading):

        Map.noimage_cantload = cairo.ImageSurface.create_from_png(placeholder_cantload)
        Map.noimage_loading = cairo.ImageSurface.create_from_png(placeholder_loading)
        Map.tile_loaders = []

        for name, params in map_providers:
            tl = openstreetmap.get_tile_loader( ** params)
            tl.noimage_loading = Map.noimage_loading
            tl.noimage_cantload = Map.noimage_cantload
            tl.base_dir = map_path
            #tl.gui = self
            Map.tile_loaders.append((name, tl))
            

    def __init__(self, center, zoom, tile_loader=None, draggable=True):
        gtk.DrawingArea.__init__(self)

        self.connect("expose_event", self.__expose_event)
        self.connect("configure_event", self.__configure_event)
        self.connect("button_press_event", self.__drag_start)
        self.connect("scroll_event", self.__scroll)
        self.connect("button_release_event", self.__drag_end)
        
        if draggable:
            self.connect("motion_notify_event", self.__drag)
        self.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.SCROLL)

        try:
            gobject.signal_new('tile-loader-changed', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
            gobject.signal_new('map-dragged', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
            gobject.signal_new('draw-marks', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, ))
        except RuntimeError:
            pass

        self.dragging = False
        self.active_tile_loaders = []
        self.surface_buffer = {}
        self.delay_expose = False
        self.double_size = False
        self.layers = []
        self.osd_message = None

        self.tile_loader_threadpool = threadpool.ThreadPool(openstreetmap.CONCURRENT_THREADS * 2)

        if tile_loader == None:
            self.tile_loader = self.tile_loaders[0][1]
        else:
            self.tile_loader = tile_loader
        #self.ts = openstreetmap.TileServer(self.tile_loader)

        self.drawing_area_configured = self.drawing_area_arrow_configured = False

        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.zoom = zoom
        self.set_center(center, False)


        ##############################################
        #
        # Controlling the layers
        #
        ##############################################

    def add_layer(self, layer):
        self.layers.append(layer)
        layer.map = self


    def set_osd_message(self, message):
        self.osd_message = message

        ##############################################
        #
        # Controlling the map view
        #
        ##############################################

    def set_center(self, coord, update = True):
        self.map_center_x, self.map_center_y = self.deg2num(coord)
        self.center_latlon = coord
        self.draw_at_x = 0
        self.draw_at_y = 0
        if update:
            self.__draw_map()

    def set_center_lazy(self, coord):
        old_center_x, old_center_y = self.coord2point(self.center_latlon)
        new_center_x, new_center_y = self.coord2point(coord)
        
        if abs(old_center_x - new_center_x) > \
            self.map_width * self.LAZY_SET_CENTER_DIFFERENCE or \
            abs(old_center_y - new_center_y) > \
            self.map_height * self.LAZY_SET_CENTER_DIFFERENCE:
            self.set_center(coord)
            logger.debug('Not lazy!')
            return True
        logger.debug('Lazy!')
        return False


    def get_center(self):
        return self.center_latlon

    def relative_zoom(self, direction=None):
        if direction != None:
            self.set_zoom(self.zoom + direction)


    def set_zoom(self, newzoom):
        if newzoom < 1 or newzoom > self.tile_loader.MAX_ZOOM:
            return
        self.zoom = newzoom
        self.set_center(self.center_latlon)

    def get_zoom(self):
        return self.zoom

    def get_max_zoom(self):
        return self.tile_loader.MAX_ZOOM

    def get_min_zoom(self):
        return 0


        ##############################################
        #
        # Marker handling
        #
        ##############################################

    def add_marker_type(self, type):
        self.marker_types.append(type)

    def del_all_markers(self):
        for x in self.marker_types:
            x.del_all_markers()


        ##############################################
        #
        # Configuration
        #
        ##############################################

    def set_double_size(self, ds):
        self.double_size = ds

    def get_double_size(self):
        return self.double_size

    def set_tile_loader(self, loader):
        self.tile_loader = loader
        self.emit('tile-loader-changed', loader)
        self.relative_zoom(0)

    def set_placeholder_images(self, cantload, loading):
        self.noimage_cantload = cairo.ImageSurface.create_from_png(cantload)
        self.noimage_loading = cairo.ImageSurface.create_from_png(loading)


        ##############################################
        #
        # Map actions
        #
        ##############################################

    def redraw_layers(self):
        if self.dragging:
            return
        self.__draw_layers()
        self.refresh()

    def refresh(self):
        self.queue_draw()

        ##############################################
        #
        # Coordinate Conversion and Checking
        #
        ##############################################

    def point_in_screen(self, point):
        a = (point[0] >= 0 and point[1] >= 0 and point[0] < self.map_width and point[1] < self.map_height)
        return a
    '''
    def pixmappoint2coord(self, point):
        size = self.tile_loader.TILE_SIZE
        coord = self.num2deg(\
                                (point[0] + self.map_center_x * size - self.map_width / 2) / size, \
                                (point[1] + self.map_center_y * size - self.map_height / 2) / size \
                                )
        return coord
    '''

    def coord2point(self, coord):
        point = self.deg2num(coord)
        size = self.tile_loader.TILE_SIZE
        p_x = int(point[0] * size + self.map_width / 2) - self.map_center_x * size
        p_y = int(point[1] * size + self.map_height / 2) - self.map_center_y * size
        return (p_x, p_y)

    def screenpoint2coord(self, point):
        size = self.tile_loader.TILE_SIZE
        coord = self.num2deg(\
                                ((point[0] - self.draw_root_x - self.draw_at_x) + self.map_center_x * size - self.map_width / 2) / size, \
                                ((point[1] - self.draw_root_y - self.draw_at_y) + self.map_center_y * size - self.map_height / 2) / size \
                                )
        return coord

    def get_visible_area(self):
        return (self.screenpoint2coord((0, 0)), self.screenpoint2coord((self.map_width, self.map_height)))


        ##############################################
        #
        # Expose & Configure
        #
        ##############################################


    def __expose_event(self, widget, event):
        if self.dragging or self.delay_expose:
            return True
        x, y, width, height = event.area

        cr = self.cr_drawing_area
        #cr.clip()
        #import time
        #start = time.time()
        #for i in xrange(50):
        cr = self.window.cairo_create()
        cr.rectangle(x, y, width, height)
        cr.clip()
        cr.set_source_surface(self.cr_drawing_area_map)
        cr.paint()
        for l in self.layers:
            if l.result == None:
                continue
            cr.set_source_surface(l.result)
            cr.paint()
        cr.reset_clip()
        #end = time.time()
        #print end - start
        #import sys
        #sys.exit(0)
        #widget.window.draw_drawable(self.xgc, self.pixmap, x, y, x, y, width, height)
        return False


    def __configure_event(self, widget, event):
        x, y, width, height = widget.get_allocation()
        self.map_width = int(width  + 2 * width * self.MAP_FACTOR)
        self.map_height = int(height + 2 * height * self.MAP_FACTOR)
        self.pixmap = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)

        self.cr_marks = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map_width, self.map_height)
        self.cr_osd = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map_width, self.map_height)
        self.cr_drawing_area_map = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map_width, self.map_height)
        self.cr_drawing_area = self.pixmap.cairo_create()#widget.window.cairo_create()
        self.cr_window = self.window.cairo_create()
        self.xgc = widget.window.new_gc()

        self.drawing_area_configured = True
        self.draw_at_x = 0
        self.draw_at_y = 0
        self.draw_root_x = int(-width * self.MAP_FACTOR)
        self.draw_root_y = int(-height * self.MAP_FACTOR)

        gobject.idle_add(self.__draw_map)


        ##############################################
        #
        # User Input
        #
        ##############################################

    def __scroll(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.map.zoom(-1)
        else:
            self.map.zoom( + 1)

    def __drag_start(self, widget, event):
        try:
            while True:
                x = self.active_tile_loaders.pop()
                x.halt()
        except IndexError:
            pass

        cr = self.cr_drawing_area
        cr.set_source_surface(self.cr_drawing_area_map)
        cr.paint()
        cr.set_source_surface(self.cr_marks)
        cr.paint()
        self.window.draw_drawable(self.xgc, self.pixmap, 0, 0, 0, 0, -1, -1)

        self.drag_start_x = int(event.x)
        self.drag_start_y = int(event.y)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.last_drag_offset_x = 0
        self.last_drag_offset_y = 0
        self.dragging = True
        gobject.timeout_add(self.DRAG_RECHECK_SPEED, self.__drag_draw)

    def __drag(self, widget, event):
        if not self.dragging:
            return True
        self.drag_offset_x = self.drag_start_x - int(event.x)
        self.drag_offset_y = self.drag_start_y - int(event.y)
        return True

    def __drag_draw(self):
        if not self.dragging:
            return False

        delta = math.sqrt((self.last_drag_offset_x - self.drag_offset_x) ** 2 + (self.last_drag_offset_y - self.drag_offset_y) ** 2)
        if delta < self.MIN_DRAG_REDRAW_DISTANCE:
            return True

        self.last_drag_offset_x = self.drag_offset_x
        self.last_drag_offset_y = self.drag_offset_y

        x, y, width, height = self.get_allocation()

        self.window.clear()
        self.window.draw_drawable(gc=self.xgc,
                                  src=self.pixmap,
                                  xsrc=0,
                                  ysrc=0,
                                  xdest=self.draw_at_x - self.drag_offset_x,
                                  ydest=self.draw_at_y - self.drag_offset_y,
                                  width=width,
                                  height=height)


        return True

    def __drag_end(self, widget, event):
        if not self.dragging:
            return
        self.dragging = False
        offset_x = float(self.drag_offset_x) #(self.drag_start_x - event.x)
        offset_y = float(self.drag_offset_y) #(self.drag_start_y - event.y)
        self.map_center_x += (offset_x / self.tile_loader.TILE_SIZE)
        self.map_center_y += (offset_y / self.tile_loader.TILE_SIZE)
        self.map_center_x, self.map_center_y = self.check_bounds(self.map_center_x, self.map_center_y)
        self.center_latlon = self.num2deg(self.map_center_x, self.map_center_y)
        if offset_x ** 2 + offset_y ** 2 < self.CLICK_RADIUS ** 2:
            self.draw_at_x -= offset_x
            self.draw_at_y -= offset_y
            x, y = event.x, event.y

            c = self.screenpoint2coord((x, y))
            c1 = self.screenpoint2coord([x-self.CLICK_RADIUS, y-self.CLICK_RADIUS])
            c2 = self.screenpoint2coord([x + self.CLICK_RADIUS, y + self.CLICK_RADIUS])

            for l in reversed(self.layers):
                if l.clicked_screen((x, y)) == False:
                    break
                if l.clicked_coordinate(c, c1, c2) == False:
                    break
        else:
            self.emit('map-dragged')
        self.draw_at_x = self.draw_at_y = 0
        if offset_x != 0 or offset_y != 0:
            self.__draw_map()


        ##############################################
        #
        # Map Drawing
        #
        ##############################################


    def __draw_map(self):
        if not self.drawing_area_configured:
            return False
        if self.map_width == 0 or self.map_height == 0:
            return

        try:
            while True:
                x = self.active_tile_loaders.pop()
                x.halt()
        except IndexError:
            pass

        zoom = self.zoom
        size = self.tile_loader.TILE_SIZE
        xi = int(self.map_center_x)
        yi = int(self.map_center_y)
        span_x = int(math.ceil(float(self.map_width) / (size * 2.0)))
        span_y = int(math.ceil(float(self.map_height) / (size * 2.0)))
        offset_x = int(self.map_width / 2 - (self.map_center_x - int(self.map_center_x)) * size)
        offset_y = int(self.map_height / 2 -(self.map_center_y - int(self.map_center_y)) * size)

        undersample = self.double_size
        requests = []
        new_surface_buffer = {}
        old_surface_buffer = self.surface_buffer
        tiles = []


        for i in xrange(-span_x, span_x + 1, 1):
            for j in xrange(-span_y, span_y + 1, 1):
                tile = (xi + i, yi + j)

                dx = i * size + offset_x
                dy = j * size + offset_y
                id_string = self.__get_id_string(tile, zoom, undersample)
                tile = self.check_bounds(*tile)
                if tile in tiles:
                    continue
                if id_string in old_surface_buffer and old_surface_buffer[id_string][0] != self.tile_loader.noimage_cantload and old_surface_buffer[id_string][0] != self.tile_loader.noimage_loading:
                    new_surface_buffer[id_string] = old_surface_buffer[id_string]
                    new_surface_buffer[id_string][1:3] = dx, dy
                else:
                    requests.append(((id_string, tile, zoom, undersample, dx, dy, self._add_to_buffer), {}))
        self.surface_buffer = new_surface_buffer

        reqs = threadpool.makeRequests(self.__run_tile_loader, requests)
        cr = gtk.gdk.CairoContext(cairo.Context(self.cr_drawing_area_map))
        cr.set_source_rgba(0, 0, 0, 1)
        self.delay_expose = True
        cr.paint()
        for r in reqs:
            self.tile_loader_threadpool.putRequest(r)
        self.__draw_layers()
        self.__draw_tiles()

    def __get_id_string(self, tile, display_zoom, undersample):
        return (self.tile_loader.PREFIX, tile[0], tile[1], display_zoom, 1 if undersample else 0)

    def __run_tile_loader(self, id_string, tile, zoom, undersample, x, y, callback_draw):
        d = self.tile_loader(id_string=id_string, tile=tile, zoom=zoom, undersample=undersample, x=x, y=y, callback_draw=callback_draw)
        self.active_tile_loaders.append(d)
        d.run()

    def _add_to_buffer(self, id_string, surface, x, y, scale_source=None):
        self.surface_buffer[id_string] = [surface, x, y, scale_source]
        self.__draw_tiles(which=([surface, x, y, scale_source],))

    def __draw_tiles(self, which=None, off_x=0, off_y=0):
        self.delay_expose = False
        cr = gtk.gdk.CairoContext(cairo.Context(self.cr_drawing_area_map))
        if which == None:
            which = self.surface_buffer.values()
        #print len(which), which
        for surface, x, y, scale_source in which:
            #cr = self.cr_map_context
            #self.i += 1
            #print self.i, surface, x, y, scale_source
            if surface == None:
                print "pbuf was none!"
                return
            size = self.tile_loader.TILE_SIZE
            if scale_source == None:
                cr.set_source_surface(surface, x + off_x, y + off_y)
            else:
                xs, ys = scale_source
                imgpat = cairo.SurfacePattern(surface)
                imgpat.set_filter(cairo.FILTER_BEST)
                scale = cairo.Matrix()
                scale.translate(xs, ys)
                scale.scale(0.5, 0.5)
                scale.translate(-x + off_x, -y + off_y)
                imgpat.set_matrix(scale)
                cr.set_source(imgpat)
            cr.rectangle(max(0, x + off_x), max(0, y + off_y), min(size + x, size, self.map_width - x + size), min(size + y, size, self.map_height - y + size))
            #cr.set_source_rgba(0.5, 0, 0, 0.3)
            cr.fill()
            self.queue_draw_area(max(0, x + off_x), max(0, y + off_y), min(size + x, size, self.map_width - x + size), min(size + y, size, self.map_height - y + size))
            #layout = self.create_pango_layout("%d" % self.i)
            #layout.set_font_description(self.CACHE_DRAW_FONT)
            #cr.set_source_rgba(0, 0, 0, 1)

            #cr.move_to(max(0, x + off_x) + 20*self.i, max(0, y + off_y))
            #cr.show_layout(layout)
        return False

        ##############################################
        #
        # Drawing marks & osd
        #
        ##############################################
    '''
    def __draw_marks(self):
        if not self.drawing_area_configured:
            return False

        self.cr_marks = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map_width, self.map_height)
        cr = gtk.gdk.CairoContext(cairo.Context(self.cr_marks))
        self.emit('draw-marks', cr)
        self.__draw_osd()'''


    def __draw_layers(self):
        if not self.drawing_area_configured:
            return False
        for l in self.layers:
            l.draw()
        

        ##############################################
        #
        # Tile Number calculations
        #
        ##############################################
    def tile_size(self):
        return self.tile_loader.TILE_SIZE

    def get_meters_per_pixel(self, lat):
        return math.cos(lat * math.pi / 180.0) * 2.0 * math.pi * self.RADIUS_EARTH / (256 * 2**self.zoom)

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
