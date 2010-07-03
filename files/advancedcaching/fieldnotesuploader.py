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

import geocaching
import re
import gobject


class FieldnotesUploader(gobject.GObject):
    __gsignals__ = { 'finished-uploading': (gobject.SIGNAL_RUN_FIRST,\
                                 gobject.TYPE_NONE,\
                                 ()),
                    'upload-error' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                    }
    #lock = threading.Lock()
    URL = 'http://www.geocaching.com/my/uploadfieldnotes.aspx'
    
    def __init__(self, downloader):
        gobject.GObject.__init__(self)
        self.downloader = downloader
        self.notes = []

    def add_fieldnote(self, geocache):
        if geocache.logdate == '':
            raise Exception("Illegal Date.")

        if geocache.logas == geocaching.GeocacheCoordinate.LOG_AS_FOUND:
            log = "Found it"
        elif geocache.logas == geocaching.GeocacheCoordinate.LOG_AS_NOTFOUND:
            log = "Didn't find it"
        elif geocache.logas == geocaching.GeocacheCoordinate.LOG_AS_NOTE:
            log = "Write note"
        else:
            raise Exception("Illegal status: %s" % geocache.logas)

        text = geocache.fieldnotes.replace('"', "'")

        self.notes.append('%s,%sT10:00Z,%s,"%s"' % (geocache.name, geocache.logdate, log, text))

    def upload(self):
        try:
            print "+ Uploading fieldnotes..."
            page = self.downloader.get_reader(self.URL).read()
            m = re.search('<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="([^"]+)" />', page)
            if m == None:
                raise Exception("Could not download fieldnotes page.")
            viewstate = m.group(1)
            text = "\r\n".join(self.notes).encode("UTF-16")
            response = self.downloader.get_reader(self.URL,
                                                  data=self.downloader.encode_multipart_formdata(
                                                    [('ctl00$ContentBody$btnUpload', 'Upload Field Note'), ('ctl00$ContentBody$chkSuppressDate', ''), ('__VIEWSTATE', viewstate)],
                                                    [('ctl00$ContentBody$FieldNoteLoader', 'geocache_visits.txt', text)]
                                                  ))

            res = response.read()
            if not "successfully uploaded" in res:
                raise Exception("Something went wrong while uploading the field notes.")
            else:
                self.emit('finished-uploading')
        except Exception, e:
            self.emit('upload-error', e)
