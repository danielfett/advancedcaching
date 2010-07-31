from PyQt4.QtCore import *
from PyQt4.QtGui import *
#from PyQt4.QtNetwork import *
from qt_main import Ui_MainWindow
import sys
import geo
from qtmap import QtMap, QtOsdLayer, QtSingleMarkLayer, QtGeocacheLayer

class Gui():
    USES = []

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

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, core, parent = None):
        #print 'mwinit'
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.painting = QtMap(self, geo.Coordinate(49, 6), 13)
        self.setCentralWidget(self.painting)
        self.osd_layer = QtOsdLayer()
        self.painting.add_layer(self.osd_layer)
        self.mark_layer = QtSingleMarkLayer(geo.Coordinate(49, 6))
        self.painting.add_layer(self.mark_layer)
        gl = QtGeocacheLayer(core.pointprovider, lambda x: 1)
        self.painting.add_layer(gl)
