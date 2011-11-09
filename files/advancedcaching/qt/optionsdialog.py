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

from PySide.QtCore import *
from PySide.QtGui import *
from ui_optionsdialog import Ui_OptionsDialog
logger = logging.getLogger('qtoptionsdialog')

d = lambda x: x.decode('utf-8')

class QtOptionsDialog(Ui_OptionsDialog, QDialog):

    saveSettings = Signal()

    TTS_SETTINGS = (
                (0, 'Off'),
                (-1, 'Automatic'),
                (10, '10 Seconds'),
                (20, '20 Seconds'),
                (30, '30 Seconds'),
                (50, '50 Seconds'),
                (100, '100 Seconds'),
                (180, '3 Minutes'),
                (5 * 60, '5 Minutes'),
                (10 * 60, '10 Minutes'),
                )

    def __init__(self, core, settings, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.core = core
        self.buttonBox.clicked.connect(self.__button_clicked)
        self.load_settings(settings)

    def load_settings(self, settings):
        self.lineEditUserName.setText(d(settings['options_username']))
        self.lineEditPassword.setText(d(settings['options_password']))
        self.checkBoxHideFound.setCheckState(Qt.Checked if settings['options_hide_found'] else Qt.Unchecked)
        self.checkBoxShowName.setCheckState(Qt.Checked if settings['options_show_name'] else Qt.Unchecked)
        self.checkBoxDoubleSize.setCheckState(Qt.Checked if settings['options_map_double_size'] else Qt.Unchecked)
        
        self.comboBoxTTS.clear()
        i = 0 
        for time, text in self.TTS_SETTINGS:
            self.comboBoxTTS.addItem(text)
            if time == settings['tts_interval']:
                self.comboBoxTTS.setCurrentIndex(i)
            i += 1

    def get_settings(self):
        return {
            'options_username' : unicode(self.lineEditUserName.text()),
            'options_password' : unicode(self.lineEditPassword.text()),
            'options_hide_found' : (self.checkBoxHideFound.checkState() == Qt.Checked),
            'options_show_name' : (self.checkBoxShowName.checkState() == Qt.Checked),
            'options_map_double_size' : (self.checkBoxDoubleSize.checkState() == Qt.Checked),
            'tts_interval' : self.TTS_SETTINGS[self.comboBoxTTS.currentIndex()][0]
        }
        
    def __button_clicked(self, button):
        id = self.buttonBox.standardButton(button)
        if id == QDialogButtonBox.Ok:
            self.saveSettings.emit()