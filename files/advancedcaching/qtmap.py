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

import logging
logger = logging.getLogger('qtmap')

from PyQt4.QtCore import *
from PyQt4.QtGui import *
logger.debug("Using pyqt bindings")
import geocaching
import geo



class QtMap(QWidget, AbstractMap):

    __pyqtSignals__ = ("tileLoaderChanged(PyObject)", "mapDragged()", "zoomChanged()")

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

        ##############################################
        #
        # Event handling
        #
        ##############################################

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

    #@pyqtSignature("zoomIn()")
    def zoom_in(self):
        self.relative_zoom(+1)


    #@pyqtSignature("zoomOut()")
    def zoom_out(self):
        self.relative_zoom(-1)

    def redraw_layers(self):
        if self.dragging:
            return
        self.__draw_layers()
        self.repaint()

    def refresh(self):
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

    @staticmethod
    def _load_tile(filename):
        return filename

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

class AbstractQtLayer(AbstractMapLayer):

    def __init__(self):
        self.painter = QPainter()

    def attach(self, map):
        AbstractMapLayer.attach(self, map)
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)

    def resize(self):
        self.result = QPixmap(self.map.size())
        self.result.fill(Qt.transparent)


class QtSingleMarkLayer(AbstractQtLayer):
    PEN_TARGET = QPen(QColor(0, 0, 200), 1)
    PEN_SHADOW_TARGET = QPen(QColor(255, 255, 255), 3)

    def __init__(self, coordinate):
        AbstractQtLayer.__init__(self)
        self.coord = coordinate

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

class QtOsdLayer(AbstractQtLayer):

    MESSAGE_DRAW_FONT = QFont('Sans', 12)
    MESSAGE_DRAW_PEN = QPen(QColor(0, 0, 0))
    OSD_PEN = QPen(QColor(255, 255, 255))
    OSD_BRUSH = QBrush(QColor(0, 0, 0))

    OSD_BORDER_TOPBOTTOM = 25
    OSD_BORDER_LEFTRIGHT = 35

    def __init__(self):
        AbstractQtLayer.__init__(self)

    @staticmethod
    def set_layout(message_draw_font, message_draw_color):
        QtOsdLayer.MESSAGE_DRAW_FONT = message_draw_font
        QtOsdLayer.MESSAGE_DRAW_COLOR = message_draw_color

    def draw(self):
        
        # scale bar position
        position = (self.OSD_BORDER_LEFTRIGHT, self.map.map_height - 10 - self.OSD_BORDER_TOPBOTTOM)

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
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QtOsdLayer.MESSAGE_DRAW_FONT)
        p.setPen(QtOsdLayer.MESSAGE_DRAW_PEN)

        # osd message
        if self.map.osd_message != None:
            p.drawText(QRect(self.OSD_BORDER_LEFTRIGHT, self.OSD_BORDER_TOPBOTTOM, 200, 20), Qt.AlignLeft, self.map.osd_message)

        # scale bar text
        p.drawText(QRect(self.OSD_BORDER_LEFTRIGHT, self.map.map_height - 10 - self.OSD_BORDER_TOPBOTTOM - 20, 200, 20), Qt.AlignLeft, scale_msg)

        # scale bar
        p.setPen(QtOsdLayer.OSD_PEN)
        p.setBrush(QtOsdLayer.OSD_BRUSH)
        p.drawRect(position[0], position[1] + 10, final_length_pixels, 3)
        p.end()


logger = logging.getLogger('geocachelayer')

