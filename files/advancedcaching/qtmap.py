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
import threadpool
import math
from threading import Lock

from abstractmap import AbstractMap, AbstractMapLayer, AbstractGeocacheLayer, AbstractMarksLayer
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import logging
import geocaching
logger = logging.getLogger('qtmap')



class QtMap(QWidget, AbstractMap):

    def __init__(self, parent, center, zoom, tile_loader = None):
        QWidget.__init__(self)
        AbstractMap.__init__(self, center, zoom, tile_loader)
        self.buffer = QPixmap(self.size())
        self.painter = QPainter()
        
        self.surface_buffer = {}
        self.tile_loader_threadpool = threadpool.ThreadPool(20)
        self.sem = Lock()
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.connect(self, SIGNAL('tile-finished'), self.__draw_tiles)


    def paintEvent(self, ev):
        # blit the pixmap
        p = QPainter(self)
        if self.dragging:
            p.drawPixmap(-self.drag_offset_x, -self.drag_offset_y, self.buffer)
            return
        else:
            p.drawPixmap(0, 0, self.buffer)
            for l in self.layers:
                if l.result == None:
                    continue
                p.drawPixmap(0, 0, l.result)

    #def mouseMoveEvent(self, ev):
    #    p = QPainter(self.buffer)
    #    p.drawLine(self.currentPos, ev.pos())
    #    self.currentPos=QPoint(ev.pos())
    #    self.repaint()

    def mousePressEvent(self, ev):
        if self.dragging or ev.button() != Qt.LeftButton:
            return
        self.dragging = True
        self.drag_start = ev.pos()

    def mouseMoveEvent(self, ev):
        if not self.dragging:
            return
        self.drag_offset_x = self.drag_start.x() - ev.x()
        self.drag_offset_y = self.drag_start.y() - ev.y()
        self.repaint()
        return
        self.drag_end = ev.pos()
        offset_x = self.drag_start.x() - self.drag_end.x()
        offset_y = self.drag_start.y() - self.drag_end.y()
        self._move_map_relative(offset_x, offset_y)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self._draw_map()
        self.drag_start = ev.pos()


    def mouseReleaseEvent(self, ev):
        if not self.dragging or ev.button() != Qt.LeftButton:
            return
        #self.dragging = False
        #self.repaint()
        self.drag_end = ev.pos()
        offset_x = self.drag_start.x() - self.drag_end.x()
        offset_y = self.drag_start.y() - self.drag_end.y()
        self._move_map_relative(offset_x, offset_y)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.dragging = False
        self._draw_map()

    @staticmethod
    def _load_tile(filename):
        return filename

    def resizeEvent(self, ev):
        s = ev.size()
        self.buffer = QPixmap(s)
        self.map_width = s.width()
        self.map_height = s.height()
        for l in self.layers:
            l.resize()
        self._draw_map()

        ##############################################
        #
        # Map actions
        #
        ##############################################

    def redraw_layers(self):
        if self.dragging:
            return
        self.__draw_layers()
        self.repaint()

        ##############################################
        #
        # Drawing marks & osd
        #
        ##############################################


    def __draw_layers(self):
        for l in self.layers:
            l.draw()

        
        ##############################################
        #
        # Map Drawing
        #
        ##############################################


    def _draw_map(self):
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
        #cr = gtk.gdk.CairoContext(cairo.Context(self.cr_drawing_area_map))
        #cr.set_source_rgba(0, 0, 0, 1)
        self.delay_expose = True
        #cr.paint()
        for r in reqs:
            self.tile_loader_threadpool.putRequest(r)
        self.__draw_layers()
        self.__draw_tiles()
        #self.repaint()

    def __get_id_string(self, tile, display_zoom, undersample):
        return (self.tile_loader.PREFIX, tile[0], tile[1], display_zoom, 1 if undersample else 0)

    def __run_tile_loader(self, id_string, tile, zoom, undersample, x, y, callback_draw):
        #callback_draw = lambda x, y, z: 1
        d = self.tile_loader(id_string=id_string, tile=tile, zoom=zoom, undersample=undersample, x=x, y=y, callback_draw=callback_draw, callback_load = self._load_tile)
        self.active_tile_loaders.append(d)
        d.run()

    def _add_to_buffer(self, id_string, surface, x, y, scale_source=None):
        self.surface_buffer[id_string] = [surface, x, y, scale_source]
        self.emit(SIGNAL('tile-finished'), (([surface, x, y, scale_source],)))
        #self.__draw_tiles(which=([surface, x, y, scale_source],))

    def __draw_tiles(self, which=None, off_x=0, off_y=0):
        self.delay_expose = False
        #cr = gtk.gdk.CairoContext(cairo.Context(self.cr_drawing_area_map))
        p = self.painter
        self.sem.acquire()

        if which == None:
            which = self.surface_buffer.values()

        for surface, x, y, scale_source in which:
            if surface == None:
                logger.info("Surface was none")
                continue
            size = self.tile_loader.TILE_SIZE
            try:
                pm = QPixmap(surface)
            except Exception:
                logger.exception("Could not load Pixmap from Filename %s" % surface)
                try:
                    pm = QPixmap(self.noimage_cantload)
                except Exception:
                    logger.exception("Could not load replacement Pixmap from Filename %s" % self.noimage_cantload)
            if scale_source == None: ###################################### delete me
                p.begin(self.buffer)
                p.drawPixmap(x+off_x, y+off_y, pm)
                p.end()
            else:
                p.begin(self.buffer)
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                xs, ys = scale_source
                target = QRectF(x + off_x, y + off_y, size, size)
                source = QRectF(xs, ys, size/2, size/2)
                p.drawPixmap(target, pm, source)
                p.end()

            #cr.rectangle(max(0, x + off_x), max(0, y + off_y), min(size + x, size, self.map_width - x + size), min(size + y, size, self.map_height - y + size))

            #cr.fill()
            #self.queue_draw_area(max(0, x + off_x), max(0, y + off_y), min(size + x, size, self.map_width - x + size), min(size + y, size, self.map_height - y + size))

        self.sem.release()
        self.repaint()
        return False


