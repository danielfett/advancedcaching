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

class HildonSearchPlace(object):
    
    def plugin_init(self):
        self.last_searched_text = ''
        try:
            super(HildonSearchPlace, self).plugin_init()
        except:
            pass


    def _get_search_place_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Search Place")
        button.set_value('requires internet')
        button.connect('clicked', self._on_show_search_place)
        return button

    def _on_show_search_place(self, widget):
        dialog = gtk.Dialog("Search Place", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
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
        self.update_fieldnotes_display()
        self.core.connect('fieldnotes-changed', self._on_fieldnotes_changed)
        try:
            super(HildonFieldnotes, self).plugin_init()
        except:
            pass

    def _get_fieldnotes_button(self):
        button = hildon.Button(gtk.HILDON_SIZE_FINGER_HEIGHT, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Upload Fieldnote(s)")
        button.set_value("You have not created any fieldnotes.")
        button.connect("clicked", self._on_upload_fieldnotes, None)
        self.button_fieldnotes = button
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
        dialog = gtk.Dialog("create fieldnote", None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

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
        try:
            super(HildonSearchGeocaches, self).plugin_init()
        except:
            pass


    def _get_search_buttons(self):
        button1 = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button1.set_label("Search Geocaches")
        button1.connect("clicked", self._on_show_search, None)

        button2 = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
        button2.set_label("Last Search Results")
        button2.connect("clicked", self._on_reopen_search_clicked, None)
        button2.set_sensitive(False)
        self.reopen_last_search_button = button2
        return button1, button2
        menu.append(button)


    def _on_show_search(self, widget, data):
        RESPONSE_SHOW_LIST = 0
        RESPONSE_RESET = 1
        dialog = gtk.Dialog("Search", self.window, gtk.DIALOG_DESTROY_WITH_PARENT, ("show on map", gtk.RESPONSE_ACCEPT))
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

