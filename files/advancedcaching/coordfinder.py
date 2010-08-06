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
#        Author: Daniel Fett simplecaching@fragcom.de
#

from __future__ import division
TEST = ('''



''', {'A': 2, 'D': 4, 'G': 3,'T': 1, 'R': 2, 'S': 1, 'H': 4, 'B': 2, 'C': 9, 'E': 0, 'F': 1})
HTML = '''

<br /></p> 
<p><font face="Arial, sans-serif"><font size=
"4"><b>Final:</b></font></font></p> 
<p style="font-style: normal"><font color="#000000"><font face=
"Arial, sans-serif"><font size="3"><b><span style=
"background: transparent">N 49°
(B-C+A+0,5*D).(F+D)(F-G)(C-2*A)</span></b></font></font></font></p> 
<p style="font-style: normal"><font color="#000000"><font face=
"Arial, sans-serif"><font size="3"><b><span style=
"background: transparent">E 6°
(2*A+C).(G-E)(B-C+0,5*D)(F-D)</span></b></font></font></font></p> 
<p style="font-style: normal; font-weight: normal"><font color=
"#000000"><font face="Arial, sans-serif"><font size=
"3"><span style="background: transparent">Es müssen keine Zäune
oder Mauern überwunden werden.</span></font></font></font></p>
N 49°
(B-C+A+0,5*D).(F+D)(F-G)(D-2*B)
<p><br /> 
<br /></p></span> 
                
            </div> 
            <p> 
</p> 
'''
import geo
import re
import logging
logger = logging.getLogger('coordfinder')

class CalcCoordinateManager(object):
    def __init__(self, vars):
        self.__vars = vars
        self.__known_signatures = {}
        self.requires = set()
        self.coords = []

    def add_text(self, text, source):
        self.__add_coords(CalcCoordinate.find(text, source))

    def __add_coords(self, coords):
        for x in coords:
            if x.signature in self.__known_signatures:
                continue
            self.__known_signatures[x.signature] = True
            self.requires |= x.requires
            self.coords.append(x)
        
    def set_var(self, char, value):
        if value != '':
            self.__vars[char] = value
        else:
            del self.__vars[char]
        self.update()

    def update(self):
        for c in self.coords:
            c.set_vars(self.__vars)
            if c.has_requires():
                c.try_get_solution()

    def get_solutions(self):
        return [(c.result, c.source) for c in self.coords if c.has_requires() and len(c.requires) > 0]

    def get_plain_coordinates(self):
        return [(c.result, c.source) for c in self.coords if len(c.requires) == 0]

    def get_vars(self):
        return self.__vars