class QtSingleMarkLayer(AbstractMapLayer):
    PEN_TARGET = QPen(QColor(0, 0, 200), 1)
    PEN_SHADOW_TARGET = QPen(QColor(255, 255, 255), 3)

    def __init__(self, coordinate):
        AbstractMapLayer.__init__(self)
        self.painter = QPainter()
        self.coord = coordinate

    def attach(self, map):
        AbstractMapLayer.attach(self, map)
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def resize(self):
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def draw(self):
        self.result.fill(Qt.transparent)

        t = self.map.coord2point(self.coord)
        if not self.map.point_in_screen(t):
            return
        p = self.painter
        p.begin(self.result)
        p.setRenderHint(QPainter.Antialiasing)


        radius_o = 15
        radius_i = 3
        radius_c = 10
        p.setPen(QtSingleMarkLayer.PEN_SHADOW_TARGET)
        p.drawLines(
            QLineF(t[0] - radius_o, t[1], t[0] - radius_i, t[1]),
            QLineF(t[0] + radius_o, t[1], t[0] + radius_i, t[1]),
            QLineF(t[0], t[1] + radius_o, t[0], t[1] + radius_i),
            QLineF(t[0], t[1] - radius_o, t[0], t[1] - radius_i)
            )
        p.drawArc(QRectF(t[0] - radius_c/2, t[1] - radius_c/2, radius_c, radius_c), 0, 16*360)

        p.setPen(QtSingleMarkLayer.PEN_TARGET)
        p.drawLines(
            QLineF(t[0] - radius_o, t[1], t[0] - radius_i, t[1]),
            QLineF(t[0] + radius_o, t[1], t[0] + radius_i, t[1]),
            QLineF(t[0], t[1] + radius_o, t[0], t[1] + radius_i),
            QLineF(t[0], t[1] - radius_o, t[0], t[1] - radius_i)
            )
        p.drawArc(QRectF(t[0] - radius_c/2, t[1] - radius_c/2, radius_c, radius_c), 0, 16*360)
        p.end()

