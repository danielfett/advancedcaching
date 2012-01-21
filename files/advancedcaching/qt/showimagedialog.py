#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2012 Daniel Fett
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

from PySide.QtCore import *
from PySide.QtGui import *
from ui_showimagedialog import Ui_ShowImageDialog
logger = logging.getLogger('qtshowimagedialog')

class QtShowImageDialog(Ui_ShowImageDialog, QDialog):

    def __init__(self, parent=None):
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