class CalcCoordinate():

    WARNING_NEGATIVE = "Negative intermediate result (%d)."
    WARNING_VERY_HIGH = "Very high intermediate result (%d)."
    WARNING_FLOAT = "Intermediate result with decimal point ('%s')."
    WARNING_WRONG_LENGTH = "%d digits where %s digits were expected (%s)."
    WARNING_CANNOT_PARSE = "Cannot parse result: %s."
    WARNING_SYNTAX = "Could not parse formula."

    HIGH_RESULT_THRESHOLD = 1000

    EXPECTED_LENGTHS = [(1,2), (1,2), (3,), (1,2,3), (1,2), (3,)]

    def __init__(self, ns, lat_deg, lat_min, lat_min_2, ew, lon_deg, lon_min, lon_min_2, source):
        self.ns = ns
        self.ew = ew
        self.lat_deg   = self.__prepare(lat_deg)
        self.lat_min   = self.__prepare(lat_min)
        self.lat_min_2 = self.__prepare(lat_min_2)
        self.lon_deg   = self.__prepare(lon_deg)
        self.lon_min   = self.__prepare(lon_min)
        self.lon_min_2 = self.__prepare(lon_min_2)
        self.orig = "%s%s %s.%s %s%s %s.%s" % (self.ns, self.lat_deg, self.lat_min, self.lat_min_2, self.ew, self.lon_deg, self.lon_min, self.lon_min_2)
        self.requires = set(x for i in [self.lat_deg, self.lat_min, self.lat_min_2, self.lon_deg, self.lon_min, self.lon_min_2] for x in re.sub('[^A-Za-z]', '', i))
        self.warnings = []
        self.vars = {}
        self.signature = "|".join(ns, self.lat_deg, self.lat_min, self.lat_min_2, ew, self.lon_deg, self.lon_min, self.lon_min_2)
        self.source = source

    def __prepare(self, text):
        return (re.sub('[^A-Za-z()+*/0-9-.,]', '', text)).replace(',', '.')

    def set_vars(self, var):
        self.warnings = []
        self.vars = var

    def has_requires(self):
        for i in self.requires:
            if not i in self.vars:
                return False
        return True

    def try_get_solution(self):

        replaced = [self.__replace(x) for x in [self.lat_deg, self.lat_min, self.lat_min_2, self.lon_deg, self.lon_min, self.lon_min_2]]
        self.replaced_result = ("%%s%s %s.%s %%s%s %s.%s" % tuple(replaced)) % (self.ns, self.ew)
        results = [self.resolve(x) for x in replaced]
        
        for i in range(len(results)):
            if len(results[i]) not in self.EXPECTED_LENGTHS[i]:
                self.warnings.append(self.WARNING_WRONG_LENGTH % (len(results[i]), " or ".join([str(x) for x in self.EXPECTED_LENGTHS[i]]), results[i]))
        
        result = ("%%s%s %s.%s %%s%s %s.%s" % tuple(results)) % (self.ns, self.ew)
        #print self.replaced_result
        try:
            self.result = geo.try_parse_coordinate(result)
            self.result.name = self.orig                
        except (Exception):
            self.warnings.append(self.WARNING_CANNOT_PARSE % result)
            self.result = False
        


    def replace(self, text):
        for char, value in self.vars.items():
            text = text.replace(char, str(value))
        return text

    def resolve(self, text):
        c = 1
        while c > 0:
            text, c = re.subn('\([^()]+\)', lambda match: self.__safe_eval(match.group(0)), text)
        if re.match('^[0-9]+$', text) == None:
            # determine number of leading zeros
            #lz = len(text) - len(str(int(text)))
            text = self.__safe_eval(text)
            try:
                text = "%03d" % int(text)
            except Exception:
                text = '?'
        return text

    def __safe_eval(self, text):
        try:
            tmp = eval(text,{"__builtins__":None},{})
        except (SyntaxError, Exception):
            self.warnings.append(self.WARNING_SYNTAX)
            return '?'
        if round(tmp) != round(tmp, 1):
            self.warnings.append(self.WARNING_FLOAT % text)
        tmp = int(tmp)
        if tmp < 0:
            self.warnings.append(self.WARNING_NEGATIVE % tmp)
        if tmp > self.HIGH_RESULT_THRESHOLD:
            self.warnings.append(self.WARNING_VERY_HIGH % tmp)
        return str(tmp)

    @staticmethod
    def find(text, source):
        text = re.sub(ur'''(?u)\s[^\W\d_]{2,}\s''', ' | ', text)
        text = re.sub(ur'''(?u)\b[^\W\d_]{4,}\b''', ' | ', text)
        text = text.replace('°', '|')
        text = text.replace(unichr(160), ' ')
        text = re.sub(ur''' +''', ' ', text)
        single_calc_part = ur'''((?:\([A-Za-z +*/0-9-.,]+\)|[A-Za-z ()+*/0-9-])+)'''
        matches = re.findall(ur'''(?<![a-zA-Z])([NSns])\s?([A-Z() -+*/0-9]+?)[\s|]{1,2}%(calc)s[.,\s]%(calc)s['`\s,/]+([EOWeow])\s?([A-Z() -+*/0-9]+?)[\s|]{1,2}%(calc)s[.,\s]%(calc)s[\s'`]*(?![a-zA-Z])''' % {'calc' : single_calc_part}, text)
        return [CalcCoordinate(*match, source = source) for match in matches]

if __name__ == "__main__":
    from simplegui import SimpleGui
    print '\n\n========================================================='
    h = SimpleGui._strip_html(HTML) 
    print h
    #for x in h:
    #    print "%d -> %s" % (ord(x), x)
    print '---------------------------------------------------------'
    for instance in CalcCoordinate.find(h)[0]:
        print "Found: %s" % (instance.orig)

