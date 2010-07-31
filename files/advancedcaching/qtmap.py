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

from abstractmap import AbstractMap, AbstractMapLayer
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import logging
logger = logging.getLogger('qtmap')



class Map(QWidget, AbstractMap):

    def __init__(self, parent, center, zoom, tile_loader = None):
        QWidget.__init__(self)
        AbstractMap.__init__(self, center, zoom, tile_loader)
        self.buffer = QPixmap(self.size())
        self.painter = QPainter()
        
        self.surface_buffer = {}
        self.tile_loader_threadpool = threadpool.ThreadPool(1)
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
        if self.dragging:
            return
        self.dragging = True
        self.drag_start = ev.pos()
        #p = QPainter()
        #p.begin(self.buffer)
        #p.drawPoint(ev.pos())
        #p.end()
        #self.currentPos=QPoint(ev.pos())
        #self._draw_map()
        #a = self.tile_loader(id_string='id_string', tile=(2118,1392), zoom=12, undersample=False, x=0, y=0, callback_draw=self.cb_draw, callback_load = self.cb_load)
        #a.run()

        #self.repaint()

    def mouseMoveEvent(self, ev):
        if not self.dragging:
            return
        #self.drag_offset_x = self.drag_start.x() - ev.x()
        #self.drag_offset_y = self.drag_start.y() - ev.y()
        #self.repaint()
        self.drag_end = ev.pos()
        offset_x = self.drag_start.x() - self.drag_end.x()
        offset_y = self.drag_start.y() - self.drag_end.y()
        self._move_map_relative(offset_x, offset_y)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self._draw_map()
        self.drag_start = ev.pos()


    def mouseReleaseEvent(self, ev):
        if not self.dragging:
            return
        self.dragging = False
        self.repaint()
        return
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
                print "pbuf was none!"
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


class SingleMarkLayer(AbstractMapLayer):
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
        print self.coord, t
        if not self.map.point_in_screen(t):
            return
        p = self.painter
        p.begin(self.result)
        p.setRenderHint(QPainter.Antialiasing)


        radius_o = 15
        radius_i = 3
        radius_c = 10
        p.setPen(SingleMarkLayer.PEN_SHADOW_TARGET)
        p.drawLines(
            QLineF(t[0] - radius_o, t[1], t[0] - radius_i, t[1]),
            QLineF(t[0] + radius_o, t[1], t[0] + radius_i, t[1]),
            QLineF(t[0], t[1] + radius_o, t[0], t[1] + radius_i),
            QLineF(t[0], t[1] - radius_o, t[0], t[1] - radius_i)
            )
        p.drawArc(QRectF(t[0] - radius_c/2, t[1] - radius_c/2, radius_c, radius_c), 0, 16*360)

        p.setPen(SingleMarkLayer.PEN_TARGET)
        p.drawLines(
            QLineF(t[0] - radius_o, t[1], t[0] - radius_i, t[1]),
            QLineF(t[0] + radius_o, t[1], t[0] + radius_i, t[1]),
            QLineF(t[0], t[1] + radius_o, t[0], t[1] + radius_i),
            QLineF(t[0], t[1] - radius_o, t[0], t[1] - radius_i)
            )
        p.drawArc(QRectF(t[0] - radius_c/2, t[1] - radius_c/2, radius_c, radius_c), 0, 16*360)
        p.end()

class OsdLayer(AbstractMapLayer):

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
        OsdLayer.MESSAGE_DRAW_FONT = message_draw_font
        OsdLayer.MESSAGE_DRAW_COLOR = message_draw_color

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
        p.setFont(OsdLayer.MESSAGE_DRAW_FONT)
        p.setPen(OsdLayer.MESSAGE_DRAW_PEN)

        # osd message
        if self.map.osd_message != None:
            p.drawText(QPoint(20, 20), self.map.osd_message)

        # scale bar text
        p.drawText(QPoint(position[0], position[1]), scale_msg)

        # scale bar
        p.setPen(OsdLayer.OSD_PEN)
        p.setBrush(OsdLayer.OSD_BRUSH)
        p.drawRect(position[0], position[1] + 10, final_length_pixels, 3)
        p.end()
