
#!/usr/bin/python
# -*- coding: utf-8 -*-

#        Copyright (C) 2009 Daniel Fett
#         This program is free software: you can redistribute it and/or modify
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
#        Author: Daniel Fett advancedcaching@fragcom.de
#

import geo
from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime
import logging

logger = logging.getLogger('gpsreader')

try:
    import location
except (ImportError):
    logger.warning("If you're on maemo, please install python-location")

class Fix():
    BEARING_HOLD_EPD = 90 # arbitrary, yet non-random value
    last_bearing = 0
    # tracking the minimum difference between a received fix time and
    # our current internal time. 
    min_timediff = datetime.utcnow() - datetime.utcfromtimestamp(0)
    
    def __init__(self,
            position = None,
            altitude = None,
            bearing = None,
            speed = None,
            sats = 0,
            sats_known = 0,
            dgps = False,
            quality = 0,
            error = 0,
            error_bearing = 0,
            timestamp = None):
        self.position = position
        self.altitude = altitude
        self.bearing = bearing
        self.speed = speed
        self.sats = sats
        self.sats_known = sats_known
        self.dgps = dgps
        self.quality = quality
        self.error = error
        self.error_bearing = error_bearing
        if timestamp == None:
            self.timestamp = datetime.utcnow()
        else:
            self.timestamp = timestamp



class GpsReader():

    BEARING_HOLD_SPEED = 0.62 # meters per second. empirical value.
    QUALITY_LOW_BOUND = 5.0 # meters of HDOP.
    DGPS_ADVANTAGE = 1 # see below for usage
    PORT = 2947
    HOST = '127.0.0.1'

    EMPTY = Fix()

    def __init__(self):
        logger.info("Using GPSD gps reader on port %d host %s" % (self.PORT, self.HOST))
        self.status = "connecting..."
        self.connected = False
        self.last_bearing = 0
        # enable this to track speeds and see the max speed
        # self.speeds = []


    def connect(self):
        try:

            self.gpsd_connection = socket(AF_INET, SOCK_STREAM)
            self.gpsd_connection.connect((self.HOST, self.PORT))
            self.status = "connected"
            self.connected = True
        except:
            text = "Could not connect to GPSD!"
            logger.warning(text)
            self.status = text
            self.connected = False

    def get_data(self):
        try:
            if not self.connected:
                self.connect()
                if not self.connected:
                    return self.EMPTY
            self.gpsd_connection.send("%s\r\n" % 'o')
            data = self.gpsd_connection.recv(512)
            self.gpsd_connection.send("%s\r\n" % 'y')
            quality_data = self.gpsd_connection.recv(512)
            # 1: Parse Quality Data

            # example output:
            # GPSD,Y=- 1243847265.000 10:32 3 105 0 0:2 36 303 20 0:16 9 65 26
            #  1:13 87 259 35 1:4 60 251 30 1:23 54 60 37 1:25 51 149 24 0:8 2
            #  188 0 0:7 33 168 24 1:20 26 110 28 1:
            if quality_data.strip() == "GPSD,Y=?":
                sats = 0
                sats_known = 0
                dgps = False
            else:
                sats = 0
                dgps = False
                groups = quality_data.split(':')
                sats_known = int(groups[0].split(' ')[2])
                for i in xrange(1, sats_known):
                    sat_data = groups[i].split(' ')
                    if sat_data[4] == "1":
                        sats = sats + 1
                    if int(sat_data[0]) > 32:
                        dgps = True


            if data.strip() == "GPSD,O=?":
                self.status = "No GPS signal"
                return Fix(sats = sats, sats_known = sats_known, dgps = dgps)


            # 2: Get current position, altitude, bearing and speed

            # example output:
            # GPSD,O=- 1243530779.000 ? 49.736876 6.686998 271.49 1.20 1.61 49.8566 0.050 -0.175 ? ? ? 3
            # GPSD,O=- 1251325613.000 ? 49.734453 6.686360 ? 10.55 ? 180.1476 1.350 ? ? ? ? 2
            # that means:
            # [tag, timestamp, time_error, lat, lon, alt, err_hor, err_vert, track, speed, delta_alt, err_track, err_speed, err_delta_alt, mode]
            #  0    1          2           3    4    5    6        7         8      9      10         11         12         13             14
            # or
            # GPSD,O=?
            try:
                splitted = data.split(' ')
                lat, lon, alt, err_hor = splitted[3:7]
                track, speed = splitted[8:10]
                err_track = splitted[11]
                time = datetime.utcfromtimestamp(int(float(splitted[1])))
            except:
                logger.info("GPSD Output: \n%s\n  -- cannot be parsed." % data)
                self.status = "Could not read GPSD output."
                return Fix()
            alt = self.to_float(alt)
            track = self.to_float(track)
            speed = self.to_float(speed)
            err_hor = self.to_float(err_hor)
            err_track = self.to_float(err_track)

            # the following is probably wrong:
            #
            # it seems that gpsd doesn't take into account that the
            # receiver may get signals from space base augmentation systems
            # like egnos. therefore, we estimate that the error is about
            # self.DGPS_ADVANTAGE meters lower. this is a complete guess.

            if dgps:
                err_hor -= self.DGPS_ADVANTAGE

            if err_hor <= 0:
                quality = 1
            elif err_hor > self.QUALITY_LOW_BOUND:
                quality = 0
            else:
                quality = 1-err_hor/self.QUALITY_LOW_BOUND

            # enable this to track speeds and see the max speed
            #self.speeds.append(speed)
            #print "Aktuell %f, max: %f" % (speed, max(self.speeds))

            return Fix(
                position =geo.Coordinate(float(lat), float(lon)),
                altitude = alt,
                bearing = track,
                speed = speed,
                sats = int(sats),
                sats_known = sats_known,
                dgps = dgps,
                quality = quality,
                error = err_hor,
                error_bearing = err_track,
                timestamp = time
                )
        except Exception, e:
            logger.exception("Fehler beim Auslesen der Daten: %s " % e)
            return self.EMPTY

    @staticmethod
    def to_float(string):
        try:
            return float(string)
        except:
            return 0.0

