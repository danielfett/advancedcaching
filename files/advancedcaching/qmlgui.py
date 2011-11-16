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

from PySide import QtGui
from PySide import QtDeclarative
from PySide import QtOpenGL
import os
import sys
from gui import Gui

d = lambda x: x.decode('utf-8')

class lm():
    pass


class QmlGui(Gui):

    USES = ['geonames']

    def __init__(self, core, dataroot, parent=None):
        self.app = QtGui.QApplication(sys.argv)

        landmarkModelAll = lm()
        self.view = QtDeclarative.QDeclarativeView()
        self.view.statusChanged.connect(self._status_changed)
        glw = QtOpenGL.QGLWidget()
        self.view.setViewport(glw)
        self.view.setSource(os.path.join('qml','main.qml'))


    def show(self):
        self.view.showFullScreen()
        self.app.exec_()

    def _status_changed(self, error):
        logger.error(self.view.errors())
