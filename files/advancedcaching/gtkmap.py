#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2010 Daniel Fett
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

import logging
import math

from abstractmap import AbstractGeocacheLayer
from abstractmap import AbstractMap
from abstractmap import AbstractMapLayer
from abstractmap import AbstractMarksLayer
import cairo
import geo
import geocaching
import gobject
import gtk
import openstreetmap
import pango
import threadpool
logger = logging.getLogger('gtkmap')


class Map(gtk.DrawingArea, AbstractMap):


    MIN_DRAG_REDRAW_DISTANCE = 5
    DRAG_RECHECK_SPEED = 20
    
    LAZY_SET_CENTER_DIFFERENCE = 0.1 # * screen (width|height)

        
    def __init__(self, center, zoom, tile_loader=None, draggable=True):
        gtk.DrawingArea.__init__(self)
        AbstractMap.__init__(self, center, zoom, tile_loader)

        self.connect("expose_event", self.__expose_event)
        self.connect("configure_event", self.__configure_event)
        self.connect("button_press_event", self.__drag_start)
        self.connect("scroll_event", self.__scroll)
        self.connect("button_release_event", self.__drag_end)
        
        if draggable:
            self.connect("motion_notify_event", self.__drag)
        self.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.SCROLL)

        try:
            gobject.signal_new('tile-loader-changed', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, ))
            gobject.signal_new('map-dragged', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
            gobject.signal_new('draw-marks', Map, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
        except RuntimeError:
            pass

        self.surface_buffer = {}
        self.delay_expose = False

        self.tile_loader_threadpool = threadpool.ThreadPool(openstreetmap.CONCURRENT_THREADS * 2)

        #self.ts = openstreetmap.TileServer(self.tile_loader)

        self.drawing_area_configured = self.drawing_area_arrow_configured = False


        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))



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
        if self.dragging:
            return
        self.queue_draw()

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
        cr.save()
        cr.clip()
        cr.set_source_surface(self.cr_drawing_area_map)
        cr.paint()
        for l in self.layers:
            if l.result == None:
                continue
            cr.set_source_surface(l.result)
            cr.paint()
        cr.restore()
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

        for l in self.layers:
            l.resize()
        gobject.idle_add(self._draw_map)


        ##############################################
        #
        # User Input
        #
        ##############################################

    def __scroll(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.relative_zoom(-1)
        else:
            self.relative_zoom(+ 1)

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
        offset_x = self.drag_offset_x #(self.drag_start_x - event.x)
        offset_y = self.drag_offset_y #(self.drag_start_y - event.y)
        self._move_map_relative(offset_x, offset_y)
        if self._check_click(offset_x, offset_y, event.x, event.y):
            self.draw_at_x -= offset_x
            self.draw_at_y -= offset_y
        else:
            self.emit('map-dragged')
        self.draw_at_x = self.draw_at_y = 0
        if offset_x != 0 or offset_y != 0:
            self._draw_map()


        ##############################################
        #
        # Map Drawing
        #
        ##############################################


    def _draw_map(self):
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

    @staticmethod
    def _load_tile(filename):
        surface = cairo.ImageSurface.create_from_png(filename)
        if surface.get_width() != surface.get_height():
            raise Exception("Image too small, probably corrupted file")
        return surface

    def __run_tile_loader(self, id_string, tile, zoom, undersample, x, y, callback_draw):
        d = self.tile_loader(id_string=id_string, tile=tile, zoom=zoom, undersample=undersample, x=x, y=y, callback_draw=callback_draw, callback_load=self._load_tile)
        self.active_tile_loaders.append(d)
        d.run()

    def _add_to_buffer(self, id_string, surface, x, y, scale_source=None):
        self.surface_buffer[id_string] = [surface, x, y, scale_source]
        self.__draw_tiles(which=([surface, x, y, scale_source], ))

    def __draw_tiles(self, which=None, off_x=0, off_y=0):
        self.delay_expose = False
        cr = gtk.gdk.CairoContext(cairo.Context(self.cr_drawing_area_map))
        if which == None:
            which = self.surface_buffer.values()

        for surface, x, y, scale_source in which:

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

            cr.fill()
            self.queue_draw_area(max(0, x + off_x), max(0, y + off_y), min(size + x, size, self.map_width - x + size), min(size + y, size, self.map_height - y + size))

        return False

        ##############################################
        #
        # Drawing marks & osd
        #
        ##############################################


    def __draw_layers(self):
        if not self.drawing_area_configured:
            return False
        for l in self.layers:
            l.draw()
        

class SingleMarkLayer(AbstractMapLayer):
    COLOR_TARGET = gtk.gdk.color_parse('darkblue')
    COLOR_TARGET_SHADOW = gtk.gdk.color_parse('white')

    def __init__(self, coordinate):
        AbstractMapLayer.__init__(self)
        self.coord = coordinate

    def draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map.map_width, self.map.map_height)
        cr = gtk.gdk.CairoContext(cairo.Context(surface))
        self.result = surface

        t = self.map.coord2point(self.coord)
        if not self.map.point_in_screen(t):
            return

        radius_o = 15
        radius_i = 3
        radius_c = 10
        cr.move_to(t[0] - radius_o, t[1])
        cr.line_to(t[0] - radius_i, t[1])
        cr.move_to(t[0] + radius_o, t[1])
        cr.line_to(t[0] + radius_i, t[1])
        cr.move_to(t[0], t[1] + radius_o)
        cr.line_to(t[0], t[1] + radius_i)
        cr.move_to(t[0], t[1] - radius_o)
        cr.line_to(t[0], t[1] - radius_i)
        cr.new_sub_path()
        cr.arc(t[0], t[1], radius_c, 0, math.pi * 2)

        cr.set_source_color(self.COLOR_TARGET_SHADOW)
        cr.set_line_width(3)
        cr.stroke_preserve()
        cr.set_source_color(self.COLOR_TARGET)
        cr.set_line_width(2)
        cr.stroke()