class QtGeocacheLayer(AbstractQtLayer, AbstractGeocacheLayer):

    CACHE_DRAW_FONT = QFont('Sans', 10)
    CACHE_DRAW_FONT_PEN = QPen(QColor(0, 0, 0))

    PEN_CURRENT_CACHE = QPen(QColor(200, 0, 0), 1)
    PEN_CACHE_DISABLED = QPen(QColor(255, 0, 0), 3)
    PEN_WAYPOINTS = QPen(QColor(200, 0, 200), 1)

    # map markers colors
    COLOR_MARKED = QColor(255, 255, 0)
    COLOR_DEFAULT = QColor(0, 0, 255)
    COLOR_FOUND = QColor(100, 100, 100)
    COLOR_REGULAR = QColor(0, 200, 0)
    COLOR_MULTI = QColor(255, 120, 0)
    COLOR_CACHE_CENTER = QColor(0, 0, 0)

    def __init__(self, pointprovider, show_cache_callback):
        AbstractQtLayer.__init__(self)
        AbstractGeocacheLayer.__init__(self, pointprovider, show_cache_callback)

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
        #p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self.CACHE_DRAW_FONT)
        cache_pen = QPen()
        cache_pen.setWidth(3)
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
                p.drawRect(loc[0] - radius, loc[1] - radius, radius * 2, radius * 2)

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


        # draw additional waypoints
        # --> print description!
        if self.current_cache != None and self.current_cache.get_waypoints() != None:
            p.setPen(self.PEN_WAYPOINTS)
            radius = 5
            num = 0
            lines = []
            for w in self.current_cache.get_waypoints():
                if w['lat'] != -1 and w['lon'] != -1:
                    num = num + 1
                    loc = self.map.coord2point(geo.Coordinate(w['lat'], w['lon']))
                    if not self.map.point_in_screen(loc):
                        continue
                    lines.append(QLine(loc[0], loc[1] - radius, loc[0], loc[1] + radius))
                    lines.append(QLine(loc[0] - radius, loc[1], loc[0] + radius, loc[1]))
                    p.drawArc(QRectF(loc[0] - radius - 1, loc[1] - radius - 1, radius * 2 + 1, radius * 2 + 1), 0, 16 * 360)
                    p.drawText(loc[0] + 3 + radius, loc[1] - 3 - radius, w['id'])
            p.drawLines(lines)
        p.end()
        
logger = logging.getLogger('markslayer')

