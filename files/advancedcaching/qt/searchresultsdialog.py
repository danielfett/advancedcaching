#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2010 Daniel Fett
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

from PySide.QtCore import *
from PySide.QtGui import *
import geo
from qt.mapwidget import QtGeocacheLayer
from qt.mapwidget import QtMap, QtOsdLayer
from ui_searchresultsdialog import Ui_SearchResultsDialog
logger = logging.getLogger('qtsearchresultsdialog')

d = lambda x: x.decode('utf-8')

class QtSearchResultsDialog(Ui_SearchResultsDialog, QDialog):
    def __init__(self, core, parent=None):
        QDialog.__init__(self, parent)
        self.core = core
        self.setupUi(self)
        self.setup_ui_custom()
        self.results = []
        self.selected_results = []

    def show(self, results):
        QDialog.show(self)
        self.results = results
        self.tableWidgetResults.clearContents()
        self.tableWidgetResults.setRowCount(len(results))
        row = 0
        max_size_first_col = 0
        for g in results:
            col = 0
            items = self.__make_items(g)
            # remember size of first col
            max_size_first_col = max(max_size_first_col, items[0].sizeHint().width())
            for item in items:
                self.tableWidgetResults.setItem(row, col, item)
                col += 1
            row += 1
        self.tableWidgetResults.resizeColumnsToContents()
        self.tableWidgetResults.setColumnWidth(0, 300)
        self.tableWidgetResults.selectAll()

    def __make_items(self, cache):
        # used to identify this cache later.
        start = QTableWidgetItem(d(cache.title))
        if self.core.current_position != None:
            distance = geo.Coordinate.format_distance(self.core.current_position.distance_to(cache))
            direction = geo.Coordinate.format_direction(self.core.current_position.bearing_to(cache))
            last = QTableWidgetItem("%s %s" % (distance, direction))
        else:
            last = QTableWidgetItem("?")
        entries = [
            start,
            QTableWidgetItem(d(cache.get_size_string())),
            QTableWidgetItem(d(cache.get_terrain())),
            QTableWidgetItem(d(cache.get_difficulty())),
            last
        ]
        cache.item = start
        return entries

    def setup_ui_custom(self):
        self.map = QtMap(self, geo.Coordinate(0, 0), 1)
        self.geocacheLayer = QtGeocacheLayer(self.__get_geocaches_callback, self.__show_cache)
        self.osdLayer = QtOsdLayer()

        self.map.add_layer(self.geocacheLayer)
        self.map.add_layer(self.osdLayer)
        #self.map = QLabel("test")
        self.layout().insertWidget(1, self.map)
        self.map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map.show()
        self.centralLayout = QVBoxLayout()

        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.addWidget(self.tableWidgetResults)
        self.splitter.addWidget(self.map)
        self.centralLayout.addWidget(self.splitter)
        self.centralLayout.addWidget(self.pushButtonExportSelected)
        l = self.layout()
        l.deleteLater()
        QCoreApplication.sendPostedEvents(l, QEvent.DeferredDelete)
        self.setLayout(self.centralLayout)
        self.splitter.setSizes([1000, 1000])
        self.tableWidgetResults.itemSelectionChanged.connect(self.__selection_changed)

    def __selection_changed(self):
        self.selected_results = [c for c in self.results if self.tableWidgetResults.isItemSelected(c.item)]
        if len(self.selected_results) > 0:
            self.map.fit_to_bounds(*geo.Coordinate.get_bounds(self.selected_results))
        #self.map.refresh()

    def __get_geocaches_callback(self, visible_area, maxresults):
        return [x for x in self.selected_results if self.map.in_area(x, visible_area)]

    def __show_cache(self, cache):
        pass


    