class OsdLayer(AbstractMapLayer):

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
            msg = "%d km" % (final_length_meters / 1000)
        layout = self.map.create_pango_layout(msg)
        layout.set_font_description(self.MESSAGE_DRAW_FONT)
        cr.move_to(position[0], position[1] - 15)
        cr.show_layout(layout)


        self.result = surface


logger = logging.getLogger('geocachelayer')

class GeocacheLayer(AbstractGeocacheLayer):

    CACHE_DRAW_FONT = pango.FontDescription("Sans 10")
    CACHE_DRAW_FONT_COLOR = gtk.gdk.color_parse('black')

    # map markers colors
    COLOR_MARKED = gtk.gdk.color_parse('yellow')
    COLOR_DEFAULT = gtk.gdk.color_parse('blue')
    COLOR_FOUND = gtk.gdk.color_parse('grey')
    COLOR_REGULAR = gtk.gdk.color_parse('green')
    COLOR_MULTI = gtk.gdk.color_parse('orange')
    COLOR_CACHE_CENTER = gtk.gdk.color_parse('black')
    COLOR_CURRENT_CACHE = gtk.gdk.color_parse('red')
    COLOR_WAYPOINTS = gtk.gdk.color_parse('deeppink')

    def draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map.map_width, self.map.map_height)
        cr = gtk.gdk.CairoContext(cairo.Context(surface))

        coords = self.get_geocaches_callback(self.map.get_visible_area(), self.MAX_NUM_RESULTS_SHOW)

        if self.map.get_zoom() < self.CACHES_ZOOM_LOWER_BOUND:
            self.map.set_osd_message('Zoom in to see geocaches.')
            self.visualized_geocaches = []
            self.result = surface
            return
        elif len(coords) >= self.MAX_NUM_RESULTS_SHOW:
            self.map.set_osd_message('Too many geocaches to display.')
            self.visualized_geocaches = []
            self.result = surface
            return
        self.map.set_osd_message(None)
        self.visualized_geocaches = coords
        draw_short = (len(coords) > self.TOO_MANY_POINTS)

        default_radius = self.CACHE_DRAW_SIZE
        found, regular, multi, default = self.COLOR_FOUND, self.COLOR_REGULAR, self.COLOR_MULTI, self.COLOR_DEFAULT



        for c in coords: # for each geocache
            radius = default_radius
            if c.found:
                color = found
            elif c.type == geocaching.GeocacheCoordinate.TYPE_REGULAR:
                color = regular
            elif c.type == geocaching.GeocacheCoordinate.TYPE_MULTI:
                color = multi
            else:
                color = default
            cr.set_source_color(color)


            p = self.map.coord2point(c)

            if c.alter_lat != None and (c.alter_lat != 0 and c.alter_lon != 0):
                x = self.map.coord2point(geo.Coordinate(c.alter_lat, c.alter_lon))
                if x != p:
                    cr.move_to(p[0], p[1])
                    cr.line_to(x[0], x[1])
                    cr.set_line_width(2)
                    cr.stroke()

            if draw_short:
                radius = radius / 2.0

            if c.marked:
                cr.set_source_rgba(1, 1, 0, 0.5)
                cr.rectangle(p[0] - radius, p[1] - radius, radius * 2, radius * 2)
                cr.fill()


            cr.set_source_color(color)
            cr.set_line_width(4)
            cr.rectangle(p[0] - radius, p[1] - radius, radius * 2, radius * 2)
            cr.stroke()

            if draw_short:
                continue




            # if we have a description for this cache...
            if c.was_downloaded():
                # draw something like:
                # ----
                # ----
                # ----
                # besides the icon
                width = 6
                dist = 3
                count = 3
                pos_x = p[0] + radius + 3 + 1
                pos_y = p[1] + radius - (dist * count) + dist
                cr.set_line_width(1)
                for i in xrange(count):
                    cr.move_to(pos_x, pos_y + dist * i)
                    cr.line_to(pos_x + width, pos_y + dist * i)
                    cr.set_line_width(2)
                cr.stroke()

            # if this cache is the active cache
            if self.current_cache != None and c.name == self.current_cache.name:
                cr.set_line_width(1)
                cr.set_source_color(self.COLOR_CURRENT_CACHE)
                #radius = 7
                radius_outline = radius + 3
                cr.rectangle(p[0] - radius_outline, p[1] - radius_outline, radius_outline * 2, radius_outline * 2)
                cr.stroke()

            # if this cache is disabled
            if c.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
                cr.set_line_width(3)
                cr.set_source_color(self.COLOR_CURRENT_CACHE)
                radius_disabled = 7
                cr.move_to(p[0]-radius_disabled, p[1]-radius_disabled)
                cr.line_to(p[0] + radius_disabled, p[1] + radius_disabled)
                cr.stroke()


            # print the name?
            if self.show_name:
                layout = self.map.create_pango_layout(AbstractGeocacheLayer.shorten_name(c.title, 20))
                layout.set_font_description(self.CACHE_DRAW_FONT)
                width, height = layout.get_pixel_size()

                cr.move_to(p[0] + 4 + radius, p[1] - height + 2)
                #cr.set_line_width(1)
                cr.set_source_color(self.CACHE_DRAW_FONT_COLOR)
                cr.show_layout(layout)

            cr.set_source_color(self.COLOR_CACHE_CENTER)
            cr.set_line_width(1)
            cr.move_to(p[0], p[1] - 3)
            cr.line_to(p[0], p[1] + 3) # |
            cr.move_to(p[0] - 3, p[1],)
            cr.line_to(p[0] + 3, p[1]) # ---
            cr.stroke()

        # draw additional waypoints
        # --> print description!
        if self.current_cache != None and self.current_cache.get_waypoints() != None:
            cr.set_source_color(self.COLOR_WAYPOINTS)
            cr.set_line_width(1)
            radius = 5
            num = 0
            for w in self.current_cache.get_waypoints():
                if w['lat'] != -1 and w['lon'] != -1:
                    num = num + 1
                    p = self.map.coord2point(geo.Coordinate(w['lat'], w['lon']))
                    if not self.map.point_in_screen(p):
                        continue
                    cr.move_to(p[0], p[1] - radius)
                    cr.line_to(p[0], p[1] + radius) #  |
                    #cr.stroke()
                    cr.move_to(p[0] - radius, p[1])
                    cr.line_to(p[0] + radius, p[1]) # ---
                    #cr.stroke()
                    cr.arc(p[0], p[1], radius, 0, math.pi * 2)
                    layout = self.map.create_pango_layout('')
                    layout.set_markup('<i>%s</i>' % (w['id']))
                    layout.set_font_description(self.CACHE_DRAW_FONT)

                    cr.move_to(p[0] + 3 + radius, p[1] - 3 - radius)
                    #cr.set_line_width(1)
                    cr.set_source_color(self.COLOR_WAYPOINTS)
                    cr.show_layout(layout)
            cr.stroke()
        self.result = surface