class QtOsdLayer(AbstractMapLayer):

    MESSAGE_DRAW_FONT = QFont('Sans', 12)
    MESSAGE_DRAW_PEN = QPen(QColor(0, 0, 0))
    OSD_PEN = QPen(QColor(255, 255, 255))
    OSD_BRUSH = QBrush(QColor(0, 0, 0))

    def __init__(self):
        AbstractMapLayer.__init__(self)
        self.painter = QPainter()

    def attach(self, map):
        AbstractMapLayer.attach(self, map)
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def resize(self):
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    @staticmethod
    def set_layout(message_draw_font, message_draw_color):
        QtOsdLayer.MESSAGE_DRAW_FONT = message_draw_font
        QtOsdLayer.MESSAGE_DRAW_COLOR = message_draw_color

    def draw(self):
        
        # scale bar position
        position = (20, self.map.map_height - 28)

        # scale bar calculation
        center = self.map.get_center()
        mpp = self.map.get_meters_per_pixel(center.lat)
        avglength = self.map.map_width / 5
        first_length_meters = mpp * avglength
        final_length_meters = round(first_length_meters, int(-math.floor(math.log(first_length_meters, 10) + 0.00001)))
        final_length_pixels = final_length_meters / mpp

        if final_length_meters < 10000:
            scale_msg = "%d m" % final_length_meters
        else:
            scale_msg = "%d km" % (final_length_meters/1000)

        # start drawing
        self.result.fill(Qt.transparent)
        p = self.painter
        p.begin(self.result)
        p.setFont(QtOsdLayer.MESSAGE_DRAW_FONT)
        p.setPen(QtOsdLayer.MESSAGE_DRAW_PEN)

        # osd message
        if self.map.osd_message != None:
            p.drawText(QPoint(20, 20), self.map.osd_message)

        # scale bar text
        p.drawText(QPoint(position[0], position[1]), scale_msg)

        # scale bar
        p.setPen(QtOsdLayer.OSD_PEN)
        p.setBrush(QtOsdLayer.OSD_BRUSH)
        p.drawRect(position[0], position[1] + 10, final_length_pixels, 3)
        p.end()


logger = logging.getLogger('geocachelayer')

