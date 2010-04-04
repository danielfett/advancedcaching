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
Formel ein: N49° 4A.BC3 E006° 4D.EF1 und bla
Formel ein: N49° 4A.B(A-E)2 E006° 4D.C(F-B)7 sfef
bei N49 44,2A E6 41,2A befand
 N49 44,(B/2)(A+(3*7)3) E6 41,B(A-9) sta
ei
N 49° 44.(TRRRS) - (S*S)
E 006° 41.RSR
PS
n bei: N 49° 45.999-12*A-62 E 006° 38.999-12*A-60', {}),
bei N 49° 45.EBA E 006° 37.DFC und', {}),
 zu N 49° 45.(A B C)+7 E 006° 38.(D E F)- 138
bei
ei N 49° 45.(A-1)(C-1)(B*E+5) E 006° 37.(B+1)(A)(E+1). ... bei N 49° 45.(G/3)(H)(H-D) E 006° 36. (H-2)(A-D-F)(G/3). Am Referenzpunkt N 49° 45.((G+1)/(A*2))(A)((R-S+1)*D) E 006° 36. (D+1)(H)(1)
''', {'A': 2, 'D': 4, 'G': 3,'T': 1, 'R': 2, 'S': 1, 'H': 4, 'B': 2, 'C': 9, 'E': 0, 'F': 1})
HTML = '''

			        <td>Note:</td> 
			        <td colspan="4">Hier findest du die erste Dose mit weiteren Informationen. S3 findest du bei<p>N49° 21.10(A-1)' E6° 40.(A-1)04'</td> 
			        <td>&nbsp;</td> 
		        </tr>  
'''
import geo
import re

class CalcCoordinateManager():
    def __init__(self, cache, text):
        self.vars = cache.get_vars()
        self.coords, self.requires = CalcCoordinate.find(text)
        self.update()
        
    def set_var(self, char, value):
        if value != '':
            self.vars[char] = value
        else:
            del self.vars[char]
        self.update()

    def update(self):
        for c in self.coords:
            c.set_vars(self.vars)
            if c.has_requires():
                result = c.try_get_solution()

    def get_solutions(self):
        return [c.result for c in self.coords if c.has_requires()]
    
        

class CalcCoordinate():

    WARNING_NEGATIVE = "Negative intermediate result (%d)."
    WARNING_VERY_HIGH = "Very high intermediate result (%d)."
    WARNING_FLOAT = "Intermediate result with decimal point ('%s')."
    WARNING_WRONG_LENGTH = "%d digits where %s digits were expected (%s)."
    WARNING_CANNOT_PARSE = "Cannot parse result: %s."
    WARNING_SYNTAX = "Could not parse formula."

    HIGH_RESULT_THRESHOLD = 1000

    EXPECTED_LENGTHS = [(1,2), (1,2), (3,), (1,2,3), (1,2), (3,)]

    def __init__(self, ns, lat_deg, lat_min, lat_min_2, ew, lon_deg, lon_min, lon_min_2):
        self.ns = ns
        self.ew = ew
        self.lat_deg   = self.prepare(lat_deg)
        self.lat_min   = self.prepare(lat_min)
        self.lat_min_2 = self.prepare(lat_min_2)
        self.lon_deg   = self.prepare(lon_deg)
        self.lon_min   = self.prepare(lon_min)
        self.lon_min_2 = self.prepare(lon_min_2)
        self.orig = "%s%s %s.%s %s%s %s.%s" % (self.ns, self.lat_deg, self.lat_min, self.lat_min_2, self.ew, self.lon_deg, self.lon_min, self.lon_min_2)
        self.requires = set([x for i in [self.lat_deg, self.lat_min, self.lat_min_2, self.lon_deg, self.lon_min, self.lon_min_2] for x in re.sub('[^A-Za-z]', '', i)])
        self.warnings = []
        self.vars = {}

    def prepare(self, text):
        return re.sub('[^A-Za-z()+*/0-9-]', '', text)

    def set_vars(self, var):
        self.warnings = []
        self.vars = var

    def has_requires(self):
        for i in self.requires:
            if not i in self.vars.keys():
                return False
        return True

    def try_get_solution(self):

        replaced = [self.replace(x) for x in [self.lat_deg, self.lat_min, self.lat_min_2, self.lon_deg, self.lon_min, self.lon_min_2]]
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
            text, c = re.subn('\([^()]+\)', lambda match: self.safe_eval(match.group(0)), text)
        print text
        if re.match('^[0-9]+$', text) == None:
            # determine number of leading zeros
            #lz = len(text) - len(str(int(text)))
            text = self.safe_eval(text)
            text = "%03d" % int(text)
        return text

    def safe_eval(self, text):
        try:
            tmp = eval(text,{"__builtins__":None},{})
        except (SyntaxError, Exception):
            self.warnings.append(self.WARNING_SYNTAX)
            return 'X'
        if round(tmp) != round(tmp, 1):
            self.warnings.append(self.WARNING_FLOAT % text)
        tmp = int(tmp)
        if tmp < 0:
            self.warnings.append(self.WARNING_NEGATIVE % tmp)
        if tmp > self.HIGH_RESULT_THRESHOLD:
            self.warnings.append(self.WARNING_VERY_HIGH % tmp)
        return str(tmp)

    @staticmethod
    def find(text):
        foundsigs = []
        text = text.replace('°', '|')
        text = text.replace(unichr(160), ' ')
        text = re.sub(ur''' +''', ' ', text)
        text = re.sub(ur'''\b[a-zA-Z]{2,}\b''', ' | ', text)
        print text
        matches = re.findall(ur'''(?<![a-zA-Z])([NS+-ns])\s?([A-Z() -+*/0-9]+?)[\s|]{1,2}([A-Za-z ()+*/0-9-]+)[.,\s]([A-Za-z ()+*/0-9-]+)['`\s,/]+([EOW+-eow])\s?([A-Za-z() +*/0-9-]+?)[\s|]{1,2}([A-Za-z ()+*/0-9-]+)[.,\s]([A-Za-z ()+*/0-9-]+)[\s'`]*(?![a-zA-Z])''', text)
        found = []
        requires = set()
        for match in matches:
            sig = "|".join(re.sub('[^A-Za-z()+*/0-9-]+', '', x) for x in match)
            print sig
            if sig in foundsigs:
                continue
            foundsigs.append(sig)
            c = CalcCoordinate(*match)
            if len(c.requires) == 0:
                continue
            found.append(c)
            requires |= c.requires
        return (found, requires)
'''
if __name__ == "__main__":
    from simplegui import SimpleGui
    print '\n\n========================================================='
    h = SimpleGui._strip_html(HTML) 
    print h
    for x in h:
        print "%d -> %s" % (ord(x), x)
    print '---------------------------------------------------------'
    CalcCoordinate.find(h)
'''
