# -*- coding: utf-8 -*-
#
# Copyright 2009-2010, Simon Kennedy, python@sffjunkie.co.uk
# Distributed under the terms of the MIT License.
#
# Shortened for AGTL by Daniel Fett 

import datetime
from math import cos, sin, tan, acos, asin, atan2, floor, radians, degrees

SUN_POSITION_CACHE_DURATION = 3600 # seconds

class Astral(object):

    sun_cache_result = None
    sun_cache_time = None
    instance = None

    def __init__(self):
        """Initialise the list of cities.
        """
        
        self._depression = 6  # Set default depression in degrees


    def solar_depression():
        doc = """The number of degrees the sun must be below the horizon for the dawn/dusk calc.
        
        Can either be set as a number of degrees below the horizon or as
        one of the following strings
        
        ============= =======
        String        Degrees
        ============= =======
        civil            6.0
        nautical        12.0
        astronomical    18.0
        ============= =======
        """
        
        def fget(self):
            return self._depression
            
        def fset(self, depression):
            if isinstance(depression, basestring):
                try:
                    self._depression = {'civil': 6, 'nautical': 12, 'astronomical': 18}[depression]
                except:
                    raise KeyError("solar_depression must be either a number or one of 'civil', 'nautical' or 'astronomical'")
            else:
                self._depression = float(depression)
            
        return locals()
        
    solar_depression = property(**solar_depression())

    def sun_utc(self, date, latitude, longitude):
        """Returns dawn, sunrise, noon, sunset and dusk times as a dictionary.
        """
        
        dawn = self.dawn_utc(date, latitude, longitude)
        sunrise = self.sunrise_utc(date, latitude, longitude)
        noon = self.solar_noon_utc(date, longitude)
        sunset = self.sunset_utc(date, latitude, longitude)
        dusk = self.dusk_utc(date, latitude, longitude)
        
        return {'dawn': dawn, 'sunrise': sunrise, 'noon': noon, 'sunset': sunset, 'dusk': dusk}

    def dawn_utc(self, date, latitude, longitude):
        """Calculate dawn time for a specific date at a particular position.
        
        Returns date/time in UTC
        """
        
        julianday = self._julianday(date.day, date.month, date.year)

        if latitude > 89.8:
            latitude = 89.8
            
        if latitude < -89.8:
            latitude = -89.8
        
        t = self._jday_to_jcentury(julianday)
        eqtime = self._eq_of_time(t)
        solarDec = self._sun_declination(t)
        
        try:
            hourangle = self._hour_angle_sunrise(latitude, solarDec)
        except:
            raise AstralError('Sun remains below horizon on this day, at this location.')

        delta = longitude - degrees(hourangle)
        timeDiff = 4.0 * delta
        timeUTC = 720.0 + timeDiff - eqtime

        newt = self._jday_to_jcentury(self._jcentury_to_jday(t) + timeUTC / 1440.0)
        eqtime = self._eq_of_time(newt)
        solarDec = self._sun_declination(newt)
        hourangle = self._hour_angle_dawn(latitude, solarDec, self._depression)
        delta = longitude - degrees(hourangle)
        timeDiff = 4 * delta
        timeUTC = 720 + timeDiff - eqtime
        
        timeUTC = timeUTC/60.0
        hour = int(timeUTC)
        minute = int((timeUTC - hour) * 60)
        second = int((((timeUTC - hour) * 60) - minute) * 60)

        if hour > 23.0:
            hour -= 24
            date += datetime.timedelta(days=1)

        dawn = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

        return dawn

    def sunrise_utc(self, date, latitude, longitude):
        """Calculate sunrise time for a specific date at a particular position.
        
        Returns date/time in UTC
        """
        
        julianday = self._julianday(date.day, date.month, date.year)

        t = self._jday_to_jcentury(julianday)
        eqtime = self._eq_of_time(t)
        solarDec = self._sun_declination(t)

        try:
            hourangle = self._hour_angle_sunrise(latitude, solarDec)
        except:
            raise AstralError('Sun remains below horizon on this day, at this location.')

        delta = longitude - degrees(hourangle)
        timeDiff = 4.0 * delta
        timeUTC = 720.0 + timeDiff - eqtime

        newt = self._jday_to_jcentury(self._jcentury_to_jday(t) + timeUTC / 1440.0)
        eqtime = self._eq_of_time(newt)
        solarDec = self._sun_declination(newt)
        hourangle = self._hour_angle_sunrise(latitude, solarDec)
        delta = longitude - degrees(hourangle)
        timeDiff = 4 * delta
        timeUTC = 720 + timeDiff - eqtime
        
        timeUTC = timeUTC/60.0
        hour = int(timeUTC)
        minute = int((timeUTC - hour) * 60)
        second = int((((timeUTC - hour) * 60) - minute) * 60)

        if hour > 23:
            hour -= 24
            date += datetime.timedelta(days=1)

        sunrise = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

        return sunrise

    def solar_noon_utc(self, date, longitude):
        """Calculate solar noon time for a specific date at a particular position.
        
        Returns date/time in UTC
        """
        
        julianday = self._julianday(date.day, date.month, date.year)

        newt = self._jday_to_jcentury(julianday + 0.5 + longitude / 360.0)

        eqtime = self._eq_of_time(newt)
        solarNoonDec = self._sun_declination(newt)
        timeUTC = 720.0 + (longitude * 4.0) - eqtime

        timeUTC = timeUTC/60.0
        hour = int(timeUTC)
        minute = int((timeUTC - hour) * 60)
        second = int((((timeUTC - hour) * 60) - minute) * 60)

        if hour > 23:
            hour -= 24
            date += datetime.timedelta(days=1)

        noon = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

        return noon

    def sunset_utc(self, date, latitude, longitude):
        """Calculate sunset time for a specific date at a particular position.
        
        Returns date/time in UTC
        """
        
        julianday = self._julianday(date.day, date.month, date.year)

        t = self._jday_to_jcentury(julianday)
        eqtime = self._eq_of_time(t)
        solarDec = self._sun_declination(t)

        try:
            hourangle = self._hour_angle_sunset(latitude, solarDec)
        except:
            raise AstralError('Sun remains below horizon on this day, at this location.')

        delta = longitude - degrees(hourangle)
        timeDiff = 4.0 * delta
        timeUTC = 720.0 + timeDiff - eqtime

        newt = self._jday_to_jcentury(self._jcentury_to_jday(t) + timeUTC / 1440.0)
        eqtime = self._eq_of_time(newt)
        solarDec = self._sun_declination(newt)
        hourangle = self._hour_angle_sunset(latitude, solarDec)
        delta = longitude - degrees(hourangle)
        timeDiff = 4 * delta
        timeUTC = 720 + timeDiff - eqtime
        
        timeUTC = timeUTC/60.0
        hour = int(timeUTC)
        minute = int((timeUTC - hour) * 60)
        second = int((((timeUTC - hour) * 60) - minute) * 60)

        if hour > 23:
            hour -= 24
            date += datetime.timedelta(days=1)

        sunset = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

        return sunset

    def dusk_utc(self, date, latitude, longitude):
        """Calculate dusk time for a specific date at a particular position.
        
        Returns date/time in UTC
        """
        
        julianday = self._julianday(date.day, date.month, date.year)

        if latitude > 89.8:
            latitude = 89.8
            
        if latitude < -89.8:
            latitude = -89.8
        
        t = self._jday_to_jcentury(julianday)
        eqtime = self._eq_of_time(t)
        solarDec = self._sun_declination(t)

        try:
            hourangle = self._hour_angle_sunset(latitude, solarDec)
        except:
            raise AstralError('Sun remains below horizon on this day, at this location.')

        delta = longitude - degrees(hourangle)
        timeDiff = 4.0 * delta
        timeUTC = 720.0 + timeDiff - eqtime

        newt = self._jday_to_jcentury(self._jcentury_to_jday(t) + timeUTC / 1440.0)
        eqtime = self._eq_of_time(newt)
        solarDec = self._sun_declination(newt)
        hourangle = self._hour_angle_dusk(latitude, solarDec, self._depression)
        delta = longitude - degrees(hourangle)
        timeDiff = 4 * delta
        timeUTC = 720 + timeDiff - eqtime
        
        timeUTC = timeUTC/60.0
        hour = int(timeUTC)
        minute = int((timeUTC - hour) * 60)
        second = int((((timeUTC - hour) * 60) - minute) * 60)

        if hour > 23:
            hour -= 24
            date += datetime.timedelta(days=1)

        dusk = datetime.datetime(date.year, date.month, date.day, hour, minute, second)

        return dusk

    def solar_azimuth(self, dateandtime, latitude, longitude):
        """Calculate the azimuth of the sun as a specific date/time and location.
        """
    
        if latitude > 89.8:
            latitude = 89.8
            
        if latitude < -89.8:
            latitude = -89.8
    
        zone = 0#-dateandtime.utcoffset().seconds / 3600.0
        utc_datetime = dateandtime #dateandtime.astimezone(pytz.utc)
        timenow = utc_datetime.hour + (utc_datetime.minute / 60.0) + (utc_datetime.second / 3600)

        JD = self._julianday(dateandtime.day, dateandtime.month, dateandtime.year)
        t = self._jday_to_jcentury(JD + timenow / 24.0)
        R = self._sun_rad_vector(t)
        alpha = self._sun_rt_ascension(t)
        theta = self._sun_declination(t)
        Etime = self._eq_of_time(t)
    
        eqtime = Etime
        solarDec = theta   # in degrees
        earthRadVec = R
    
        solarTimeFix = eqtime - (4.0 * longitude) + (60 * zone)
        trueSolarTime = dateandtime.hour * 60.0 + dateandtime.minute + dateandtime.second / 60.0 + solarTimeFix
        #    in minutes
    
        while trueSolarTime > 1440:
            trueSolarTime = trueSolarTime - 1440
        
        hourangle = trueSolarTime / 4.0 - 180.0
        #    Thanks to Louis Schwarzmayr for the next line:
        if hourangle < -180:
            hourangle = hourangle + 360.0
    
        harad = radians(hourangle)
    
        csz = sin(radians(latitude)) * sin(radians(solarDec)) + \
              cos(radians(latitude)) * cos(radians(solarDec)) * cos(harad)
    
        if csz > 1.0:
            csz = 1.0
        elif csz < -1.0:
            csz = -1.0
        
        zenith = degrees(acos(csz))
    
        azDenom = (cos(radians(latitude)) * sin(radians(zenith)))
        
        if (abs(azDenom) > 0.001):
            azRad = ((sin(radians(latitude)) *  cos(radians(zenith))) - sin(radians(solarDec))) / azDenom
            
            if abs(azRad) > 1.0:
                if azRad < 0:
                    azRad = -1.0
                else:
                    azRad = 1.0
    
            azimuth = 180.0 - degrees(acos(azRad))
    
            if hourangle > 0.0:
                azimuth = -azimuth
        else:
            if latitude > 0.0:
                azimuth = 180.0
            else:
                azimuth = 0#
    
        if azimuth < 0.0:
            azimuth = azimuth + 360.0
                 
        return azimuth

    def solar_elevation(self, dateandtime, latitude, longitude):
        """Calculate the elevation of the sun as a specific date/time and location.
        """
    
        if latitude > 89.8:
            latitude = 89.8
            
        if latitude < -89.8:
            latitude = -89.8

        zone = -dateandtime.utcoffset().seconds / 3600.0
        utc_datetime = dateandtime.astimezone(pytz.utc)
        timenow = utc_datetime.hour + (utc_datetime.minute / 60.0) + (utc_datetime.second / 3600)
    
        JD = self._julianday(dateandtime.day, dateandtime.month, dateandtime.year)
        t = self._jday_to_jcentury(JD + timenow / 24.0)
        R = self._sun_rad_vector(t)
        alpha = self._sun_rt_ascension(t)
        theta = self._sun_declination(t)
        Etime = self._eq_of_time(t)
    
        eqtime = Etime
        solarDec = theta   # in degrees
        earthRadVec = R
    
        solarTimeFix = eqtime - (4.0 * longitude) + (60 * zone)
        trueSolarTime = dateandtime.hour * 60.0 + dateandtime.minute + dateandtime.second / 60.0 + solarTimeFix
        #    in minutes
    
        while trueSolarTime > 1440:
            trueSolarTime = trueSolarTime - 1440
        
        hourangle = trueSolarTime / 4.0 - 180.0
        #    Thanks to Louis Schwarzmayr for the next line:
        if hourangle < -180:
            hourangle = hourangle + 360.0
    
        harad = radians(hourangle)
    
        csz = sin(radians(latitude)) * sin(radians(solarDec)) + \
              cos(radians(latitude)) * cos(radians(solarDec)) * cos(harad)
    
        if csz > 1.0:
            csz = 1.0
        elif csz < -1.0:
            csz = -1.0
        
        zenith = degrees(acos(csz))
    
        azDenom = (cos(radians(latitude)) * sin(radians(zenith)))
        
        if (abs(azDenom) > 0.001):
            azRad = ((sin(radians(latitude)) *  cos(radians(zenith))) - sin(radians(solarDec))) / azDenom
            
            if abs(azRad) > 1.0:
                if azRad < 0:
                    azRad = -1.0
                else:
                    azRad = 1.0
    
            azimuth = 180.0 - degrees(acos(azRad))
    
            if hourangle > 0.0:
                azimuth = -azimuth
        else:
            if latitude > 0.0:
                azimuth = 180.0
            else:
                azimuth = 0#
    
        if azimuth < 0.0:
            azimuth = azimuth + 360.0
                    
        exoatmElevation = 90.0 - zenith

        if exoatmElevation > 85.0:
            refractionCorrection = 0.0
        else:
            te = tan(radians(exoatmElevation))
            if exoatmElevation > 5.0:
                refractionCorrection = 58.1 / te - 0.07 / (te * te * te) + 0.000086 / (te * te * te * te * te)
            elif exoatmElevation > -0.575:
                step1 = (-12.79 + exoatmElevation * 0.711)
                step2 = (103.4 + exoatmElevation * (step1))
                step3 = (-518.2 + exoatmElevation * (step2))
                refractionCorrection = 1735.0 + exoatmElevation * (step3)
            else:
                refractionCorrection = -20.774 / te
    
            refractionCorrection = refractionCorrection / 3600.0
            
        solarzen = zenith - refractionCorrection
                     
        solarelevation = 90.0 - solarzen
    
        return solarelevation

    def _julianday(self, day, month, year):
        if month <= 2:
            year = year - 1
            month = month + 12
        
        A = floor(year / 100.0)
        B = 2 - A + floor(A / 4.0)

        return floor(365.25 * (year + 4716)) + floor(30.6001 * (month + 1)) + day + B - 1524.5
        
    def _jday_to_jcentury(self, julianday):
        return (julianday - 2451545.0) / 36525.0

    def _jcentury_to_jday(self, juliancentury):
        return (juliancentury * 36525.0) + 2451545.0

    def _mean_obliquity_of_ecliptic(self, juliancentury):
        seconds = 21.448 - juliancentury * (46.815 + juliancentury * (0.00059 - juliancentury * (0.001813)))
        return 23.0 + (26.0 + (seconds / 60.0)) / 60.0

    def _obliquity_correction(self, juliancentury):
        e0 = self._mean_obliquity_of_ecliptic(juliancentury)

        omega = 125.04 - 1934.136 * juliancentury
        return e0 + 0.00256 * cos(radians(omega))
    
    def _geom_mean_long_sun(self, juliancentury):
        l0 = 280.46646 + juliancentury * (36000.76983 + 0.0003032 * juliancentury)
        return l0 % 360.0
        
    def _eccentricity_earth_orbit(self, juliancentury):
        return 0.016708634 - juliancentury * (0.000042037 + 0.0000001267 * juliancentury)
        
    def _geom_mean_anomaly_sun(self, juliancentury):
        return 357.52911 + juliancentury * (35999.05029 - 0.0001537 * juliancentury)

    def _eq_of_time(self, juliancentury):
        epsilon = self._obliquity_correction(juliancentury)
        l0 = self._geom_mean_long_sun(juliancentury)
        e = self._eccentricity_earth_orbit(juliancentury)
        m = self._geom_mean_anomaly_sun(juliancentury)

        y = tan(radians(epsilon) / 2.0)
        y = y * y

        sin2l0 = sin(2.0 * radians(l0))
        sinm = sin(radians(m))
        cos2l0 = cos(2.0 * radians(l0))
        sin4l0 = sin(4.0 * radians(l0))
        sin2m = sin(2.0 * radians(m))

        Etime = y * sin2l0 - 2.0 * e * sinm + 4.0 * e * y * sinm * cos2l0 - \
                0.5 * y * y * sin4l0 - 1.25 * e * e * sin2m

        return degrees(Etime) * 4.0

    def _sun_eq_of_center(self, juliancentury):
        m = self._geom_mean_anomaly_sun(juliancentury)

        mrad = radians(m)
        sinm = sin(mrad)
        sin2m = sin(mrad + mrad)
        sin3m = sin(mrad + mrad + mrad)

        c = sinm * (1.914602 - juliancentury * (0.004817 + 0.000014 * juliancentury)) + \
            sin2m * (0.019993 - 0.000101 * juliancentury) + sin3m * 0.000289
            
        return c

    def _sun_true_long(self, juliancentury):
        l0 = self._geom_mean_long_sun(juliancentury)
        c = self._sun_eq_of_center(juliancentury)

        return l0 + c

    def _sun_apparent_long(self, juliancentury):
        O = self._sun_true_long(juliancentury)

        omega = 125.04 - 1934.136 * juliancentury
        return O - 0.00569 - 0.00478 * sin(radians(omega))

    def _sun_declination(self, juliancentury):
        e = self._obliquity_correction(juliancentury)
        lambd = self._sun_apparent_long(juliancentury)

        sint = sin(radians(e)) * sin(radians(lambd))
        return degrees(asin(sint))

    def _hour_angle(self, latitude, solar_dec, solar_depression):
        latRad = radians(latitude)
        sdRad = radians(solar_dec)

        HA = (acos(cos(radians(90 + solar_depression)) / (cos(latRad) * cos(sdRad)) - tan(latRad) * tan(sdRad)))
        
        return HA

    def _hour_angle_sunrise(self, latitude, solar_dec):
        return self._hour_angle(latitude, solar_dec, 0.833)
        
    def _hour_angle_sunset(self, latitude, solar_dec):
        return -self._hour_angle(latitude, solar_dec, 0.833)

    def _hour_angle_dawn(self, latitude, solar_dec, solar_depression):
        return self._hour_angle(latitude, solar_dec, solar_depression)

    def _hour_angle_dusk(self, latitude, solar_dec, solar_depression):
        return -self._hour_angle(latitude, solar_dec, solar_depression)

    def _sun_true_anomoly(self, juliancentury):
        m = self._geom_mean_anomaly_sun(juliancentury)
        c = self._sun_eq_of_center(juliancentury)

        return m + c

    def _sun_rad_vector(self, juliancentury):
        v = self._sun_true_anomoly(juliancentury)
        e = self._eccentricity_earth_orbit(juliancentury)
 
        return (1.000001018 * (1 - e * e)) / (1 + e * cos(radians(v)))

    def _sun_rt_ascension(self, juliancentury):
        e = self._obliquity_correction(juliancentury)
        lambd = self._sun_apparent_long(juliancentury)
 
        tananum = (cos(radians(e)) * sin(radians(lambd)))
        tanadenom = (cos(radians(lambd)))

        return degrees(atan2(tananum, tanadenom))

    def get_sun_azimuth_from_fix(self, fix, time = None):
        if time != None:
            fix.timestamp = time
        if self.sun_cache_time == None or abs((fix.timestamp - self.sun_cache_time).seconds) > SUN_POSITION_CACHE_DURATION:
            self.sun_cache_time = fix.timestamp
            sunrise = self.sunrise_utc(fix.timestamp, fix.position.lat, -fix.position.lon)
            sunset = self.sunset_utc(fix.timestamp, fix.position.lat, -fix.position.lon)
            if fix.timestamp > sunrise and fix.timestamp < sunset:
                self.sun_cache_result = self.solar_azimuth(fix.timestamp, fix.position.lat, -fix.position.lon)
            else:
                self.sun_cache_result = None
        return self.sun_cache_result


