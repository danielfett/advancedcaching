# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger('qtgui')

from PyQt4.QtCore import *
from PyQt4.QtGui import *
logger.debug("Using pyqt bindings")
#from PyQt4.QtNetwork import *
from qt_mainwindow import Ui_MainWindow
from qt_searchdialog import Ui_SearchDialog
from qt_showimagedialog import Ui_ShowImageDialog
from qt_geocachedetailswindow import Ui_GeocacheDetailsWindow
import sys
import geo
import geocaching
from gui import Gui
from qtmap import QtMap, QtOsdLayer, QtGeocacheLayer, QtMarksLayer

d = lambda x: x.decode('utf-8')
    
class QtGui(QMainWindow, Ui_MainWindow, Gui):

    USES = ['geonames']

    def __init__(self, core, dataroot, parent = None):
        #print 'mwinit'
        self.app = QApplication(sys.argv)
        QMainWindow.__init__(self, parent)
        self.core = core
        self.setupUi(self)
        self.setup_ui_map(dataroot)
        self.setup_ui_custom()
        self.setup_ui_signals()

    def __on_settings_changed(self, caller, settings, source):
        if 'last_target_lat' in settings:
            self.set_target(geo.Coordinate(settings['last_target_lat'], settings['last_target_lon']))

    def set_target(self, cache):
        self.core.set_target(cache)


        ##############################################
        #
        # GUI stuff
        #
        ##############################################
        
    def setup_ui_map(self, dataroot):
        noimage_cantload = "%s/noimage-cantload.png" % dataroot
        noimage_loading = "%s/noimage-loading.png" % dataroot
        QtMap.set_config(self.core.settings['map_providers'], self.core.settings['download_map_path'], noimage_cantload, noimage_loading)
        self.map = QtMap(self, geo.Coordinate(50, 7), 13)
        self.setCentralWidget(self.map)
        self.osd_layer = QtOsdLayer()
        self.map.add_layer(self.osd_layer)
        #self.mark_layer = QtSingleMarkLayer(geo.Coordinate(49, 6))
        #self.map.add_layer(self.mark_layer)
        self.geocacheLayer = QtGeocacheLayer(self.core.pointprovider, self.__show_cache)
        self.map.add_layer(self.geocacheLayer)
        self.marksLayer = QtMarksLayer()
        self.map.add_layer(self.marksLayer)


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
        self.actionZoom_In.triggered.connect(self.map.zoom_in)
        self.actionZoom_Out.triggered.connect(self.map.zoom_out)
        self.actionSearch_Place.triggered.connect(self.__show_search_place)
        self.actionUpdate_Geocache_Map.triggered.connect(self.__download_overview)
        self.actionDownload_Details_for_all_visible_Geocaches.triggered.connect(self.__download_details_map)
        self.map.centerChanged.connect(self.__update_progress_bar)
        self.core.connect('target-changed', self.marksLayer.on_target_changed)
        self.core.connect('good-fix', self.marksLayer.on_good_fix)
        self.core.connect('no-fix', self.marksLayer.on_no_fix)
        self.core.connect('settings-changed', self.__on_settings_changed)
        

    def show(self):
        QMainWindow.show(self)
        self.core.connect('map-marks-changed', lambda caller: self.geocacheLayer.refresh())
        sys.exit(self.app.exec_())

    def __show_search_place(self):
        dialog = QtSearchDialog(self.core, self)
        dialog.show()
        dialog.locationSelected.connect(self.map.set_center)

    def __update_progress_bar(self):
        text = self.map.get_center().get_latlon()
        self.labelPosition.setText(d(text))

    def __show_cache(self, geocache):
        window = QtGeocacheWindow(self.core, self)
        window.show_geocache(geocache)
        window.show()

        ##############################################
        #
        # called by Core and Signals
        #
        ##############################################

    def set_download_progress(self, fraction, text = ''):
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

logger = logging.getLogger('qtsearchdialog')

class QtSearchDialog(Ui_SearchDialog, QDialog):

    locationSelected = pyqtSignal(geo.Coordinate)

    def __init__(self, core, parent = None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.core = core
        self.pushButtonSearch.clicked.connect(self.__start_search)
        self.lineEditSearch.returnPressed.connect(self.__start_search)
        self.listWidgetResults.itemClicked.connect(self.__return_location)

    def __start_search(self):
        search_text = unicode(self.lineEditSearch.text()).strip()
        if search_text == '':
            return
        try:
            self.results = self.core.search_place(search_text)
        except Exception, e:
            QErrorMessage.qtHandler().showMessage(repr(e))
            logger.exception(repr(e))
        self.listWidgetResults.clear()
        if len(self.results) == 0:
            QMessageBox.information(self, "Search results", "The search returned no results.")
            return

        i = 0
        if self.core.current_position == None:
            for res in self.results:
                m = QListWidgetItem(res.name, self.listWidgetResults)
                m.setData(Qt.UserRole, QVariant(i))
                i += 1
        else:
            pos = self.core.current_position
            for res in self.results:
                distance = geo.Coordinate.format_distance(res.distance_to(pos))
                direction = geo.Coordinate.format_direction(pos.bearing_to(res))
                text = "%s (%s %s)" % (res.name, distance, direction)
                m = QListWidgetItem(text, self.listWidgetResults)
                m.setData(Qt.UserRole, QVariant(i))
                i += 1
        
    def __return_location(self, item):
        res = self.results[item.data(Qt.UserRole).toInt()[0]]
        logger.debug("Setting center to %s" % res)
        self.locationSelected.emit(res)

        


logger = logging.getLogger('qtgeocachewindow')


from os import path, extsep
import re

class QtGeocacheWindow(QMainWindow, Ui_GeocacheDetailsWindow):

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

    def __init__(self, core, parent = None):
        QMainWindow.__init__(self, parent)
        self.core = core
        self.setupUi(self)

    def show_geocache(self, geocache):

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



logger = logging.getLogger('qtshowimagedialog')

class QtShowImageDialog(Ui_ShowImageDialog, QDialog):

    def __init__(self, parent = None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.size_hint = QSize(10, 10)

    def show_image(self, pixmap):
        self.labelImage.setPixmap(pixmap)
        self.size_hint = pixmap.size()
        self.labelImage.adjustSize()
        self.scrollAreaWidgetContents.adjustSize()
        self.scrollArea.adjustSize()
        self.adjustSize()

    def sizeHint(self):
        return self.size_hint