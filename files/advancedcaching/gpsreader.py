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
import socket

try:
    import location
except (ImportError):
    print "If you're on maemo, please install python-location"

class Fix():
    BEARING_HOLD_EPD = 90 # arbitrary, yet non-random value
    last_bearing = 0
    
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
            error_bearing = 0):
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

    @staticmethod
    def from_tuple(f, device):
        a = Fix()
        if (not f[1] & (location.GPS_DEVICE_LATLONG_SET | location.GPS_DEVICE_ALTITUDE_SET | location.GPS_DEVICE_TRACK_SET)):
            return a
        a.position = geo.Coordinate(f[4], f[5])
        a.altitude = f[7]
        if f[10] > Fix.BEARING_HOLD_EPD:
            a.bearing = Fix.last_bearing
        else:
            a.bearing = f[9]
            Fix.last_bearing = a.bearing
        a.speed = f[11]
        a.sats = device.satellites_in_use
        a.sats_known = device.satellites_in_view
        a.dgps = False
        a.quality = 0
        a.error = f[6]/100.0
        a.error_bearing = f[10]
        return a

class GpsReader():

    BEARING_HOLD_SPEED = 0.62 # meters per second. empirical value.
    QUALITY_LOW_BOUND = 5.0 # meters of HDOP.
    DGPS_ADVANTAGE = 1 # see below for usage


    EMPTY = Fix()

    def __init__(self):
        self.status = "connecting..."
        self.connected = False
        self.last_bearing = 0
        # enable this to track speeds and see the max speed
        # self.speeds = []


    def connect(self):
        try:

            self.gpsd_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.gpsd_connection.connect(("127.0.0.1", 2947))
            self.status = "connected"
            self.connected = True
        except:
            self.status = "Could not connect to GPSD on Localhost, Port 2947"
            print "Could not connect"
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
            except:
                print "GPSD Output: \n%s\n  -- cannot be parsed." % data
                self.status = "Could not read GPSD output."
            alt = self.to_float(alt)
            track = self.to_float(track)
            speed = self.to_float(speed)
            err_hor = self.to_float(err_hor)

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

            if speed < self.BEARING_HOLD_SPEED:
                error_bearing = 360
            else:
                error_bearing = 0
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
                error_bearing = error_bearing
                )
        except Exception, e:
            print "Fehler beim Auslesen der Daten: %s " % e
            return self.EMPTY

    @staticmethod
    def to_float(string):
        try:
            return float(string)
        except:
            return 0.0


class FakeGpsReader():


    START_LAT = 49.6
    START_LON = 6.6
    INC = 0.001
    

    def __init__(self, something):
        self.status = "faking..."
        self.current_lat, self.current_lon = (self.START_LAT, self.START_LON)

    def get_data(self):
        print "faking"
        self.current_lat += self.INC
        self.current_lon += self.INC
        return Fix(
            position = geo.Coordinate(self.current_lat, self.current_lon),
            altitude = 212,
            bearing = 120,
            speed = 2,
            sats = 42,
            sats_known = 42,
            dgps = True,
            quality = 0,
            error = 50
            )


class LocationGpsReader():
    def __init__(self, cb_error, cb_changed):
        print "+ Using liblocation GPS device"

        control = location.GPSDControl.get_default()
        device = location.GPSDevice()
        control.set_properties(preferred_method = location.METHOD_GNSS | location.METHOD_AGNSS, preferred_interval=location.INTERVAL_1S)
        control.connect("error-verbose", cb_error)
        device.connect("changed", cb_changed)
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
