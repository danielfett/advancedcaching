
import logging
logger = logging.getLogger('qtgui')

from PyQt4.QtCore import *
from PyQt4.QtGui import *
logger.debug("Using pyqt bindings")
#from PyQt4.QtNetwork import *
from qt_mainwindow import Ui_MainWindow
from qt_searchdialog import Ui_SearchDialog
import sys
import geo
from qtmap import QtMap, QtOsdLayer, QtSingleMarkLayer, QtGeocacheLayer, QtMarksLayer

class Gui():
    USES = []
    
class QtGui(QMainWindow, Ui_MainWindow, Gui):

    USES = ['geonames']

    def __init__(self, core, dataroot, parent = None):
        #print 'mwinit'
        self.app = QApplication(sys.argv)
        QMainWindow.__init__(self, parent)
        self.core = core
        noimage_cantload = "%s/noimage-cantload.png" % dataroot
        noimage_loading = "%s/noimage-loading.png" % dataroot
        QtMap.set_config(self.core.settings['map_providers'], self.core.settings['download_map_path'], noimage_cantload, noimage_loading)
        self.setupUi(self)
        self.qa = QActionGroup(None)
        self.qa.addAction(self.actionBlub_1)
        self.qa.addAction(self.actionBlub_2)
        self.map = QtMap(self, geo.Coordinate(50, 7), 13)
        self.setCentralWidget(self.map)
        self.osd_layer = QtOsdLayer()
        self.map.add_layer(self.osd_layer)
        #self.mark_layer = QtSingleMarkLayer(geo.Coordinate(49, 6))
        #self.map.add_layer(self.mark_layer)
        gl = QtGeocacheLayer(core.pointprovider, lambda x: 1)
        self.map.add_layer(gl)
        self.marks_layer = QtMarksLayer()
        self.map.add_layer(self.marks_layer)
        self.connect(self.actionZoom_In, SIGNAL("triggered()"), self.map.zoom_in)
        self.connect(self.actionZoom_Out, SIGNAL("triggered()"), self.map.zoom_out)
        self.connect(self.actionSearch_Place, SIGNAL('triggered()'), self.__show_search_place)
        core.connect('target-changed', self.marks_layer.on_target_changed)
        core.connect('good-fix', self.marks_layer.on_good_fix)
        core.connect('no-fix', self.marks_layer.on_no_fix)
        core.connect('settings-changed', self._on_settings_changed)

    def show(self):
        QMainWindow.show(self)
        sys.exit(self.app.exec_())

    def _on_settings_changed(self, caller, settings, source):
        if 'last_target_lat' in settings:
            self.set_target(geo.Coordinate(settings['last_target_lat'], settings['last_target_lon']))

    def __show_search_place(self):
        dialog = QtSearchDialog(self.core, self)
        dialog.show()
        self.connect(dialog, SIGNAL("locationSelected(PyQt_PyObject)"), self.map.set_center)

    def set_target(self, cache):
        self.core.set_target(cache)

logger = logging.getLogger('qtsearchdialog')

class QtSearchDialog(Ui_SearchDialog, QDialog):
    def __init__(self, core, parent = None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.core = core
        self.connect(self.pushButtonSearch, SIGNAL('clicked()'), self.__start_search)
        self.connect(self.lineEditSearch, SIGNAL('returnPresed()'), self.__start_search)
        self.connect(self.listWidgetResults, SIGNAL('itemClicked (QListWidgetItem *)'), self.__return_location)

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
        self.core.current_position = geo.Coordinate(49.736927,6.686951)
        i = 0
        if self.core.current_position == None:
            for res in self.results:
                m = QListWidgetItem(res.name, self.listWidgetResults)
                m.setData(Qt.UserRole, i)
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
        self.emit(SIGNAL('locationSelected(PyQt_PyObject)'), res)

        



        