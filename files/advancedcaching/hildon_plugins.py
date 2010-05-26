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
        button = hildon.Button(gtk.HILDON_SIZE_AUTO, hildon.BUTTON_ARRANGEMENT_VERTICAL)
        button.set_title("Upload Fieldnote(s)")
        button.set_value("You have not created any fieldnotes.")
        button.connect("clicked", self._on_upload_fieldnotes, None)
        self.button_fieldnotes = button
        return button

    def _get_write_fieldnote_button(self):
        button = hildon.GtkButton(gtk.HILDON_SIZE_AUTO)
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
