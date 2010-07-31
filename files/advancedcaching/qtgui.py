
import logging
logger = logging.getLogger('qtgui')

from PyQt4.QtCore import *
from PyQt4.QtGui import *
logger.debug("Using pyqt bindings")
#from PyQt4.QtNetwork import *
from qt_main import Ui_MainWindow
import sys
import geo
from qtmap import QtMap, QtOsdLayer, QtSingleMarkLayer, QtGeocacheLayer, QtMarksLayer

class Gui():
    USES = []
'''
class QtGui(Gui):
    def __init__(self, core, dataroot):
        self.app = QApplication(sys.argv)
        #core.connect('good-fix', self._on_good_fix)
        self.core = core
        noimage_cantload = "%s/noimage-cantload.png" % dataroot
        noimage_loading = "%s/noimage-loading.png" % dataroot
        QtMap.set_config(self.core.settings['map_providers'], self.core.settings['download_map_path'], noimage_cantload, noimage_loading)

    def show(self):
        a = MainWindow(self.core)
        a.show()
        sys.exit(self.app.exec_())
'''
class QtGui(QMainWindow, Ui_MainWindow, Gui):
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

    def set_target(self, cache):
        self.core.set_target(cache)