#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2011 Daniel Fett
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
logger = logging.getLogger('connection')

offline = False
_conic_connection = None

def _conic_connection_changed(connection, event, magic = None):
    global offline
    try: 
        import conic
    except ImportError:
        logger.debug("Not using conic library")
    status = event.get_status()
    if status == conic.STATUS_CONNECTED:
        offline = False
        logger.debug("Going online")
    elif status in [conic.STATUS_DISCONNECTED, conic.STATUS_DISCONNECTING]:
        offline = True
        logger.debug("Going offline")
    else: 
        logger.debug("Not touching offline mode.")

def init():
    try: 
        import conic
        logger.debug("Using conic library")
    except ImportError:
        logger.debug("Not using conic library")
        return

    global _conic_connection
    _conic_connection = conic.Connection()
    _conic_connection.connect("connection-event", _conic_connection_changed)
    _conic_connection.set_property("automatic-connection-events", True)
    logger.debug("Connection events initialized")


    