class LocationGpsReader():
    TIMEOUT = 5
    BEARING_HOLD_SPEED = 2.5 # km/h

    def __init__(self, cb_error, cb_changed):
        logger.info("Using liblocation GPS device")

        control = location.GPSDControl.get_default()
        device = location.GPSDevice()
        control.set_properties(preferred_method = location.METHOD_CWP | location.METHOD_ACWP | location.METHOD_GNSS | location.METHOD_AGNSS, preferred_interval=location.INTERVAL_1S)
        control.connect("error-verbose", cb_error)
        device.connect("changed", cb_changed)
        self.last_gps_bearing = 0
        self.control = control
        self.device = device


    def start(self):
        self.control.start()
        return False

    @staticmethod
    def get_error_from_code(error):
        if error == location.ERROR_USER_REJECTED_DIALOG:
            return "Requested GPS method not enabled"
        elif error == location.ERROR_USER_REJECTED_SETTINGS:
            return "Location disabled due to change in settings"
        elif error == location.ERROR_BT_GPS_NOT_AVAILABLE:
            return "Problems with BT GPS"
        elif error == location.ERROR_METHOD_NOT_ALLOWED_IN_OFFLINE_MODE:
            return "Requested method is not allowed in offline mode"
        elif error == location.ERROR_SYSTEM:
            return "System error"

    def fix_from_tuple(self, f, device):
        a = Fix()
        # check if this is an actual fix
        if (not f[1] & (location.GPS_DEVICE_LATLONG_SET | location.GPS_DEVICE_ALTITUDE_SET | location.GPS_DEVICE_TRACK_SET)):
            return a

        # location independent data
        a.sats = device.satellites_in_use
        a.sats_known = device.satellites_in_view
        a.dgps = False
        a.quality = 0



        # if this fix is too old, discard it
        if f[2] == f[2]: # is not NaN
            a.timestamp = datetime.utcfromtimestamp(f[2])
        else:
            a.timestamp = datetime.utcfromtimestamp(0)

        Fix.min_timediff = min(Fix.min_timediff, datetime.utcnow() - a.timestamp)
        # if this fix is too old, discard it
        if ((datetime.utcnow() - a.timestamp) - Fix.min_timediff).seconds > LocationGpsReader.TIMEOUT:
            logger.info("Discarding fix: Timestamp diff is %d, should not be > %d" % (((datetime.utcnow() - a.timestamp) - Fix.min_timediff).seconds, LocationGpsReader.TIMEOUT))
            return a

        # now on for location dependent data
        #if f[10] > Fix.BEARING_HOLD_EPD:
        #    a.bearing = Fix.last_bearing
        #else:
        a.altitude = f[7]
        a.speed = f[11]
        if a.speed > self.BEARING_HOLD_SPEED:
            a.bearing = f[9]
            self.last_gps_bearing = a.bearing
        else:
            a.bearing = self.last_gps_bearing

        #    Fix.last_bearing = a.bearing
        a.position = geo.Coordinate(f[4], f[5])

        a.error = f[6]/100.0
        a.error_bearing = f[10]

        return a

