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

import geocaching
import gtk
import hildon
import pango
import threadpool
import logging
import geo
logger = logging.getLogger('plugins')

class HildonSearchPlace(object):
    
    def plugin_init(self):
        self.last_searched_text = ''
        logger.info("Using Search Place plugin")


    def _get_search_place_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Search Place")
        button.set_value('requires internet')
        button.connect('clicked', self._on_show_search_place)
        return button

    def _on_show_search_place(self, widget):
        dialog = gtk.Dialog("Search Place", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        search = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        search.set_text(self.last_searched_text)
        dialog.vbox.pack_start(search)
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        search_text = search.get_text().strip()
        self.last_searched_text = search_text
        if result != gtk.RESPONSE_ACCEPT or search_text == '':
            return
        try:
            results = self.core.search_place(search_text)
        except Exception, e:
            self.show_error(e)
            return

        if len(results) == 0:
            self.show_error("The search returned no results.")
            return

        sel = hildon.TouchSelector(text=True)
        for x in results:
            sel.append_text(x.name)

        dlg = hildon.PickerDialog(self.window)
        dlg.set_selector(sel)
        dlg.show_all()
        res = dlg.run()
        dlg.hide()
        if res != gtk.RESPONSE_OK:
            return
        self.set_center(results[self._get_selected_pos(sel)])
        
class HildonFieldnotes(object):
    def plugin_init(self):
        #self.update_fieldnotes_display()
        self.core.connect('fieldnotes-changed', self._on_fieldnotes_changed)
        logger.info("Using Fieldnotes plugin")

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Upload Fieldnote(s)")
        button.set_value("You have not created any fieldnotes.")
        button.connect("clicked", self._on_upload_fieldnotes, None)
        self.button_fieldnotes = button

    def _get_fieldnotes_button(self):
        self.update_fieldnotes_display()
        self.button_fieldnotes.unparent()
        return self.button_fieldnotes

    def _get_write_fieldnote_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("Write Fieldnote")
        button.connect("clicked", self._on_show_log_fieldnote_dialog, None)
        return button

    def _on_show_log_fieldnote_dialog(self, widget, data):
    
        from time import gmtime
        from time import localtime
        from time import strftime
        
        if self.current_cache == None:
            return

        statuses = [
            ("Don't upload a fieldnote", geocaching.GeocacheCoordinate.LOG_NO_LOG),
            ("Found it", geocaching.GeocacheCoordinate.LOG_AS_FOUND),
            ("Did not find it", geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND),
            ("Post a note", geocaching.GeocacheCoordinate.LOG_AS_NOTE)
        ]

        cache = self.current_cache
        dialog = gtk.Dialog("Write Fieldnote", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        if cache.logdate == '':
            try:
                text = strftime(self.settings['options_default_log_text'], localtime()) % {'machine': 'N900'}
            except ValueError:
                text = self.settings['options_default_log_text']
        else:
            text = cache.fieldnotes

        fieldnotes = gtk.TextView()
        #fieldnotes.set_placeholder("Your fieldnote text...")
        fieldnotes.get_buffer().set_text(text)


        fieldnotes_log_as_selector = hildon.TouchSelector(text=True)

        for text, status in statuses:
            fieldnotes_log_as_selector.append_text(text)
        i = 0
        for text, status in statuses:
            if cache.logas == status:
                fieldnotes_log_as_selector.select_iter(0, fieldnotes_log_as_selector.get_model(0).get_iter(i), False)
            i += 1
        fieldnotes_log_as = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        fieldnotes_log_as.set_title('Log Type')
        fieldnotes_log_as.set_selector(fieldnotes_log_as_selector)

        dialog.vbox.pack_start(fieldnotes_log_as, False)
        dialog.vbox.pack_start(fieldnotes, True)
        #dialog.vbox.pack_start(hildon.Caption(None, "Text", fieldnotes, None, hildon.CAPTION_OPTIONAL))
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result != gtk.RESPONSE_ACCEPT:
            logger.debug('Not logging this fieldnote')
            return

        cache.logas = statuses[fieldnotes_log_as_selector.get_selected_rows(0)[0][0]][1]
        cache.logdate = strftime('%Y-%m-%d', gmtime())
        cache.fieldnotes = fieldnotes.get_buffer().get_text(fieldnotes.get_buffer().get_start_iter(), fieldnotes.get_buffer().get_end_iter())
        self.core.save_fieldnote(cache)


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

class HildonSearchGeocaches(object):

    def plugin_init(self):
        self.old_search_window = None
        self.map_filter_active = False
        logger.info("Using Search plugin")


    def _get_search_button(self):
        button1 = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button1.set_title("Search Geocaches")
        button1.set_value("in local database")
        button1.connect("clicked", self._on_show_search, None)
        return button1


    def _on_show_search(self, widget, data):


        name = hildon.Entry(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
        name.set_placeholder("search for name...")
        name_hbox = hildon.Caption(None, "Name", name, None, hildon.CAPTION_OPTIONAL)

        sel_dist_type = hildon.TouchSelector(text=True)
        sel_dist_type.append_text('anywhere')
        sel_dist_type.append_text('around my position')
        sel_dist_type.append_text('around the current map center')
        pick_dist_type = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_dist_type.set_selector(sel_dist_type)
        pick_dist_type.set_title("Search")
        sel_dist_type.select_iter(0, sel_dist_type.get_model(0).get_iter(1), False)

        list_dist_radius = (1, 5, 10, 20, 50, 100, 200)
        sel_dist_radius = hildon.TouchSelector(text=True)
        for x in list_dist_radius:
            sel_dist_radius.append_text('%d km' % x)
        pick_dist_radius = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_dist_radius.set_selector(sel_dist_radius)
        pick_dist_radius.set_title("Radius")
        pick_dist_type.connect('value-changed', lambda caller: pick_dist_radius.set_sensitive(sel_dist_type.get_selected_rows(0)[0][0] != 0))
        sel_dist_radius.select_iter(0, sel_dist_radius.get_model(0).get_iter(1), False)

        sel_size = hildon.TouchSelector(text=True)
        sel_size.append_text('micro')
        sel_size.append_text('small')
        sel_size.append_text('regular')
        sel_size.append_text('huge')
        sel_size.append_text('other')
        sel_size.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_size = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_size.set_selector(sel_size)
        pick_size.set_title("Select Size(s)")
        for i in xrange(5):
            sel_size.select_iter(0, sel_size.get_model(0).get_iter(i), False)

        sel_type = hildon.TouchSelector(text=True)
        sel_type.append_text('traditional')
        sel_type.append_text('multi-stage')
        sel_type.append_text('virtual')
        sel_type.append_text('earth')
        sel_type.append_text('event')
        sel_type.append_text('mystery')
        sel_type.append_text('all')
        sel_type.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_type = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_type.set_selector(sel_type)
        pick_type.set_title("Select Type(s)")
        sel_type.unselect_all(0)
        sel_type.select_iter(0, sel_type.get_model(0).get_iter(6), False)

        sel_status = hildon.TouchSelector(text=True)
        sel_status.append_text('any')
        sel_status.append_text("Geocaches I haven't found")
        sel_status.append_text("Geocaches I have found")
        sel_status.append_text("Marked Geocaches")
        sel_status.append_text("Marked Geocaches I haven't found")
        pick_status = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_status.set_selector(sel_status)
        pick_status.set_title("Select Status")

        sel_status.unselect_all(0)
        sel_status.select_iter(0, sel_status.get_model(0).get_iter(0), False)

        sel_diff = hildon.TouchSelector(text=True)
        sel_diff.append_text('1..2.5')
        sel_diff.append_text('3..4')
        sel_diff.append_text('4.5..5')
        sel_diff.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_diff = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_diff.set_selector(sel_diff)
        pick_diff.set_title("Select Difficulty")
        for i in xrange(3):
            sel_diff.select_iter(0, sel_diff.get_model(0).get_iter(i), False)

        sel_terr = hildon.TouchSelector(text=True)
        sel_terr.append_text('1..2.5')
        sel_terr.append_text('3..4')
        sel_terr.append_text('4.5..5')
        sel_terr.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_terr = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_terr.set_selector(sel_terr)
        pick_terr.set_title("Select Terrain")
        for i in xrange(3):
            sel_terr.select_iter(0, sel_terr.get_model(0).get_iter(i), False)



        RESPONSE_SHOW_LIST, RESPONSE_RESET, RESPONSE_LAST_RESULTS = range(3)
        dialog = gtk.Dialog("Search", self.window, gtk.DIALOG_DESTROY_WITH_PARENT,
                            ("OK", RESPONSE_SHOW_LIST))
        dialog.add_button("Filter Map", gtk.RESPONSE_ACCEPT)
        if self.map_filter_active:
            dialog.add_button("Reset Filter", RESPONSE_RESET)
        if self.old_search_window != None:
            dialog.add_button("Last Results", RESPONSE_LAST_RESULTS)
        dialog.set_size_request(800, 800)
        pan = hildon.PannableArea()
        options = gtk.VBox()
        pan.add_with_viewport(options)
        dialog.vbox.pack_start(pan)

        options.pack_start(gtk.Label("Search Geocaches"))
        options.pack_start(name_hbox)
        options.pack_start(pick_dist_type)
        options.pack_start(pick_dist_radius)
        options.pack_start(pick_type)
        options.pack_start(pick_status)

        options.pack_start(gtk.Label("Details..."))
        w = gtk.Label("If you select something here, only geocaches for which details were downloaded will be shown in the result.")
        w.set_line_wrap(True)
        w.set_alignment(0, 0.5)
        options.pack_start(w)

        options.pack_start(pick_size)
        options.pack_start(pick_diff)
        options.pack_start(pick_terr)

        

        while True:
            dialog.show_all()
            response = dialog.run()
            dialog.hide()

            if response == RESPONSE_RESET:
                self.core.reset_filter()
                self.map_filter_active = False
                self.show_success("Showing all geocaches.")
                return
            elif response == RESPONSE_LAST_RESULTS:
                if self.old_search_window == None:
                    return
                hildon.WindowStack.get_default().push_1(self.old_search_window)
                
                return
            
            name_search = name.get_text().strip().lower()

            sizes = [x + 1 for x, in sel_size.get_selected_rows(0)]
            if sizes == [1, 2, 3, 4, 5]:
                sizes = None

            typelist = [
                geocaching.GeocacheCoordinate.TYPE_REGULAR,
                geocaching.GeocacheCoordinate.TYPE_MULTI,
                geocaching.GeocacheCoordinate.TYPE_VIRTUAL,
                geocaching.GeocacheCoordinate.TYPE_EARTH,
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

            center = None
            dist_type = sel_dist_type.get_selected_rows(0)[0][0]
            if dist_type == 1:
                try:
                    center = self.gps_last_good_fix.position
                except AttributeError:
                    logger.debug("No current Fix.")
                    pass
            elif dist_type == 2:
                center = self.map.get_center()
            if center != None:
                radius = list_dist_radius[sel_dist_radius.get_selected_rows(0)[0][0]]
                sqrt_2 = 1.41421356
                c1 = center.transform(-45, radius * 1000 * sqrt_2)
                c2 = center.transform(-45 + 180, radius * 1000 * sqrt_2)
                location = (c1, c2)
            else:
                location = None

            if response == RESPONSE_SHOW_LIST:
                points, truncated = self.core.get_points_filter(found=found, name_search=name_search, size=sizes, terrain=terrains, diff=difficulties, ctype=types, marked=marked, location=location)
                if len(points) > 0:
                    self._display_results(points, truncated)
                    break
                else:
                    self.show_error("Search returned no geocaches. Please remember that search works only within the downloaded geocaches.")

            elif response == gtk.RESPONSE_ACCEPT:
                self.core.set_filter(found=found, name_search=name_search, size=sizes, terrain=terrains, diff=difficulties, ctype=types, marked=marked)
                self.show_success("Filter for map activated, ignoring distance restrictions.")
                self.map_filter_active = True
                break
            else:
                break

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
                ls.append([self.shorten_name(c.title, 40), " " + c.get_size_string(), ' D%s T%s' % (c.get_difficulty(), c.get_terrain()), " " + geo.Coordinate.format_distance(c.prox), c])
            tv.handler_unblock_by_func(select_cache)


        menu = hildon.AppMenu()
        button = None
        for name, function in sortfuncs:
            button = hildon.GtkRadioButton(gtk.HILDON_SIZE_AUTO, button)
            button.set_label(name)
            button.connect("clicked", on_change_sort, function)
            menu.add_filter(button)
            button.set_mode(False)

        def download_geocaches(widget):
            self.core.update_coordinates(caches)



        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Details")
        button.set_value("for all Geocaches")
        button.connect("clicked", download_geocaches)
        menu.append(button)

        menu.show_all()
        win.set_app_menu(menu)
        win.add(tv)

        on_change_sort(None, sortfuncs[0][1])

        win.show_all()
        if truncated:
            hildon.hildon_banner_show_information_with_markup(win, "hu", "Showing only the first %d results." % len(caches))

        win.connect('delete_event', self.hide_search_view)

    def hide_search_view(self, widget, data):
        self.old_search_window = hildon.WindowStack.get_default().pop_1()
        return True


class HildonAboutDialog(object):

    def plugin_init(self):
        logger.info("Using About Dialog plugin")
        logger.debug("trying update")
        
        #import gobject
        #def try_update():
        #    if 'options_auto_update' in self.settings and not self.settings['options_auto_update']:
        #        return False
        #    from time import sleep
        #    
        #    updates = self.core.try_update(silent = True)
        #    
        #    if updates not in [None, False]:
        #        self.show_success("Parser update installed.")
        #    return False
        #gobject.timeout_add(5000, try_update)

    def _get_about_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("About AGTL")
        button.set_value("and online update")
        button.connect("clicked", self._on_show_about, None)
        return button

    def _on_show_about(self, widget, data):
        (RESPONSE_UPDATE, RESPONSE_HOMEPAGE, RESPONSE_OPTIMIZE) = range(3)
        dialog = gtk.Dialog("About AGTL", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, ('Update', RESPONSE_UPDATE, 'Website', RESPONSE_HOMEPAGE, 'Optimize', RESPONSE_OPTIMIZE))
        dialog.set_size_request(800, 800)

        notebook = gtk.Notebook()
        dialog.vbox.pack_start(notebook)
        page = gtk.VBox()
        notebook.append_page(page, gtk.Label('About'))

        copyright = '''Copyright (C) in most parts 2012 Daniel Fett
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see http://www.gnu.org/licenses/.

Author: Daniel Fett advancedcaching@fragcom.de'''
        additional = '''Neither the author nor the software is affiliated with or endorsed by any geocaching website.'''

        text = "%s\n\n%s\n\n" % (copyright, additional)

        l = gtk.Label('')
        import core
        l.set_markup("<b><u>AGTL version %s</u></b>" % core.VERSION)
        l.set_alignment(0, 0)
        page.pack_start(l, False)

        l = gtk.Label()
        l.set_line_wrap(True)
        l.set_alignment(0, 0)
        l.set_size_request(self.window.size_request()[0] - 10, -1)
        l.set_markup(text)
        p = hildon.PannableArea()
        p.set_property('mov-mode', hildon.MOVEMENT_MODE_BOTH)
        p.add_with_viewport(l)
        page.pack_start(p)


        page = gtk.VBox()
        notebook.append_page(page, gtk.Label('Update'))

        l = gtk.Label('')
        import cachedownloader
        l.set_markup("Website parser version %d (from %s)\n\nIf you're having trouble downloading geocaches or uploading fieldnotes, try clicking 'update' to fetch the latest website parser.\n\nAlso check the regular maemo updates from time to time." % (cachedownloader.VERSION, cachedownloader.VERSION_DATE))
        l.set_alignment(0, 0)
        l.set_line_wrap(True)
        page.pack_start(l, False)

        page = gtk.VBox()
        notebook.append_page(page, gtk.Label('Files'))

        sizes = self.core.get_file_sizes()
        l = gtk.Label('')
        l.set_markup("Database Size: %s\nImage Folder Size: %s\n\nClick 'optimize' to purge found geocaches and their images. Be aware that this includes your notes and calculation values for those geocaches." % (self.core.format_file_size(sizes['sqlite']), self.core.format_file_size(sizes['images'])))
        l.set_alignment(0, 0)
        l.set_line_wrap(True)
        page.pack_start(l, False)


        dialog.show_all()
        result = dialog.run()

        if result == RESPONSE_HOMEPAGE:
            dialog.hide()
            self._open_browser(None, 'http://www.danielfett.de/')
            return
        elif result == RESPONSE_UPDATE:
            dialog.hide()
            self._try_parser_update()
            self._on_show_about(None, None)
        elif result == RESPONSE_OPTIMIZE:
            hildon.hildon_gtk_window_set_progress_indicator(dialog, 1)
            self.core.optimize_data()
            hildon.hildon_gtk_window_set_progress_indicator(dialog, 0)
            dialog.hide()
            self._on_show_about(None, None)


    def _try_parser_update(self):
        updates = self.core.try_update()
        if updates not in [None, False]:
            self.show_success("%d modules upgraded. There's no need to restart AGTL." % updates)
            

logger = logging.getLogger('mapdownloader')

class HildonDownloadMap(object):

    SIZE_PER_TILE = 1200

    def plugin_init(self):
        logger.info("Using Map Download plugin")

    def _get_download_map_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Download Map")
        button.set_value("for offline use")
        button.connect("clicked", self._on_show_download_map, None)
        return button

    def _show_tile_select_dialog(self, zoom_steps):
        sel_zoom = hildon.TouchSelector(text=True)
        current_zoom = self.map.get_zoom()

        for zoom, size, count in zoom_steps:
            sel_zoom.append_text('Zoom %d (Current+%d) ~%s' % (zoom, zoom - current_zoom, self.core.format_file_size(size)))

        sel_zoom.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_MULTIPLE)
        pick_zoom = hildon.PickerButton(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
        pick_zoom.set_selector(sel_zoom)
        pick_zoom.set_title("Select Zoom Levels")
        def print_func(widget):
            size = sum(zoom_steps[x][1] for x, in sel_zoom.get_selected_rows(0))
            pick_zoom.set_value('~' + self.core.format_file_size(size))
        pick_zoom.connect('value-changed', print_func)
        pick_zoom.connect('realize', print_func)

        dialog = gtk.Dialog("Download Map Tiles", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.vbox.pack_start(pick_zoom)
        dialog.show_all()
        res = dialog.run()
        dialog.hide()

        if res != gtk.RESPONSE_ACCEPT:
            return []

        steps = [zoom_steps[x] for x, in sel_zoom.get_selected_rows(0)]
        return steps

    def _on_show_download_map(self, widget, data):
        current_visible_tiles = self.map.surface_buffer.keys()
        if len(current_visible_tiles) == 0:
            return

        current_zoom = self.map.get_zoom()
        if current_zoom == self.map.get_max_zoom():
            self.show_error("Please zoom out to download tiles")

        zoom_steps = []
        for zoom in xrange(current_zoom + 1, min(self.map.get_max_zoom() + 1, current_zoom + 7)):
            count = len(current_visible_tiles) * (4 ** (zoom-current_zoom))
            size = (count * HildonDownloadMap.SIZE_PER_TILE)
            zoom_steps.append((zoom, size, count))

        active_zoom_steps = self._show_tile_select_dialog(zoom_steps)
        for zoom, size, count in active_zoom_steps:
            logger.info("Requesting zoom %d" % zoom)

        if len(active_zoom_steps) == 0:
            return

        zoom_step_keys = [x[0] for x in active_zoom_steps]
        max_zoom_step = max(zoom_step_keys)

        todo = sum(x[2] for x in active_zoom_steps)
        status = {'finished': 0, 'aborted': 0}
        tile_loader_threadpool = threadpool.ThreadPool(6)
        requests = []

        dialog = gtk.Dialog("Downloading Map Tiles...", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_CANCEL))
        hildon.hildon_gtk_window_set_progress_indicator(dialog, 1)
        pbar = gtk.ProgressBar()
        dialog.vbox.pack_start(pbar)
        dialog.show_all()

        stopped = [False]
        def cancel(widget, data):
            stopped[0] = True

        dialog.connect('response', cancel)
        pbar.set_text("Preparing download of %d map tiles..." % todo)
        while gtk.events_pending():
            gtk.main_iteration()
        if stopped[0]:
                return

        def add_tiles(source, zoom):
            if zoom in zoom_step_keys:
                requests.append(((source, zoom), {}))

            if zoom + 1 <= max_zoom_step:
                for add_x in (0, 1):
                    for add_y in (0, 1):
                        tile = (source[0] * 2 + add_x, source[1] * 2 + add_y)
                        add_tiles(tile, zoom + 1)

        for prefix, tile_x, tile_y, zoom, undersample in current_visible_tiles:
            add_tiles((tile_x, tile_y), current_zoom)

        if len(requests) != todo:
            raise Exception("Something went wrong while calculating the amount of tiles. (%d vs. %d)" % (len(requests), todo))

        def download_tile(tile, zoom):
            tl = self.map.tile_loader(None, tile = tile, zoom = zoom)
            res = tl.download_tile_only()
            if res:
                status['finished'] += 1
            else:
                status['aborted'] += 1


        reqs = threadpool.makeRequests(download_tile, requests)
        i = 0
        count = len(reqs)
        for r in reqs:
            i += 1
            tile_loader_threadpool.putRequest(r)
            if i % 100 == 0:
                pbar.set_text("Starting download...")
                pbar.set_fraction(i/count)
                while gtk.events_pending():
                    gtk.main_iteration()
                if stopped[0]:
                    return
        
        import time
        try:
            while True:
                time.sleep(0.5)
                while gtk.events_pending():
                    gtk.main_iteration()
                tile_loader_threadpool.poll()
                pbar.set_fraction(sum(status.values())/float(todo))
                pbar.set_text("%d of %d downloaded (%d errors)" % (sum(status.values()), todo, status['aborted']))
                if stopped[0]:
                    tile_loader_threadpool.dismissWorkers
                    break
        except threadpool.NoResultsPending:
            logger.info("Downloading finished")
        except Exception,e:
            print e
            self.show_error(e)
        finally:
            logger.info("Closing")
            dialog.hide()
            

class HildonToolsDialog(object):

    def plugin_init(self):
        logger.info("Using Tools Dialog plugin")

        
    def _get_tools_button(self):
        button1 = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button1.set_title("Tools")
        button1.connect("clicked", self._on_show_tools)
        return button1
        
    def _on_show_tools(self, caller, data = None):
        dialog = gtk.Dialog("Tools", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        #dialog.set_size_request(800, 480)

        list = dialog.vbox
        
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("Coordinate Projection")
        button.connect("clicked", self._show_tool_heading, None)
        button.connect("clicked", lambda caller: dialog.hide())
        list.pack_start(button)

        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("ROT13")
        button.connect("clicked", self._show_tool_rot13, None)
        button.connect("clicked", lambda caller: dialog.hide())
        list.pack_start(button)
        
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("Roman Numbers")
        button.connect("clicked", self._show_tool_romans, None)
        button.connect("clicked", lambda caller: dialog.hide())
        list.pack_start(button)
        
        dialog.show_all()
        dialog.run()
        dialog.hide()
        
    def _show_tool_rot13(self, caller, data = None):
        dialog = gtk.Dialog("ROT13", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, ())
        dialog.set_size_request(800, 480)
        
        source = hildon.TextView()
        dialog.vbox.pack_start(source)
        destination = hildon.TextView()
        destination.set_editable(False)    
        dialog.vbox.pack_start(destination)
        
        def do_rot(widget):
            import cachedownloader
            try:
                text = cachedownloader.CacheDownloader._rot13(source.get_buffer().get_text(source.get_buffer().get_start_iter(), source.get_buffer().get_end_iter()))
            except Exception:
                text = ''
                
            destination.get_buffer().set_text(text)
        
        source.get_buffer().connect('changed', do_rot)
        
        dialog.show_all()
        dialog.run()
        dialog.hide()
        
    def _show_tool_romans(self, caller, data = None):
        dialog = gtk.Dialog("Roman Numbers", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, ())
        #dialog.set_size_request(800, 480)
        
        source = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        source.set_property("hildon-input-mode", gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
        dialog.vbox.pack_start(hildon.Caption(None, "Arabic", source, None, 0))
        destination = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        dialog.vbox.pack_start(hildon.Caption(None, "Roman", destination, None, 0))
        
        inhibit = [False]
        
        def to_roman(widget):
            if inhibit[0] == True:
                return
            try:
                text = HildonToolsDialog._int_to_roman(int(source.get_text()))
            except ValueError:
                text = ''
            inhibit[0] = True
            destination.set_text(text)
            inhibit[0] = False
            
        
        def to_arabic(widget):
            if inhibit[0] == True:
                return
            try:
                text = str(HildonToolsDialog._roman_to_int(destination.get_text()))
            except ValueError:
                text = ''
            inhibit[0] = True
            source.set_text(text)
            inhibit[0] = False
        
        source.connect('changed', to_roman)
        destination.connect('changed', to_arabic)
        
        dialog.show_all()
        dialog.run()
        dialog.hide()
    NUMERAL_MAP = zip(
        (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
        ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    )
    
    def _show_tool_heading(self, caller, data = None):
        RESULT_WPT, RESULT_TARGET = range(2)
        dialog = gtk.Dialog("Coordinate Projection", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, ("as target", RESULT_TARGET))
        if self.current_cache != None:
            dialog.add_button("add waypoint", RESULT_WPT)
        #dialog.set_size_request(800, 480)
        
        
        def select_origin(widget, data = None):
            start = self._get_best_coordinate() if origin[0] == None else origin[0]
            new = self._show_target_input_list(start, show_current = True)
            if new != None:
                origin[0] = new
                text = new.get_latlon()
                button.set_value(text)
                recalc(None)
        
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Select Origin")
        button.set_value("current Target")
        button.connect("clicked", select_origin, None)
        dialog.vbox.pack_start(button)
        
        origin = [self.core.current_target]
        
        direction = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        direction.set_property("hildon-input-mode", gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
        
        dialog.vbox.pack_start(hildon.Caption(None, "Heading in Degrees", direction, None, 0))
        
        distance = hildon.Entry(gtk.HILDON_SIZE_AUTO)
        distance.set_property("hildon-input-mode", gtk.HILDON_GTK_INPUT_MODE_NUMERIC)
        dialog.vbox.pack_start(hildon.Caption(None, "Distance in Meters", distance, None, 0))
        
        result = gtk.Label()
        dialog.vbox.pack_start(hildon.Caption(None, "Resulting Point", result, None, 0))
        
        resulting_coordinate = [None]
        
        def recalc(widget):
            try:
                res = origin[0].transform(-float(direction.get_text()), float(distance.get_text()))
                text = res.get_latlon()
            except Exception:
                res = None
                text = 'enter values...'
            resulting_coordinate[0] = res
            result.set_text(text)
            
        direction.connect('changed', recalc)
        distance.connect('changed', recalc)    
        
                
        dialog.show_all()
        res = dialog.run()
        dialog.hide()
        if res == RESULT_WPT:
            if resulting_coordinate[0] == None:
                return
            distance = resulting_coordinate[0].format_distance(float(distance.get_text()))
            heading = int(direction.get_text())
            name = "hdg %s, %d deg from %s" % (distance, heading, origin[0].get_latlon())
            self.current_cache.get_user_coordinates(None)
            self.current_cache.set_user_coordinate(geocaching.GeocacheCoordinate.USER_TYPE_COORDINATE, (resulting_coordinate[0].lat, resulting_coordinate[0].lon), name)
            self.core.save_cache_attribute(self.current_cache, 'user_coordinates')
            self._on_cache_changed(None, self.current_cache)

        elif res == RESULT_TARGET:
            if resulting_coordinate[0] == None:
                return
            self.set_target(resulting_coordinate[0])
        
    @staticmethod
    def _int_to_roman(i):
        result = []
        for integer, numeral in HildonToolsDialog.NUMERAL_MAP:
            count = int(i / integer)
            result.append(numeral * count)
            i -= integer * count
        return ''.join(result)

    @staticmethod
    def _roman_to_int(n):
        n = unicode(n).upper()

        i = result = 0
        for integer, numeral in HildonToolsDialog.NUMERAL_MAP:
            while n[i:i + len(numeral)] == numeral:
                result += integer
                i += len(numeral)
        return result