logger = logging.getLogger('markslayer')

class MarksLayer(AbstractMarksLayer):

    SIZE_CURRENT_POSITION = 3
    COLOR_CURRENT_POSITION = gtk.gdk.color_parse('green')
    COLOR_CURRENT_POSITION_NO_FIX = gtk.gdk.color_parse('red')
    COLOR_TARGET = gtk.gdk.color_parse('darkblue')
    COLOR_TARGET_SHADOW = gtk.gdk.color_parse('white')
    COLOR_CROSSHAIR = gtk.gdk.color_parse("black")
    COLOR_LINE_INVERT = gtk.gdk.color_parse("blue")
    COLOR_ACCURACY = gtk.gdk.color_parse("orange")

    COLOR_DIRECTION_ARROW = gtk.gdk.color_parse("black")
    COLOR_DIRECTION_ARROW_SHADOW = gtk.gdk.color_parse("white")

    DISTANCE_DRAW_FONT = pango.FontDescription("Sans 20")
    DISTANCE_DRAW_FONT_COLOR = gtk.gdk.color_parse("black")

    OSD_BORDER_TOPBOTTOM = 25
    OSD_BORDER_LEFTRIGHT = 35


    def __init__(self):
        AbstractMarksLayer.__init__(self)

    def draw(self):

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.map.map_width, self.map.map_height)
        cr = gtk.gdk.CairoContext(cairo.Context(surface))
        # if we have a target, draw it
        if self.current_target != None:
            t = self.map.coord2point(self.current_target)
            if t != False and self.map.point_in_screen(t):


                radius_o = 15
                radius_i = 3
                radius_c = 10
                cr.move_to(t[0] - radius_o, t[1])
                cr.line_to(t[0] - radius_i, t[1])
                cr.move_to(t[0] + radius_o, t[1])
                cr.line_to(t[0] + radius_i, t[1])
                cr.move_to(t[0], t[1] + radius_o)
                cr.line_to(t[0], t[1] + radius_i)
                cr.move_to(t[0], t[1] - radius_o)
                cr.line_to(t[0], t[1] - radius_i)
                cr.new_sub_path()
                cr.arc(t[0], t[1], radius_c, 0, math.pi * 2)

                cr.set_source_color(self.COLOR_TARGET_SHADOW)
                cr.set_line_width(3)
                cr.stroke_preserve()
                cr.set_source_color(self.COLOR_TARGET)
                cr.set_line_width(2)
                cr.stroke()

        else:
            t = False

        if self.gps_last_good_fix != None and self.gps_last_good_fix.position != None:
            p = self.map.coord2point(self.gps_last_good_fix.position)
        else:
            p = None

        # a line between target and position if we have both
        if p != None and t != False:
            cr.set_line_width(5)
            cr.set_source_rgba(1, 1, 0, 0.5)
            if self.map.point_in_screen(t) and self.map.point_in_screen(p):
                cr.move_to(p[0], p[1])
                cr.line_to(t[0], t[1])
                cr.stroke()
            elif self.map.point_in_screen(p):
                direction = math.radians(self.gps_target_bearing - 180)
                # correct max length: sqrt(width**2 + height**2)
                length = self.map.map_width
                cr.move_to(p[0], p[1])
                cr.line_to(int(p[0] - math.sin(direction) * length), int(p[1] + math.cos(direction) * length))
                cr.stroke()

            elif self.map.point_in_screen(t):
                direction = math.radians(self.gps_target_bearing)
                length = self.map.map_width + self.map.map_height
                cr.move_to(t[0], t[1])
                cr.line_to(int(t[0] - math.sin(direction) * length), int(t[1] + math.cos(direction) * length))
                cr.stroke()

        if p != None and self.map.point_in_screen(p):

            cr.set_line_width(2)

            if self.gps_has_fix:
                radius = self.gps_data.error
                radius_pixels = radius / self.map.get_meters_per_pixel(self.gps_last_good_fix.position.lat)
            else:
                radius_pixels = 10

            radius_o = int((radius_pixels + 8) / math.sqrt(2))
            radius_i = int((radius_pixels - 8) / math.sqrt(2))



            if radius_i < 2:
                radius_i = 2
            if self.gps_has_fix:
                cr.set_source_color(self.COLOR_CURRENT_POSITION)
            else:
                cr.set_source_color(self.COLOR_CURRENT_POSITION_NO_FIX)

            # \  /
            #
            # /  \

            cr.arc(p[0], p[1], self.SIZE_CURRENT_POSITION, 0, math.pi * 2)
            cr.fill()
            if self.gps_has_fix:
                cr.set_line_width(1)
                cr.set_source_color(self.COLOR_ACCURACY)
                cr.set_dash((5, 3))
                cr.new_sub_path()
                cr.arc(p[0], p[1], radius_pixels, 0, math.pi * 2)
                cr.stroke()
                cr.set_dash(())

                # draw moving direction, if we're moving
                if self.gps_data.speed > 2.5: # km/h
                    position = p#(self.map.map_width - self.OSD_BORDER_LEFTRIGHT, self.map.map_height - self.OSD_BORDER_TOPBOTTOM)

                    arrow = self._get_arrow_transformed(position[0] - 15, position[1] - 15, 30, 30, self.gps_data.bearing)
                    cr.move_to(* arrow[0])
                    for x, y in arrow:
                        cr.line_to(x, y)
                    cr.line_to(* arrow[0])
                else:
                    cr.arc(p[0], p[1], self.SIZE_CURRENT_POSITION + 5, 0, math.pi * 2)

                cr.set_source_color(self.COLOR_DIRECTION_ARROW_SHADOW)
                cr.set_line_width(2)
                cr.stroke_preserve()
                cr.set_source_color(self.COLOR_DIRECTION_ARROW)
                cr.set_line_width(1)
                cr.stroke()

        if self.gps_data != None and self.gps_has_fix:
            position = (self.map.map_width - self.OSD_BORDER_LEFTRIGHT, self.OSD_BORDER_TOPBOTTOM)
            layout = self.map.create_pango_layout(geo.Coordinate.format_distance(self.gps_target_distance))
            layout.set_font_description(self.DISTANCE_DRAW_FONT)
            width, height = layout.get_pixel_size()
            cr.set_source_color(self.DISTANCE_DRAW_FONT_COLOR)
            cr.move_to(position[0] - width, position[1])
            cr.show_layout(layout)

        self.result = surface
