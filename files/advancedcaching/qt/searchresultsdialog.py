#!/usr/bin/python
# -*- coding: utf-8 -*-

#        Copyright (C) 2010 Daniel Fett
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

import logging

from PyQt4.QtCore import *
from PyQt4.QtGui import *
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
        for g in results:
            print g
            col = 0
            for item in self.__make_items(g):
                self.tableWidgetResults.setItem(row, col, item)
                col += 1
            row += 1
        self.tableWidgetResults.resizeColumnsToContents()
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

        self.geocacheLayer.TOO_MANY_POINTS = 1001
        self.geocacheLayer.MAX_NUM_RESULTS_SHOW = 1001
        self.geocacheLayer.CACHES_ZOOM_LOWER_BOUND = 1
        self.map.add_layer(self.geocacheLayer)
        self.map.add_layer(self.osdLayer)
        #self.map = QLabel("test")
        self.layout().insertWidget(1, self.map)
        self.map.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map.show()
        self.centralLayout = QVBoxLayout(self)

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


    