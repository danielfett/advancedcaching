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

 
# deps: python-html python-image python-netclient python-misc python-pygtk python-mime python-json
 
### For the gui :-)

from math import ceil
from os import extsep
from os import path
from os import system
import re

from astral import Astral
import geo
import geocaching
import gobject
import gtk
import hildon
from utils import HTMLManipulations
from hildon_plugins import HildonFieldnotes
from hildon_plugins import HildonSearchPlace
from hildon_plugins import HildonSearchGeocaches
from hildon_plugins import HildonAboutDialog
from hildon_plugins import HildonDownloadMap
from hildon_plugins import HildonToolsDialog
import pango
from portrait import FremantleRotation
from simplegui import SimpleGui
from simplegui import UpdownRows
from xml.sax.saxutils import escape as my_gtk_label_escape
from gtkmap import Map, OsdLayer, SingleMarkLayer
from coordfinder import CalcCoordinate


import logging
logger = logging.getLogger('simplegui')

class HildonGui(HildonToolsDialog, HildonSearchPlace, HildonFieldnotes, HildonSearchGeocaches, HildonAboutDialog, HildonDownloadMap, SimpleGui):

    USES = ['locationgpsprovider', 'geonames']

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

    TOO_MANY_POINTS = 80
    MAX_NUM_RESULTS_SHOW = 80
    CACHES_ZOOM_LOWER_BOUND = 8

    ICONS = {
        geocaching.GeocacheCoordinate.LOG_TYPE_FOUND: 'found',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTFOUND: 'cross',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTE: 'comment',
        geocaching.GeocacheCoordinate.LOG_TYPE_MAINTENANCE: 'wrench',
        geocaching.GeocacheCoordinate.LOG_TYPE_PUBLISHED: 'accept',
        geocaching.GeocacheCoordinate.LOG_TYPE_DISABLED: 'delete',
        geocaching.GeocacheCoordinate.LOG_TYPE_ARCHIVED: 'traffic_cone',
        geocaching.GeocacheCoordinate.LOG_TYPE_NEEDS_MAINTENANCE: 'error',
        geocaching.GeocacheCoordinate.LOG_TYPE_WILLATTEND: 'calendar_edit',
        geocaching.GeocacheCoordinate.LOG_TYPE_ATTENDED: 'group',
        geocaching.GeocacheCoordinate.LOG_TYPE_UPDATE: 'asterisk_yellow',
    }

    ICONPATH='/usr/share/icons/hicolor/%(size)dx%(size)d/hildon/%(name)s.png'


    CACHE_DRAW_SIZE = 13
    CACHE_DRAW_FONT = pango.FontDescription("Nokia Sans Maps 10")

    def __init__(self, core, dataroot):
        gtk.gdk.threads_init()
        self._prepare_images(dataroot)
        
        self.core = core
        self.core.connect('map-marks-changed', self._on_map_changed)
        self.core.connect('cache-changed', self._on_cache_changed)
        self.core.connect('target-changed', self._on_target_changed)
        self.core.connect('good-fix', self._on_good_fix)
        self.core.connect('no-fix', self._on_no_fix)
        self.core.connect('settings-changed', self._on_settings_changed)
        self.core.connect('save-settings', self._on_save_settings)
        self.core.connect('error', lambda caller, message: self.show_error(message))
        self.core.connect('progress', lambda caller, fraction, text: self.set_progress(fraction, text))
        self.core.connect('hide-progress', lambda caller: self.hide_progress())

        self.settings = {}

        self.format = geo.Coordinate.FORMAT_DM

        Map.set_config(self.core.settings['map_providers'], self.core.settings['download_map_path'], self.noimage_cantload, self.noimage_loading)
        OsdLayer.set_layout(pango.FontDescription("Nokia Sans Maps 13"), gtk.gdk.color_parse('black'))
        

        self.current_cache = None
        self.current_cache_window_open = False
                
        self.gps_data = None
        self.gps_has_fix = False
        self.gps_last_good_fix = None
        self.gps_last_screen_position = (0, 0)
        self.banner = None
        self.old_cache_window = None
        self.cache_calc_vars = {}

                
        self.north_indicator_layout = None
        self.notes_changed = False
        
        gtk.set_application_name("Geocaching Tool")
        program = hildon.Program.get_instance()
        self.window = hildon.StackableWindow()
        program.add_window(self.window)
        self.window.connect("delete_event", self.on_window_destroy, None)
        self.window.add(self._create_main_view())
        self.window.set_app_menu(self._create_main_menu())

        gtk.link_button_set_uri_hook(self._open_browser)
        
        self.rotation_manager = FremantleRotation('advancedcaching', main_window = self.window)

        self.astral = Astral()
        
        self.plugin_init()

    def plugin_init(self):
        for x in (HildonSearchGeocaches, HildonSearchPlace, HildonFieldnotes, HildonAboutDialog, HildonToolsDialog):
            x.plugin_init(self)

    def on_window_destroy(self, target, more=None, data=None):
        hildon.hildon_gtk_window_take_screenshot(self.window, True)
        SimpleGui.on_window_destroy(self, target, more, data)

    def _prepare_images(self, dataroot):
        p = "%s%s%%s" % (path.join(dataroot, '%s'), extsep)
        self.noimage_cantload = p % ('noimage-cantload', 'png')
        self.noimage_loading = p % ('noimage-loading', 'png')

        #MarksLayer.load_image_target(p % ('target', 'png'))

        out = {}

        for key, name in self.ICONS.items():
            out[key] = gtk.gdk.pixbuf_new_from_file(p % (name, 'png'))
        self.icon_pixbufs = out

        self.image_icon_add = self.ICONPATH % {'size' : 64, 'name':'general_add'}
        self.image_zoom_in = gtk.image_new_from_file(self.ICONPATH % {'size' : 48, 'name':'pdf_zoomin'})
        self.image_zoom_out = gtk.image_new_from_file(self.ICONPATH % {'size' : 48, 'name':'pdf_zoomout'})
        self.image_action = gtk.image_new_from_file(self.ICONPATH % {'size' : 64, 'name':'keyboard_menu'})
        self.image_preferences = gtk.image_new_from_file(self.ICONPATH % {'size' : 48, 'name':'camera_camera_setting'})
        self.image_info = gtk.image_new_from_file(self.ICONPATH % {'size' : 48, 'name':'general_information'})
        self.image_left = self.ICONPATH % {'size' : 48, 'name':'general_back'}
        self.image_right = self.ICONPATH % {'size' : 48, 'name':'general_forward'}


    def _open_browser(self, widget, link):
        system("dbus-send --print-reply --dest=com.nokia.osso_browser /com/nokia/osso_browser/request com.nokia.osso_browser.open_new_window 'string:%s' &" % link)

    def show_coordinate_input(self, start, none_on_cancel = False, show_name_input = False):
        udr = UpdownRows(self.format, start, True)
        dialog = gtk.Dialog("Edit Target", self.window, gtk.DIALOG_MODAL, ("OK", gtk.RESPONSE_ACCEPT))
        if show_name_input:
            e = hildon.Entry(gtk.HILDON_SIZE_AUTO)
            dialog.vbox.pack_start(e)
            e.set_text(start.name)

        dialog.set_size_request(-1, 480)
        dialog.vbox.pack_start(udr.table_lat)
                
        dialog.vbox.pack_start(udr.table_lon)
                
        dialog.show_all()
        res = dialog.run()
        dialog.destroy()
        if res == gtk.RESPONSE_ACCEPT:
            c = udr.get_value()
            if show_name_input:
                c.name = e.get_text()
            else:
                c.name = 'manual'
            return c
        elif none_on_cancel:
            return None
        else:
            return start


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

        def reorder_gps(widget, event):
            widget = self.main_gpspage
            portrait = (event.width < event.height)
            x = self.drawing_area_arrow.get_parent()
            if x != None:
                x.remove(self.drawing_area_arrow)

            x = self.main_gpspage_table.get_parent()
            if x != None:
                x.remove(self.main_gpspage_table)

            for x in widget.get_children():
                widget.remove(x)

            if portrait: 
                widget.pack_start(self.drawing_area_arrow, True)
                widget.pack_start(self.main_gpspage_table, False)
            else:
                landscape_hbox = gtk.HBox(True)
                landscape_hbox.pack_start(self.drawing_area_arrow, True)
                landscape_hbox.pack_start(self.main_gpspage_table, True)
                widget.pack_start(landscape_hbox)
                landscape_hbox.show()

        self.window.connect('configure-event', reorder_gps)
        #self.main_gpspage.add_events(gtk.gdk.STRUCTURE_MASK)

        self.main_gpspage.pack_start(self.main_gpspage_table, False, True)
        
        self.main_mappage = gtk.VBox()
        self._configure_map()

        buttons = gtk.HBox()

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_image(self.image_action)
        button.connect("clicked", self._on_show_actions_clicked, None)
        buttons.pack_start(button, True, True)

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_image(self.image_preferences)
        button.connect("clicked", self._on_show_preferences, None)
        buttons.pack_start(button, True, True)



        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_image(self.image_zoom_in)
        button.connect("clicked", self.on_zoomin_clicked, None)
        self.button_zoom_in = button
        buttons.pack_start(button, True, True)

        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_image(self.image_zoom_out)
        button.connect("clicked", self.on_zoomout_clicked, None)
        self.button_zoom_out = button
        buttons.pack_start(button, True, True)


        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Show Details")
        button.set_value('No Cache selected')
        button.set_sensitive(False)
        button.connect("clicked", self._on_show_cache_details, None)
        buttons.pack_start(button, True, True)
        self.button_show_details = button

        button_replace = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button_replace.set_image(self.image_info)
        button_replace.connect("clicked", self._on_show_cache_details, None)
        buttons.pack_start(button_replace, True, True)

        def reorder_main(widget, event):
            portrait = (event.width < event.height)
            if not portrait:
                button_replace.hide()
                self.button_show_details.show()
                buttons.set_homogeneous(False)
            else:
                button_replace.show()
                self.button_show_details.hide()
                buttons.set_homogeneous(True)
        self.window.connect('configure-event', reorder_main)


        button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("GPS")
        button.connect("clicked", self._on_set_active_page, True)
        buttons.pack_start(button, True, True)
        
        #self.main_mappage.pack_start(self.drawing_area, True)
        pan = hildon.PannableArea()
        pan.add(self.map)

        self.main_mappage.pack_start(pan, True)
        self.main_mappage.pack_start(buttons, False)
        root.pack_start(self.main_gpspage, True)
        root.pack_start(self.main_mappage, True)



        # arrow drawing area
        
        self.drawing_area_arrow.connect("expose_event", self._expose_event_arrow)
        self.drawing_area_arrow.connect("configure_event", self._configure_event_arrow)
        self.drawing_area_arrow.set_events(gtk.gdk.EXPOSURE_MASK)

        return root

    def _create_main_menu(self):
        menu = hildon.AppMenu()
    
        sel_tiles = hildon.TouchSelector(text=True)
        for name, loader in self.map.tile_loaders:
            sel_tiles.append_text(name)
        pick_tiles = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        pick_tiles.set_selector(sel_tiles)
        pick_tiles.set_title("Map Style")
        pick_tiles.set_active(0)
        pick_tiles.connect('value-changed', lambda widget: self.map.set_tile_loader(self.map.tile_loaders[widget.get_active()][1]))
        menu.append(pick_tiles)

        menu.append(self._get_search_place_button())
        
        menu.append(self._get_search_button())

        menu.append(self._get_about_button())

        menu.append(self._get_download_map_button())
        
        menu.append(self._get_tools_button())

    
        



        menu.show_all()
        return menu

    def _on_show_actions_clicked(self, caller, event):
        dialog = gtk.Dialog("Actions Menu", self.window, gtk.DIALOG_MODAL, ())

        buttons = []

        if self.core.current_position != None:
            button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_title("Go to my Position")
            button.set_value(self.core.current_position.get_latlon(self.format))
            button.connect("clicked", lambda caller: self.set_center(self.core.current_position))
            button.connect("clicked", lambda caller: dialog.hide())
        else:
            button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
            button.set_title("Go to my Position")
            button.set_value('Not available')
            button.set_sensitive(False)
        buttons.append(button)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Go to Target")
        button.set_value(self.core.current_target.get_latlon(self.format))
        button.connect("clicked", self.on_show_target_clicked, None)
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)

        c = self.map.get_center()
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Use Center as Target")
        button.set_value(c.get_latlon(self.format))
        button.connect("clicked", self.on_set_target_center, None)
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)
        self.button_center_as_target = button

        button = self._get_fieldnotes_button()
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Overview")
        button.set_value("for the visible area")
        button.connect("clicked", self.on_download_clicked)
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Details")
        button.set_value("for all visible caches")
        button.connect("clicked", self.on_download_details_map_clicked)
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)


        self.make_rearranging_table(buttons, dialog)
        dialog.show_all()
        dialog.run()
        dialog.hide()


    def _on_show_preferences(self, caller, event):
        dialog = gtk.Dialog("Quick Settings", self.window, gtk.DIALOG_MODAL, ())

        buttons = []
        
        button = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        button.set_label("Follow Position")
        button.set_active(self._get_track_mode())
        button.connect("clicked", self.on_track_toggled, None)
        buttons.append(button)

        check_map_double_size = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_map_double_size.set_label("Show Map in double size")
        check_map_double_size.set_active(self.settings['options_map_double_size'])
        buttons.append(check_map_double_size)

        tts_button, tts_get_result = self._get_tts_settings()
        buttons.append(tts_button)

        rotate_button, rotate_get_result = self._get_rotate_settings()
        buttons.append(rotate_button)



        check_hide_found = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_hide_found.set_label("Hide Found Geocaches")
        check_hide_found.set_active(self.settings['options_hide_found'])
        buttons.append(check_hide_found)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("more Settings")
        button.connect("clicked", self._on_show_settings_dialog, None)
        button.connect("clicked", lambda caller: dialog.hide())
        buttons.append(button)

        self.make_rearranging_table(buttons, dialog)
        dialog.show_all()
        dialog.run()
        dialog.hide()

        logger.debug("Setting 'Hide Found Geocaches' to %s" % check_hide_found.get_active())
        update = {
            'tts_interval': tts_get_result(),
            'options_rotate_screen': rotate_get_result(),
            'options_map_double_size': check_map_double_size.get_active(),
            'options_hide_found': check_hide_found.get_active(),
        }
        self.settings.update(update)
        self.core.save_settings(update, self)
 
    def make_rearranging_table(self, elements, dialog, columns = 2):
        count = len(elements)
        container = gtk.VBox()

        def reorder_table(widget, event):
            portrait = (event.width < event.height)
            if portrait:
                real_cols = 1
            else:
                real_cols = columns
            for table in container.get_children():
                for x in table.get_children():
                    table.remove(x)
                container.remove(table)
            table = gtk.Table(int(ceil(count/float(real_cols))), real_cols, True)
            i = 0
            for x in elements:
                table.attach(x, i % real_cols, i % real_cols + 1, i//real_cols, i//real_cols + 1)
                i += 1
            container.pack_start(table, False)
            container.show_all()
        id = self.window.connect('configure-event', reorder_table)

        dialog.connect('hide', lambda widget: self.window.disconnect(id))
        dialog.vbox.pack_start(container)
        reorder_table(None, self.window.get_allocation())

    def show(self):
        self.window.show_all()
        self.set_active_page(False)
        gtk.main()

        
    def _on_show_settings_dialog(self, widget, data):
        dialog = gtk.Dialog("Settings", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.set_size_request(800, 480)

        p = hildon.PannableArea()
        list = gtk.VBox()
        p.add_with_viewport(list)
        dialog.vbox.pack_start(p, True)

        c_size = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        username = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        username.set_text(self.settings['options_username'])
        list.pack_start(hildon.Caption(c_size, "Username", username, None, hildon.CAPTION_MANDATORY))
        
        password = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        password.set_visibility(False)
        password.set_text(self.settings['options_password'])
        list.pack_start(hildon.Caption(c_size, "Password", password, None, hildon.CAPTION_MANDATORY))

        

        
        list.pack_start(gtk.Label('Display'))
        check_show_cache_id = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_show_cache_id.set_label("Show Geocache Name on Map")
        check_show_cache_id.set_active(self.settings['options_show_name'])
        list.pack_start(check_show_cache_id)

        #check_map_double_size = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        #check_map_double_size.set_label("Show Map in double size")
        #check_map_double_size.set_active(self.settings['options_map_double_size'])
        #list.pack_start(check_map_double_size)

        #check_hide_found = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        #check_hide_found.set_label("Hide Found Geocaches on Map")
        #check_hide_found.set_active(self.settings['options_hide_found'])
        #list.pack_start(check_hide_found)

        check_show_html_description = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_show_html_description.set_label("Show Cache Description with HTML")
        check_show_html_description.set_active(self.settings['options_show_html_description'])
        list.pack_start(check_show_html_description)

        #rotate_button, rotate_get_result = self._get_rotate_settings()
        #list.pack_start(rotate_button)

        #list.pack_start(gtk.Label('TTS Settings'))
        #tts_button, tts_get_result = self._get_tts_settings()
        #list.pack_start(tts_button)

        list.pack_start(gtk.Label('Other'))

        check_dl_images = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        check_dl_images.set_label("Don't Download Images")
        check_dl_images.set_active(self.settings['download_noimages'])
        list.pack_start(check_dl_images)
        
        
        auto_update = hildon.CheckButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
        auto_update.set_label("Update cache parser on startup")
        auto_update.set_active(self.settings['options_auto_update'])
        list.pack_start(auto_update)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("Change default fieldnote text")
        button.connect("clicked", self._show_default_log_text_settings, None)
        #button.connect("clicked", lambda caller: dialog.hide())
        list.pack_start(button)
        
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result != gtk.RESPONSE_ACCEPT:
            return
        if self.settings['options_show_html_description'] != check_show_html_description.get_active():
            self.old_cache_window = None
            
        update = {
                 'options_username': username.get_text(),
                 'options_password': password.get_text(),
                 'download_noimages': check_dl_images.get_active(),
                 'options_show_name': check_show_cache_id.get_active(),
                 'options_auto_update': auto_update.get_active(),
                 #'options_map_double_size': check_map_double_size.get_active(),
                 #'options_hide_found': check_hide_found.get_active(),
                 'options_show_html_description': check_show_html_description.get_active(),
                 #'options_rotate_screen': rotate_get_result(),
                 #'tts_interval':tts_get_result(),
                 }
        self.settings.update(update)
        self.core.save_settings(update, self)
        #self.core.on_userdata_changed(self.settings['options_username'], self.settings['options_password'])
    
    def _show_default_log_text_settings(self, widget, data):
        dialog = gtk.Dialog("Default Fieldnote Text", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        default_log_text = hildon.TextView()
        default_log_text.get_buffer().set_text(self.settings['options_default_log_text'])
        dialog.vbox.pack_start(default_log_text)
        l = gtk.Label()
        l.set_alignment(0, 0.5)
        l.set_markup("<b>Placeholders:</b>\n%(machine)s = device name\n%c = Date and Time, %x = Date, %X = Time\nand more, just search the web for <i>strftime</i>.")
        dialog.vbox.pack_start(l)
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        
        if result != gtk.RESPONSE_ACCEPT:
            return
        text = default_log_text.get_buffer().get_text(default_log_text.get_buffer().get_start_iter(), default_log_text.get_buffer().get_end_iter())
        update = {'options_default_log_text' : text}
        self.settings.update(update)
        self.core.save_settings(update, self)
        
            
            
    def _get_tts_settings(self):
        tts_settings = (
                        (0, 'Off'),
                        (-1, 'Automatic'),
                        (10, '10 Seconds'),
                        (20, '20 Seconds'),
                        (30, '30 Seconds'),
                        (50, '50 Seconds'),
                        (100, '100 Seconds'),
                        (180, '3 Minutes'),
                        (5 * 60, '5 Minutes'),
                        (10 * 60, '10 Minutes'),
                        )
        tts_selector = hildon.TouchSelector(text=True)

        i = 0
        for seconds, text in tts_settings:
            tts_selector.append_text(text)
            if self.settings['tts_interval'] == seconds:
                tts_selector.select_iter(0, tts_selector.get_model(0).get_iter(i), False)
            i += 1

        tts_button = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        tts_button.set_title('TTS interval')
        tts_button.set_selector(tts_selector)
        tts_get_result = lambda: tts_settings[tts_selector.get_selected_rows(0)[0][0]][0]
        return tts_button, tts_get_result

    def _get_rotate_settings(self):
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
        rotate_get_result = lambda: rotate_settings[rotate_selector.get_selected_rows(0)[0][0]][0]
        return rotate_screen, rotate_get_result

    def _on_show_dialog_change_target(self, widget, data):
        c = self._get_best_coordinate(self.core.current_target)
        res = self._show_target_input_list(c)
        if res != None: 
            self.set_target(res)
        
    def _show_target_input_list(self, start, show_current = False):
        dialog = gtk.Dialog("change target", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        
        RESPONSE_CURRENT = 2
        current = None
        if self.gps_data != None and self.gps_data.position != None:
            current = self.gps_data.position
            dialog.add_button("current position", RESPONSE_CURRENT)    
            
        bar_label = gtk.Label("Lat/Lon: ")
        bar_entry = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        bar_entry.set_property('hildon-input-mode', gtk.HILDON_GTK_INPUT_MODE_ALPHA | gtk.HILDON_GTK_INPUT_MODE_SPECIAL | gtk.HILDON_GTK_INPUT_MODE_TELE)
        bar_entry.set_text(start.get_latlon(self.format))

        def show_coord_input(widget):
            try:
                m = geo.try_parse_coordinate(bar_entry.get_text())
            except Exception:
                m = start
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
            coord = clist[self._get_selected_pos(widget)]
            bar_entry.set_text(coord.get_latlon(self.format))

        if self.current_cache != None:
            sel, clist = self._get_coord_selector(self.current_cache, sel_coord, True)
            sel.set_size_request(-1, 200)
            dialog.vbox.pack_start(sel)
        
        
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result == gtk.RESPONSE_ACCEPT:
            return geo.try_parse_coordinate(bar_entry.get_text())
        elif result == RESPONSE_CURRENT and current != None:
            return current
        return None
        
    def _on_show_more_logs(self, widget, logs, events):
        '''
        This is callback for button 'show all logs'. Will start new dialog with tabs
        '''
        #print "Show all logs:", len(logs)
        dialog = gtk.Dialog("All logs", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, None)
        dialog.set_decorated(False)    #No need for title, hide it.
        dialog.set_size_request(800, 800) #this is needed

        logs_in_page = 30  #how many logs in one tab

        #One notebook (tab-set) inside this dialog
        notebook = gtk.Notebook()
        dialog.vbox.pack_start(notebook)

        number_of_tabs = (len(logs)-10)/(float(logs_in_page))   #subtract 10 because they are visible in basic view
        number_of_tabs = int(round(number_of_tabs+0.49999))     #round up
        #print "Number of needed tabs:", number_of_tabs

        for tab_number in range(number_of_tabs):
            #Each tab has own pannable-area
            panArea = hildon.PannableArea()
            panArea.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)

            #Page=tab
            page = gtk.VBox()

            #logs are counted from zero (as it is array)
            first_log = 10 + tab_number*logs_in_page #10=number of logs shown in basic view
            last_log = first_log + logs_in_page
            if last_log >= len(logs):
               last_log = len(logs)
            label = str(first_log+1) +"-"+ str(last_log) #add 1 to showing first log, so they are more human readable
            notebook.append_page(page, gtk.Label(label))

            content = self._generate_list_of_logs(logs[first_log:last_log],events,True)
            #content inside pannable. pannable inside page.
            panArea.add_with_viewport(content)
            page.pack_start(panArea)


        dialog.show_all()
        dialog.run() #this will prevent multiple dialogs to open


    def show_cache(self, cache, select=True):
        if cache == None:
            return
        if self.current_cache != None and self.current_cache.name == cache.name and self.old_cache_window != None:
            
            hildon.WindowStack.get_default().push_1(self.old_cache_window)
            self.current_cache_window_open = True
            return
        if self.old_cache_window != None:
            self.old_cache_window.destroy()
        
        if select:
            self.set_current_cache(cache)

        
        win = hildon.StackableWindow()
        win.set_title(cache.title)
        events = []

        
        notebook = gtk.Notebook()
        notebook.set_tab_pos(gtk.POS_BOTTOM)
                
        # info
        p = gtk.Table(10, 2)

        #Attributes (images). They are 30x30px. 10 is a maximum of attributes one cache can have
        attribute_table = gtk.HBox()

        #print "list'"+cache.attributes+"'"
        #cache.attributes is comma separated list of filenames without path
        #(ending comma, so drop it with [0,-1]
        for attribute in cache.attributes.split(',')[0:-1]:
            #print attribute
            filename = path.join(self.settings['download_output_dir'], attribute)
            attribute_table.pack_start(gtk.image_new_from_file(filename))


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
            

        #Attributes
        l = gtk.Label()
        l.set_alignment(0, 0.5)
        l.set_markup("<b>Attributes</b>")
        p.attach(l, 0, 1, i, i + 1)
        p.attach(attribute_table, 1, 2, i, i + 1)


        # links for listing & log
        '''
        l = gtk.Label()
        l.set_markup("<b>Open Website</b>")
        l.set_alignment(0, 0.5)
        p.attach(l, 0, 1, 8, 9)
        z = gtk.HBox(True)

        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/cache_details.aspx?wp=%s" % cache.name, 'Listing'))
        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/log.aspx?wp=%s" % cache.name, 'Post Log'))
        z.pack_start(gtk.LinkButton("http://www.geocaching.com/seek/cache_details.aspx?wp=%s&log=y#ctl00_ContentBody_CacheLogs" % cache.name, 'All Logs'))
        p.attach(z, 1, 2, 8, 9)
        '''

        # cache-was-not-downloaded-yet-warning
        if not cache.was_downloaded():
            p.attach(gtk.Label("Please download full details to see the description."), 0, 2, 9, 10)
        
        notebook.append_page(p, gtk.Label("Info"))
        
        if cache.was_downloaded():
            # Description
            p = hildon.PannableArea()
            notebook.append_page(p, gtk.Label("Description"))
            text_longdesc = re.sub(r'(?i)<img[^>]+?>', ' [to get all images, re-download description] ', re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: self._replace_image_callback(a, cache), cache.desc))
            if not self.settings['options_show_html_description']:
                
                widget_description = gtk.Label()
                widget_description.set_line_wrap(True)
                widget_description.set_alignment(0, 0)
                widget_description.set_size_request(self.window.size_request()[0] - 10, -1)
                p.add_with_viewport(widget_description)

                text_shortdesc = my_gtk_label_escape(self._strip_html(cache.shortdesc).strip())
                text_longdesc = my_gtk_label_escape(self._strip_html(text_longdesc).strip())
                
                if cache.status == geocaching.GeocacheCoordinate.STATUS_DISABLED:
                    text_shortdesc = '<u>This Cache is not available!</u>\n%s' % text_shortdesc

                if text_longdesc != '' and text_shortdesc != '':
                    showdesc = "<b>%s</b>\n\n%s" % (text_shortdesc, text_longdesc)
                elif text_longdesc == '' and text_shortdesc == '':
                    showdesc = "<i>No description available</i>"
                elif text_longdesc == '':
                    showdesc = text_shortdesc
                else:
                    showdesc = text_longdesc
                    
                widget_description.set_markup(showdesc)
                events.append(self.window.connect('configure-event', self._on_configure_label, widget_description))
                
            else:
                text_shortdesc = cache.shortdesc
                if text_longdesc != '' and text_shortdesc != '':
                    showdesc = "<b>%s</b><br />%s" % (text_shortdesc, text_longdesc)
                elif text_longdesc == '' and text_shortdesc == '':
                    showdesc = "<i>No description available</i>"
                elif text_longdesc == '':
                    showdesc = text_shortdesc
                else:
                    showdesc = text_longdesc

                import gtkhtml2
                description = gtkhtml2.Document()
                description.clear()
                description.open_stream('text/html')
                description.write_stream('<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head><body>%s</body></html>' % showdesc)
                description.close_stream()
                description.connect('link-clicked', self._open_browser)

                widget_description = gtkhtml2.View()
                widget_description.set_document(description)
                p.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
                p.add(widget_description)
                text_longdesc = self._strip_html(text_longdesc)
           
            # logs&hints
            p = hildon.PannableArea()
            widget_hints = gtk.VBox()
            p.add_with_viewport(widget_hints)
            notebook.append_page(p, gtk.Label("Logs & Hints"))

            hints = cache.hints.strip()
            if len(hints) > 0:
                button_hints = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
                button_hints.set_label('Show Hints (%d chars)' % len(hints))
                label_hints = gtk.Label()
                label_hints.set_line_wrap(True)
                label_hints.set_alignment(0, 0)
                events.append(self.window.connect('configure-event', self._on_configure_label, label_hints))
                label_hints.set_size_request(self.window.size_request()[0] - 10, -1)
                def show_hints(widget):
                    label_hints.set_text(hints)
                    widget.hide()
                button_hints.connect('clicked', show_hints)
                widget_hints.pack_start(button_hints, False, False)
                widget_hints.pack_start(label_hints, False, False)
            else:
                label_hints = gtk.Label()
                label_hints.set_markup('<i>No hints available</i>')
                widget_hints.pack_start(label_hints, False, False)


            logs = cache.get_logs()

            #button for showing list of all logs in another window/dialog
            if len(logs) > 10:
                button_more_logs = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
                button_more_logs .set_label('Show all logs (%d logs more)' % (len(logs)-10) ) #as 10 is already visible
                button_more_logs.connect('clicked', self._on_show_more_logs,logs,events)
                widget_hints.pack_start(button_more_logs, False, False)
            
            content = self._generate_list_of_logs(logs[0:10],events)
            widget_hints.pack_start(content, False, False)
            
            if len(logs) == 0:
                label_logs = gtk.Label()
                label_logs.set_markup('<i>Select "Download all Details" to get logs, waypoints and images.</i>')
                widget_hints.pack_start(label_logs, False, False)
                

            # images
            self.build_cache_images(cache, notebook)

            # calculated coords
            cache_calc_box = gtk.VBox()
            notebook.append_page(cache_calc_box, gtk.Label("Calc"))

            def rebuild_cache_calc():
                cache.start_calc(self._strip_html(text_longdesc))
                self.build_cache_calc(cache, cache_calc_box)

            rebuild_cache_calc()
            self.rebuild_cache_calc = rebuild_cache_calc



        # coords
        p = gtk.VBox()
        self.cache_coord_page = p
        coord_page_number = notebook.get_n_pages()
        notebook.append_page(p, gtk.Label("Coords"))

        # notes
        pan = hildon.PannableArea()
        pan.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        self.cache_notes = gtk.TextView()
        pan.add(self.cache_notes)
        self.cache_notes.get_buffer().set_text(cache.notes)
        self.cache_notes.get_buffer().connect('changed', self.on_notes_changed)
        self.notes_changed = False

        button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL	)
        button.set_title("Add Waypoint")
        button.set_image(gtk.image_new_from_file(self.image_icon_add))
        button.connect("clicked", self._on_add_waypoint_clicked)

        p = gtk.VBox()
        p.pack_start(button, False)
        p.pack_start(pan, True)
        notebook.append_page(p, gtk.Label("Notes"))


        # portrait mode notebook switcher
        notebook_switcher = gtk.HBox(True)
        notebook_switcher.set_no_show_all(True)
        def switch_nb(widget, forward):
            if forward:
                notebook.next_page()
            else:
                notebook.prev_page()
        for label, fwd in ((self.image_left, False), (self.image_right, True)):
            nb = hildon.GtkButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
            nb.set_image(gtk.image_new_from_file(label))
            nb.connect('clicked', switch_nb, fwd)
            notebook_switcher.pack_start(nb)
        details = gtk.VBox()
        details.pack_start(notebook)
        details.pack_start(notebook_switcher, False)


        def on_switch_page(caller, page, pageno):
            if pageno == coord_page_number:
                self.update_coords()
            notebook_switcher.get_children()[0].set_sensitive(pageno != 0)
            notebook_switcher.get_children()[1].set_sensitive(pageno != notebook.get_n_pages() - 1)

        notebook.connect("switch-page", on_switch_page)

        def reorder_details(widget, event=None):
            portrait = (event.width < event.height)

            notebook.set_property('show-tabs', not portrait)
            if portrait:
                notebook_switcher.show_all()
            else:
                notebook_switcher.hide()
        events.append(self.window.connect('configure-event', reorder_details))
        

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
    
        
        menu.append(self._get_write_fieldnote_button())
        menu.show_all()
        
        win.set_app_menu(menu)        
        win.show_all()
        notebook_switcher.set_no_show_all(False)
        reorder_details(None, win.get_allocation())
        def delete_events(widget):
            for x in events:
                self.window.disconnect(x)
        win.connect('delete_event', self.hide_cache_view)
        win.connect('unrealize', delete_events)
        self.current_cache_window_open = True


    def _generate_list_of_logs(self, logs, events, dialog=False):
            '''
            return vbox container
            logs should be some slice of cache.logs
            dialog=True affects size_request
            '''
            container = gtk.VBox()
            for l in logs:
                try:
                    w_type = gtk.image_new_from_pixbuf(self.icon_pixbufs[l['type']])
                except KeyError:
                    w_type = gtk.Label(l['type'].upper())
                    w_type.set_alignment(0, 0)
                w_finder = gtk.Label()
                w_finder.set_markup(" <b>%s</b>" % my_gtk_label_escape(HTMLManipulations._decode_htmlentities(l['finder'])))
                w_finder.set_alignment(0, 0)
                w_date = gtk.Label()
                if 'year' in l:
                    w_date.set_markup("<b>%4d-%02d-%02d</b>" % (int(l['year']), int(l['month']), int(l['day'])))
                else:
                    w_date.set_markup("<b>%s</b>" % l['date'])
                w_date.set_alignment(0.95, 0)
                #w_text = gtk.Label("%s\n" % l['text'].strip())
                w_text = gtk.Label("%s" % l['text'].strip()) #without linebreak
                w_text.set_line_wrap(True)
                w_text.set_alignment(0, 0)

                if events != None:
                   events.append(self.window.connect('configure-event', self._on_configure_label, w_text, True))

                if dialog: #inside dialog (not window)
                   w_text.set_size_request(self.window.size_request()[0] - 60, -1)
                else:
                   w_text.set_size_request(self.window.size_request()[0] - 10, -1)

                w_first = gtk.HBox()
                w_first.pack_start(w_type, False, False)
                w_first.pack_start(w_finder)
                w_first.pack_start(w_date)
                container.pack_start(w_first, False, False)
                container.pack_start(w_text, False, False)
                container.pack_start(gtk.HSeparator(), False, False)

            return container


    def _on_configure_label(self, source, event, widget, force=False, factor = 1):
        widget.set_size_request(event.width * factor - 10, -1)
        if force:
            widget.realize()

    def build_coordinates(self, cache, p):
        button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        button.set_title("Add Coordinate")
        button.set_image(gtk.image_new_from_file(self.image_icon_add))
        button.connect("clicked", lambda caller, cache: self._add_waypoint_to_user_coordinates_list(cache), cache)
        p.pack_start(button, False)
        def show_details(widget_coords, stuff, clist):
            c = clist[self._get_selected_pos(widget_coords)]
            if c == None:
                return
            self.__show_coordinate_details(c, cache)
        widget_coords, clist = self._get_coord_selector(cache, show_details)


        p.pack_start(widget_coords, True, True)
        p.show_all()

    def __show_coordinate_details(self, c, cache):
        RESPONSE_AS_TARGET, RESPONSE_AS_MAIN, RESPONSE_COPY_EDIT, RESPONSE_EDIT, RESPONSE_DELETE = range(5)
        try:
            name = c.display_text
        except AttributeError:
            name = "Coordinate Details" if (c.name == "") else c.name
        dialog = gtk.Dialog(self.shorten_name(name, 70), self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.set_size_request(800, 800)
        if c.lat != None:
            dialog.add_button("as Target", RESPONSE_AS_TARGET)
            dialog.add_button("as Main Coord.", RESPONSE_AS_MAIN)
        if c.user_coordinate_id != None:
            dialog.add_button("edit", RESPONSE_EDIT)
            dialog.add_button("delete", RESPONSE_DELETE)
        elif c.lat != None:
            dialog.add_button("copy & edit", RESPONSE_COPY_EDIT)
        lbl = gtk.Label()
        lbl.set_line_wrap(True)
        lbl.set_alignment(0, 0.5)
        lbl.set_markup("<b>%s</b>\n%s" % (c.get_latlon(self.format) if c.lat != None else '???', c.comment))
        
        
        #lbl.set_size_request(dialog.size_request()[0]/2, -1)
        dialog.connect('configure-event', self._on_configure_label, lbl, True, 2.0/3)
        dialog.vbox.pack_start(lbl, False)
        if c.lat != None:
            map = Map(center = c, zoom = 17, draggable = False)
            map.add_layer(SingleMarkLayer(c))
            dialog.vbox.pack_start(map, True)
        dialog.show_all()
        resp = dialog.run()
        dialog.hide()
        if resp == RESPONSE_AS_TARGET:
            self.set_current_cache(cache)
            self.set_target(c)
            self.hide_cache_view(go_to_map = True)
        elif resp == RESPONSE_AS_MAIN:
            self.core.set_alternative_position(cache, c)
        elif resp == RESPONSE_COPY_EDIT:
            self._add_waypoint_to_notes(c)
            self.update_coords()
        elif resp == RESPONSE_EDIT:
            self._on_edit_user_coordinate(None, cache, c.user_coordinate_id)
            self.update_coords()
        elif resp == RESPONSE_DELETE:
            self.__delete_user_coordinate(cache, c.user_coordinate_id)



    def update_coords(self):
        self.current_cache.notes = self.get_cache_notes()
        for x in self.cache_coord_page.get_children():
            self.cache_coord_page.remove(x)
        self.build_coordinates(self.current_cache, self.cache_coord_page)
        self.cache_coord_page.show()

    def build_cache_images(self, cache, notebook):
        selector = hildon.TouchSelector(text=True)
        selector.get_column(0).get_cells()[0].set_property('xalign', 0)
        selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)

        images = self.current_cache.get_images()
        if len(images) == 0:
            return
        imagelist = images.items()
        imagelist.sort(cmp=lambda x, y: cmp(x[1], y[1]))
        i = 1
        for filename, caption in imagelist:
            if len(caption) == 0:
                caption = "(no caption)"
            text = "#%d: %s" % (i, caption)
            i += 1
            selector.append_text(text)


        def on_imagelist_clicked(widget, data):
            path, caption = imagelist[self._get_selected_pos(widget)]
            self._on_show_image(path, caption)

        selector.connect("changed", on_imagelist_clicked)

        notebook.append_page(selector, gtk.Label("Images"))

    def build_cache_calc(self, cache, p):
        logger.debug("Cache calc for %s" % p)
        def input_changed(widget, char):
            cache.calc.set_var(char, widget.get_text())
            self.show_cache_calc_results(cache)

        for x in p.get_children():
            p.remove(x)
        count = len(cache.calc.requires)
        # create table with n rows.
        cols = 7
        rows = max(int(ceil(float(count) / float(cols))), 1)
        table = gtk.Table(rows, cols)
        i = 0
        requires_sort = list(cache.calc.requires)
        requires_sort.sort()
        vars = cache.calc.get_vars()
        for char in requires_sort:
            row = i / cols
            col = i % cols
            m = gtk.HBox()
            m.pack_start(gtk.Label(str(char)))
            e = hildon.Entry(gtk.HILDON_SIZE_AUTO)
            e.set_property("hildon-input-mode", gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
            try:
                e.set_text(vars[char])
            except KeyError:
                pass
            e.connect('changed', input_changed, str(char))
            e.set_size_request(50, -1)
            m.pack_start(e)
            table.attach(m, col, col + 1, row, row + 1)
            i += 1


        # add button
        button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL	)
        button.set_title("Add Calculation")
        button.set_image(gtk.image_new_from_file(self.image_icon_add))
        button.connect("clicked", self._on_edit_user_coordinate, cache)
        p.pack_start(button, False)

        # add contents
        p.pack_start(table, False)
        p.pack_start(gtk.HSeparator(), False)

        # add list vbox
        a = hildon.PannableArea()
        a.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        self.cache_calc_vbox = gtk.VBox()
        a.add_with_viewport(self.cache_calc_vbox)
        p.pack_start(a, True)


        p.show_all()
        self.show_cache_calc_results(cache)

    def show_cache_calc_results(self, cache):
        for x in self.cache_calc_vbox.get_children():
            self.cache_calc_vbox.remove(x)
        vars = cache.calc.get_vars()
        for c in cache.calc.coords:
            if len(c.requires) == 0:
                continue
            if type(c.source) == int:
                source = cache.get_user_coordinate(c.source)['name']
            else:
                source = c.source
            if c.has_requires():
                text_calc = "= %s\n%s%s" % (c.replaced_result, c.result if c.result != False else '', "".join("\n<b>!</b> <span color='gold'>%s</span>" % warning for warning in c.warnings))
            else:
                text_calc = "<i>Needs %s</i>\n" % (', '.join(("<s>%s</s>" if r in vars else "<b>%s</b>") % r for r in c.requires))

            label_text = '%s: <b>%s</b>\n%s' % (source, c.orig, text_calc)
            #logger.debug("Showing cache calc: %s" % label_text)
            l = gtk.Label()
            l.set_alignment(0, 0.5)
            l.set_markup(label_text)
            b = gtk.Table(rows = 2, columns = 2)
            b.attach(l, 0, 1, 0, 2)
            
            button = hildon.GtkButton(gtk.HILDON_SIZE_FINGER_HEIGHT)
            button.set_label("edit")
            button.connect("clicked", self._on_edit_user_coordinate, cache, c.source, c)
            b.attach(button, 1, 2, 0, 1, 0, 0)

            self.cache_calc_vbox.pack_start(b, False)
            self.cache_calc_vbox.pack_start(gtk.HSeparator(), False)
            
        self.cache_calc_vbox.show_all()

    def _on_edit_user_coordinate(self, caller, cache, source_id = None, coordinate = None):
        if source_id == None:
            before_calc = ''
            before_name = ''
            ctype = geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING
            logger.debug("Adding new calc string")
            button_text = None
        elif type(source_id) != int:
            before_calc = coordinate.orig
            before_name = ''
            ctype = geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING_OVERRIDE
            logger.debug("Overwriting original coordinate.")
            button_text = None
        else:
            info = cache.get_user_coordinate(source_id)
            before_name = info['name']
            ctype = info['type']
            if info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING:
                before_calc = info['value']
                logger.debug("Editing user supplied calc string.")
                button_text = 'Delete'
            elif info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING_OVERRIDE:
                before_calc = info['value'][1]
                logger.debug("Editing user supplied overwrite.")
                button_text = 'Reset'
            elif info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE:
                start = geo.Coordinate(info['value'][0], info['value'][1], info['name'])
                res = self.show_coordinate_input(start, none_on_cancel = True, show_name_input = True)
                if res == None:
                    return
                cache.set_user_coordinate(geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE, (res.lat, res.lon), res.name, source_id)
                self.core.save_cache_attribute(self.current_cache, 'user_coordinates')
                self.update_coords()
                return
            else:
                raise Exception("Illegal type.")

        (res, after_name, after_calc) = self.__show_edit_calculation(before_calc, before_name, button_text)

        if res not in (gtk.RESPONSE_ACCEPT, gtk.RESPONSE_NO):
            return
        if res == gtk.RESPONSE_ACCEPT:
            try:
                geo.try_parse_coordinate(after_calc)
                self.show_success("Coordinate saved.")
            except Exception:
                self.show_success("Calc string saved.")
            if source_id == None:
                value = after_calc
                id = None
            elif type(source_id) != int:
                value = (coordinate.signature, after_calc)
                id = None
            elif info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_CALC_STRING or info['type'] == geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE:
                value = after_calc
                id = source_id
            else:
                value = (info['value'][0], after_calc)
                id = source_id
            cache.set_user_coordinate(ctype, value, after_name, id)
        elif res == gtk.RESPONSE_NO:
            cache.delete_user_coordinate(source_id)

        self.core.save_cache_attribute(self.current_cache, 'user_coordinates')
        self.rebuild_cache_calc()
        
    def __delete_user_coordinate(self, cache, id):
        cache.delete_user_coordinate(id)
        self.core.save_cache_attribute(cache, 'user_coordinates')
        self.rebuild_cache_calc()
        self.update_coords()

    def __show_edit_calculation(self, before_calc, before_name, button_text):
        dialog = gtk.Dialog("Edit Calculation", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (
            gtk.STOCK_OK, gtk.RESPONSE_ACCEPT
            ))

        if button_text != None:
            dialog.add_button(button_text, gtk.RESPONSE_NO)

        text = "Enter a Coordinate or a calculation string.\n" + \
        "Format is: <b>N12 12.123 E123 12.123</b>\n" + \
        "Variables: <b>A-Z</b>, Operators: <b>+-*/%()</b>"
        lbl = gtk.Label()
        dialog.vbox.pack_start(lbl)
        lbl.set_line_wrap(True)
        lbl.set_alignment(0, 0.5)
        lbl.set_markup(text)

        grp = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        entry_name = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        entry_name.set_text(before_name)
        dialog.vbox.pack_start(hildon.Caption(grp, "Name", entry_name, None, hildon.CAPTION_MANDATORY))

        entry_calc = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        entry_calc.set_text(before_calc)
        dialog.vbox.pack_start(hildon.Caption(grp, "Calculation", entry_calc, None, hildon.CAPTION_MANDATORY))

        dialog.show_all()
        while True:
            res = dialog.run()
            if res == gtk.RESPONSE_ACCEPT and not CalcCoordinate.is_calc_string(entry_calc.get_text()):
                self.show_error("Please enter a valid calculation.")
            else:
                break
        dialog.hide()
        return (res, entry_name.get_text(), entry_calc.get_text())
        
    def _on_add_waypoint_clicked (self, widget):
        self._add_waypoint_to_notes()

    def _add_waypoint_to_notes(self, start=None):
        res = self.show_coordinate_input(self._get_best_coordinate(start), none_on_cancel = True)
        if res == None:
            return
        text = "\n%s\n" % res.get_latlon(self.format)
        self.cache_notes.get_buffer().insert(self.cache_notes.get_buffer().get_end_iter(), text)



    def _add_waypoint_to_user_coordinates_list(self, cache, start=None):
        res = self.show_coordinate_input(self._get_best_coordinate(start), none_on_cancel = True, show_name_input = True)
        if res == None:
            return
        cache.set_user_coordinate(geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE, (res.lat, res.lon), res.name)
        self.core.save_cache_attribute(self.current_cache, 'user_coordinates')
        self.update_coords()

        
    def _on_show_image(self, dpath, caption):
        fullpath = path.join(self.settings['download_output_dir'], dpath)
        if not path.exists(fullpath):
            print "file does not exist: " + fullpath
            return
        win = hildon.StackableWindow()
        win.set_title(caption)
        p = hildon.PannableArea()
        p.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        i = gtk.Image()
        i.set_from_file(fullpath)
        i.set_pixel_size(3)
        win.add(p)
        p.add_with_viewport(i)
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
        clist = cache.get_collected_coordinates(include_unknown=not no_empty, format=self.format, htmlcallback=self._strip_html, shorten_callback=lambda text: self.shorten_name(text, 65))
        for number, c in clist.items():
            selector.append_text(c.display_text)
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
        self.hide_cache_view(go_to_map = True)
        self._on_set_active_page(None, False)



    @staticmethod
    def _get_selected(widget):
        ls, iter = widget.get_selected(0)
        return ls[ls.get_path(iter)[0]]

    @staticmethod
    def _get_selected_pos(widget):
        ls, iter = widget.get_selected(0)
        return ls.get_path(iter)[0]



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
        # Current Cache / Current Target / Setting Center
        #
        ##############################################

    #def set_center(self, coord, noupdate=False, reset_track=True):
    #    SimpleGui.set_center(self, coord, noupdate, reset_track)


    def set_current_cache(self, cache):
        self.current_cache = cache
        self.button_show_details.set_value(self.shorten_name(cache.title, 25))
        self.button_show_details.set_sensitive(True)
        self.button_show_details_small.set_sensitive(True)
        self.geocache_layer.set_current_cache(cache)
        gobject.idle_add(self.map.redraw_layers)

    def _on_set_target_clicked(self, some, cache): 
        self.set_target(cache)
        self.hide_cache_view(go_to_map = True)
        self.set_active_page(True)

    def _on_target_changed(self, caller, cache, distance, bearing):
        self.gps_target_distance = distance
        self.gps_target_bearing = bearing
        coord = cache.get_latlon(self.format)
        self.label_target.set_value(coord)
        
        ##############################################
        #
        # Map
        #
        ##############################################

        


    def _update_zoom_buttons(self):
        if self.map.get_zoom() == self.map.get_min_zoom():
            self.button_zoom_out.set_sensitive(False)
        else:
            self.button_zoom_out.set_sensitive(True)
            
        if self.map.get_zoom() == self.map.get_max_zoom():
            self.button_zoom_in.set_sensitive(False)
        else:
            self.button_zoom_in.set_sensitive(True)

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


    def hide_cache_view(self, widget=None, data=None, go_to_map = False):
        if self.current_cache.calc != None:
            self.core.save_cache_attribute(self.current_cache, 'vars')
        self.current_cache_window_open = False
        if self.notes_changed:
            self.current_cache.notes = self.get_cache_notes()
            self.core.save_cache_attribute(self.current_cache, 'notes')
            self.notes_changed = False
        self.old_cache_window = hildon.WindowStack.get_default().pop_1()
        while go_to_map and hildon.WindowStack.get_default().size() > 1:
            hildon.WindowStack.get_default().pop_1()

        return True

    def get_cache_notes(self):
        b = self.cache_notes.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter())
                
    def set_progress(self, fraction, text = ''):
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
        hildon.hildon_banner_show_information(self.window, "", "%s" % errormsg)

    def show_success(self, message):
        hildon.hildon_banner_show_information(self.window, "", message)




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
            return

        self.label_altitude.set_markup("Altitude\n<small>%d m</small>" % self.gps_data.altitude)
        self.label_bearing.set_markup("Bearing\n<small>%d°</small>" % self.gps_data.bearing)
        self.label_latlon.set_markup("Current Position\n<small>%s</small>" % self.gps_data.position.get_latlon(self.format))


        if self.gps_has_fix and self.gps_target_distance != None:
            td_string = geo.Coordinate.format_distance(self.gps_target_distance)
            self.label_dist.set_markup("<span size='xx-large'>%s</span>" % td_string)
        elif self.gps_target_distance == None:
            self.label_dist.set_markup("<span size='x-large'>No Target</span>")
        else:
            self.label_dist.set_markup("<span size='xx-large'>No Fix</span>")


    def _on_no_fix(self, caller, gps_data, status):
        self.gps_data = gps_data
        self.gps_has_fix = False

        self.label_bearing.set_text("No Fix")
        self.label_latlon.set_text(status)
        self.update_gps_display()
        self._draw_arrow()
        self.map.redraw_layers()

        ##############################################
        #
        # Settings
        #
        ##############################################

    def _on_settings_changed_gui(self, settings):
        if 'options_rotate_screen' in settings:
            self.rotation_manager.set_mode(settings['options_rotate_screen'])
        


    def _on_save_settings(self, caller):
        c = self.map.get_center()
        settings = {}
        settings['map_position_lat'] = c.lat
        settings['map_position_lon'] = c.lon
        settings['map_zoom'] = self.map.get_zoom()
        settings['map_follow_position'] = self._get_track_mode()

        if self.current_cache != None:
            settings['last_selected_geocache'] = self.current_cache.name

        for i in ['options_username', 'options_password', 'download_noimages', 'options_show_name', 'options_hide_found', 'options_show_html_description', 'options_map_double_size', 'options_rotate_screen', 'tts_interval']:
            settings[i] = self.settings[i]
        caller.save_settings(settings, self)
