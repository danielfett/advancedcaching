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

from xml.sax.saxutils import escape
import geo
import os

def GPXExporter():
    def __init__(self):
        pass
        
    def export(self, coordinate, folder = None):
        if coordinate.name == '':
            raise Exception('Koordinate hat keinen Namen')
        if folder == None:
            folder = self.path
        filename = self.__get_uri(coordinate, folder)
        f = open(filename, 'w')
        self.__write_html(f, coordinate)
        f.close()
        
                        
    def __get_uri(self, coordinate, folder):
        return os.path.join(folder, "%s%shtml" % (coordinate.name, os.extsep))
        
    def __write_html(self, file, coordinate):
        self.__write_header(f)
        self.__write_intro(f, coordinate)
        self.__write_main_wpt(f, coordinate)
        for wpt in coordinate.get_waypoints():
            self.__write_wpt(f, wpt)
        self.__write_footer(f)
        
    def __write_header(self, f):
        f.write("""<?xml version="1.0" encoding="utf-8"?><gpx xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" version="1.0" creator="Advanced Geocaching Tool for Linux" xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd http://www.groundspeak.com/cache/1/0 http://www.groundspeak.com/cache/1/0/cache.xsd" xmlns="http://www.topografix.com/GPX/1/0">""")
        
    def __write_intro(self, f, c):
        f.write("""<name>AGTL Cache Listing</name>""")
        f.write("""<desc> </desc>""")
        f.write("""<author>%s</author>""" % escape(c.owner))
        f.write("""<bounds minlat="%.5f" maxlat="%.5f" minlon="%.5f" maxlon="%.5f" />""" % c.get_bounds())

    def __write_main_wpt(self, f, c):
        f.write("""<wpt lat="%.5f" lon="%.5f">""" % (c.lat, c.lon))
        f.write("""<name>%s</name>""" % escape (c.name))
        f.write("""<desc>%s D%1.2f T%1.2f: %s</desc>""" % (escape(c.type), c.difficulty, c.terrain, c.title))
        f.write("""<sym>Geocache</sym>""")
        f.write("""<type>Geocache|%s</type>""" % c.type)
        available = archived = 'True'
        if c.status & GeocacheCoordinate.STATUS_DISABLED:
            available = 'False'
        if not (c.status & GeocacheCoordinate.STATUS_ARCHIVED):
            archived = 'False'
            
        f.write("""<groundspeak:cache id="42" available="%s" archived="%s" xmlns:groundspeak="http://www.groundspeak.com/cache/1/0">""" % (available, archived))
        f.write("""<groundspeak:name>%s</groundspeak:name>""" % escape(c.title))
        f.write("""<groundspeak:placed_by>%s</groundspeak:placed_by>""" % escape(c.owner))
        f.write("""<groundspeak:owner id="%d">%s</groundspeak:owner>""" % (42, escape(c.owner)))
        # determine gs_type here.
        f.write("""<groundspeak:type>%s</groundspeak:type>""" % gs_type)
        # determine container here
        f.write("""<groundspeak:container>%s</groundspeak:container>""" % container)
        f.write("""<groundspeak:difficulty>%s</groundspeak:difficulty>""" % c.get_difficulty())
        f.write("""<groundspeak:terrain>%s</groundspeak:terrain>""" % c.get_terrain())
        f.write("""<groundspeak:country>unknown</groundspeak:country>""")
        f.write("""<groundspeak:state>unknown</groundspeak:state>""")
        f.write("""<groundspeak:short_description html="True">%s</groundspeak:short_description>""" % escape(c.short_desc))
        f.write("""<groundspeak:long_description html="True">%s</groundspeak:long_description>""" % escape(c.desc))
        f.write("""<groundspeak:encoded_hints>%s</groundspeak:encoded_hints>""" % escape(c.hints))
        f.write("""</groundspeak:cache>""")
        f.write("""</wpt>""")
        """
    <wpt lat="49.333167" lon="6.699517">
        <time>2009-11-01T05:47:40.72</time>
        <name>LA20FX5</name>
        <cmt>Sucht hier nach den Koordinaten für [b]STAGE 3[/b]. Ihr könnt euer Cachemobil hier parken, falls noch ein Plätzchen frei ist, ansonsten 500m weiter auf dem Parkplatz von Haus Sonnental. Full-Cycle-Cacher fahren natürlich weiter.</cmt>
        <desc>Der Schilderwald</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=90cede5d-13e8-45a7-85c7-bbeace82bbae</url>
        <urlname>Der Schilderwald</urlname>
        <sym>Stages of a Multicache</sym>
        <type>Waypoint|Stages of a Multicache</type>
    </wpt>
    <wpt lat="49.333967" lon="6.692183">
        <time>2009-11-01T05:55:55.833</time>
        <name>LB20FX5</name>
        <cmt>Hier findet ihr nochmal die Koordinaten für [b]STAGE3[/b]. Das ist eine Backup-Station, falls ihr an [b]STAGE1[/b] nichts finden konntet.</cmt>
        <desc>Haus Sonnental</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=d9cb1a3f-7023-43fe-91a7-b876bd3b9555</url>
        <urlname>Haus Sonnental</urlname>
        <sym>Stages of a Multicache</sym>
        <type>Waypoint|Stages of a Multicache</type>
    </wpt>
    <wpt lat="49.336567" lon="6.680867">
        <time>2009-11-01T06:01:23.077</time>
        <name>LC20FX5</name>
        <cmt>Folgt dem Weg nach rechts und geht weiter zu [b]TRAIL2[/b].</cmt>
        <desc>Abzweigung</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=393199c5-f52f-4e1f-86ed-5ea4086ab966</url>
        <urlname>Abzweigung</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.34065" lon="6.6823">
        <time>2009-11-01T06:05:57.74</time>
        <name>LD20FX5</name>
        <cmt>Folgt dem Weg weiter zu [b]TRAIL3[/b].</cmt>
        <desc>Weg</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=5e3228a3-21ed-40dc-bb18-6e74b2035305</url>
        <urlname>Weg</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.33965" lon="6.674667">
        <time>2009-11-01T06:08:24.507</time>
        <name>LE20FX5</name>
        <cmt>Hier findet ihr den besten Einstieg zu [b]STAGE3[/b]. Folgt dann dem Weg weiter zu [b]TRAIL4[/b].</cmt>
        <desc>Weg</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=67ef6040-c731-4f73-a48f-f08fdec08963</url>
        <urlname>Weg</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.336767" lon="6.673933">
        <time>2009-11-01T06:13:09.843</time>
        <name>LG20FX5</name>
        <cmt>Haltet euch hier rechts und geht weiter zu [b]TRAIL5[/b].</cmt>
        <desc>Abzweigung</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=656da828-09fe-43ad-bf37-37596d8afb52</url>
        <urlname>Abzweigung</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.33595" lon="6.67985">
        <time>2009-11-01T06:14:46.047</time>
        <name>LH20FX5</name>
        <cmt>Biegt rechts ab und folgt dem ansteigenden Weg bis zum [b]FINAL[/b].</cmt>
        <desc>Abzweigung</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=59b6e90f-a263-4511-9975-daf3fe5ba381</url>
        <urlname>Abzweigung</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.333033" lon="6.674433">
        <time>2009-11-01T06:22:57.973</time>
        <name>LJ20FX5</name>
        <cmt>Im Frühjahr und Sommer, wenn der Hang mit Farnen bedeckt ist, ist es hier besonders schön.</cmt>
        <desc>Die Felswand</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=7f33e99c-da81-471b-ac1d-b41647a14a3f</url>
        <urlname>Die Felswand</urlname>
        <sym>Reference Point</sym>
        <type>Waypoint|Reference Point</type>
    </wpt>
    <wpt lat="49.333417" lon="6.686817">
        <time>2009-11-01T06:24:45.05</time>
        <name>LK20FX5</name>
        <cmt>Folgt dem Weg rechts zu [b]TRAIL7[/b].</cmt>
        <desc>Abzweigung</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=9e0cbbe9-5e33-4e0c-a9a4-fedd9988f2c6</url>
        <urlname>Abzweigung</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
    <wpt lat="49.3322" lon="6.689283">
        <time>2009-11-01T06:28:02.667</time>
        <name>LL20FX5</name>
        <cmt>Ein schmaler Pfad biegt links ab. Folgt ihm den Hang hinunter und ihr gelangt direkt zum Parkplatz von Haus Sonnental. Wenn ihr jedoch den Weg weitergeht, könnt ihr noch den Cache "Alter Trinkwasserhochbehälter" (GC1WM95) machen.</cmt>
        <desc>Abzweigung</desc>
        <url>http://www.geocaching.com/seek/wpt.aspx?WID=14b55000-edb5-4b52-8c13-7c9baed44882</url>
        <urlname>Abzweigung</urlname>
        <sym>Trailhead</sym>
        <type>Waypoint|Trailhead</type>
    </wpt>
</gpx>
"""
