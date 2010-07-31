# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'files/qt/test.ui'
#
# Created: Thu Jul 29 22:44:55 2010
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 20))
        self.menubar.setObjectName("menubar")
        self.menuMap = QtGui.QMenu(self.menubar)
        self.menuMap.setObjectName("menuMap")
        self.menuSearch = QtGui.QMenu(self.menubar)
        self.menuSearch.setObjectName("menuSearch")
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionHallo_Welt = QtGui.QAction(MainWindow)
        self.actionHallo_Welt.setObjectName("actionHallo_Welt")
        self.actionTsch_ss_Welt = QtGui.QAction(MainWindow)
        self.actionTsch_ss_Welt.setObjectName("actionTsch_ss_Welt")
        self.actionSelect_Map_Style = QtGui.QAction(MainWindow)
        self.actionSelect_Map_Style.setObjectName("actionSelect_Map_Style")
        self.actionGeocaches = QtGui.QAction(MainWindow)
        self.actionGeocaches.setObjectName("actionGeocaches")
        self.actionPlaces = QtGui.QAction(MainWindow)
        self.actionPlaces.setObjectName("actionPlaces")
        self.actionAbout_AGTL = QtGui.QAction(MainWindow)
        self.actionAbout_AGTL.setObjectName("actionAbout_AGTL")
        self.actionDownload_Map_Tiles = QtGui.QAction(MainWindow)
        self.actionDownload_Map_Tiles.setObjectName("actionDownload_Map_Tiles")
        self.menuMap.addAction(self.actionDownload_Map_Tiles)
        self.menuMap.addAction(self.actionSelect_Map_Style)
        self.menuSearch.addAction(self.actionGeocaches)
        self.menuSearch.addAction(self.actionPlaces)
        self.menuHelp.addAction(self.actionAbout_AGTL)
        self.menubar.addAction(self.menuMap.menuAction())
        self.menubar.addAction(self.menuSearch.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.menuMap.setTitle(QtGui.QApplication.translate("MainWindow", "Map", None, QtGui.QApplication.UnicodeUTF8))
        self.menuSearch.setTitle(QtGui.QApplication.translate("MainWindow", "Search", None, QtGui.QApplication.UnicodeUTF8))
        self.menuHelp.setTitle(QtGui.QApplication.translate("MainWindow", "Help", None, QtGui.QApplication.UnicodeUTF8))
        self.actionHallo_Welt.setText(QtGui.QApplication.translate("MainWindow", "Hallo Welt!", None, QtGui.QApplication.UnicodeUTF8))
        self.actionTsch_ss_Welt.setText(QtGui.QApplication.translate("MainWindow", "Tschüss Welt!", None, QtGui.QApplication.UnicodeUTF8))
        self.actionSelect_Map_Style.setText(QtGui.QApplication.translate("MainWindow", "Select Map Style", None, QtGui.QApplication.UnicodeUTF8))
        self.actionGeocaches.setText(QtGui.QApplication.translate("MainWindow", "Geocaches", None, QtGui.QApplication.UnicodeUTF8))
        self.actionGeocaches.setStatusTip(QtGui.QApplication.translate("MainWindow", "Test", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPlaces.setText(QtGui.QApplication.translate("MainWindow", "Places", None, QtGui.QApplication.UnicodeUTF8))
        self.actionAbout_AGTL.setText(QtGui.QApplication.translate("MainWindow", "About AGTL", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDownload_Map_Tiles.setText(QtGui.QApplication.translate("MainWindow", "Download Map Tiles", None, QtGui.QApplication.UnicodeUTF8))

