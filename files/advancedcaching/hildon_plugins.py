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
import gtk
import hildon
import geocaching
import pango

class HildonSearchPlace(object):
    
    def plugin_init(self):
        self.last_searched_text = ''
        print "+ Using Search Place plugin"


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
        self.set_center(results[self._get_selected_index(sel)])
        
class HildonFieldnotes(object):
    def plugin_init(self):
        #self.update_fieldnotes_display()
        self.core.connect('fieldnotes-changed', self._on_fieldnotes_changed)
        print "+ Using Fieldnotes plugin"

    def _get_fieldnotes_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Upload Fieldnote(s)")
        button.set_value("You have not created any fieldnotes.")
        button.connect("clicked", self._on_upload_fieldnotes, None)
        self.button_fieldnotes = button
        self.update_fieldnotes_display()
        return button

    def _get_write_fieldnote_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_label("Write Fieldnote")
        button.connect("clicked", self._on_show_log_fieldnote_dialog, None)
        return button

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
        dialog = gtk.Dialog("create fieldnote", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        fieldnotes = hildon.TextView()
        fieldnotes.set_placeholder("Your fieldnote text...")
        fieldnotes.get_buffer().set_text(cache.fieldnotes)

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
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result != gtk.RESPONSE_ACCEPT:
            print 'Not logging this fieldnote'
            return
        from time import gmtime
        from time import strftime

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
        print "+ Using Search plugin"


    def _get_search_button(self):
        button1 = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button1.set_title("Search Geocaches")
        button1.set_value("in local database")
        button1.connect("clicked", self._on_show_search, None)
        return button1


    def _on_show_search(self, widget, data):


        name = hildon.Entry(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT)
        name.set_placeholder("search for name...")
        name_hbox = gtk.HBox()
        name_hbox.pack_start(gtk.Label("Name: "), False, False)
        name_hbox.pack_start(name, True, True)

        sel_dist_type = hildon.TouchSelector(text=True)
        sel_dist_type.append_text('anywhere')
        sel_dist_type.append_text('around my position')
        sel_dist_type.append_text('around the current center')
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
        dialog.set_size_request(800,800)
        pan = hildon.PannableArea()
        options = gtk.VBox()
        pan.add_with_viewport(options)
        dialog.vbox.pack_start(pan)

        frame_all = gtk.Frame("Search Geocaches")
        vbox_all = gtk.VBox()
        frame_all.add(vbox_all)
        options.pack_start(frame_all)


        frame_details = gtk.Frame("Details...")
        vbox_details = gtk.VBox()
        frame_details.add(vbox_details)
        options.pack_start(frame_details)

        vbox_all.pack_start(name_hbox)
        vbox_all.pack_start(pick_dist_type)
        vbox_all.pack_start(pick_dist_radius)
        vbox_all.pack_start(pick_type)
        vbox_all.pack_start(pick_status)

        w = gtk.Label("If you select something here, only geocaches for which details were downloaded will be shown in the result.")
        vbox_details.pack_start(w)
        w.set_line_wrap(True)
        w.set_alignment(0, 0.5)
        vbox_details.pack_start(pick_size)
        vbox_details.pack_start(pick_diff)
        vbox_details.pack_start(pick_terr)

        

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
                print self.old_search_window.get_allocation()
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
                    print "No current Fix."
                    pass
            elif dist_type == 2:
                center = self.ts.num2deg(self.map_center_x, self.map_center_y)
            if center != None:
                radius = list_dist_radius[sel_dist_radius.get_selected_rows(0)[0][0]]
                sqrt_2 = 1.41421356
                c1 = center.transform(-45, radius * 1000 * sqrt_2)
                c2 = center.transform(-45 + 180, radius * 1000 * sqrt_2)
                location = (c1, c2)
                print "Using: ", c1, c2
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
                self.show_success("Filter for map activated.")
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
                ls.append([self.shorten_name(c.title, 40), " " + c.get_size_string(), ' D%s T%s' % (c.get_difficulty(), c.get_terrain()), " " + self._format_distance(c.prox), c])
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

        win.connect('delete_event', self.hide_search_view)

    def hide_search_view(self, widget, data):
        self.old_search_window = hildon.WindowStack.get_default().pop_1()