class QtGeocacheLayer(AbstractGeocacheLayer):

    CACHE_DRAW_FONT = QFont('Sans', 10)
    CACHE_DRAW_FONT_PEN = QPen(QColor(0, 0, 0))

    PEN_CURRENT_CACHE = QPen(QColor(200, 0, 0), 1)
    PEN_CACHE_DISABLED = QPen(QColor(255, 0, 0), 1)

    # map markers colors
    COLOR_MARKED = QColor(255, 255, 0)
    COLOR_DEFAULT = QColor(0, 0, 255)
    COLOR_FOUND = QColor(100, 100, 100)
    COLOR_REGULAR = QColor(0, 200, 0)
    COLOR_MULTI = QColor(255, 120, 0)
    COLOR_CACHE_CENTER = QColor(0, 0, 0)
    COLOR_WAYPOINTS = QColor(200, 0, 200)

    def __init__(self, pointprovider, show_cache_callback):
        AbstractGeocacheLayer.__init__(self, pointprovider, show_cache_callback)
        self.painter = QPainter()

    def attach(self, map):
        AbstractMapLayer.attach(self, map)
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def resize(self):
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def draw(self):

        coords = self.pointprovider.get_points_filter(self.map.get_visible_area(), self.select_found, self.MAX_NUM_RESULTS_SHOW)
        self.result.fill(Qt.transparent)
        if self.map.get_zoom() < self.CACHES_ZOOM_LOWER_BOUND:
            self.map.set_osd_message('Too many geocaches to display.')
            self.visualized_geocaches = []
            return
        elif len(coords) >= self.MAX_NUM_RESULTS_SHOW:
            self.map.set_osd_message('Too many geocaches to display.')
            self.visualized_geocaches = []
            return
        self.map.set_osd_message(None)
        self.visualized_geocaches = coords
        draw_short = (len(coords) > self.TOO_MANY_POINTS)

        default_radius = self.CACHE_DRAW_SIZE
        found, regular, multi, default = self.COLOR_FOUND, self.COLOR_REGULAR, self.COLOR_MULTI, self.COLOR_DEFAULT


        p = self.painter
        p.begin(self.result)
        p.setFont(self.CACHE_DRAW_FONT)
        cache_pen = QPen()
        cache_pen.setWidth(4)
        cache_pen.setJoinStyle(Qt.MiterJoin)

        desc_pen = QPen()
        desc_pen.setWidth(2)

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
            cache_pen.setColor(color)


            loc = self.map.coord2point(c)

            if c.alter_lat != None and (c.alter_lat != 0 and c.alter_lon != 0):
                x = self.map.coord2point(geo.Coordinate(c.alter_lat, c.alter_lon))
                if x != loc:
                    p.setPen(QPen(color, 2))
                    p.drawLine(QPoint(*loc), QPoint(*t))

            if draw_short:
                radius = radius / 2.0

            if c.marked:
                p.setBrush(QBrush(QColor(1, 1, 0, 0.5)))
                p.setPen(QPen(Qt.transparent))
                p.drawRectangle(loc[0] - radius, loc[1] - radius, radius * 2, radius * 2)

            p.setBrush(Qt.transparent)
            p.setPen(cache_pen)
            p.drawRect(loc[0] - radius, loc[1] - radius, radius * 2, radius * 2)
            p.setBrush(QBrush(Qt.transparent))

            if draw_short:
                continue

            # +
            p.setPen(QPen(color, 1))
            p.drawLines(QLine(loc[0], loc[1] - 3, loc[0], loc[1] + 3), QLine(loc[0] - 3, loc[1], loc[0] + 3, loc[1]))


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
                pos_x = loc[0] + radius + 3 + 1
                pos_y = loc[1] + radius - (dist * count) + dist
                desc_pen.setColor(color)
                p.setPen(desc_pen)
                lines = (QLine(pos_x, pos_y + dist * i, pos_x + width, pos_y + dist * i) for i in xrange(count))
                p.drawLines(*lines)

            # if this cache is the active cache
            if self.current_cache != None and c.name == self.current_cache.name:
                p.setPen(self.PEN_CURRENT_CACHE)
                p.setBrush(QBrush(Qt.transparent))
                radius_outline = radius + 3
                p.drawRect(loc[0] - radius_outline, loc[1] - radius_outline, radius_outline * 2, radius_outline * 2)

            # if this cache is disabled
            if c.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
                p.setPen(self.PEN_CACHE_DISABLED)
                radius_disabled = 7
                p.drawLine(loc[0]-radius_disabled, loc[1]-radius_disabled, loc[0] + radius_disabled, loc[1] + radius_disabled)

            # print the name?
            if self.show_name:
                p.setPen(self.CACHE_DRAW_FONT_PEN)
                p.drawText(loc[0] + 4 + radius, loc[1] - height + 2, AbstractGeocacheLayer.shorten_name(c.title, 20))

        p.end()
        return

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

logger = logging.getLogger('markslayer')
'''
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
                cr.set_dash((5,3))
                cr.new_sub_path()
                cr.arc(p[0], p[1], radius_pixels, 0, math.pi * 2)
                cr.stroke()
                cr.set_dash(())

                # draw moving direction, if we're moving
                if self.gps_data.speed > 2.5: # km/h
                    position = p#(self.map.map_width - self.OSD_BORDER_LEFTRIGHT, self.map.map_height - self.OSD_BORDER_TOPBOTTOM)

                    arrow = SimpleGui._get_arrow_transformed(position[0] - 15, position[1] - 15, 30, 30, self.gps_data.bearing)
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
            layout = self.map.create_pango_layout(SimpleGui._format_distance(self.gps_target_distance))
            layout.set_font_description(self.DISTANCE_DRAW_FONT)
            width, height = layout.get_pixel_size()
            cr.set_source_color(self.DISTANCE_DRAW_FONT_COLOR)
            cr.move_to(position[0] - width, position[1])
            cr.show_layout(layout)

        self.result = surface'''