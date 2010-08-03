set -o verbose
pyuic4 files/qt/MainWindow.ui > files/advancedcaching/qt/ui_mainwindow.py
pyuic4 files/qt/SearchDialog.ui > files/advancedcaching/qt/ui_searchdialog.py
pyuic4 files/qt/ShowImageDialog.ui > files/advancedcaching/qt/ui_showimagedialog.py
pyuic4 files/qt/GeocacheDetailsWindow.ui > files/advancedcaching/qt/ui_geocachedetailswindow.py
pyuic4 files/qt/SearchGeocachesDialog.ui > files/advancedcaching/qt/ui_searchgeocachesdialog.py
pyuic4 files/qt/SearchResultsDialog.ui > files/advancedcaching/qt/ui_searchresultsdialog.py
pyrcc4 files/qt/icons.qrc > files/advancedcaching/qt/icons_rc.py