class QtMarksLayer(AbstractQtLayer, AbstractMarksLayer):

    SIZE_CURRENT_POSITION = 5
    BRUSH_CURRENT_POSITION = QBrush(QColor(0, 255, 0))
    BRUSH_CURRENT_POSITION_NO_FIX = QBrush(QColor(255, 0, 0))

    PEN_TARGET = QPen(QColor(0, 0, 200), 1)
    PEN_SHADOW_TARGET = QPen(QColor(255, 255, 255), 3)

    PEN_LINE_DIRECT_LINE = QPen(QColor(255, 255, 0, 0.5), 5)
    PEN_ACCURACY = QPen(QColor(255, 125, 0), 2)

    PEN_POSITION = QPen(QColor(0, 0, 0), 2)
    PEN_POSITION_SHADOW = QPen(QColor(255, 255, 255), 4)

    DISTANCE_DRAW_FONT = QFont('Sans', 12)
    DISTANCE_DRAW_PEN = QPen(QColor(0, 0, 0))

    OSD_BORDER_TOPBOTTOM = 25
    OSD_BORDER_LEFTRIGHT = 35

    RADIUS_ARROW = 30
    RADIUS_STANDING = 5


    ARROW_OFFSET = 1.0 / 3.0 # Offset to center of arrow, calculated as 2-x = sqrt(1^2+(x+1)^2)
    ARROW_SHAPE = [(0, -2 + ARROW_OFFSET), (1, + 1 + ARROW_OFFSET), (0, 0 + ARROW_OFFSET), (-1, 1 + ARROW_OFFSET), (0, -2 + ARROW_OFFSET)]




    def __init__(self):
        AbstractQtLayer.__init__(self)
        AbstractMarksLayer.__init__(self)
        self.PEN_ACCURACY.setDashPattern([5, 3])


    def draw(self):
        self.result.fill(Qt.transparent)
        p = self.painter
        p.begin(self.result)
        p.setRenderHint(QPainter.Antialiasing)
        # if we have a target, draw it
        if self.current_target != None:
            t = self.map.coord2point(self.current_target)
            if t != False and self.map.point_in_screen(t):


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

        else:
            t = False

        if self.gps_last_good_fix != None and self.gps_last_good_fix.position != None:
            loc = self.map.coord2point_float(self.gps_last_good_fix.position)
        else:
            loc = None

        # a line between target and position if we have both
        if loc != None and t != False:
            p.setPen(self.PEN_LINE_DIRECT_LINE)
            if self.map.point_in_screen(t) and self.map.point_in_screen(loc):
                p.drawLine(loc[0], loc[1], t[0], t[1])
            elif self.map.point_in_screen(loc):
                direction = math.radians(self.gps_target_bearing - 180)
                # correct max length: sqrt(width**2 + height**2)
                length = self.map.map_width
                p.drawLine(loc[0], loc[1], loc[0] - math.sin(direction) * length, loc[1] + math.cos(direction) * length)

            elif self.map.point_in_screen(t):
                direction = math.radians(self.gps_target_bearing)
                length = self.map.map_width + self.map.map_height
                p.drawLine(t[0], t[1], t[0] - math.sin(direction) * length, t[1] + math.cos(direction) * length)

        if loc != None and self.map.point_in_screen(loc):
            

            if self.gps_has_fix:
                radius = self.gps_data.error
                radius_pixels = radius / self.map.get_meters_per_pixel(self.gps_last_good_fix.position.lat)
            else:
                radius_pixels = 10


            if self.gps_has_fix:
                p.setPen(self.PEN_ACCURACY)
                p.setBrush(QBrush(Qt.transparent))
                p.drawArc(loc[0] - radius_pixels/2.0 - 1, loc[1] - radius_pixels/2.0 - 1, radius_pixels, radius_pixels, 0, 16 * 360)

                # draw moving direction, if we're moving
                if self.gps_data.speed > 2.5: # km/h
                    arrow = self._get_arrow_transformed(loc[0] - self.RADIUS_ARROW/2, loc[1] - self.RADIUS_ARROW/2, self.RADIUS_ARROW, self.RADIUS_ARROW, self.gps_data.bearing)
                    p.setPen(self.PEN_POSITION_SHADOW)
                    p.drawPolyline(*arrow)
                    p.setPen(self.PEN_POSITION)
                    p.drawPolyline(*arrow)
                else:
                    p.drawArc(loc[0] - self.RADIUS_STANDING/2.0 , loc[1] - self.RADIUS_STANDING/2.0 - 1, self.RADIUS_STANDING + 1, self.RADIUS_STANDING + 1, 0, 16 * 360)
            
            if self.gps_has_fix:
                p.setBrush(self.BRUSH_CURRENT_POSITION)
            else:
                p.setBrush(self.BRUSH_CURRENT_POSITION_NO_FIX)
            p.setPen(QPen(Qt.transparent))
            p.drawPie(loc[0] - self.SIZE_CURRENT_POSITION/2.0 , loc[1] - self.SIZE_CURRENT_POSITION/2.0 , self.SIZE_CURRENT_POSITION + 1, self.SIZE_CURRENT_POSITION + 1, 0, 16 * 360)
            

        if self.gps_data != None and self.gps_has_fix:
            p.setFont(self.DISTANCE_DRAW_FONT)
            p.setPen(self.DISTANCE_DRAW_PEN)
            position = QRect(self.map.map_width - self.OSD_BORDER_LEFTRIGHT - 100, self.OSD_BORDER_TOPBOTTOM, 100, 40)
            text = self._format_distance(self.gps_target_distance)
            p.drawText(position, Qt.AlignRight | Qt.TextDontClip, text)
            

        p.end()


    @staticmethod
    def _format_distance(distance):
        if distance == None:
            return '?'
        if distance >= 1000:
            return "%d km" % round(distance / 1000.0)
        elif distance >= 100:
            return "%d m" % round(distance)
        else:
            return "%.1f m" % round(distance, 1)

    @staticmethod
    def _get_arrow_transformed(root_x, root_y, width, height, angle):
        multiply = height / (2 * (2-QtMarksLayer.ARROW_OFFSET))
        offset_x = width / 2
        offset_y = height / 2
        s = multiply * math.sin(math.radians(angle))
        c = multiply * math.cos(math.radians(angle))
        arrow_transformed = [QPointF(x * c + offset_x - y * s + root_x,
                              y * c + offset_y + x * s + root_y) for x, y in QtMarksLayer.ARROW_SHAPE]
        return arrow_transformed