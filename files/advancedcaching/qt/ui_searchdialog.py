# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'files/qt/SearchDialog.ui'
#
# Created: Tue Aug  3 13:52:33 2010
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_SearchDialog(object):
    def setupUi(self, SearchDialog):
        SearchDialog.setObjectName("SearchDialog")
        SearchDialog.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(SearchDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEditSearch = QtGui.QLineEdit(SearchDialog)
        self.lineEditSearch.setObjectName("lineEditSearch")
        self.horizontalLayout.addWidget(self.lineEditSearch)
        self.pushButtonSearch = QtGui.QPushButton(SearchDialog)
        self.pushButtonSearch.setObjectName("pushButtonSearch")
        self.horizontalLayout.addWidget(self.pushButtonSearch)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.listWidgetResults = QtGui.QListWidget(SearchDialog)
        self.listWidgetResults.setObjectName("listWidgetResults")
        self.verticalLayout.addWidget(self.listWidgetResults)

        self.retranslateUi(SearchDialog)
        QtCore.QMetaObject.connectSlotsByName(SearchDialog)

    def retranslateUi(self, SearchDialog):
        SearchDialog.setWindowTitle(QtGui.QApplication.translate("SearchDialog", "Search Place", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonSearch.setText(QtGui.QApplication.translate("SearchDialog", "Search", None, QtGui.QApplication.UnicodeUTF8))