class FakeGpsReader():


    INC = 0.0001
    

    def __init__(self, something):
        self.status = "Fake GPS reader."
        self.index = -1
        self.data = [x.split('\t') for x in self.TESTDATA.split("\n")]
        self.lastpos = None

    @staticmethod
    def get_target():
        return geo.Coordinate(50.0000798795372000, 6.9949468020349700)

    def get_data(self):
        import random
        if self.index < len(self.data) - 1:
            self.index += 1
        if self.data[self.index][0] == '0':
            return Fix()
        pos = geo.Coordinate(float(self.data[self.index][0]), float(self.data[self.index][1]))

        if self.lastpos != None:
            bearing = self.lastpos.bearing_to(pos)
        else:
            bearing = 0
        self.lastpos = pos
        return Fix(
            position = pos,
            altitude = 5,
            bearing = bearing,
            speed = 4,
            sats = 12,
            sats_known = 6,
            dgps = True,
            quality = 0,
            error = random.randrange(10, 100),
            error_bearing = 10
            )

    TESTDATA = '''0	0
0	0
0	0
50.0000000000000000	7.0000000000000000
49.9999706633389000	7.0001229625195300
49.9997950624675000	7.0003442447632600
49.9997997563332000	7.0004659499973100
49.9997218046337000	7.0005903374403700
49.9995578546077000	7.0006271339952900
49.9994435254484000	7.0008635874837600
49.9993037991226000	7.0009828619659000
49.9992146994919000	7.0010608136653900
49.9991217441857000	7.0012173876166300
49.9990843608975000	7.0012444611638800
49.9990095943213000	7.0015110895037700
49.9988885596395000	7.0016821641475000
0	0
0	0
0	0
49.9987537786365000	7.0018086470663600
49.9985118769109000	7.0020990800112500
49.9983842205256000	7.0021572504192600
49.9982605036348000	7.0022816378623300
49.9980872496963000	7.0023336894810200
49.9979986529797000	7.0024224538356100
49.9979185219854000	7.0025429017841800
49.9978181067854000	7.0025481823831800
49.9976762011647000	7.0025224499404400
49.9975882750005000	7.0024726614356000
49.9974449444562000	7.0023075379431300
49.9973412603140000	7.0022041890770200
49.9972049705684000	7.0021101441234400
0	0
0	0
0	0
49.9970952514559000	7.0020336173474800
49.9969987757504000	7.0019501335918900
49.9968421179801000	7.0017190445214500
49.9967520125210000	7.0016104150563500
49.9966504238546000	7.0015143584460000
49.9965638387948000	7.0014302041381600
49.9964761640877000	7.0013357400894200
49.9963049218059000	7.0011528469622100
49.9962143134326000	7.0009845383465300
49.9961593281478000	7.0008703768253300
49.9960857350379000	7.0007528625428700
49.9960248824209000	7.0006081908941300
49.9959259759635000	7.0004951190203400
49.9958231300116000	7.0003485195338700
49.9957155063748000	7.0002043507993200
49.9956013448536000	7.0000658817589300
49.9954995047301000	6.9999083019793000
49.9954301863909000	6.9997342936694600
49.9954084772617000	6.9995050486177200
49.9953969940543000	6.9992866162210700
49.9965626653284000	6.9970068223774400
49.9966021440923000	6.9968105182051700
49.9968151282519000	6.9966180697083500
49.9971344787627000	6.9964923411607700
49.9972403421998000	6.9964339192956700
49.9973804876208000	6.9963862262666200
49.9979287479073000	6.9956857506185800
49.9980570748448000	6.9955223873257600
49.9982320051640000	6.9954270012676700
49.9984868150204000	6.9951742030680200
49.9985938519239000	6.9949829280376400
49.9986792635173000	6.9948330596089400
49.9987863004208000	6.9947258550673700
49.9990340694785000	6.9947269447147800
49.9992224946618000	6.9946833588182900
49.9994972534478000	6.9947828520089400
49.9996298551559000	6.9948167987167800
49.9997046217322000	6.9948615580797200
49.9997673183680000	6.9949107598513400
49.9999811407179000	6.9948655813932400
50.0000479444861000	6.9948898889124400
50.0000799633563000	6.9948716163635300
50.0000798795372000	6.9949468020349700'''
    pass

