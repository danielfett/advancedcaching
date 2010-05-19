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
# download map data
# direction indicator in map view
# edit waypoints
 
### For the gui :-)

from math import ceil
from os import path, system
import re

import coordfinder
import geo
import geocaching
import gtk
import hildon
import openstreetmap
import pango
from simplegui import SimpleGui, UpdownRows
from portrait import FremantleRotation
class HildonGui(SimpleGui):

    USES = ['locationgpsprovider']

    MIN_DRAG_REDRAW_DISTANCE = 2
    DRAG_RECHECK_SPEED = 40

    # arrow colors and sizes
    COLOR_ARROW_DISABLED = gtk.gdk.color_parse("red")
    COLOR_ARROW_CIRCLE = gtk.gdk.color_parse("lightslategrey")
    COLOR_CROSSHAIR = gtk.gdk.color_parse("deeppink")
    COLOR_ARROW_OUTER_LINE = gtk.gdk.color_parse("white")
    COLOR_QUALITY_OUTER = None
    ARROW_LINE_WIDTH = 2
    NORTH_INDICATOR_SIZE = 30
    FONT_NORTH_INDICATOR = pango.FontDescription("Sans 19")


    CLICK_RADIUS = 25

    TOO_MUCH_POINTS = 100
    CACHES_ZOOM_LOWER_BOUND = 8
    CACHE_DRAW_FONT = pango.FontDescription("Sans 10")
    MESSAGE_DRAW_FONT = pango.FontDescription("Sans 12")

    def __init__(self, core, pointprovider, userpointprovider, dataroot):
        gtk.gdk.threads_init()
        self.ts = openstreetmap.TileServer()

        self.noimage_cantload = gtk.gdk.pixbuf_new_from_file(path.join(dataroot, 'noimage-cantload.png'))
        self.noimage_loading = gtk.gdk.pixbuf_new_from_file(path.join(dataroot, 'noimage-loading.png'))
        
        self.core = core
        self.core.connect('map-changed', self._on_map_changed)
        self.core.connect('cache-changed', self._on_cache_changed)
        self.core.connect('fieldnotes-changed', self._on_fieldnotes_changed)

        self.pointprovider = pointprovider

        self.build_tile_loaders()
                
        self.format = geo.Coordinate.FORMAT_DM

        # @type self.current_cache geocaching.GeocacheCoordinate
        self.current_cache = None
        self.current_cache_window_open = False
                
        self.current_target = None
        self.gps_data = None
        self.gps_has_fix = False
        self.gps_last_good_fix = None
        self.gps_last_screen_position = (0, 0)
        self.banner = None
        self.old_cache_window = None
        self.old_search_window = None
        self.cache_calc_vars = {}
        #self.osd_string = ''
                
        self.dragging = False
        self.block_changes = False
                
        self.north_indicator_layout = None
        self.drawing_area_configured = self.drawing_area_arrow_configured = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.notes_changed = False
        self.map_center_x, self.map_center_y = 100, 100
        self.active_tile_loaders = []
        self.reorder_functions = []
        
        gtk.set_application_name("Geocaching Tool")
        program = hildon.Program.get_instance()
        self.window = hildon.StackableWindow()
        program.add_window(self.window)
        self.window.connect("delete_event", self.on_window_destroy, None)
        self.window.connect("key-press-event", self._on_key_press)
        self.window.connect('configure_event', self.__configure_root)
        self.window.add(self._create_main_view())
        self.window.set_app_menu(self._create_main_menu())
        self.update_fieldnotes_display()

        gtk.link_button_set_uri_hook(self._open_browser)
        #self.show_coordinate_input(geo.Coordinate(49.344, 6.584))

        self.rotation_manager = FremantleRotation('advancedcaching')

        self.astral = Astral()

    def _open_browser(self, widget, link):
        system("browser --url='%s' &" % link)

    def show_coordinate_input(self, start):
        udr = UpdownRows(self.format, start, True)
        dialog = gtk.Dialog("Edit Target", None, gtk.DIALOG_MODAL, ("OK", gtk.RESPONSE_ACCEPT))
        dialog.set_size_request(-1, 480)
        dialog.vbox.pack_start(udr.table_lat)
                
        dialog.vbox.pack_start(udr.table_lon)
                
        dialog.show_all()
        res = dialog.run()
        dialog.destroy()
        if res == gtk.RESPONSE_ACCEPT:
            c = udr.get_value()
            c.name = 'manual'
            return c
        else:
            return startd

    def set_tile_loader(self, widget, loader):
        if widget.get_active():
            self.tile_loader = loader
            self._draw_map()


    def _on_key_press(self, window, event):
        return
        if event.keyval == gtk.keysyms.F7:
            self.zoom(+ 1)
            return False
        elif event.keyval == gtk.keysyms.F8:
            self.zoom(-1)
            return False


    def _create_main_view(self):
        root = gtk.VBox()

        self.main_gpspage = gtk.VBox()
        self.main_gpspage_table = gtk.Table(7, 3)
        self.drawing_area_arrow = gtk.DrawingArea()

        self.label_dist = gtk.Label()
        self.label_dist.set_markup("")
        self.label_dist.set_alignment(0, 0)

        self.label_bearing = gtk.Label()
        self.label_bearing.set_markup("")
        self.label_bearing.set_alignment(0, 0)

        self.label_altitude = gtk.Label()
        self.label_altitude.set_markup("")
        self.label_altitude.set_alignment(0, 0)

        self.label_latlon = gtk.Label()
        self.label_latlon.set_markup("")
        self.label_latlon.set_alignment(0, 0)

        self.label_quality = gtk.Label()
        self.label_quality.set_markup("")
        self.label_quality.set_alignment(0, 0)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Target")
        button.set_value('none set')
        button.connect('clicked', self._on_show_dialog_change_target, None)
        button.set_size_request(270, -1)
        self.label_target = button

        #buttons = gtk.HBox()

        button_details = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button_details.set_title("Details")
        button_details.set_sensitive(False)
        button_details.connect("clicked", self._on_show_cache_details, None)
        #buttons.pack_start(button, True, True)
        
        self.button_show_details_small = button_details
        
        button_map = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button_map.set_label("Map")
        button_map.connect("clicked", self._on_set_active_page, False)
        #buttons.pack_start(button, True, True)


        self.main_gpspage_table.attach(self.label_dist, 1, 3, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
        self.main_gpspage_table.attach(self.label_altitude, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
        self.main_gpspage_table.attach(self.label_bearing, 2, 3, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
        self.main_gpspage_table.attach(self.label_latlon, 1, 3, 3, 4, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
        self.main_gpspage_table.attach(self.label_quality, 1, 3, 4, 5, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
        self.main_gpspage_table.attach(self.label_target, 1, 3, 5, 6, gtk.FILL | gtk.EXPAND, 0)
        self.main_gpspage_table.attach(button_details, 1, 2, 6, 7, gtk.FILL | gtk.EXPAND, 0)
        self.main_gpspage_table.attach(button_map, 2, 3, 6, 7, gtk.FILL | gtk.EXPAND, 0)
        self.main_gpspage_table.attach(self.drawing_area_arrow, 0, 1, 0, 7, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL)

        def reorder_gps(portrait):
            x = self.drawing_area_arrow.get_parent()
            if x != None:
                x.remove(self.drawing_area_arrow)

            x = self.main_gpspage_table.get_parent()
            if x != None:
                x.remove(self.main_gpspage_table)

            for x in self.main_gpspage.get_children():
                self.main_gpspage.remove(x)

            if portrait: 
                self.main_gpspage.pack_start(self.drawing_area_arrow, True)
                self.main_gpspage.pack_start(self.main_gpspage_table, False)
            else:
                landscape_hbox = gtk.HBox(True)
                landscape_hbox.pack_start(self.drawing_area_arrow, True)
                landscape_hbox.pack_start(self.main_gpspage_table, True)
                self.main_gpspage.pack_start(landscape_hbox)
                landscape_hbox.show()

        self.reorder_functions.append(reorder_gps)

        self.main_gpspage.pack_start(self.main_gpspage_table, False, True)
        
        self.main_mappage = gtk.VBox()
        self.drawing_area = gtk.DrawingArea()

        buttons = gtk.HBox()

        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("track")
        button.connect("clicked", self.on_track_toggled, None)
        self.button_track = button
        buttons.pack_start(button, True, True)
        def reorder_gps(portrait):
            if portrait: 
                text = ''
            else:
                text = 'track'
            self.button_track.set_label(text)

        self.reorder_functions.append(reorder_gps)

        #icon = gtk.image_new_from_stock(gtk.STOCK_ZOOM_IN, gtk.ICON_SIZE_BUTTON)
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("+")
        #button.set_image(icon)
        button.connect("clicked", self.on_zoomin_clicked, None)
        buttons.pack_start(button, True, True)

        #icon = gtk.image_new_from_stock(gtk.STOCK_ZOOM_OUT, gtk.ICON_SIZE_BUTTON)
        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("-")
        #button.set_image(icon)
        button.connect("clicked", self.on_zoomout_clicked, None)
        buttons.pack_start(button, True, True)


        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Show Details")
        button.set_value('No Cache selected')
        button.set_sensitive(False)
        button.connect("clicked", self._on_show_cache_details, None)
        buttons.pack_start(button, True, True)
        self.button_show_details = button


        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("GPS")
        button.connect("clicked", self._on_set_active_page, True)
        buttons.pack_start(button, True, True)
        
        #self.main_mappage.pack_start(self.drawing_area, True)
        pan = hildon.PannableArea()
        pan.add(self.drawing_area)

        self.main_mappage.pack_start(pan, True)
        self.main_mappage.pack_start(buttons, False)
        root.pack_start(self.main_gpspage, True)
        root.pack_start(self.main_mappage, True)


        self.drawing_area.connect("expose_event", self._expose_event)
        self.drawing_area.connect("configure_event", self._configure_event)
        self.drawing_area.connect("button_press_event", self._drag_start)
        self.drawing_area.connect("scroll_event", self._scroll)
        self.drawing_area.connect("button_release_event", self._drag_end)
        self.drawing_area.connect("motion_notify_event", self._drag)
        self.drawing_area.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.SCROLL)
        

        # arrow drawing area
        
        self.drawing_area_arrow.connect("expose_event", self._expose_event_arrow)
        self.drawing_area_arrow.connect("configure_event", self._configure_event_arrow)
        self.drawing_area_arrow.set_events(gtk.gdk.EXPOSURE_MASK)

        return root

    def __configure_root(self, root, event):
        #(x, y, width, height) = root.get_allocation()
        if event != None:
            w, h = event.width, event.height
        else:
            x, y, w, h = root.get_allocation()

        for x in self.reorder_functions:
            x(w < h)

    def _create_main_menu(self):
        menu = hildon.AppMenu()
    
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Show current Target")
        button.set_value('')
        button.connect("clicked", self.on_show_target_clicked, None)
        menu.append(button)
        self.button_goto_target = button
        
        
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Use Center as Target")
        button.set_value('')
        button.connect("clicked", self.on_set_target_center, None)
        menu.append(button)
        self.button_center_as_target = button
        
        
        
        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Search Geocaches")
        button.connect("clicked", self._on_show_search, None)
        menu.append(button)

        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Last Search Results")
        button.connect("clicked", self._on_reopen_search_clicked, None)
        button.set_sensitive(False)
        self.reopen_last_search_button = button
        menu.append(button)

        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Overview")
        button.set_value("for the visible area")
        button.connect("clicked", self.on_download_clicked, None)
        menu.append(button)
    
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Details")
        button.set_value("for all visible caches")
        button.connect("clicked", self.on_download_details_map_clicked, None)
        menu.append(button)

        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Upload Fieldnote(s)")
        button.set_value("You have not created any fieldnotes.")
        button.connect("clicked", self._on_upload_fieldnotes, None)
        menu.append(button)
        self.button_fieldnotes = button
    
    
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Options")
        button.connect("clicked", self._on_show_options, None)
        menu.append(button)

        button = None
        for name, loader in self.tile_loaders:
            button = hildon.GtkRadioButton(gtk.HILDON_SIZE_AUTO, button)
            button.set_label(name)
            button.connect("clicked", self.set_tile_loader, loader)
            menu.add_filter(button)
            button.set_mode(False)
    
        menu.show_all()
        return menu


    def show(self):
        self.window.show_all()
        self.set_active_page(False)
        gtk.main()



        ##############################################
        #
        # Search
        #
        ##############################################
        
    def _on_show_search(self, widget, data):
        RESPONSE_SHOW_LIST = 0
        RESPONSE_RESET = 1
        dialog = gtk.Dialog("set filter", None, gtk.DIALOG_DESTROY_WITH_PARENT, ("show on map", gtk.RESPONSE_ACCEPT))
        dialog.add_button("show list", RESPONSE_SHOW_LIST)
        dialog.add_button("reset", RESPONSE_RESET)
        sel_size = hildon.TouchSelector(text=True)
        sel_size.append_text('micro')
        sel_size.append_text('small')
        sel_size.append_text('regular')
        sel_size.append_text('huge')
        sel_size.append_text('other')
        sel_size.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_size = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_size.set_selector(sel_size)
        pick_size.set_title("Select Size(s)")
        for i in xrange(5):
            sel_size.select_iter(0, sel_size.get_model(0).get_iter(i), False)
        
        sel_type = hildon.TouchSelector(text=True)
        sel_type.append_text('tradit.')
        sel_type.append_text('multi')
        sel_type.append_text('virt.')
        #sel_type.append_text('earth')
        sel_type.append_text('event')
        sel_type.append_text('mystery')
        sel_type.append_text('all')
        sel_type.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_type = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_type.set_selector(sel_type)
        pick_type.set_title("Select Type(s)")
        sel_type.unselect_all(0)
        sel_type.select_iter(0, sel_type.get_model(0).get_iter(5), False)

        sel_status = hildon.TouchSelector(text=True)
        sel_status.append_text('all')
        sel_status.append_text('not found')
        sel_status.append_text('found')
        sel_status.append_text('marked')
        sel_status.append_text('not found & marked')
        pick_status = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_status.set_selector(sel_status)
        pick_status.set_title("Select Status")
        
        sel_status.unselect_all(0)
        sel_status.select_iter(0, sel_status.get_model(0).get_iter(0), False)
                        
        sel_diff = hildon.TouchSelector(text=True)
        sel_diff.append_text('1..2.5')
        sel_diff.append_text('3..4')
        sel_diff.append_text('4.5..5')
        sel_diff.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_diff = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_diff.set_selector(sel_diff)
        pick_diff.set_title("Select Difficulty")
        for i in xrange(3):
            sel_diff.select_iter(0, sel_diff.get_model(0).get_iter(i), False)
                        
        sel_terr = hildon.TouchSelector(text=True)
        sel_terr.append_text('1..2.5')
        sel_terr.append_text('3..4')
        sel_terr.append_text('4.5..5')
        sel_terr.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_terr = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_terr.set_selector(sel_terr)
        pick_terr.set_title("Select Terrain")
        for i in xrange(3):
            sel_terr.select_iter(0, sel_terr.get_model(0).get_iter(i), False)
        
        name = hildon.Entry(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
        name.set_placeholder("search for name...")
        
        t = gtk.Table(4, 3, False)
        t.attach(name, 0, 1, 1, 2)
        t.attach(gtk.Label("All Geocaches:"), 0, 1, 0, 1)
        t.attach(pick_type, 0, 1, 2, 3)
        t.attach(pick_status, 0, 1, 3, 4)
        t.attach(gtk.VSeparator(), 1, 2, 0, 4)
        t.attach(gtk.Label("If Details available:"), 2, 3, 0, 1)
        t.attach(pick_size, 2, 3, 1, 2)
        t.attach(pick_diff, 2, 3, 2, 3)
        t.attach(pick_terr, 2, 3, 3, 4)
        #t.attach(check_visible, 0, 1, 3, 4)
        
        dialog.vbox.pack_start(t)
        
        dialog.show_all()
        response = dialog.run()
        dialog.hide()

        if response == RESPONSE_RESET:
            self.core.reset_filter()

        name_search = name.get_text()

        sizes = [x + 1 for x, in sel_size.get_selected_rows(0)]
        if sizes == [1, 2, 3, 4, 5]:
            sizes = None

        typelist = [
            geocaching.GeocacheCoordinate.TYPE_REGULAR,
            geocaching.GeocacheCoordinate.TYPE_MULTI,
            geocaching.GeocacheCoordinate.TYPE_VIRTUAL,
            #geocaching.GeocacheCoordinate.TYPE_EARTH,
            geocaching.GeocacheCoordinate.TYPE_EVENT,
            geocaching.GeocacheCoordinate.TYPE_MYSTERY,
            geocaching.GeocacheCoordinate.TYPE_UNKNOWN
        ]

        types = [typelist[x] for x, in sel_type.get_selected_rows(0)]
        if geocaching.GeocacheCoordinate.TYPE_UNKNOWN in types:
            types = None

        # found, marked
        statuslist = [
            (None, None),
            (False, None),
            (True, None),
            (None, True),
            (False, True),
        ]
        found, marked = statuslist[sel_status.get_selected_rows(0)[0][0]]

        numberlist = [
            [1, 1.5, 2, 2.5],
            [3, 3.5, 4],
            [4.5, 5]
        ]

        difficulties = []
        count = 0
        for x, in sel_diff.get_selected_rows(0):
            difficulties += numberlist[x]
            count += 1
        if count == len(numberlist):
            difficulties = None


        terrains = []
        count = 0
        for x, in sel_terr.get_selected_rows(0):
            terrains += numberlist[x]
            count += 1
        if count == len(numberlist):
            terrains = None

        if response == RESPONSE_SHOW_LIST:
            points, truncated = self.core.get_points_filter(found=found, name_search=name_search, size=sizes, terrain=terrains, diff=difficulties, ctype=types, marked=marked)
            self._display_results(points, truncated)
        elif response == gtk.RESPONSE_ACCEPT:
            self.core.set_filter(found=found, name_search=name_search, size=sizes, terrain=terrains, diff=difficulties, ctype=types, marked=marked)


    def _display_results(self, caches, truncated):
        sortfuncs = [
            ('Dist', lambda x, y: cmp(x.prox, y.prox)),
            ('Name', lambda x, y: cmp(x.title, y.title)),
            ('Diff', lambda x, y: cmp(x.difficulty if x.difficulty > 0 else 100, y.difficulty if y.difficulty > 0 else 100)),
            ('Terr', lambda x, y: cmp(x.terrain if x.terrain > 0 else 100, y.terrain if y.terrain > 0 else 100)),
            ('Size', lambda x, y: cmp(x.size if x.size > 0 else 100, y.size if y.size > 0 else 100)),
            ('Type', lambda x, y: cmp(x.type, y.type)),
        ]

        if self.gps_data != None and self.gps_data.position != None:
            for c in caches:
                c.prox = c.distance_to(self.gps_data.position)
        else:
            for c in caches:
                c.prox = None

        win = hildon.StackableWindow()
        win.set_title("Search results")
        ls = gtk.ListStore(str, str, str, str, object)
        
        tv = hildon.TouchSelector()
        col1 = tv.append_column(ls, gtk.CellRendererText())
        
        c1cr = gtk.CellRendererText()
        c1cr.ellipsize = pango.ELLIPSIZE_MIDDLE
        c2cr = gtk.CellRendererText()
        c3cr = gtk.CellRendererText()
        c4cr = gtk.CellRendererText()
        
        col1.pack_start(c1cr, True)
        col1.pack_end(c2cr, False)
        col1.pack_start(c3cr, False)
        col1.pack_end(c4cr, False)

        col1.set_attributes(c1cr, text=0)
        col1.set_attributes(c2cr, text=1)
        col1.set_attributes(c3cr, text=2)
        col1.set_attributes(c4cr, text=3)

        def select_cache(widget, data, more):
            self.show_cache(self._get_selected(tv)[4])
        
        tv.connect("changed", select_cache, None)


        def on_change_sort(widget, sortfunc):
            tv.handler_block_by_func(select_cache)
            ls.clear()
            caches.sort(cmp=sortfunc)
            for c in caches:
                ls.append([self.shorten_name(c.title, 40), " " + c.get_size_string(), ' D%s T%s' % (c.get_difficulty(), c.get_terrain()), " " + self.__format_distance(c.prox), c])
            tv.handler_unblock_by_func(select_cache)


        menu = hildon.AppMenu()
        button = None
        for name, function in sortfuncs:
            button = hildon.GtkRadioButton(gtk.HILDON_SIZE_AUTO, button)
            button.set_label(name)
            button.connect("clicked", on_change_sort, function)
            menu.add_filter(button)
            button.set_mode(False)
        menu.show_all()
        win.set_app_menu(menu)
        win.add(tv)

        on_change_sort(None, sortfuncs[0][1])

        win.show_all()
        if truncated:
            hildon.hildon_banner_show_information_with_markup(win, "hu", "Showing only the first %d results." % len(caches))
        self.old_search_window = win
        self.reopen_last_search_button.set_sensitive(True)

    def _on_reopen_search_clicked(self, widget, data):
        if self.old_search_window == None:
            return
        hildon.WindowStack.get_default().push_1(self.old_search_window)


        ##############################################
        #
        # /Search
        #
        ##############################################
        
        
    def _on_show_options(self, widget, data):
        dialog = gtk.Dialog("options", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.set_size_request(800, 480)
        opts = gtk.Table(7, 2)
        opts.attach(gtk.Label("Username"), 0, 1, 0, 1)
        username = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        #username.set_property(hildon.HILDON_AUTOCAP, False)
        opts.attach(username, 1, 2, 0, 1)
        username.set_text(self.settings['options_username'])
        
        opts.attach(gtk.Label("Password"), 0, 1, 1, 2)
        password = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        password.set_visibility(False)
        #password.set_property("autocap", False)
        opts.attach(password, 1, 2, 1, 2)
        password.set_text(self.settings['options_password'])
        
        check_dl_images = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_dl_images.set_label("Don't Download Images")
        check_dl_images.set_active(self.settings['download_noimages'])

        check_show_cache_id = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_show_cache_id.set_label("Show Geocache ID on Map")
        check_show_cache_id.set_active(self.settings['options_show_name'])

        check_map_double_size = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_map_double_size.set_label("Show Map in double size (ugly)")
        check_map_double_size.set_active(self.settings['options_map_double_size'])

        check_hide_found = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_hide_found.set_label("Hide Found Geocaches on Map")
        check_hide_found.set_active(self.settings['options_hide_found'])

        rotate_settings = (
            (FremantleRotation.AUTOMATIC, 'Automatic'),
            (FremantleRotation.NEVER, 'Landscape'),
            (FremantleRotation.ALWAYS, 'Portrait')
        )
        rotate_selector = hildon.TouchSelector(text=True)
        
        i = 0
        for status, text in rotate_settings:
            rotate_selector.append_text(text)
            if self.settings['options_rotate_screen'] == status:
                rotate_selector.select_iter(0, rotate_selector.get_model(0).get_iter(i), False)
            i += 1

        rotate_screen = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        rotate_screen.set_title('Screen Rotation')
        rotate_screen.set_selector(rotate_selector)


        check_hide_found = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_hide_found.set_label("Hide Found Geocaches on Map")
        check_hide_found.set_active(self.settings['options_hide_found'])
        
        opts.attach(check_dl_images, 0, 2, 2, 3)
        opts.attach(check_show_cache_id, 0, 2, 3, 4)
        opts.attach(check_map_double_size, 0, 2, 4, 5)
        opts.attach(check_hide_found, 0, 2, 5, 6)
        opts.attach(rotate_screen, 0, 2, 6, 7)
        p = hildon.PannableArea()
        vp = gtk.Viewport()
        p.add(vp)
        vp.add(opts)
        dialog.vbox.pack_start(p, True)
        
        
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result == gtk.RESPONSE_ACCEPT:
            rotate = rotate_settings[rotate_selector.get_selected_rows(0)[0][0]][0]
            self.rotation_manager.set_mode(rotate)
            self.settings['options_username'] = username.get_text()
            self.settings['options_password'] = password.get_text()
            self.settings['download_noimages'] = check_dl_images.get_active()
            self.settings['options_show_name'] = check_show_cache_id.get_active()
            self.settings['options_map_double_size'] = check_map_double_size.get_active()
            self.settings['options_hide_found'] = check_hide_found.get_active()
            self.settings['options_rotate_screen'] = rotate
            self.core.on_userdata_changed(self.settings['options_username'], self.settings['options_password'])

    def _on_show_dialog_change_target(self, widget, data):
        if self.current_target != None:
            c = self.current_target
        elif self.gps_data != None and self.gps_data.position != None:
            c = self.gps_data.position
        else:
            c = geo.Coordinate(0, 0)

        dialog = gtk.Dialog("change target", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        bar_label = gtk.Label("Lat/Lon: ")
        bar_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        bar_entry.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_ALPHA | gtk.HILDON_GTK_INPUT_MODE_SPECIAL | gtk.HILDON_GTK_INPUT_MODE_TELE)
        bar_entry.set_text(c.get_latlon(self.format))

        def show_coord_input(widget):
            try:
                m = geo.try_parse_coordinate(bar_entry.get_text())
            except Exception, e:
                m = c
            m_new = self.show_coordinate_input(m)
            bar_entry.set_text(m_new.get_latlon(self.format))

        bar_button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        bar_button.set_label(" Edit ")
        bar_button.connect("clicked", show_coord_input)

        bar = gtk.HBox()      
        bar.pack_start(bar_label, False)
        bar.pack_start(bar_entry, True)
        bar.pack_start(bar_button, False)

        dialog.vbox.pack_start(bar, False)

        def sel_coord(widget, data, clist):
            tm = widget.get_model(0)
            iter = tm.get_iter(0)
            widget.get_selected(0, iter)
            coord = clist[tm.get_path(iter)[0]]
            bar_entry.set_text(coord.get_latlon(self.format))

        if self.current_cache != None:
            sel, clist = self._get_coord_selector(self.current_cache, sel_coord, True)
            sel.set_size_request(-1, 200)
            dialog.vbox.pack_start(sel)
        
        
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result == gtk.RESPONSE_ACCEPT:
            self.set_target(geo.try_parse_coordinate(bar_entry.get_text()))

    def show_cache(self, cache, select=True):
        if cache == None:
            return
        if self.current_cache != None and self.current_cache.name == cache.name and self.old_cache_window != None:
            
            hildon.WindowStack.get_default().push_1(self.old_cache_window)
            self.current_cache_window_open = True
            return
        
        if select:
            self.set_current_cache(cache)

        
        win = hildon.StackableWindow()
        win.set_title(cache.title)
        
        notebook = gtk.Notebook()
        notebook.set_tab_pos(gtk.POS_BOTTOM)
                
        # info
        p = gtk.Table(10, 2)
        labels = (
                  ('Full Name', cache.title),
                  ('ID', cache.name),
                  ('Type', cache.type),
                  ('Size', cache.get_size_string()),
                  ('Terrain', cache.get_terrain()),
                  ('Difficulty', cache.get_difficulty()),
                  ('Owner', cache.owner),
                  ('Status', cache.get_status())
                  )
        i = 0
        for label, text in labels:
            l = gtk.Label()
            l.set_alignment(0, 0.5)
            l.set_markup("<b>%s</b>" % label)
            w = gtk.Label(text)
            w.set_line_wrap(True)
            w.set_alignment(0, 0.5)
            p.attach(l, 0, 1, i, i + 1)
            p.attach(w, 1, 2, i, i + 1)
            i += 1
            
        # links for listing & log
        l = gtk.Label()
        l.set_markup("<b>Open Website</b>")
        l.set_alignment(0, 0.5)
        p.attach(l, 0, 1, 8, 9)
        z = gtk.HBox(True)

        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/cache_details.aspx?wp=%s" % cache.name, 'Listing'))
        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/log.aspx?wp=%s" % cache.name, 'Post Log'))
        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/cache_details.aspx?wp=%s&log=y#ctl00_ContentBody_CacheLogs" % cache.name, 'All Logs'))
        p.attach(z, 1, 2, 8, 9)

        # cache-was-not-downloaded-yet-warning
        if not cache.was_downloaded():
            p.attach(gtk.Label("Please download full details to see the description."), 0, 2, 9, 10)
        
        notebook.append_page(p, gtk.Label("info"))
        self.cache_calc = None
        if cache.was_downloaded():
        
            # desc
            p = hildon.PannableArea()
            vp = gtk.Viewport()
            p.add(vp)
            widget_description = gtk.Label()
            widget_description.set_line_wrap(True)
            widget_description.set_alignment(0, 0)
            widget_description.set_size_request(self.window.size_request()[0] - 10, -1)
            vp.add(widget_description)

            notebook.append_page(p, gtk.Label("description"))
            text_shortdesc = self._strip_html(cache.shortdesc)
            if cache.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
                text_shortdesc = 'This Cache is not available!\n' + text_shortdesc
            text_longdesc = self._strip_html(re.sub(r'(?i)<img[^>]+?>', ' [to get all images, re-download description] ', re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: self._replace_image_callback(a, cache), cache.desc)))

            if text_longdesc == '':
                text_longdesc = '(no Description available)'
            if not text_shortdesc == '':
                showdesc = text_shortdesc + "\n\n" + text_longdesc
            else:
                showdesc = text_longdesc
            widget_description.set_text(showdesc)

            # logs&hints
            p = hildon.PannableArea()
            vp = gtk.Viewport()
            p.add(vp)
            widget_hints = gtk.Label()
            widget_hints.set_line_wrap(True)
            widget_hints.set_alignment(0, 0)
            widget_hints.set_size_request(self.window.size_request()[0] - 10, -1)

            def reorder_description(portrait):
                widget_description.set_size_request(self.window.size_request()[0] - 10, -1)
                widget_hints.set_size_request(self.window.size_request()[0] - 10, -1)
            self.reorder_functions.append(reorder_description)

            vp.add(widget_hints)
            notebook.append_page(p, gtk.Label("logs & hints"))

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
                text_hints = 'No Logs.\n\n'
            text_hints += "Hints:\n%s" % cache.hints
            widget_hints.set_text(text_hints)

            # images
            
            if len(cache.get_images()) > 0:
                self.build_cache_images(cache, notebook)

            # calculated coords
            text = text_longdesc
            for w in cache.get_waypoints():
                text += " | " + w['comment']
            self.cache_calc = coordfinder.CalcCoordinateManager(cache, text)
            if len(self.cache_calc.coords) > 0:
                self.build_cache_calc(cache, notebook)

        # coords


        p = gtk.VBox()
        #self.build_coordinates(cache, p)
        self.cache_coord_page = p
        x = notebook.get_n_pages()
        notebook.append_page(p, gtk.Label("coords"))
        def switchpage(caller, page, pageno):
            if pageno != x:
                return
            cache.notes = self.get_cache_notes()
            self.update_coords()
        notebook.connect("switch-page", switchpage)

        # notes
        pan = hildon.PannableArea()
        pan.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        self.cache_notes = gtk.TextView()
        #cache_notes.set_editable(True)
        self.cache_notes.get_buffer().set_text(cache.notes)
        pan.add(self.cache_notes)

        self.notes_changed = False
        def notes_changed(caller):
            self.notes_changed = True
        self.cache_notes.get_buffer().connect('changed', notes_changed)

        def add_waypoint(widget):
            if self.gps_data != None and self.gps_data.position != None:
                c = self.gps_data.position
            elif self.current_target != None:
                c = self.current_target
            else:
                c = geo.Coordinate(0, 0)
            res = self.show_coordinate_input(c)
            text = "\n%s\n" % res.get_latlon(self.format)
            self.cache_notes.get_buffer().insert(self.cache_notes.get_buffer().get_end_iter(), text)
                

        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Add Waypoint")
        button.connect("clicked", add_waypoint)

        p = gtk.VBox()
        p.pack_start(button, False)
        p.pack_start(pan, True)
        notebook.append_page(p, gtk.Label("notes"))
        
        notebook_switcher = gtk.HBox(True)

        def switch_nb(widget, forward):
            if forward:
                notebook.next_page()
            else:
                notebook.prev_page()
        for label, fwd in (('<-', False), ('->', True)):
            nb = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
            nb.set_label(label)
            nb.connect('clicked', switch_nb, fwd)
            notebook_switcher.pack_start(nb)
        details = gtk.VBox()
        details.pack_start(notebook)
        details.pack_start(notebook_switcher, False)

        def reorder_details(portrait):
            notebook.set_property('show-tabs', not portrait)
            if portrait:
                notebook_switcher.show()
            else:   
                notebook_switcher.hide()
        self.reorder_functions.append(reorder_details)
        
        def destroy(obj):
            self.reorder_functions.remove(reorder_details)
            try:
                self.reorder_functions.remove(reorder_description)
            except NameError:
                pass
        win.connect('destroy', destroy)

        win.add(details)
        
        # menu
        menu = hildon.AppMenu()
        widget_marked = hildon.CheckButton(gtk.HILDON_SIZE_AUTO)
        widget_marked.set_label("marked")
        widget_marked.set_active(cache.marked)
        widget_marked.connect("clicked", self._on_cache_marked_toggle, None)
        menu.append(widget_marked)
        
        ### großschreibung

        
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Download all Details")
        button.connect("clicked", self._on_download_cache_clicked, None)
        menu.append(button)
    
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Set as Target")
        button.connect("clicked", self._on_set_target_clicked, cache)
        menu.append(button)

        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Show on Map")
        button.connect("clicked", self._on_show_on_map, cache)
        menu.append(button)
    
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button.set_label("Write Fieldnote")
        button.connect("clicked", self._on_show_log_fieldnote_dialog, None)
        menu.append(button)
        menu.show_all()
        
        win.set_app_menu(menu)        
        win.show_all()

        self.__configure_root(win, None)


        win.connect('delete_event', self.hide_cache_view)
        self.current_cache_window_open = True

    def build_coordinates(self, cache, p):

        def show_details(widget_coords, stuff, clist):
            tm = widget_coords.get_model(0)
            iter = tm.get_iter(0)
            widget_coords.get_selected(0, iter)
            c = clist[tm.get_path(iter)[0]]
            if c == None:
                return
            self.__show_coordinate_details(c, cache)
        widget_coords, clist = self._get_coord_selector(cache, show_details)


        p.pack_start(widget_coords, True, True)
        widget_coords.show_all()

    def __show_coordinate_details(self, c, cache):
        RESPONSE_AS_TARGET, RESPONSE_AS_MAIN = range(2)
        name = "Coordinate Details" if (c.name == "") else c.name
        dialog = gtk.Dialog(name, None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        if c.lat != None:
            dialog.add_button("as Target", RESPONSE_AS_TARGET)
            dialog.add_button("as Main Coord.", RESPONSE_AS_MAIN)
        lbl = gtk.Label()
        lbl.set_markup("<b>%s</b>\n%s" % (c.get_latlon(self.format) if c.lat != None else '???', c.comment))        
        lbl.set_line_wrap(True)
        lbl.set_alignment(0, 0.5)
        dialog.vbox.pack_start(lbl)
        dialog.show_all()
        resp = dialog.run()
        dialog.hide()
        if resp == RESPONSE_AS_TARGET:
            self.set_current_cache(cache)
            self.set_target(c)
            self.hide_cache_view()
        elif resp == RESPONSE_AS_MAIN:
            self.core.set_alternative_position(cache, c)


    def update_coords(self):
        for x in self.cache_coord_page.get_children():
            self.cache_coord_page.remove(x)
        self.build_coordinates(self.current_cache, self.cache_coord_page)
        self.cache_coord_page.show()

    def build_cache_images(self, cache, notebook):
        selector = hildon.TouchSelector(text=True)
        selector.get_column(0).get_cells()[0].set_property('xalign', 0)
        selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)


        imagelist = self.current_cache.get_images().items()
        imagelist.sort(cmp=lambda x, y: cmp(x[1], y[1]))
        i = 1
        for filename, caption in imagelist:
            if len(caption) == 0:
                caption = "(no caption)"
            text = "#%d: %s" % (i, caption)
            i += 1
            selector.append_text(text)


        def on_imagelist_clicked(widget, data):
            tm = widget.get_model(0)
            iter = tm.get_iter(0)
            widget.get_selected(0, iter)
            path, caption = imagelist[tm.get_path(iter)[0]]
            self._on_show_image(path, caption)

        selector.connect("changed", on_imagelist_clicked)

        notebook.append_page(selector, gtk.Label("images"))

    def build_cache_calc(self, cache, notebook):

        def input_changed(widget, char):
            self.cache_calc.set_var(char, widget.get_text())
            self.show_cache_calc_results()

        p = gtk.VBox()
        count = len(self.cache_calc.requires)
        # create table with n columns.
        cols = 7
        rows = int(ceil(float(count) / float(cols)))
        table = gtk.Table(rows, cols)
        i = 0
        requires_sort = list(self.cache_calc.requires)
        requires_sort.sort()
        for char in requires_sort:
            row = i / cols
            col = i % cols
            m = gtk.HBox()
            m.pack_start(gtk.Label(str(char)))
            e = hildon.Entry(gtk.HILDON_SIZE_AUTO)
            e.set_property("hildon-input-mode", gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
            if char in self.cache_calc.vars.keys():
                e.set_text(self.cache_calc.vars[char])
            e.connect('changed', input_changed, str(char))
            e.set_size_request(50, -1)
            m.pack_start(e)
            table.attach(m, col, col + 1, row, row + 1)
            i += 1
        p.pack_start(table, False)
        p.pack_start(gtk.HSeparator(), False)
        a = hildon.PannableArea()
        vp = gtk.Viewport()
        a.add(vp)
        p.pack_start(a, True)
        self.cache_calc_viewport = vp
        self.show_cache_calc_results()
        notebook.append_page(p, gtk.Label("calc"))

    def show_cache_calc_results(self):
        p = gtk.VBox()
        
        for c in self.cache_calc.coords:
            if len(c.requires) == 0:
                continue
            label_text = '<b>%s</b>\n' % c.orig
            button = None
            if c.has_requires():
                label_text += '= %s\n' % c.replaced_result
                if c.result != False:
                    label_text += '= %s\n' % c.result
                for warning in c.warnings:
                    label_text += "<b>!</b> <span color='gold'>%s</span>\n" % warning
            else:
                label_text += "<i>Needs "
                for r in c.requires:
                    if r in self.cache_calc.vars.keys():
                        label_text += "<s>%s </s>" % r
                    else:
                        label_text += "<b>%s </b>" % r
                label_text += "</i>\n"

            b = gtk.Table(2, 1)
            l = gtk.Label()
            l.set_alignment(0, 0.5)
            l.set_markup(label_text)
            b.attach(l, 0, 1, 0, 2, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL)
            if button != None:
                b.attach(button, 1, 2, 1, 2, 0, 0)
            p.pack_start(b, False)
            p.pack_start(gtk.HSeparator(), False)
            
        for x in self.cache_calc_viewport.get_children():
            self.cache_calc_viewport.remove(x)
        self.cache_calc_viewport.add(p)
        self.cache_calc_viewport.show_all()

        
    def _on_show_image(self, dpath, caption):
        fullpath = path.join(self.settings['download_output_dir'], dpath)
        if not path.exists(fullpath):
            print "file does not exist: " + fullpath
            return
        win = hildon.StackableWindow()
        win.set_title(caption)
        p = hildon.PannableArea()
        p.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        vp = gtk.Viewport()
        p.add(vp)
        i = gtk.Image()
        i.set_from_file(fullpath)
        i.set_pixel_size(3)
        win.add(p)
        vp.add(i)
        win.show_all()

    @staticmethod
    def wrap(text, width):
        """
        A word-wrap function that preserves existing line breaks
        and most spaces in the text. Expects that existing line
        breaks are posix newlines (\n).
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
                      (line,
                      ' \n'[(len(line)-line.rfind('\n')-1
                      + len(word.split('\n', 1)[0]
                      ) >= width)],
                      word),
                      text.split(' ')
                      )

    def _get_coord_selector(self, cache, callback, no_empty=False):
        selector = hildon.TouchSelector(text=True)
        selector.get_column(0).get_cells()[0].set_property('xalign', 0)
        selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
        format = lambda n: "%s %s" % (re.sub(r' ', '', n.get_lat(self.format)), re.sub(r' ', '', n.get_lon(self.format)))
        selector.append_text("First Waypoint: %s" % format(cache))
        cache.comment = "Original coordinate given in the cache description."
        clist = {0: cache}
        i = 1
        for w in cache.get_waypoints():
            if not (w['lat'] == -1 and w['lon'] == -1):
                coord = geo.Coordinate(w['lat'], w['lon'], w['name'])
                coord.comment = self._strip_html(w['comment'])
                latlon = format(coord)
            elif no_empty:
                continue
            else:
                coord = geo.Coordinate(None, None, w['name'])
                coord.comment = self._strip_html(w['comment'])
                latlon = '???'
            text = self.wrap("%s - %s - %s\n%s" % (w['name'], latlon, w['id'], self._strip_html(w['comment'])), 80)
            selector.append_text(text)
            clist[i] = coord
            i += 1
        
        for coord in geo.search_coordinates(cache.notes):
            selector.append_text("manually entered: " + format(coord))
            coord.comment = "This coordinate was manually entered in the notes field."
            clist[i] = coord
            i += 1
        if self.cache_calc != None:
            for coord in self.cache_calc.get_solutions():
                if coord == False:
                    continue
                selector.append_text("calculated: %s = %s" % (coord.name, format(coord)))
                coord.comment = "This coordinate was calculated:\n%s = %s" % (coord.name, format(coord))
                clist[i] = coord
                i += 1
            for coord in self.cache_calc.get_plain_coordinates():
                if coord == False:
                    continue
                selector.append_text("found: %s" % (coord.name, format(coord)))
                coord.comment = "This coordinate was found in the description."
                clist[i] = coord
                i += 1

        

        selector.connect('changed', callback, clist)
        return selector, clist


    def _on_download_cache_clicked(self, some, thing):
        self.core.on_download_cache(self.current_cache)

    def _on_cache_marked_toggle(self, widget, data):
        if self.current_cache == None:
            return
        self._update_mark(self.current_cache, widget.get_active())

    def _on_show_cache_details(self, widget, data, touched=None):
        self.show_cache(self.current_cache)

    def set_active_page(self, show_gps):
        self._on_set_active_page(None, show_gps)

    def _on_set_active_page(self, widget, show_gps):

        if show_gps:
            self.main_gpspage.show()
            self.main_mappage.hide()
        else:
            self.main_gpspage.hide()
            self.main_mappage.show()


    def _on_show_on_map(self, widget, data):
        self.set_center(data)
        self.hide_cache_view(None, None)



    @staticmethod
    def _get_selected(widget):
        tm = widget.get_model(0)
        iter = tm.get_iter(0)
        widget.get_selected(0, iter)
        return tm[tm.get_path(iter)[0]]



        ##############################################
        #
        # Signal Handling from Core
        #
        ##############################################


    def _on_cache_changed(self, something, cache):
        if self.current_cache != None \
            and cache.name == self.current_cache.name \
            and self.current_cache_window_open:

            self.hide_cache_view()
            self.old_cache_window = None
            self.show_cache(cache)
            return False
        else:
            return False




        ##############################################
        #
        # /Signal Handling from Core
        #
        ##############################################

        ##############################################
        #
        # Fieldnotes
        #
        ##############################################


    def _on_show_log_fieldnote_dialog(self, widget, data):
        if self.current_cache == None:
            return
        
        statuses = [
            ("Don't upload a fieldnote", geocaching.GeocacheCoordinate.LOG_NO_LOG),
            ("Found it", geocaching.GeocacheCoordinate.LOG_AS_FOUND),
            ("Did not find it", geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND),
            ("Post a note", geocaching.GeocacheCoordinate.LOG_AS_NOTE)
        ]
        
        cache = self.current_cache
        dialog = gtk.Dialog("create fieldnote", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        fieldnotes = hildon.TextView()
        fieldnotes.set_placeholder("Your fieldnote text...")
        fieldnotes.get_buffer().set_text(cache.fieldnotes)

        fieldnotes_log_as_selector = hildon.TouchSelector(text=True)
        
        for text, status in statuses:
            fieldnotes_log_as_selector.append_text(text)
        i = 0
        for text, status in statuses:
            if cache.log_as == status:
                fieldnotes_log_as_selector.select_iter(0, fieldnotes_log_as_selector.get_model(0).get_iter(i), False)
            i += 1
        fieldnotes_log_as = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        fieldnotes_log_as.set_title('Log Type')
        fieldnotes_log_as.set_selector(fieldnotes_log_as_selector)

        dialog.vbox.pack_start(fieldnotes_log_as, False)
        dialog.vbox.pack_start(fieldnotes, True)
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result != gtk.RESPONSE_ACCEPT:
            print 'Not logging this fieldnote'
            return
        from time import gmtime
        from time import strftime

        cache.log_as = statuses[fieldnotes_log_as_selector.get_selected_rows(0)[0][0]][1]
        cache.log_date = strftime('%Y-%m-%d', gmtime())
        cache.fieldnotes = fieldnotes.get_buffer().get_text(fieldnotes.get_buffer().get_start_iter(), fieldnotes.get_buffer().get_end_iter())
        self.core.write_fieldnote(self.current_cache, cache.log_as, cache.log_date, cache.fieldnotes)
        
        
    def _on_upload_fieldnotes(self, some, thing):
        self.core.on_upload_fieldnotes()

    #emitted by core
    def _on_fieldnotes_changed(self, core):
        self.update_fieldnotes_display()
        
    def update_fieldnotes_display(self):
        count = self.core.get_new_fieldnotes_count()
        w = self.button_fieldnotes
        if count == 0:
            w.set_value("Nothing to upload.")
            w.set_sensitive(False)
        else:
            w.set_value("You have %d fieldnotes." % count)
            w.set_sensitive(True)

        ##############################################
        #   
        # /Fieldnotes
        # 
        ##############################################


        ##############################################
        #
        # Current Cache / Current Target / Setting Center
        #
        ##############################################

    def set_center(self, coord, noupdate=False):
        SimpleGui.set_center(self, coord, noupdate)
        self.button_center_as_target.set_value(coord.get_latlon(self.format))

    def set_current_cache(self, cache):
        self.current_cache = cache
        self.button_show_details.set_value(self.shorten_name(cache.title, 25))
        self.button_show_details.set_sensitive(True)
        self.button_show_details_small.set_sensitive(True)

    def _on_set_target_clicked(self, some, cache):
        self.set_target(cache)
        self.hide_cache_view()
        self.set_active_page(True)

    def set_target(self, cache):
        self.current_target = cache
        coord = cache.get_latlon(self.format)
        self.label_target.set_value(coord)
        self.button_goto_target.set_value(coord)
        
        ##############################################
        #
        # Map
        #
        ##############################################

        
    def on_waypoint_clicked(self, listview, event, element):
        if event.type != gtk.gdk._2BUTTON_PRESS or element == None:
            return
        if self.current_cache == None:
            return
        if element[0] == 0:
            self.set_target(self.current_cache)
            self.set_active_page(True)
            self.hide_cache_view()
        else:
            wpt = self.current_cache.get_waypoints()[element[0]-1]
            if wpt['lat'] == -1 or wpt['lon'] == -1:
                return
            self.set_target(geo.Coordinate(wpt['lat'], wpt['lon'], wpt['id']))
            self.set_active_page(True)
            self.hide_cache_view()

    def _drag_end(self, widget, event):
        SimpleGui._drag_end(self, widget, event)
        c = self.ts.num2deg(self.map_center_x, self.map_center_y)
        self.button_center_as_target.set_value(c.get_latlon(self.format))

    def on_zoom_changed(self, blub):
        self.zoom()

    def zoom(self, direction=None):
        size = self.ts.tile_size()
        center = self.ts.num2deg(self.map_center_x - float(self.draw_at_x) / size, self.map_center_y - float(self.draw_at_y) / size)
        if direction == None:
            return
        else:
            newzoom = self.ts.get_zoom() + direction
        self.ts.set_zoom(newzoom)
        self.set_center(center)

        ##############################################
        #
        # /Map
        #
        ##############################################

        ##############################################
        #
        # Displaying Messages and Window Handling
        #
        ##############################################

    def hide_progress(self):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
        if self.banner != None:
            self.banner.hide()
            self.banner = None


    def hide_cache_view(self, widget=None, data=None):
        if self.cache_calc != None:
            self.current_cache.set_vars(self.cache_calc.vars)
            self.core.set_cache_calc_vars(self.current_cache, self.current_cache.vars)
        self.current_cache_window_open = False
        if self.notes_changed:
            self.core.on_notes_changed(self.current_cache, self.get_cache_notes())
            self.notes_changed = False
        self.old_cache_window = hildon.WindowStack.get_default().peek()
        hildon.WindowStack.get_default().pop(hildon.WindowStack.get_default().size()-1)
        return True

    def get_cache_notes(self):
        b = self.cache_notes.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter())
                

    #called by core
    def set_download_progress(self, fraction, text):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)
        if text == '':
            text = 'Please wait...'
        if self.banner == None:
            self.banner = hildon.Banner()
            self.banner.set_text(text)
            self.banner.show_all()
        else:
            self.banner.set_text(text)



    def show_error(self, errormsg):
        #if isinstance(errormsg, Exception):
        #    raise errormsg
        hildon.hildon_banner_show_information(self.window, "", "%s" % errormsg)

    def show_success(self, message):
        hildon.hildon_banner_show_information(self.window, "", message)

        ##############################################
        #
        # /Displaying Messages and Window Handling
        #
        ##############################################



        ##############################################
        #
        # GPS Display
        #
        ##############################################

    def update_gps_display(self):
        if self.gps_data == None:
            #self.osd_string = "<span gravity='west' size='xx-large'>No Fix </span>"
            return

        if self.gps_data.sats == 0:
            text = "No sats, error: ±%3.1fm" % self.gps_data.error
        else:
            text = "%d/%d sats, error: ±%3.1fm" % (self.gps_data.sats, self.gps_data.sats_known, self.gps_data.error)
        self.label_quality.set_markup("Accuracy\n<small>%s</small>" % text)
        if self.gps_data.altitude == None or self.gps_data.bearing == None:
            #self.osd_string = "<span gravity='west' size='xx-large'>No Fix </span>"
            return

        self.label_altitude.set_markup("Altitude\n<small>%d m</small>" % self.gps_data.altitude)
        self.label_bearing.set_markup("Bearing\n<small>%d°</small>" % self.gps_data.bearing)
        self.label_latlon.set_markup("Current Position\n<small>%s</small>" % self.gps_data.position.get_latlon(self.format))

        if self.current_target == None:
            #self.osd_string = ""
            return

        target_distance = self.gps_data.position.distance_to(self.current_target)
        td_string = self.__format_distance(target_distance)
        if self.gps_has_fix:
            self.label_dist.set_markup("<span size='xx-large'>%s</span>" % td_string)

            #self.osd_string = "<span gravity='west' size='xx-large'>%s </span>" % td_string
        else:
            self.label_dist.set_markup("<span size='xx-large'>No Fix</span>")

            #self.osd_string = "<span gravity='west' size='xx-large'>No Fix </span>"

    def __format_distance(self, distance):
        if distance == None:
            return '?'
        if distance >= 1000:
            return "%d km" % round(distance / 1000)
        elif distance >= 100:
            return "%d m" % round(distance)
        else:
            return "%.1f m" % round(distance, 1)



    def on_no_fix(self, gps_data, status):
        self.gps_data = gps_data
        self.label_bearing.set_text("No Fix")
        self.label_latlon.set_text(status)
        self.gps_has_fix = False
        self.update_gps_display()
        self._draw_arrow()
        self.redraw_marks()

               
        ##############################################
        #
        # /GPS Display
        #
        ##############################################

        ##############################################
        #
        # Reading & Writing Settings
        #
        ##############################################

    def read_settings(self):
        settings = self.settings
        c = self.ts.num2deg(self.map_center_x, self.map_center_y)
        settings['map_position_lat'] = c.lat
        settings['map_position_lon'] = c.lon
        settings['map_zoom'] = self.ts.get_zoom()
        
        if self.current_target != None:
            settings['last_target_lat'] = self.current_target.lat
            settings['last_target_lon'] = self.current_target.lon

        for i in ['options_username', 'options_password', 'download_noimages', 'options_show_name', 'options_hide_found']:
            settings[i] = self.settings[i]
        self.settings = settings
        return settings

                
    def write_settings(self, settings):
        self.settings = settings
        self.block_changes = True
        self.ts.set_zoom(self.settings['map_zoom'])
        self.set_center(geo.Coordinate(self.settings['map_position_lat'], self.settings['map_position_lon']))

        if 'last_target_lat' in self.settings.keys():
            self.set_target(geo.Coordinate(self.settings['last_target_lat'], self.settings['last_target_lon'], self.settings['last_target_name']))

        self.block_changes = False

        ##############################################
        #
        # /Reading & Writing Settings
        #
        ##############################################
        
