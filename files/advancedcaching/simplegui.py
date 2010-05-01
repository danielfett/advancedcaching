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

 
# deps: python-html python-image python-netclient python-misc python-pygtk python-mime python-json

# todo:
# show logs
# parse attributes
# add "next waypoint" button
# add description to displayed images
# add translation support?


 
### For the gui :-)
import math

import geo
import geocaching
import gobject
import gtk
try:
    import gtk.glade
    import extListview
except (ImportError):
    print "Please install glade if you're NOT on the maemo platform."
import pango
import openstreetmap
import os
import re
from cachedownloader import HTMLAware

class SimpleGui(object, HTMLAware):
    USES = ['gpsprovider']
    XMLFILE = "freerunner.glade"

    MAP_FACTOR = 0
    CACHE_SIZE = 20
    CLICK_RADIUS = 20
    TOO_MUCH_POINTS = 30
    CACHES_ZOOM_LOWER_BOUND = 9
    CACHE_DRAW_SIZE = 10
    CACHE_DRAW_FONT = pango.FontDescription("Sans 4")
    MESSAGE_DRAW_FONT = pango.FontDescription("Sans 5")
    MESSAGE_DRAW_COLOR = gtk.gdk.color_parse('black')

    MIN_DRAG_REDRAW_DISTANCE = 5
    DRAG_RECHECK_SPEED = 50


    REDRAW_DISTANCE_TRACKING = 50 # distance from center of visible map in px
    REDRAW_DISTANCE_MINOR = 4 # distance from last displayed point in px
    DISTANCE_DISABLE_ARROW = 5 # meters

    MAX_NUM_RESULTS = 50
    MAX_NUM_RESULTS_SHOW = 100


    ARROW_OFFSET = 1.0 / 3.0 # Offset to center of arrow, calculated as 2-x = sqrt(1^2+(x+1)^2)
    ARROW_SHAPE = [(0, -2 + ARROW_OFFSET), (1, + 1 + ARROW_OFFSET), (0, 0 + ARROW_OFFSET), (-1, 1 + ARROW_OFFSET)]

    # map markers colors
    COLOR_MARKED = gtk.gdk.color_parse('yellow')
    COLOR_DEFAULT = gtk.gdk.color_parse('blue')
    COLOR_FOUND = gtk.gdk.color_parse('grey')
    COLOR_REGULAR = gtk.gdk.color_parse('green')
    COLOR_MULTI = gtk.gdk.color_parse('orange')
    COLOR_CACHE_CENTER = gtk.gdk.color_parse('black')
    COLOR_CURRENT_CACHE = gtk.gdk.color_parse('red')
    COLOR_WAYPOINTS = gtk.gdk.color_parse('deeppink')
    COLOR_CURRENT_POSITION = gtk.gdk.color_parse('red')
    COLOR_CURRENT_POSITION_NO_FIX = gtk.gdk.color_parse('darkgray')
    COLOR_TARGET = gtk.gdk.color_parse('black')
    COLOR_CROSSHAIR = gtk.gdk.color_parse("black")
    COLOR_LINE_INVERT = gtk.gdk.color_parse("blue")
    SIZE_CURRENT_POSITION = 3

    # arrow colors and sizes
    COLOR_ARROW_DEFAULT = gtk.gdk.color_parse("green")
    COLOR_ARROW_NEAR = gtk.gdk.color_parse("orange")
    COLOR_ARROW_ATTARGET = gtk.gdk.color_parse("red")
    COLOR_ARROW_DISABLED = gtk.gdk.color_parse("red")
    COLOR_ARROW_CIRCLE = gtk.gdk.color_parse("darkgray")
    COLOR_ARROW_OUTER_LINE = gtk.gdk.color_parse("black")
    COLOR_ARROW_CROSS = gtk.gdk.color_parse('darkslategray')
    COLOR_ARROW_ERROR = gtk.gdk.color_parse('gold')
    COLOR_NORTH_INDICATOR = gtk.gdk.color_parse("gold")
    ARROW_LINE_WIDTH = 3
    NORTH_INDICATOR_SIZE = 30
    FONT_NORTH_INDICATOR = pango.FontDescription("Sans 9")


    # quality indicator
    COLOR_QUALITY_OUTER = gtk.gdk.color_parse("black")
    COLOR_QUALITY_INNER = gtk.gdk.color_parse("green")
        
    SETTINGS_CHECKBOXES = [
        'download_visible',
        'download_notfound',
        'download_new',
        'download_nothing',
        'download_resize',
        'options_show_name',
        'download_noimages',
        'options_hide_found',
    ]
    SETTINGS_INPUTS = [
        'download_output_dir',
        'download_resize_pixel',
        'options_username',
        'options_password',
        'download_map_path'
    ]

                
    def __init__(self, core, pointprovider, userpointprovider, dataroot):
    
        gtk.gdk.threads_init()
        self.ts = openstreetmap.TileServer()
        self.noimage_cantload = gtk.gdk.pixbuf_new_from_file(os.path.join(dataroot, 'noimage-cantload.png'))
        self.noimage_loading = gtk.gdk.pixbuf_new_from_file(os.path.join(dataroot, 'noimage-loading.png'))
        
        self.core = core
        self.core.connect('map-changed', self._on_map_changed)
        self.core.connect('cache-changed', self._on_cache_changed)
        self.pointprovider = pointprovider
        self.userpointprovider = userpointprovider
        
                
        self.format = geo.Coordinate.FORMAT_DM

        # @type self.current_cache geocaching.GeocacheCoordinate
        self.current_cache = None
                
        self.current_target = None
        self.gps_data = None
        self.gps_has_fix = False
        self.gps_last_position = (0, 0)
                
        self.dragging = False
        self.block_changes = False
                
        self.image_zoomed = False
        self.image_no = 0
        self.images = []
        self.active_tile_loaders = []

        
        self.north_indicator_layout = None
        self.drawing_area_configured = self.drawing_area_arrow_configured = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.notes_changed = False
        self.fieldnotes_changed = False
        self.map_center_x, self.map_center_y = 100, 100
        
        
        global xml
        xml = gtk.glade.XML(os.path.join(dataroot, self.XMLFILE))
        self.load_ui()
        # self.build_tile_loaders()

    def _on_cache_changed(self, something, cache):
        
        if self.current_cache != None \
            and cache.name == self.current_cache.name:
            self.show_cache(cache)
        return False


    def _on_map_changed(self, something):
        self.redraw_marks()
        return False

    def build_tile_loaders(self):
        self.tile_loaders = []
        for name, params in self.core.settings['map_providers']:
            self.tile_loaders.append((name, openstreetmap.get_tile_loader(**params)))
        self.tile_loader = self.tile_loaders[0][1]
        
    def load_ui(self):
        self.window = xml.get_widget("window1")
        xml.signal_autoconnect(self)
        
        # map drawing area
        self.drawing_area = xml.get_widget("drawingarea")
        self.drawing_area_arrow = xml.get_widget("drawingarea_arrow")
        self.filtermsg = xml.get_widget('label_filtermsg')
        self.scrolledwindow_image = xml.get_widget('scrolledwindow_image')
        self.image_cache = xml.get_widget('image_cache')
        self.image_cache_caption = xml.get_widget('label_cache_image_caption')
        self.notebook_cache = xml.get_widget('notebook_cache')
        self.notebook_all = xml.get_widget('notebook_all')
        self.notebook_search = xml.get_widget('notebook_search')
        self.progressbar = xml.get_widget('progress_download')
        self.button_download_details = xml.get_widget('button_download_details')
        self.button_track = xml.get_widget('togglebutton_track')
        self.check_result_marked = xml.get_widget('check_result_marked')
        self.label_fieldnotes = xml.get_widget('label_fieldnotes')
                
        self.label_bearing = xml.get_widget('label_bearing')
        self.label_dist = xml.get_widget('label_dist')
        self.label_altitude = xml.get_widget('label_altitude')
        self.label_latlon = xml.get_widget('label_latlon')
        self.label_target = xml.get_widget('label_target')
        self.label_quality = xml.get_widget('label_quality')
        
        self.input_export_path = xml.get_widget('input_export_path')
                
        self.drawing_area.set_double_buffered(False)
        self.drawing_area.connect("expose_event", self._expose_event)
        self.drawing_area.connect("configure_event", self._configure_event)
        self.drawing_area.connect("button_press_event", self._drag_start)
        self.drawing_area.connect("scroll_event", self._scroll)
        self.drawing_area.connect("button_release_event", self._drag_end)
        self.drawing_area.connect("motion_notify_event", self._drag)
        self.drawing_area.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.SCROLL | gtk.gdk.BUTTON_MOTION_MASK)
                
        # arrow drawing area
        self.drawing_area_arrow.connect("expose_event", self._expose_event_arrow)
        self.drawing_area_arrow.connect("configure_event", self._configure_event_arrow)
        self.drawing_area_arrow.set_events(gtk.gdk.EXPOSURE_MASK)
                
                
        self.cache_elements = {
            'name_downloaded': xml.get_widget('link_cache_name'),
            'name_not_downloaded': xml.get_widget('button_cache_name'),
            'title': xml.get_widget('label_cache_title'),
            'type': xml.get_widget('label_cache_type'),
            'size': xml.get_widget('label_cache_size'),
            'terrain': xml.get_widget('label_cache_terrain'),
            'difficulty': xml.get_widget('label_cache_difficulty'),
            'desc': xml.get_widget('textview_cache_desc').get_buffer(),
            'notes': xml.get_widget('textview_cache_notes').get_buffer(),
            'fieldnotes': xml.get_widget('textview_cache_fieldnotes').get_buffer(),
            'hints': xml.get_widget('label_cache_hints').get_buffer(),
            'coords': xml.get_widget('label_cache_coords'),
            'log_found': xml.get_widget('radiobutton_cache_log_found'),
            'log_notfound': xml.get_widget('radiobutton_cache_log_notfound'),
            'log_note': xml.get_widget('radiobutton_cache_log_note'),
            'log_no': xml.get_widget('radiobutton_cache_log_no'),
            'log_date': xml.get_widget('label_cache_log_date'),
            'marked': xml.get_widget('check_cache_marked'),
        }
                
        self.search_elements = {
            'type': {
                geocaching.GeocacheCoordinate.TYPE_REGULAR: xml.get_widget('check_search_type_traditional'),
                geocaching.GeocacheCoordinate.TYPE_MULTI: xml.get_widget('check_search_type_multi'),
                geocaching.GeocacheCoordinate.TYPE_MYSTERY: xml.get_widget('check_search_type_unknown'),
                geocaching.GeocacheCoordinate.TYPE_VIRTUAL: xml.get_widget('check_search_type_virtual'),
                'all': xml.get_widget('check_search_type_other')
                },
            'name': xml.get_widget('entry_search_name'),
            'status': xml.get_widget('combo_search_status'),
            'size': {
                1: xml.get_widget('check_search_size_1'),
                2: xml.get_widget('check_search_size_2'),
                3: xml.get_widget('check_search_size_3'),
                4: xml.get_widget('check_search_size_4'),
                5: xml.get_widget('check_search_size_5'),
            },
            'diff': {
                'selector': xml.get_widget('combo_search_diff_sel'),
                'value': xml.get_widget('combo_search_diff'),
            },
            'terr': {
                'selector': xml.get_widget('combo_search_terr_sel'),
                'value': xml.get_widget('combo_search_terr'),
            },
            'inview': xml.get_widget('check_search_inview'),

        }
                
        #
        # setting up TABLES
        #
                
        # Create the renderer used in the listview
        txtRdr        = gtk.CellRendererText()
        (
         ROW_TITLE,
         ROW_TYPE,
         ROW_SIZE,
         ROW_TERRAIN,
         ROW_DIFF,
         ROW_ID,
         ) = range(6)
        columns = (
                   ('name', [(txtRdr, gobject.TYPE_STRING)], (ROW_TITLE,), False, True),
                   ('type', [(txtRdr, gobject.TYPE_STRING)], (ROW_TYPE,), False, True),
                   ('size', [(txtRdr, gobject.TYPE_STRING)], (ROW_SIZE, ROW_ID), False, True),
                   ('ter', [(txtRdr, gobject.TYPE_STRING)], (ROW_TERRAIN, ROW_ID), False, True),
                   ('dif', [(txtRdr, gobject.TYPE_STRING)], (ROW_DIFF, ROW_ID), False, True),
                   ('ID', [(txtRdr, gobject.TYPE_STRING)], (ROW_ID,), False, True),
                   )
        self.cachelist = listview = extListview.ExtListView(columns, sortable=True, useMarkup=True, canShowHideColumns=False)
        self.cachelist_contents = []
        listview.connect('extlistview-button-pressed', self.on_search_cache_clicked)
        xml.get_widget('scrolledwindow_search').add(listview)
                
        (
         COL_COORD_NAME,
         COL_COORD_LATLON,
         COL_COORD_ID,
         COL_COORD_COMMENT,
         ) = range(4)
        columns = (
                   ('name', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_NAME), False, True),
                   ('pos', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_LATLON), False, True),
                   ('id', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_ID), False, True),
                   ('comment', [(txtRdr, gobject.TYPE_STRING)], (COL_COORD_COMMENT,), False, True),
                   )
        self.coordlist = extListview.ExtListView(columns, sortable=True, useMarkup=False, canShowHideColumns=False)
        self.coordlist.connect('extlistview-button-pressed', self.on_waypoint_clicked)
        xml.get_widget('scrolledwindow_coordlist').add(self.coordlist)

        self.notebook_all.set_current_page(1)
        gobject.timeout_add_seconds(10, self._check_notes_save)


    def on_marked_label_clicked(self, event=None, widget=None):
        w = xml.get_widget('check_cache_marked')
        w.set_active(not w.get_active())

    def dmap(self, widget):
        pass

    def dunmap(self, widget):
        pass

    def _check_notes_save(self):
        if self.current_cache != None and self.notes_changed:
            self.core.on_notes_changed(self.current_cache, self.cache_elements['notes'].get_text(self.cache_elements['notes'].get_start_iter(), self.cache_elements['notes'].get_end_iter()))
            self.notes_changed = False

        if self.current_cache != None and self.fieldnotes_changed:
            self.core.on_fieldnotes_changed(self.current_cache, self.cache_elements['fieldnotes'].get_text(self.cache_elements['fieldnotes'].get_start_iter(), self.cache_elements['fieldnotes'].get_end_iter()))
            self.fieldnotes_changed = False
                
    def _configure_event(self, widget, event):
        x, y, width, height = widget.get_allocation()
        self.map_width = int(width  + 2 * width * self.MAP_FACTOR)
        self.map_height = int(height + 2 * height * self.MAP_FACTOR)
        self.pixmap = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)
                        
        self.pixmap_marks = gtk.gdk.Pixmap(widget.window, self.map_width, self.map_height)
        self.xgc = widget.window.new_gc()
        self.drawing_area_configured = True
        self.draw_at_x = 0
        self.draw_at_y = 0
        self.draw_root_x = int(-width * self.MAP_FACTOR)
        self.draw_root_y = int(-height * self.MAP_FACTOR)

        gobject.idle_add(self._draw_map)
                
                
    def _configure_event_arrow(self, widget, event):
        x, y, width, height = widget.get_allocation()
        self.pixmap_arrow = gtk.gdk.Pixmap(widget.window, width, height)
        self.xgc_arrow = widget.window.new_gc()

        if self.north_indicator_layout == None:
            # prepare font
            self.north_indicator_layout = widget.create_pango_layout("N")
            self.north_indicator_layout.set_alignment(pango.ALIGN_CENTER)
            self.north_indicator_layout.set_font_description(self.FONT_NORTH_INDICATOR)

            '''
            self.pixmap_north_indicator = gtk.gdk.Pixmap(widget.window, self.NORTH_INDICATOR_SIZE, self.NORTH_INDICATOR_SIZE)
            self.xgc_arrow.set_rgb_fg_color(gtk.gdk.color_parse("white"))
            self.pixmap_north_indicator.draw_rectangle(self.xgc_arrow, True, 0, 0, self.NORTH_INDICATOR_SIZE, self.NORTH_INDICATOR_SIZE)
            x, y = north_indicator_layout.get_size()
            self.xgc_arrow.set_rgb_fg_color(gtk.gdk.color_parse("black"))
            self.pixmap_north_indicator.draw_layout(self.xgc_arrow, (self.NORTH_INDICATOR_SIZE - x / pango.SCALE) / 2, (self.NORTH_INDICATOR_SIZE - y / pango.SCALE) / 2, north_indicator_layout)
            '''

        self.drawing_area_arrow_configured = True
        gobject.idle_add(self._draw_arrow)
                
    def _coord2point(self, coord):
        point = self.ts.deg2num(coord)
        size = self.ts.tile_size()
                
        p_x = int(point[0] * size - self.map_center_x * size + self.map_width / 2)
        p_y = int(point[1] * size - self.map_center_y * size + self.map_height / 2)
        return [p_x, p_y]
        
    def on_window_destroy(self, target, more=None, data=None):
        self.core.on_destroy()
        gtk.main_quit()

    def do_events(self):
        while gtk.events_pending():
            gtk.main_iteration()
                
                
    # called by core
    def display_results_advanced(self, caches):
        label = xml.get_widget('label_too_much_results')
        too_much = len(caches) > self.MAX_NUM_RESULTS
        if too_much:
            text = 'Too much results. Only showing first %d.' % self.MAX_NUM_RESULTS
            label.set_text(text)
            label.show()
            caches = caches[:self.MAX_NUM_RESULTS]
        else:
            label.hide()
        self.cachelist_contents = caches
        rows = []
        for r in caches:
            if r.size == -1:
                s = "?"
            else:
                s = "%d" % r.size
                                
            if r.difficulty == -1:
                d = "?"
            else:
                d = "%.1f" % (r.difficulty / 10)
                                
            if r.terrain == -1:
                t = "?"
            else:
                t = "%.1f" % (r.terrain / 10)
            title = self._format_cache_title(r)
            rows.append((title, r.type, s, t, d, r.name, ))
        self.cachelist.replaceContent(rows)
        self.notebook_search.set_current_page(1)
        self.redraw_marks()


    @staticmethod
    def _format_cache_title(cache):
        m = cache.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if cache.marked and cache.found:
            return '<span bgcolor="yellow" fgcolor="gray">%s</span>' % m
        elif cache.marked:
            return '<span bgcolor="yellow" fgcolor="black">%s</span>' % m
        elif cache.found:
            return '<span fgcolor="gray">%s</span>' % m
        else:
            return m

    def _draw_arrow(self):

        outer_circle_size = 3
        circle_border = 10
        indicator_border = 40
        distance_attarget = 50
        distance_near = 150
        disabled_border_size = 30
        signal_width = 15
        error_circle_size = 0.95
        error_circle_width = 7
        
        if not self.drawing_area_arrow_configured:
            return
        widget = self.drawing_area_arrow
        x, y, width, height = widget.get_allocation()
                        
        disabled = not (self.gps_has_fix and self.current_target != None and self.gps_data != None and self.gps_data.position != None)
                        
        self.pixmap_arrow.draw_rectangle(widget.get_style().bg_gc[gtk.STATE_NORMAL],
                                         True, 0, 0, width, height)
                                         
        if disabled:
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_DISABLED)
            border = disabled_border_size
            self.pixmap_arrow.draw_line(self.xgc_arrow, border, border, width - border, height - border)
            self.pixmap_arrow.draw_line(self.xgc_arrow, border, height - border, width - border, border)
            self.drawing_area_arrow.queue_draw()
                
            return False
        
        # draw signal indicator
        if self.COLOR_QUALITY_OUTER != None:
            self.xgc_arrow.line_width = 1
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_QUALITY_OUTER)
            self.pixmap_arrow.draw_rectangle(self.xgc_arrow, True, width - signal_width - 2, 0, signal_width + 2, height)
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_QUALITY_INNER)
            usable_height = height - 1
            target_height = int(round(usable_height * self.gps_data.quality))
            self.pixmap_arrow.draw_rectangle(self.xgc_arrow, True, width - signal_width - 1, usable_height - target_height, signal_width, target_height)

        display_bearing = self.gps_data.position.bearing_to(self.current_target) - self.gps_data.bearing
        display_distance = self.gps_data.position.distance_to(self.current_target)
        display_north = math.radians(self.gps_data.bearing)

        # draw moving direction
        if self.COLOR_ARROW_CROSS != None:
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_CROSS)
            self.pixmap_arrow.draw_line(self.xgc_arrow, width / 2, height, width / 2, 0)
            self.pixmap_arrow.draw_line(self.xgc_arrow, 0, height / 2, width, height / 2)


        self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_CIRCLE)
        self.xgc_arrow.line_width = outer_circle_size
        circle_size = min(height, width) / 2 - circle_border
        indicator_dist = min(height, width) / 2 - indicator_border
        center_x, center_y = width / 2, height / 2

        # outer circle
        self.pixmap_arrow.draw_arc(self.xgc_arrow, False, center_x - circle_size, center_y - circle_size, circle_size * 2, circle_size * 2, 0, 64 * 360)
        #position_x - indicator_radius / 2, position_y - indicator_radius / 2,

        if display_distance > self.DISTANCE_DISABLE_ARROW:
            self.xgc_arrow.line_width = error_circle_width
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_ERROR)
            self.xgc_arrow.set_dashes(1, (5, 5))

            self.xgc_arrow.line_style = gtk.gdk.LINE_ON_OFF_DASH 
            ecc = int(error_circle_size * circle_size)
            err = min(self.gps_data.error_bearing, 181) # don't draw multiple circles :-)
            err_start = (90-(display_bearing + err))*64
            err_delta = err * 2 * 64
            self.pixmap_arrow.draw_arc(self.xgc_arrow, False, center_x - ecc, center_y - ecc, ecc * 2, ecc * 2, err_start, err_delta)
            self.xgc_arrow.line_style = gtk.gdk.LINE_SOLID




        if (display_distance < distance_attarget):
            color = self.COLOR_ARROW_ATTARGET
        elif (display_distance < distance_near):
            color = self.COLOR_ARROW_NEAR
        else:
            color = self.COLOR_ARROW_DEFAULT
        
                
        self.xgc_arrow.set_rgb_fg_color(color)

        if display_distance > self.DISTANCE_DISABLE_ARROW:
            arrow_transformed = self._get_arrow_transformed(x, y, width, height, display_bearing)
            #self.xgc_arrow.line_style = gtk.gdk.LINE_SOLID
            self.pixmap_arrow.draw_polygon(self.xgc_arrow, True, arrow_transformed)
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_OUTER_LINE)
            self.xgc_arrow.line_width = self.ARROW_LINE_WIDTH
            self.pixmap_arrow.draw_polygon(self.xgc_arrow, False, arrow_transformed)

            # north indicator
            ni_w, ni_h = self.north_indicator_layout.get_size()
            position_x = int(width / 2 - math.sin(display_north) * indicator_dist - (ni_w / pango.SCALE) / 2)
            position_y = int(height / 2 - math.cos(display_north) * indicator_dist - (ni_h / pango.SCALE) / 2)
            self.xgc_arrow.set_function(gtk.gdk.COPY)
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_NORTH_INDICATOR)
            self.pixmap_arrow.draw_layout(self.xgc_arrow, position_x, position_y, self.north_indicator_layout)

        else:
            # if we are closer than a few meters, the arrow will almost certainly
            # point in the wrong direction. therefore, we don't draw the arrow.
            circle_size = int(max(height / 2.5, width / 2.5))
            self.pixmap_arrow.draw_arc(self.xgc_arrow, True, width / 2 - circle_size / 2, height / 2 - circle_size / 2, circle_size, circle_size, 0, 64 * 360)
            self.xgc_arrow.set_rgb_fg_color(self.COLOR_ARROW_OUTER_LINE)
            self.xgc_arrow.line_width = self.ARROW_LINE_WIDTH
            self.pixmap_arrow.draw_arc(self.xgc_arrow, False, width / 2 - circle_size / 2, height / 2 - circle_size / 2, circle_size, circle_size, 0, 64 * 360)

        
        self.drawing_area_arrow.queue_draw()
        return False

    def _get_arrow_transformed(self, x, y, width, height, angle):
        multiply = height / (2 * (2-self.ARROW_OFFSET))
        offset_x = width / 2
        offset_y = height / 2
        s = math.sin(math.radians(angle))
        c = math.cos(math.radians(angle))
        arrow_transformed = []
        for (x, y) in self.ARROW_SHAPE:
            arrow_transformed.append((int(x * multiply * c + offset_x - y * multiply * s),
                                     int(y * multiply * c + offset_y + x * multiply * s)))
        return arrow_transformed
                
                
    def _drag(self, widget, event):
        if not self.dragging:
            return True
        self.drag_offset_x = self.drag_start_x - event.x
        self.drag_offset_y = self.drag_start_y - event.y
        return True
                
    def _drag_end(self, widget, event):
        if not self.dragging:
            return
        #print "drag end with: ", self.drag_offset_x, self.drag_offset_y
        self.dragging = False
        offset_x = self.drag_offset_x #(self.drag_start_x - event.x)
        offset_y = self.drag_offset_y #(self.drag_start_y - event.y)
        self.map_center_x += (offset_x / self.ts.tile_size())
        self.map_center_y += (offset_y / self.ts.tile_size())
        self.map_center_x, self.map_center_y = self.ts.check_bounds(self.map_center_x, self.map_center_y)
        if offset_x ** 2 + offset_y ** 2 < self.CLICK_RADIUS ** 2:
            self.draw_at_x -= offset_x
            self.draw_at_y -= offset_y
            x, y = event.x, event.y
            c = self.screenpoint2coord([x, y])
            c1 = self.screenpoint2coord([x-self.CLICK_RADIUS, y-self.CLICK_RADIUS])
            c2 = self.screenpoint2coord([x + self.CLICK_RADIUS, y + self.CLICK_RADIUS])
            if self.settings['options_hide_found']:
                found = False
            else:
                found = None
            cache = self.pointprovider.get_nearest_point_filter(c, c1, c2, found)
            self.core.on_cache_selected(cache)
        self.draw_at_x = self.draw_at_y = 0
        if offset_x != 0 or offset_y != 0:
            gobject.idle_add(self._draw_map)
                
                        
    def _drag_draw(self):
        if not self.dragging:
            return False

        delta = math.sqrt((self.last_drag_offset_x - self.drag_offset_x) ** 2 + (self.last_drag_offset_y - self.drag_offset_y) ** 2)
        if delta < self.MIN_DRAG_REDRAW_DISTANCE:
            return True

        self.last_drag_offset_x = self.drag_offset_x
        self.last_drag_offset_y = self.drag_offset_y

        x, y, width, height = self.drawing_area.get_allocation()
        #gc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
        self.drawing_area.window.draw_drawable(self.xgc,
                                               self.pixmap, -self.draw_at_x + self.drag_offset_x - self.draw_root_x, -self.draw_at_y + self.drag_offset_y - self.draw_root_y, 0, 0, width, height)
        return True
        
                
    def _drag_start(self, widget, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.last_drag_offset_x = 0
        self.last_drag_offset_y = 0
        self.dragging = True
        gobject.timeout_add(self.DRAG_RECHECK_SPEED, self._drag_draw)
                
                
    def _draw_map(self):
        if not self.drawing_area_configured:
            return False
                
        if self.map_width == 0 or self.map_height == 0:
            return
        self._draw_marks()

        for x in self.active_tile_loaders:
            x.halt()
                        
        size = self.ts.tile_size()
        xi = int(self.map_center_x)
        yi = int(self.map_center_y)
        span_x = int(math.ceil(float(self.map_width) / (size * 2.0)))
        span_y = int(math.ceil(float(self.map_height) / (size * 2.0)))
        tiles = []
        self.active_tile_loaders = []
        for i in xrange(0, span_x + 1, 1):
            for j in xrange(0, span_y + 1, 1):
                for dir in xrange(0, 4, 1):
                    dir_ns = dir_ew = 1
                    if dir % 2 == 1: # if dir == 1 or dir == 3
                        dir_ns = -1
                    if dir > 1:
                        dir_ew = -1
                                
                    tile = (xi + (i * dir_ew), yi + (j * dir_ns))
                    if not tile in tiles:
                        tiles.append(tile)
                        #print "Requesting ", tile, " zoom ", ts.zoom
                        d = self.tile_loader(tile, self.ts.zoom, self, self.settings['download_map_path'], noimage_cantload = self.noimage_cantload, noimage_loading = self.noimage_loading, undersample = self.settings['options_map_double_size'])
                        d.start()
                        self.active_tile_loaders.append(d)
        #print 'end draw map'

    def _draw_marks_caches(self, coords):
        xgc = self.xgc
        draw_short = (len(coords) > self.TOO_MUCH_POINTS)

        for c in coords: # for each geocache
            radius = self.CACHE_DRAW_SIZE
            if c.found:
                color = self.COLOR_FOUND
            elif c.type == geocaching.GeocacheCoordinate.TYPE_REGULAR:
                color = self.COLOR_REGULAR
            elif c.type == geocaching.GeocacheCoordinate.TYPE_MULTI:
                color = self.COLOR_MULTI
            else:
                color = self.COLOR_DEFAULT

            xgc.set_rgb_fg_color(color)

            p = self._coord2point(c)

            if c.alter_lat != None and (c.alter_lat != 0 and c.alter_lon != 0):
                print c.alter_lat
                x = self._coord2point(geo.Coordinate(c.alter_lat, c.alter_lon))
                if x != p:
                    self.pixmap_marks.draw_line(xgc, p[0], p[1], x[0], x[1])


            if draw_short:
                radius = radius / 2.0

            if c.marked:
                xgc.set_rgb_fg_color(self.COLOR_MARKED)
                self.pixmap_marks.draw_rectangle(xgc, True, p[0] - radius, p[1] - radius, radius * 2, radius * 2)


            xgc.set_rgb_fg_color(color)
            xgc.line_width = 3
            self.pixmap_marks.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)

            if draw_short:
                continue


            # print the name?
            if self.settings['options_show_name']:
                layout = self.drawing_area.create_pango_layout(self.shorten_name(c.title, 20))
                layout.set_font_description(self.CACHE_DRAW_FONT)
                self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)

            # if we have a description for this cache...
            if c.was_downloaded():
                # draw something like:
                # ----
                # ----
                # ----
                # besides the icon
                width = 6
                dist = 2
                pos_x = p[0] + radius + 3 + 1
                pos_y = p[1] + 2
                xgc.line_width = 1
                for i in xrange(0, 3):
                    self.pixmap_marks.draw_line(xgc, pos_x, pos_y + dist * i, pos_x + width, pos_y + dist * i)

            # if this cache is the active cache
            if self.current_cache != None and c.name == self.current_cache.name:
                xgc.line_width = 3
                xgc.set_rgb_fg_color(self.COLOR_CURRENT_CACHE)
                radius = 7
                self.pixmap_marks.draw_rectangle(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2)

            # if this cache is disabled
            if c.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
                xgc.line_width = 3
                xgc.set_rgb_fg_color(self.COLOR_CURRENT_CACHE)
                radius = 7
                self.pixmap_marks.draw_line(xgc, p[0]-radius, p[1]-radius, p[0] + radius, p[1] + radius)

            xgc.set_rgb_fg_color(self.COLOR_CACHE_CENTER)
            xgc.line_width = 1
            self.pixmap_marks.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
            self.pixmap_marks.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---

        # draw additional waypoints
        # --> print description!
        if self.current_cache != None and self.current_cache.get_waypoints() != None:
            xgc.set_function(gtk.gdk.AND)
            xgc.set_rgb_fg_color(self.COLOR_WAYPOINTS)
            xgc.line_width = 1
            radius = 4
            num = 0
            for w in self.current_cache.get_waypoints():
                if w['lat'] != -1 and w['lon'] != -1:
                    num = num + 1
                    p = self._coord2point(geo.Coordinate(w['lat'], w['lon']))
                    self.pixmap_marks.draw_line(xgc, p[0], p[1] - 3, p[0], p[1] + 4) #  |
                    self.pixmap_marks.draw_line(xgc, p[0] - 3, p[1], p[0] + 4, p[1]) # ---
                    self.pixmap_marks.draw_arc(xgc, False, p[0] - radius, p[1] - radius, radius * 2, radius * 2, 0, 360 * 64)
                    layout = self.drawing_area.create_pango_layout('')
                    layout.set_markup('<i>%s</i>' % (w['id']))
                    layout.set_font_description(self.CACHE_DRAW_FONT)
                    self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)

    def _draw_marks_message(self, message):
        xgc = self.xgc
        xgc.set_rgb_fg_color(self.MESSAGE_DRAW_COLOR)
        layout = self.drawing_area.create_pango_layout(message)
        layout.set_font_description(self.MESSAGE_DRAW_FONT)
        self.pixmap_marks.draw_layout(xgc, 20, 20, layout)

    def _draw_marks(self):
            
        xgc = self.xgc
        xgc.set_function(gtk.gdk.COPY)
        self.xgc.set_rgb_fg_color(gtk.gdk.color_parse('white'))
        self.pixmap_marks.draw_rectangle(self.xgc, True, 0, 0, self.map_width, self.map_height)
                
        #
        # draw geocaches
        #

        if self.ts.get_zoom() < self.CACHES_ZOOM_LOWER_BOUND:
            self._draw_marks_message('Zoom in to see geocaches.')
        else:

            if self.settings['options_hide_found']:
                found = False
            else:
                found = None
            coords = self.pointprovider.get_points_filter(self.get_visible_area(), found, self.MAX_NUM_RESULTS_SHOW)
            if len(coords) >= self.MAX_NUM_RESULTS_SHOW:
                self._draw_marks_message('Too many geocaches to display.')
            else:
                self._draw_marks_caches(coords)
            
                        
        #
        # next, draw the user defined points
        #
        """
                coords = self.userpointprovider.get_points_filter((self.pixmap_markspoint2coord([0,0]), self.pixmap_markspoint2coord([self.map_width, self.map_height])))

                xgc.set_function(gtk.gdk.AND)
                radius = 7
                color = gtk.gdk.color_parse('darkorchid')
                for c in coords: # for each geocache
                        p = self.coord2point(c)
                        xgc.line_width = 3                
                        xgc.set_rgb_fg_color(color)
                        radius = 8
                        self.pixmap_marks.draw_line(xgc, p[0] - radius, p[1], p[0], p[1] + radius)
                        self.pixmap_marks.draw_line(xgc, p[0], p[1] + radius, p[0] + radius, p[1])
                        self.pixmap_marks.draw_line(xgc, p[0] + radius, p[1], p[0], p[1] - radius)
                        self.pixmap_marks.draw_line(xgc, p[0], p[1] - radius, p[0] - radius, p[1])
                        xgc.line_width = 1
                        self.pixmap_marks.draw_line(xgc, p[0], p[1] - 2, p[0], p[1] + 3) #  |
                        self.pixmap_marks.draw_line(xgc, p[0] - 2, p[1], p[0] + 3, p[1]) # ---
                        layout = self.drawing_area.create_pango_layout(c.name)
                        layout.set_font_description(font)
                        self.pixmap_marks.draw_layout(xgc, p[0] + 3 + radius, p[1] - 3 - radius, layout)
                
                """
        #
        # and now for our current data!
        #
                
                
                
        # if we have a target, draw it
        if self.current_target != None:
            t = self._coord2point(self.current_target)
            if t != False and self.point_in_screen(t):
                        
        
                xgc.line_width = 2
                radius_o = 10
                radius_i = 3
                xgc.set_function(gtk.gdk.INVERT)
                xgc.set_rgb_fg_color(self.COLOR_TARGET)
                self.pixmap_marks.draw_line(xgc, t[0] - radius_o, t[1], t[0] - radius_i, t[1])
                self.pixmap_marks.draw_line(xgc, t[0] + radius_o, t[1], t[0] + radius_i, t[1])
                self.pixmap_marks.draw_line(xgc, t[0], t[1] + radius_o, t[0], t[1] + radius_i)
                self.pixmap_marks.draw_line(xgc, t[0], t[1] - radius_o, t[0], t[1] - radius_i)
        else:
            t = False
                
                
                
        if self.gps_has_fix and self.gps_data != None and self.gps_data.position != None:
            p = self._coord2point(self.gps_data.position)
            if p != False:
                self.gps_last_position = p

        p = self.gps_last_position
        if self.point_in_screen(p):

            xgc.line_width = 2

            if self.gps_has_fix:
                radius = self.gps_data.error

                # determine radius in meters
                (x, y) = self._coord2point(self.gps_data.position.transform(90.0, radius))

                (x2, y2) = self._coord2point(self.gps_data.position)
                radius_pixels = (x2 - x)
            else:
                radius_pixels = 10

            radius_o = int((radius_pixels + 8) / math.sqrt(2))
            radius_i = int((radius_pixels - 8) / math.sqrt(2))



            if radius_i < 2:
                radius_i = 2
            xgc.set_function(gtk.gdk.COPY)
            if self.gps_has_fix:
                xgc.set_rgb_fg_color(self.COLOR_CURRENT_POSITION)
            else:
                xgc.set_rgb_fg_color(self.COLOR_CURRENT_POSITION_NO_FIX)

            # \  /
            #
            # /  \

            self.pixmap_marks.draw_line(xgc, p[0] - radius_o, p[1] - radius_o, p[0] - radius_i, p[1] - radius_i)
            self.pixmap_marks.draw_line(xgc, p[0] + radius_o, p[1] + radius_o, p[0] + radius_i, p[1] + radius_i)
            self.pixmap_marks.draw_line(xgc, p[0] + radius_o, p[1] - radius_o, p[0] + radius_i, p[1] - radius_i)
            self.pixmap_marks.draw_line(xgc, p[0] - radius_o, p[1] + radius_o, p[0] - radius_i, p[1] + radius_i)

            self.pixmap_marks.draw_arc(xgc, True, p[0] - self.SIZE_CURRENT_POSITION, p[1] - self.SIZE_CURRENT_POSITION, 2 * self.SIZE_CURRENT_POSITION, 2 * self.SIZE_CURRENT_POSITION, 0, 360 * 64)
            if self.gps_has_fix:
                xgc.set_function(gtk.gdk.INVERT)
                xgc.line_width = 1
                xgc.set_rgb_fg_color(gtk.gdk.color_parse('blue'))

                self.pixmap_marks.draw_arc(xgc, False, p[0] - radius_pixels, p[1] - radius_pixels, radius_pixels * 2, radius_pixels * 2, 0, 360 * 64)



        # and a line between target and position if we have both
        if self.gps_has_fix and t != False:
            xgc.line_width = 5
            xgc.set_function(gtk.gdk.AND_INVERT)
            xgc.set_rgb_fg_color(self.COLOR_LINE_INVERT)
            if self.point_in_screen(t) and self.point_in_screen(p):
                self.pixmap_marks.draw_line(xgc, p[0], p[1], t[0], t[1])
            elif self.point_in_screen(p):
                direction = math.radians(self.current_target.bearing_to(self.gps_data.position))
                # correct max length: sqrt(width**2 + height**2)
                length = self.map_width
                self.pixmap_marks.draw_line(xgc, p[0], p[1], int(p[0] - math.sin(direction) * length), int(p[1] + math.cos(direction) * length))

            elif self.point_in_screen(t):
                direction = math.radians(self.gps_data.position.bearing_to(self.current_target))
                length = self.map_width + self.map_height
                self.pixmap_marks.draw_line(xgc, t[0], t[1], int(t[0] - math.sin(direction) * length), int(t[1] + math.cos(direction) * length))



        # draw cross across the screen
        xgc.line_width = 1
        xgc.set_function(gtk.gdk.XOR)
        xgc.set_rgb_fg_color(self.COLOR_CROSSHAIR)

        radius_inner = 30
        self.pixmap_marks.draw_line(xgc, self.map_width / 2, 0, self.map_width / 2, self.map_height / 2 - radius_inner)
        self.pixmap_marks.draw_line(xgc, self.map_width / 2, self.map_height / 2 + radius_inner, self.map_width / 2, self.map_height)
        self.pixmap_marks.draw_line(xgc, 0, self.map_height / 2, self.map_width / 2 - radius_inner, self.map_height / 2)
        self.pixmap_marks.draw_line(xgc, self.map_width / 2 + radius_inner, self.map_height / 2, self.map_width, self.map_height / 2)
                
        xgc.set_function(gtk.gdk.COPY)
        return False
        
    def _expose_event(self, widget, event):
        if self.dragging:
            return
        x, y, width, height = event.area

        widget.window.draw_drawable(self.xgc, self.pixmap, x, y, self.draw_root_x + self.draw_at_x  + x, self.draw_root_y + self.draw_at_y + y, width, height)
        self.xgc.set_function(gtk.gdk.AND)
        widget.window.draw_drawable(self.xgc, self.pixmap_marks, x, y, self.draw_root_x + self.draw_at_x  + x, self.draw_root_y + self.draw_at_y + y, width, height)
        self.xgc.set_function(gtk.gdk.COPY)
                
        return False
                
        
    def _expose_event_arrow(self, widget, event):
        x, y, width, height = event.area
        widget.window.draw_drawable(self.xgc_arrow, self.pixmap_arrow, x, y, x, y, width, height)
        return False


    def get_visible_area(self):
        return (self.pixmappoint2coord([0, 0]), self.pixmappoint2coord([self.map_width, self.map_height]))

    def hide_progress(self):
        self.progressbar.hide()
                
                        
                
    def _load_images(self):
        if self.current_cache == None:
            self._update_cache_image(reset=True)
            return
        if len(self.current_cache.get_images()) > 0:
            self.images = self.current_cache.get_images().items()
        else:
            self.images = {}
        self._update_cache_image(reset=True)

    def on_download_clicked(self, widget, data=None):
        self.core.on_download(self.get_visible_area())


    def on_download_details_map_clicked(self, some, thing=None):
        self.core.on_download_descriptions(self.get_visible_area(), True)
        self._draw_map()

    def on_download_details_sync_clicked(self, something):
        self.core.on_download_descriptions(self.get_visible_area())
        self._draw_map()
                
    def on_actions_clicked(self, widget, event):
        xml.get_widget('menu_actions').popup(None, None, None, event.button, event.get_time())

    def on_cache_marked_toggled(self, widget):
        if self.current_cache == None:
            return
        self._update_mark(self.current_cache, widget.get_active())

    def on_change_coord_clicked(self, something):
        self.set_target(self.show_coordinate_input(self.current_target))

    def _get_search_selected_cache(self):
        index = self.cachelist.getFirstSelectedRowIndex()
        if index == None:
            return (None, None)
        cache = self.cachelist_contents[index]
        return (index, cache)
        
    def on_result_marked_toggled(self, widget):
        (index, cache) = self._get_search_selected_cache()
        if cache == None:
            return
        self._update_mark(cache, widget.get_active())
        title = self._format_cache_title(cache)
        self.cachelist.setItem(index, 0, title)

    def _update_mark(self, cache, status):
        cache.marked = status
        if status:
            s = 1
        else:
            s = 0
        self.pointprovider.update_field(cache, 'marked', s)
        self.redraw_marks()

                
    def on_download_cache_clicked(self, something):
        self.core.on_download_cache(self.current_cache)
        
    def on_export_cache_clicked(self, something):
        if self.input_export_path.get_value().strip() == '':
            self.show_error("Please input path to export to.")
            return
        self.core.on_export_cache(self.current_cache, self.input_export_path.get_value())
        
    def on_good_fix(self, gps_data):
        self.gps_data = gps_data
        self.gps_has_fix = True
        self._draw_arrow()
        #self.do_events()
        self.update_gps_display()
                
        if self.dragging:
            return
                
        # redraw marks if we need to
        if not self.drawing_area_configured:
            return False
                
        x, y = self._coord2point(self.gps_data.position)
        if self.gps_last_position != None:
                                    
            l, m = self.gps_last_position
            dist_from_last = (x - l) ** 2 + (y - m) ** 2

            # if we are tracking the user, redraw if far enough from center:
            if self.button_track.get_active():
                n, o = self.map_width / 2, self.map_height / 2
                dist_from_center = (x - n) ** 2 + (y - o) ** 2
                if dist_from_center > self.REDRAW_DISTANCE_TRACKING ** 2:
                    self.set_center(self.gps_data.position)
                    # update last position, as it is now drawed
                    self.gps_last_position = (x, y)
                    return

            # if we are tracking and we have not moved out of the center
            # or if we are not tracking the user
            # in either case, if we have moved far enough since last draw, redraw just the marks
            if dist_from_last > self.REDRAW_DISTANCE_MINOR ** 2:
                a, b = self.get_visible_area()
                if self.gps_data.position.lat > min(a.lat, b.lat) \
                    and self.gps_data.position.lat < max(a.lat, b.lat) \
                    and self.gps_data.position.lon > min(a.lon, b.lon) \
                    and self.gps_data.position.lon < max(a.lon, b.lon):
                        self.redraw_marks()
                # update last position, as it is now drawed
                self.gps_last_position = (x, y)
            return
        else:
            self.redraw_marks()
            # also update when it was None
            self.gps_last_position = (x, y)
                
                
    def redraw_marks(self):

        self._draw_marks()
        self.refresh()
        
    def on_image_next_clicked(self, something):
        if len(self.images) == 0:
            self._update_cache_image(reset=True)
            return
        self.image_no += 1
        self.image_no %= len(self.images)
        self._update_cache_image()
                
        
    def on_image_zoom_clicked(self, something):
        self.image_zoomed = not self.image_zoomed
        self._update_cache_image()

    def on_label_fieldnotes_mapped(self, widget):
        if (widget == None):
            widget = self.label_fieldnotes
        self._check_notes_save()
        l = self.pointprovider.get_new_fieldnotes_count()
        if l > 0:
            widget.set_text("you have created %d fieldnotes" % l)
        else:
            widget.set_text("you have not created any new fieldnotes")
                
    def on_list_marked_clicked(self, widget):
        self.core.on_start_search_advanced(marked=True)


    def on_no_fix(self, gps_data, status):
        self.gps_data = gps_data
        self.label_bearing.set_text("No Fix")
        self.label_latlon.set_text(status)
        self.gps_has_fix = False
        self.update_gps_display()
        self._draw_arrow()

    def on_notes_changed(self, something, somethingelse):
        self.notes_changed = True
        
    def on_fieldnotes_changed(self, something, somethingelse):
        self.fieldnotes_changed = True

    def on_fieldnotes_log_changed(self, something):
        from time import gmtime
        from time import strftime
        if self.current_cache == None:
            return
        log = geocaching.GeocacheCoordinate.LOG_NO_LOG
        if self.cache_elements['log_found'].get_active():
            log = geocaching.GeocacheCoordinate.LOG_AS_FOUND
            self.pointprovider.update_field(self.current_cache, 'found', '1')
        elif self.cache_elements['log_notfound'].get_active():
            log = geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND
            self.pointprovider.update_field(self.current_cache, 'found', '0')
        elif self.cache_elements['log_note'].get_active():
            log = geocaching.GeocacheCoordinate.LOG_AS_NOTE
        logdate = strftime('%Y-%m-%d', gmtime())
        self.cache_elements['log_date'].set_text('fieldnote date: %s' % logdate)
        self.pointprovider.update_field(self.current_cache, 'logas', log)
        self.pointprovider.update_field(self.current_cache, 'logdate', logdate)


    def on_save_config(self, something):
        if not self.block_changes:
            self.core.on_config_changed(self.read_settings())

    def on_search_action_center_clicked(self, widget):
        (index, cache) = self._get_search_selected_cache()
        if cache == None:
            return
        self.set_center(cache)
        self.notebook_all.set_current_page(1)

    def on_search_action_set_target_clicked(self, widget):
        (index, cache) = self._get_search_selected_cache()
        if cache == None:
            return
        self.current_cache = cache
        self.set_target(cache)
        self.notebook_all.set_current_page(0)

    def on_search_action_view_details_clicked(self, widget):
        (index, cache) = self._get_search_selected_cache()
        if cache == None:
            return
        self.show_cache(cache)

                
    def on_search_advanced_clicked(self, something):
        def get_val_from_text(input, use_max):
            if not use_max:
                valmap = {'1..1.5': 1, '2..2.5': 2, '3..3.5': 3, '4..4.5': 4, '5': 5}
                default = 1
            else:
                valmap = {'1..1.5': 1.5, '2..2.5': 2.5, '3..3.5': 3.5, '4..4.5': 4.5, '5': 5}
                default = 5
            if input in valmap.keys():
                return valmap[input]
            else:
                return default

        types = [a for a in [geocaching.GeocacheCoordinate.TYPE_REGULAR,
            geocaching.GeocacheCoordinate.TYPE_MULTI,
            geocaching.GeocacheCoordinate.TYPE_MYSTERY,
            geocaching.GeocacheCoordinate.TYPE_VIRTUAL] if self.search_elements['type'][a].get_active()]

        if self.search_elements['type']['all'].get_active() or len(types) == 0:
            types = None

        name_search = self.search_elements['name'].get_text()

        status = self.search_elements['status'].get_active_text()
        if status == 'not found':
            found = False
            marked = None
        elif status == 'found':
            found = True
            marked = None
        elif status == 'marked & new':
            found = False
            marked = True
        else:
            found = None
            marked = None

        sizes = [a for a in [1, 2, 3, 4, 5] if self.search_elements['size'][a].get_active()]
        if len(sizes) == 0:
            sizes = None

        search = {}
        for i in ['diff', 'terr']:

            sel = self.search_elements[i]['selector'].get_active_text()
            value = self.search_elements[i]['value'].get_active_text()
            if sel == 'min':
                search[i] = (get_val_from_text(value, False), 5)
            elif sel == 'max':
                search[i] = (0, get_val_from_text(value, True))
            elif sel == '=':
                search[i] = (get_val_from_text(value, False), get_val_from_text(value, True))
            else:
                search[i] = None


        if self.search_elements['inview'].get_active():
            location = self.get_visible_area()
        else:
            location = None
        if found == None and name_search == None and sizes == None and \
            search['terr'] == None and search['diff'] == None and types == None:
            self.filtermsg.hide()
        else:
            self.filtermsg.show()
        self.core.on_start_search_advanced(found=found, name_search=name_search, size=sizes, terrain=search['terr'], diff=search['diff'], ctype=types, location=location, marked=marked)

    def on_search_cache_clicked(self, listview, event, element):
        if element == None:
            return
        (index, cache) = self._get_search_selected_cache()
        if cache == None:
            return

        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.core.on_cache_selected(cache)
            self.set_center(cache)
        else:
            self.check_result_marked.set_active(cache.marked)
            
                
    def on_search_reset_clicked(self, something):
        self.filtermsg.hide()
        self.core.on_start_search_advanced()

                
    def on_set_target_clicked(self, something):
        if self.current_cache == None:
            return
        else:
            self.set_target(self.current_cache)
            self.notebook_all.set_current_page(0)

    def on_set_target_center(self, some, thing=None):
        self.set_target(self.ts.num2deg(self.map_center_x, self.map_center_y))

    def on_show_target_clicked(self, some=None, data=None):
        if self.current_target == None:
            return
        else:
            self.set_center(self.current_target)
                
    def on_track_toggled(self, something, data=None):
        if self.button_track.get_active() and self.gps_data != None and self.gps_data.position != None:
            self.set_center(self.gps_data.position)

    def on_upload_fieldnotes(self, something):
        self.core.on_upload_fieldnotes()
        self.on_label_fieldnotes_mapped(None)
        
    def on_waypoint_clicked(self, listview, event, element):
        if event.type != gtk.gdk._2BUTTON_PRESS or element == None:
            return

        if self.current_cache == None:
            return
        if element[0] == 0:
            self.set_target(self.current_cache)
            self.notebook_all.set_current_page(0)
        else:
            wpt = self.current_cache.get_waypoints()[element[0]-1]
            if wpt['lat'] == -1 or wpt['lon'] == -1:
                return
            self.set_target(geo.Coordinate(wpt['lat'], wpt['lon'], wpt['id']))
            self.notebook_all.set_current_page(0)
                
    def on_zoom_changed(self, blub):
        self.zoom()
                
    def on_zoomin_clicked(self, widget, data=None):
        self.zoom(+ 1)
                
    def on_zoomout_clicked(self, widget, data=None):
        self.zoom(-1)
                
    def _update_cache_image(self, reset=False):
        if reset:
            self.image_zoomed = False
            self.image_no = 0
            if len(self.images) == 0:
                self.image_cache.set_from_stock(gtk.STOCK_CANCEL, -1)
                self.image_cache_caption.set_text("There's nothing to see here.")
                return
        try:
            if self.current_cache == None or len(self.images) <= self.image_no:
                self._update_cache_image(True)
                return
            filename = os.path.join(self.settings['download_output_dir'], self.images[self.image_no][0])
            if not os.path.exists(filename):
                self.image_cache_caption.set_text("not found: %s" % filename)
                self.image_cache.set_from_stock(gtk.STOCK_GO_FORWARD, -1)
                return
            
            if not self.image_zoomed:
                mw, mh = self.scrolledwindow_image.get_allocation().width - 10, self.scrolledwindow_image.get_allocation().height - 10
                pb = gtk.gdk.pixbuf_new_from_file_at_size(filename, mw, mh)
            else:
                pb = gtk.gdk.pixbuf_new_from_file(filename)
                        
            self.image_cache.set_from_pixbuf(pb)
            caption = self.images[self.image_no][1]

            self.image_cache_caption.set_text("<b>%d</b> %s" % (self.image_no, caption))
            self.image_cache_caption.set_use_markup(True)
        except Exception, e:
            print "Error loading image: %s" % e
                        
                
    def pixmappoint2coord(self, point):
        size = self.ts.tile_size()
        coord = self.ts.num2deg(\
                                (point[0] + self.map_center_x * size - self.map_width / 2) / size, \
                                (point[1] + self.map_center_y * size - self.map_height / 2) / size \
                                )
        return coord
                
    def point_in_screen(self, point):
        return (point[0] >= 0 and point[1] >= 0 and point[0] < self.map_width and point[1] < self.map_height)

    def read_settings(self):
        c = self.ts.num2deg(self.map_center_x, self.map_center_y)
        settings = {\
            'map_position_lat': c.lat, \
            'map_position_lon': c.lon, \
            'map_zoom': self.ts.get_zoom() \
        }
        if self.current_target != None:
            settings['last_target_lat'] = self.current_target.lat
            settings['last_target_lon'] = self.current_target.lon
            settings['last_target_name'] = self.current_target.name
                        
        for x in self.SETTINGS_CHECKBOXES:
            w = xml.get_widget('check_%s' % x)
            if w != None:
                settings[x] = w.get_active()
                
        for x in self.SETTINGS_INPUTS:
            w = xml.get_widget('input_%s' % x)
            if w != None:
                settings[x] = w.get_text()
                
        self.settings = settings
                
        return settings
                        
                
    def refresh(self):
        self.drawing_area.queue_draw()
                       
    @staticmethod 
    def replace_image_tag(m):
        if m.group(1) != None and m.group(1).strip() != '':
            return ' [Image: %s] ' % m.group(1).strip()
        else:
            return ' [Image] '
                        
    def screenpoint2coord(self, point):
        size = self.ts.tile_size()
        coord = self.ts.num2deg(\
                                ((point[0] - self.draw_root_x - self.draw_at_x) + self.map_center_x * size - self.map_width / 2) / size, \
                                ((point[1] - self.draw_root_y - self.draw_at_y) + self.map_center_y * size - self.map_height / 2) / size \
                                )
        return coord
        
    def _scroll(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.zoom(-1)
        else:
            self.zoom(+ 1)
        
                
    def set_center(self, coord, noupdate=False):
        #xml.get_widget("notebook_all").set_current_page(0)
        self.map_center_x, self.map_center_y = self.ts.deg2num(coord)
        self.draw_at_x = 0
        self.draw_at_y = 0
        if not noupdate:
            self._draw_map()
                
    #called by core
    def set_download_progress(self, fraction, text):
        self.progressbar.show()
        self.progressbar.set_text(text)
        self.progressbar.set_fraction(fraction)
        #self.do_events()
                
    def set_target(self, cache):
        self.current_target = cache
        self.label_target.set_text("<span size='large'>%s\n%s</span>" % (cache.get_lat(self.format), cache.get_lon(self.format)))
        self.label_target.set_use_markup(True)
        
        #self.set_center(cache)
                
    def show(self):
        self.window.show_all()
        gtk.main()
                
                        
    # called by core
    def show_cache(self, cache):
        if cache == None:
            return
        self._check_notes_save()
        self.current_cache = cache

        # Title
        self.cache_elements['title'].set_text("<b>%s</b> %s" % (cache.name, cache.title))
        self.cache_elements['title'].set_use_markup(True)

        # Type
        self.cache_elements['type'].set_text("%s" % cache.type)
        if cache.size == -1:
            self.cache_elements['size'].set_text("?")
        else:
            self.cache_elements['size'].set_text("%d/5" % cache.size)

        # Terrain
        if cache.terrain == -1:
            self.cache_elements['terrain'].set_text("?")
        else:
            self.cache_elements['terrain'].set_text("%s/5" % cache.get_terrain())

        # Difficulty
        if cache.difficulty == -1:
            self.cache_elements['difficulty'].set_text("?")
        else:
            self.cache_elements['difficulty'].set_text("%s/5" % cache.get_difficulty())
                                                
        # Description and short description
        text_shortdesc = self._strip_html(cache.shortdesc)
        if cache.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
            text_shortdesc = 'ATTENTION! This Cache is Disabled!\n--------------\n' + text_shortdesc
        text_longdesc = self._strip_html(re.sub(r'(?i)<img[^>]+?>', ' [to get all images, re-download description] ', re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: self._replace_image_callback(a, cache), cache.desc)))

        if text_longdesc == '':
            text_longdesc = '(no description available)'
        if not text_shortdesc == '':
            showdesc = text_shortdesc + "\n\n" + text_longdesc
        else:
            showdesc = text_longdesc
        self.cache_elements['desc'].set_text(showdesc)

        # is cache marked?
        self.cache_elements['marked'].set_active(cache.marked)

        # Set View
        self.notebook_cache.set_current_page(0)
        self.notebook_all.set_current_page(2)

        # Update view here for fast user feedback
        #self.do_events()

        # logs
        logs = cache.get_logs()
        if len(logs) > 0:
            text_hints = 'LOGS:\n'
            for l in logs:
                if l['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_FOUND:
                    t = 'FOUND'
                elif l['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_NOTFOUND:
                    t = 'NOT FOUND'
                elif l['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_NOTE:
                    t = 'NOTE'
                elif l['type'] == geocaching.GeocacheCoordinate.LOG_TYPE_MAINTENANCE:
                    t = 'MAINTENANCE'
                else:
                    t = l['type'].upper()
                text_hints += '%s by %s at %4d/%d/%d: %s\n\n' % (t, l['finder'], int(l['year']), int(l['month']), int(l['day']), l['text'])
            text_hints += '\n----------------\n'
        else:
            text_hints = 'NO LOGS.\n\n'


        # hints
        hints = cache.hints.strip()
        if hints == '':
            hints = '(no hints available)'
            showdesc += "\n[no hints]"
        else:
            showdesc += "\n[hints available]"
        text_hints += 'HINTS:\n' + hints

        self.cache_elements['hints'].set_text(text_hints)

        # Waypoints
        format = lambda n: "%s %s" % (re.sub(r' ', '', n.get_lat(geo.Coordinate.FORMAT_DM)), re.sub(r' ', '', n.get_lon(geo.Coordinate.FORMAT_DM)))
        rows = [(cache.name, format(cache), '(cache coord)', '')]
        for w in cache.get_waypoints():
            if not (w['lat'] == -1 and w['lon'] == -1):
                latlon = format(geo.Coordinate(w['lat'], w['lon']))
            else:
                latlon = "???"
            rows.append((w['name'], latlon, w['id'], self._strip_html(w['comment'])))
        self.coordlist.replaceContent(rows)
                        
        # Set button for downloading to correct state
        self.button_download_details.set_sensitive(True)

        # Load notes
        self.cache_elements['notes'].set_text(cache.notes)
        self.cache_elements['fieldnotes'].set_text(cache.fieldnotes)

        # Set field note (log) settings
        if cache.log_as == geocaching.GeocacheCoordinate.LOG_AS_FOUND:
            self.cache_elements['log_found'].set_active(True)
        elif cache.log_as == geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND:
            self.cache_elements['log_notfound'].set_active(True)
        elif cache.log_as == geocaching.GeocacheCoordinate.LOG_AS_NOTE:
            self.cache_elements['log_note'].set_active(True)
        else:
            self.cache_elements['log_no'].set_active(True)

        if cache.log_date != '':
            self.cache_elements['log_date'].set_text('fieldnote date: %s' % cache.log_date)
        else:
            self.cache_elements['log_date'].set_text('fieldnote date: not set')

        # Load images
        self._load_images()
        self.image_no = 0
        if len(self.images) > 0:
            showdesc += "\n[%d image(s) available]" % len(self.images)
        else:
            showdesc += "\n[no images available]"
        # now, update the main text field a second time
        self.cache_elements['desc'].set_text(showdesc)

        #gobject.idle_add(self._draw_marks)
        #self.refresh()


    def _replace_image_callback(self, match, coordinate):
        if match.group(1) in coordinate.get_images().keys():
            desc = coordinate.get_images()[match.group(1)]
            if desc.strip() != '':
                return ' [image: %s] ' % desc
            else:
                return ' [image] '
        else:
            return ' [image not found -- please re-download geocache description] '

                
    def show_error(self, errormsg):
        if isinstance(errormsg, Exception):
            raise errormsg
        error_dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, \
                                      message_format="%s" % errormsg, \
                                      buttons=gtk.BUTTONS_OK)
        error_dlg.run()
        error_dlg.destroy()

    def show_success(self, message):
        suc_dlg = gtk.MessageDialog(type=gtk.MESSAGE_INFO \
                                    , message_format=message \
                                    , buttons=gtk.BUTTONS_OK)
        suc_dlg.run()
        suc_dlg.destroy()

    def show_coordinate_input(self, start):
        udr = UpdownRows(self.format, start, False)
        dialog = gtk.Dialog("Change Target", None, gtk.DIALOG_MODAL, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        frame = gtk.Frame("Latitude")
        frame.add(udr.table_lat)
        dialog.vbox.pack_start(frame)
                
        frame = gtk.Frame("Longitude")
        frame.add(udr.table_lon)
        dialog.vbox.pack_start(frame)
                
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        c = udr.get_value()
        c.name = 'manual'
        return c

    @staticmethod 
    def _strip_html(text):
        text = text.replace("\n", " ")
        text = re.sub(r"""(?i)<img[^>]+alt=["']?([^'"> ]+)[^>]+>""", SimpleGui.replace_image_tag, text)
        text = re.sub(r'(?i)<(br|p)[^>]*?>', "\n", text)
        text = re.sub(r'<[^>]*?>', '', text)
        text = SimpleGui._decode_htmlentities(text)
        text = re.sub(r'[\n\r]+\s*[\n\r]+', '\n', text)
        return text.strip()
                
                        
    def update_gps_display(self):
        if self.gps_data == None:
            return

        if self.gps_data.sats == 0:
            label = "No sats available"
        else:
            label = "%d/%d sats, error: ±%3.1fm" % (self.gps_data.sats, self.gps_data.sats_known, self.gps_data.error)
            if self.gps_data.dgps:
                label += " DGPS"
        self.label_quality.set_text(label)
        if self.gps_data.altitude == None or self.gps_data.bearing == None:
            return

        self.label_altitude.set_text("alt %3dm" % self.gps_data.altitude)
        self.label_bearing.set_text("%d°" % self.gps_data.bearing)
        self.label_latlon.set_text("<span size='large'>%s\n%s</span>" % (self.gps_data.position.get_lat(self.format), self.gps_data.position.get_lon(self.format)))
        self.label_latlon.set_use_markup(True)
                
        if self.current_target == None:
            return
                        
                
        target_distance = self.gps_data.position.distance_to(self.current_target)
        if target_distance >= 1000:
            label = "%3dkm" % round(target_distance / 1000)
        elif display_dist >= 100:
            label = "%3dm" % round(target_distance)
        else:
            label = "%2.1fm" % round(target_distance, 1)
        self.label_dist.set_text("<span size='large'>%s</span>" % label)
        self.label_dist.set_use_markup(True)
        
        
                
                
    def write_settings(self, settings):
        self.settings = settings
        self.block_changes = True
        self.ts.set_zoom(self.settings['map_zoom'])
        self.set_center(geo.Coordinate(self.settings['map_position_lat'], self.settings['map_position_lon']))
                
        if 'last_target_lat' in self.settings.keys():
            self.set_target(geo.Coordinate(self.settings['last_target_lat'], self.settings['last_target_lon'], self.settings['last_target_name']))

        for x in self.SETTINGS_CHECKBOXES:
            if x in self.settings.keys():
                w = xml.get_widget('check_%s' % x)
                if w == None:
                    continue
                w.set_active(self.settings[x])
            elif x in self.DEFAULT_SETTINGS.keys():
                w = xml.get_widget('check_%s' % x)
                if w == None:
                    continue
                w.set_active(self.DEFAULT_SETTINGS[x])
        
        for x in self.SETTINGS_INPUTS:
            if x in self.settings.keys():
                w = xml.get_widget('input_%s' % x)
                if w == None:
                    continue
                w.set_text(str(self.settings[x]))
            elif x in self.DEFAULT_SETTINGS.keys():
                w = xml.get_widget('input_%s' % x)
                if w == None:
                    continue
                w.set_text(self.DEFAULT_SETTINGS[x])
                                        
        self.block_changes = False
        self.build_tile_loaders()
                
    def zoom(self, direction=None):
        size = self.ts.tile_size()
        center = self.ts.num2deg(self.map_center_x - float(self.draw_at_x) / size, self.map_center_y - float(self.draw_at_y) / size)
        if direction == None:
            #newzoom = self.zoom_adjustment.get_value()
            print "not"
        else:
            newzoom = self.ts.get_zoom() + direction
        self.ts.set_zoom(newzoom)
        self.set_center(center)
                

    @staticmethod
    def shorten_name(s, chars):
        max_pos = chars
        min_pos = chars - 10

        NOT_FOUND = -1

        suffix = '…'

        # Case 1: Return string if it is shorter (or equal to) than the limit
        length = len(s)
        if length <= max_pos:
            return s
        else:
            # Case 2: Return it to nearest period if possible
            try:
                end = s.rindex('.', min_pos, max_pos)
            except ValueError:
                # Case 3: Return string to nearest space
                end = s.rfind(' ', min_pos, max_pos)
                if end == NOT_FOUND:
                    end = max_pos
            return s[0:end] + suffix


class Updown():
    def __init__(self, table, position, small):
        self.value = int(0)
        self.label = gtk.Label("<b>0</b>")
        self.label.set_use_markup(True)
        self.button_up = gtk.Button("+")
        self.button_down = gtk.Button("-")
        table.attach(self.button_up, position, position + 1, 0, 1)
        table.attach(self.label, position, position + 1, 1, 2, 0, 0)
        table.attach(self.button_down, position, position + 1, 2, 3)
        self.button_up.connect('clicked', self.value_up)
        self.button_down.connect('clicked', self.value_down)
        if small != None:
            if small:
                font = pango.FontDescription("sans 8")
            else:
                font = pango.FontDescription("sans 12")
            self.label.modify_font(font)
            self.button_up.child.modify_font(font)
            self.button_down.child.modify_font(font)
        
    def value_up(self, target):
        self.value = int((self.value + 1) % 10)
        self.update()
        
    def value_down(self, target):
        self.value = int((self.value - 1) % 10)
        self.update()
                
    def set_value(self, value):
        self.value = int(value)
        self.update()
                
    def update(self):
        self.label.set_markup("<b>%d</b>" % self.value)
                

                
class PlusMinusUpdown():
    def __init__(self, table, position, labels, small = None):
        self.is_neg = False
        self.labels = labels
        self.button = gtk.Button(labels[0])
        table.attach(self.button, position, position + 1, 1, 2, gtk.FILL, gtk.FILL)
        self.button.connect('clicked', self.value_toggle)
        if small != None:
            self.button.child.modify_font(pango.FontDescription("sans 8"))
        
    def value_toggle(self, target):
        self.is_neg = not self.is_neg
        self.update()
                
    def set_value(self, value):
        self.is_neg = (value < 0)
        self.update()
                
    def get_value(self):
        if self.is_neg:
            return -1
        else:
            return 1
                
    def update(self):
        if self.is_neg:
            text = self.labels[0]
        else:
            text = self.labels[1]
        self.button.child.set_text(text)

class UpdownRows():
    def __init__(self, format, coord, large_dialog):
        self.format = format
        self.large_dialog = large_dialog
        if coord == None:
            coord = geo.Coordinate(50, 10, 'none')
        if format == geo.Coordinate.FORMAT_DM:
            [init_lat, init_lon] = coord.to_dm_array()
        elif format == geo.Coordinate.FORMAT_D:
            [init_lat, init_lon] = coord.to_d_array()
        [self.table_lat, self.chooser_lat] = self.generate_table(False, init_lat)
        [self.table_lon, self.chooser_lon] = self.generate_table(True, init_lon)
        self.switcher_lat.set_value(coord.lat)
        self.switcher_lon.set_value(coord.lon)

    def get_value(self):
        coord = geo.Coordinate(0, 0)
        lat_values = [ud.value for ud in self.chooser_lat]
        lon_values = [ud.value for ud in self.chooser_lon]
        if self.format == geo.Coordinate.FORMAT_DM:
            coord.from_dm_array(self.switcher_lat.get_value(), lat_values, self.switcher_lon.get_value(), lon_values)
        elif self.format == geo.Coordinate.FORMAT_D:
            coord.from_d_array(self.switcher_lat.get_value(), lat_values, self.switcher_lon.get_value(), lon_values)
        return coord

    def generate_table(self, is_long, initial_value):
        interrupt = {}
        if self.format == geo.Coordinate.FORMAT_DM and not is_long:
            small = 2
            num = 7
            interrupt[3] = "°"
            interrupt[6] = "."
        elif self.format == geo.Coordinate.FORMAT_DM and is_long:
            small = 3
            num = 8
            interrupt[4] = "°"
            interrupt[7] = "."
        elif self.format == geo.Coordinate.FORMAT_D and not is_long:
            small = 2
            num = 7
            interrupt[3] = "."
        elif self.format == geo.Coordinate.FORMAT_D and is_long:
            small = 3
            num = 8
            interrupt[4] = "."

        table = gtk.Table(3, num + len(interrupt) + 1, False)
                
        if is_long:
            self.switcher_lon = PlusMinusUpdown(table, 0, ['W', 'E'], None if self.large_dialog else False)
        else:
            self.switcher_lat = PlusMinusUpdown(table, 0, ['S', 'N'], None if self.large_dialog else False)
                
        chooser = []
        cn = 0
        for i in xrange(1, num + len(interrupt) + 1):
            if i in interrupt:
                table.attach(gtk.Label(interrupt[i]), i, i + 1, 1, 2, 0, 0)
            else:
                ud = Updown(table, i, (cn < small) if not self.large_dialog else None)
                if cn < len(initial_value):
                    ud.set_value(initial_value[cn])
                    chooser.append(ud)
                    cn = cn + 1

        return [table, chooser]

