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
logger = logging.getLogger('qtgui')

from PySide.QtCore import *
from PySide.QtGui import *
from qt.ui_mainwindow import Ui_MainWindow
from qt.geocachedetailswindow import QtGeocacheDetailsWindow
from qt.searchgeocachesdialog import QtSearchGeocachesDialog
from qt.searchdialog import QtSearchDialog
from qt.optionsdialog import QtOptionsDialog
import sys
import geo
from gui import Gui
from qt.mapwidget import QtMap, QtOsdLayer, QtGeocacheLayer, QtMarksLayer

d = lambda x: x.decode('utf-8')
    
class QtGui(QMainWindow, Ui_MainWindow, Gui):

    USES = ['geonames']

    def __init__(self, core, dataroot, parent=None):
        #print 'mwinit'
        self.app = QApplication(sys.argv)
        QMainWindow.__init__(self, parent)
        self.core = core
        self.setupUi(self)
        self.setup_ui_map(dataroot)
        self.setup_ui_custom()
        self.setup_ui_signals()

    def set_target(self, cache):
        self.core.set_target(cache)


        ##############################################
        #
        # GUI stuff
        #
        ##############################################
        
    def setup_ui_map(self, dataroot):

        QtGeocacheLayer.TOO_MANY_POINTS = 150
        QtGeocacheLayer.MAX_NUM_RESULTS_SHOW = 1001
        QtGeocacheLayer.CACHES_ZOOM_LOWER_BOUND = 5
        noimage_cantload = "%s/noimage-cantload.png" % dataroot
        noimage_loading = "%s/noimage-loading.png" % dataroot
        QtMap.set_config(self.core.settings['map_providers'], self.core.settings['download_map_path'], noimage_cantload, noimage_loading)
        self.map = QtMap(self, geo.Coordinate(50, 7), 13)
        #self.mark_layer = QtSingleMarkLayer(geo.Coordinate(49, 6))
        #self.map.add_layer(self.mark_layer)
        self.geocacheLayer = QtGeocacheLayer(self.__get_geocaches_callback, self.__show_cache)
        self.map.add_layer(self.geocacheLayer)
        self.marksLayer = QtMarksLayer()
        self.map.add_layer(self.marksLayer)
        self.osd_layer = QtOsdLayer()
        self.map.add_layer(self.osd_layer)
        self.setCentralWidget(self.map)


    def setup_ui_custom(self):
        self.qa = QActionGroup(None)
        self.qa.addAction(self.actionBlub_1)
        self.qa.addAction(self.actionBlub_2)
        self.progressBarLabel = QLabel()
        self.progressBar = QProgressBar()
        self.progressBar.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.statusBar.addPermanentWidget(self.progressBar)
        self.labelPosition = QLabel()

        self.statusBar.addPermanentWidget(self.progressBar)
        self.statusBar.addPermanentWidget(self.progressBarLabel)
        self.statusBar.addWidget(self.labelPosition)
        self.progressBar.hide()

    def setup_ui_signals(self):
        self.actionSearch_Place.triggered.connect(self.__show_search_place)
        self.actionUpdate_Geocache_Map.triggered.connect(self.__download_overview)
        self.actionDownload_Details_for_all_visible_Geocaches.triggered.connect(self.__download_details_map)
        self.actionSearch_Geocaches.triggered.connect(self.__show_search_geocaches)
        self.actionOptions.triggered.connect(self.__show_options)
        self.map.centerChanged.connect(self.__update_progress_bar)
        self.core.connect('target-changed', self.marksLayer.on_target_changed)
        self.core.connect('good-fix', self.marksLayer.on_good_fix)
        self.core.connect('no-fix', self.marksLayer.on_no_fix)
        self.core.connect('settings-changed', self.__on_settings_changed)
        self.core.connect('save-settings', self._on_save_settings)
        

    def show(self):
        QMainWindow.show(self)
        self.core.connect('map-marks-changed', lambda caller: self.geocacheLayer.refresh())
        self.app.exec_()

    def __get_geocaches_callback(self, visible_area, maxresults):
        return self.core.pointprovider.get_points_filter(visible_area, None, maxresults)
        #return self.core.pointprovider.get_points_filter(visible_area, not self.settings['options_hide_found'], maxresults)


        ##############################################
        #
        # show subwindows
        #
        ##############################################

    def __show_search_geocaches(self):
        d = QtSearchGeocachesDialog(self.core, self.map.get_center(), self.core.current_position, self)
        d.show()

    def __show_cache(self, geocache):
        window = QtGeocacheDetailsWindow(self.core, self)
        window.show_geocache(geocache)
        window.show()

    def __show_search_place(self):
        #self.map.fit_to_bounds(47.301585, 55.021921, 8.407974, 10.244751)
        dialog = QtSearchDialog(self.core, self)
        dialog.show()
        dialog.locationSelected.connect(self.map.set_center)

    def __show_options(self):
        dialog = QtOptionsDialog(self.core, self.core.settings, self)
        dialog.setModal(True)
        dialog.saveSettings.connect(lambda: self.core.save_settings(dialog.get_settings(), self))
        dialog.show()


        ##############################################
        #
        # called by Core and Signals
        #
        ##############################################

    def __update_progress_bar(self):
        text = self.map.get_center().get_latlon()
        self.labelPosition.setText(d(text))

    def set_download_progress(self, fraction, text=''):
        self.progressBar.setValue(int(100 * fraction))
        self.progressBarLabel.setText(text)
        self.progressBar.show()

    def hide_progress(self):
        self.progressBarLabel.setText('')
        self.progressBar.hide()

    def show_error(self, errormsg):
        QMessageBox.warning(None, "Error", "%s" % errormsg, "close")

    def show_success(self, message):
        hildon.hildon_banner_show_information(self.window, "", message)


        ##############################################
        #
        # Downloading Geocaches
        #
        ##############################################

    def __download_overview(self):
        self.core.on_download(self.map.get_visible_area())

    def __download_details_map(self):
        self.core.on_download_descriptions(self.map.get_visible_area(), True)


        
        ##############################################
        #
        # Settings handling
        #
        ##############################################

    def _on_save_settings(self, caller):
        c = self.map.get_center()
        settings['map_position_lat'] = c.lat
        settings['map_position_lon'] = c.lon
        settings['map_zoom'] = self.map.get_zoom()
        settings['map_follow_position'] = self.marksLayer.get_follow_position()

        #if self.current_cache != None:
        #    settings['last_selected_geocache'] = self.current_cache.name

        #for i in ['options_username', 'options_password', 'download_noimages', 'options_show_name', 'options_hide_found', 'options_show_html_description', 'options_map_double_size', 'options_rotate_screen', 'tts_interval']:
        #    settings[i] = self.settings[i]
        caller.save_settings(settings, self)

    def __on_settings_changed(self, caller, settings, source):
        if 'last_target_lat' in settings:
            self.set_target(geo.Coordinate(settings['last_target_lat'], settings['last_target_lon']))



