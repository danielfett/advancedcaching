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

import logging
import geocaching
import re

from PySide.QtCore import *
from PySide.QtGui import *
from showimagedialog import QtShowImageDialog
from ui_geocachedetailswindow import Ui_GeocacheDetailsWindow
from os import path, extsep

# @type x str
d = lambda x: x #x.decode('ascii', 'replace')
logger = logging.getLogger('qtgeocachewindow')



class QtGeocacheDetailsWindow(QMainWindow, Ui_GeocacheDetailsWindow):

    download_details = Signal()

    ICONS = {
        geocaching.GeocacheCoordinate.LOG_TYPE_FOUND: 'emoticon_grin',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTFOUND: 'cross',
        geocaching.GeocacheCoordinate.LOG_TYPE_NOTE: 'comment',
        geocaching.GeocacheCoordinate.LOG_TYPE_MAINTENANCE: 'wrench',
        geocaching.GeocacheCoordinate.LOG_TYPE_PUBLISHED: 'accept',
        geocaching.GeocacheCoordinate.LOG_TYPE_DISABLED: 'delete',
        geocaching.GeocacheCoordinate.LOG_TYPE_NEEDS_MAINTENANCE: 'error',
        geocaching.GeocacheCoordinate.LOG_TYPE_WILLATTEND: 'calendar_edit',
        geocaching.GeocacheCoordinate.LOG_TYPE_ATTENDED: 'group',
        geocaching.GeocacheCoordinate.LOG_TYPE_UPDATE: 'asterisk_yellow',
    }

    def __init__(self, core, parent=None):
        QMainWindow.__init__(self, parent)
        self.core = core
        self.setupUi(self)
        self.actionDownload_Details.triggered.connect(self.__download_details)
        self.core.connect('cache-changed', self.__cache_changed)

    def __download_details(self):
        self.core.update_coordinates([self.current_geocache])

    def __cache_changed(self, caller, geocache):
        if geocache.name == self.current_geocache.name:
            self.show_geocache(geocache)

    def show_geocache(self, geocache):
        self.current_geocache = geocache
        # window title
        self.setWindowTitle("Geocache Details: %s" % d(geocache.title))

        # information
        labels = (
                  (self.labelFullName, geocache.title),
                  (self.labelID, geocache.name),
                  (self.labelType, geocache.type),
                  (self.labelSize, geocache.get_size_string()),
                  (self.labelTerrain, geocache.get_terrain()),
                  (self.labelDifficulty, geocache.get_difficulty()),
                  (self.labelOwner, geocache.owner),
                  (self.labelStatus, geocache.get_status())
                  )
        for label, text in labels:
            label.setText(d(text))

        if geocache.desc != '' and geocache.shortdesc != '':
            showdesc = "<b>%s</b><br />%s" % (geocache.shortdesc, geocache.desc)
        elif geocache.desc == '' and geocache.shortdesc == '':
            showdesc = "<i>No description available</i>"
        elif geocache.desc == '':
            showdesc = geocache.shortdesc
        else:
            showdesc = geocache.desc
        showdesc = d(showdesc)
        showdesc = re.sub(r'\[\[img:([^\]]+)\]\]', lambda a: "<img src='%s' />" % self.get_path_to_image(a.group(1)), showdesc)

        self.labelDescription.setText(showdesc)

        # logs and hints
        logs = []
        for l in geocache.get_logs():
            logs.append(self.__get_log_line(l))

        self.labelLogs.setText(''.join(logs))

        hint = d(geocache.hints).strip()
        if len(hint) > 0:
            self.pushButtonShowHint.clicked.connect(lambda: self.__show_hint(hint))
        else:
            self.pushButtonShowHint.hide()

        # images

        self.listWidgetImages.clear()
        images = geocache.get_images()
        if len(images) > 0:
            i = 0
            for filename, description in images.items():
                file = self.get_path_to_image(filename)
                icon = QIcon(file)
                m = QListWidgetItem(icon, d(description), self.listWidgetImages)
                m.setData(Qt.UserRole, QVariant(i))
                i += 1

            self.listWidgetImages.itemClicked.connect(lambda item: self.__show_image(item.icon().pixmap(QApplication.desktop().size())))
        else:
            self.tabImages.deleteLater()



    def __get_log_line(self, log):
        icon = "%s%spng" % (path.join(self.core.dataroot, self.ICONS[log['type']]), extsep)
        date = "%4d-%02d-%02d" % (int(log['year']), int(log['month']), int(log['day']))
        finder = d(log['finder'])
        line1 = "<tr><td><img src='%s'>%s</td><td align='right'>%s</td></tr>" % (icon, finder, date)
        line2 = "<tr><td colspan='2'>%s</td></tr>" % log['text'].strip()
        line3 = "<tr>td colspan='2'><hr></td></tr>"

        return ''.join((line1, line2, line3))

    def __show_hint(self, text):
        QMessageBox.information(self, "Hint, Hint!", text)

    def get_path_to_image(self, image):
        return path.join(self.core.settings['download_output_dir'], image)

    def __show_image(self, pixmap):
        m = QtShowImageDialog(self)
        m.show_image(pixmap)
        m.show()
