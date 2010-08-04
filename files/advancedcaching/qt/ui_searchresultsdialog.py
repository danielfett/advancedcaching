# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'files/qt/SearchResultsDialog.ui'
#
# Created: Wed Aug  4 14:54:50 2010
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_SearchResultsDialog(object):
    def setupUi(self, SearchResultsDialog):
        SearchResultsDialog.setObjectName("SearchResultsDialog")
        SearchResultsDialog.resize(613, 605)
        self.verticalLayout = QtGui.QVBoxLayout(SearchResultsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableWidgetResults = QtGui.QTableWidget(SearchResultsDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidgetResults.sizePolicy().hasHeightForWidth())
        self.tableWidgetResults.setSizePolicy(sizePolicy)
        self.tableWidgetResults.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidgetResults.setAlternatingRowColors(True)
        self.tableWidgetResults.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tableWidgetResults.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidgetResults.setShowGrid(False)
        self.tableWidgetResults.setWordWrap(True)
        self.tableWidgetResults.setObjectName("tableWidgetResults")
        self.tableWidgetResults.setColumnCount(5)
        self.tableWidgetResults.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetResults.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetResults.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetResults.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetResults.setHorizontalHeaderItem(3, item)
        item = QtGui.QTableWidgetItem()
        self.tableWidgetResults.setHorizontalHeaderItem(4, item)
        self.tableWidgetResults.horizontalHeader().setVisible(True)
        self.tableWidgetResults.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidgetResults.horizontalHeader().setHighlightSections(True)
        self.tableWidgetResults.horizontalHeader().setMinimumSectionSize(40)
        self.tableWidgetResults.horizontalHeader().setSortIndicatorShown(True)
        self.tableWidgetResults.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetResults.verticalHeader().setVisible(False)
        self.tableWidgetResults.verticalHeader().setSortIndicatorShown(False)
        self.tableWidgetResults.verticalHeader().setStretchLastSection(False)
        self.verticalLayout.addWidget(self.tableWidgetResults)
        self.pushButtonExportSelected = QtGui.QPushButton(SearchResultsDialog)
        self.pushButtonExportSelected.setObjectName("pushButtonExportSelected")
        self.verticalLayout.addWidget(self.pushButtonExportSelected)

        self.retranslateUi(SearchResultsDialog)
        QtCore.QMetaObject.connectSlotsByName(SearchResultsDialog)

    def retranslateUi(self, SearchResultsDialog):
        SearchResultsDialog.setWindowTitle(QtGui.QApplication.translate("SearchResultsDialog", "Search Results", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidgetResults.setSortingEnabled(True)
        self.tableWidgetResults.horizontalHeaderItem(0).setText(QtGui.QApplication.translate("SearchResultsDialog", "Geocache", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidgetResults.horizontalHeaderItem(1).setText(QtGui.QApplication.translate("SearchResultsDialog", "Size", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidgetResults.horizontalHeaderItem(2).setText(QtGui.QApplication.translate("SearchResultsDialog", "T", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidgetResults.horizontalHeaderItem(3).setText(QtGui.QApplication.translate("SearchResultsDialog", "D", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidgetResults.horizontalHeaderItem(4).setText(QtGui.QApplication.translate("SearchResultsDialog", "Distance", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonExportSelected.setText(QtGui.QApplication.translate("SearchResultsDialog", "Export selected...", None, QtGui.QApplication.UnicodeUTF8))

