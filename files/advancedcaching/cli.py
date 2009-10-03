#!/usr/bin/python
# -*- coding: utf-8 -*-

#    Copyright (C) 2009 Daniel Fett
#     This program is free software: you can redistribute it and/or modify
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
#    Author: Daniel Fett advancedcaching@fragcom.de
#

import geocaching
import sys
import geo
import math
import os

class ParseError(Exception):
    def __init__(self, errormsg, token = None):
        self.msg = errormsg
        self.token = token
        
    def __str__(self):
        return repr(self.msg)
        
        
class RunError(Exception):
    def __init__(self, errormsg):
        self.msg = errormsg
        
    def __str__(self):
        return repr(self.msg)

class Cli():
    USES = ['geonames']

    # operators
    EQ = 0
    MIN = 1
    MAX = 2

    def __init__(self, core, pointprovider, userpointprovider, dataroot):
        self.nt = 1
        self.core = core
        self.caches = None
        self.new_caches = []
        self.pointprovider = pointprovider
        pass
        
    def write_settings(self, settings):
        self.settings = settings
        
    def show(self):
        print "$ The command line interface is not fully implemented yet, feel"
        print "$ free to contribute at git://github.com/webhamster/advancedcaching.git"
        
        try:
            self.parse_input()
        except ParseError as e:
            if e.token == None:
                print "# Parse Error at token '%s': " % sys.argv[self.nt - 1]
            else:
                print "# Parse Error after Token '%s':" % sys.argv[e.token]
            print "# %s" % e.msg
        except RunError as e:
            print "# Execution Error at token '%s': " % sys.argv[self.nt - 1]
            print "# %s" % e.msg
            
            
    def check_caches_retrieved(self):
        if self.caches == None:
            self.caches = self.pointprovider.get_all()
            print "* retrieved all caches (%d) from database" % len(self.caches)
        

    def parse_input (self):
        while self.has_next():
            if sys.argv[self.nt] == 'set':
                self.parse_set()
            if sys.argv[self.nt] == 'import':
                self.parse_import()
            elif sys.argv[self.nt] == 'sql':
                self.parse_sql()
            elif sys.argv[self.nt] == 'filter':
                self.parse_filter()
            elif sys.argv[self.nt] == 'do':
                self.parse_actions()
            else: 
                raise ParseError("Expected 'import', 'sql', 'filter' or 'do'", self.nt - 1)


    def parse_set(self):
        self.nt += 1
        if not self.has_next():
            raise ParseError("Expected some options.")
        while self.has_next():
            token = sys.argv[self.nt]
            self.nt += 1
            if token == '--pass' or token == '--password':
                password = self.parse_string()
                self.set_password(password)
            elif token == '--user' or token == '--username':
                username = self.parse_string()
                self.set_username(username)
            else:
                raise ParseError("I don't understand '%s'" % token)
        print "* Finished setting options. Exiting."
        sys.exit()
        
    def parse_import(self):
        self.nt += 1
        if not self.has_next():
            raise ParseError("Expected import actions.")
        
        token = sys.argv[self.nt]
        self.nt += 1
        if token == '--in':
            coord1 = self.parse_coord()
            coord2 = self.parse_coord()
            self.import_points(coord1, coord2)
        elif token == '--around':
            coord1 = self.parse_coord()
            radius = self.parse_int()
            self.import_points(coord1, radius)
        else:
            # undo what we did.
            self.nt -= 1
            return
            
    def parse_sql(self):
        self.nt += 1
        if not self.has_next():
            print "Table structure for geocaches:"
            info = self.pointprovider.get_table_info()
            for row in info:
                print "\t".join([str(x) for x in row])
            print "Example SQL-Query:"
            print "SELECT * FROM geocaches WHERE type = 'multi' AND name LIKE 'GC1X%' AND found = 0 ORDER BY title DESC LIMIT 5"
            raise ParseError("Expected sql string.")
        text = self.parse_string()
        self.caches = self.pointprovider.get_by_query(text)
            
        
    def parse_filter(self):
        self.check_caches_retrieved()
        self.nt += 1
        if not self.has_next():
            raise ParseError("Expected filter options.")
        while self.has_next():
            token = sys.argv[self.nt]
            self.nt += 1
            if token == '--in':
                coord1 = self.parse_coord()
                coord2 = self.parse_coord()
                self.add_filter_in(coord1, coord2)
            elif token == '--around':
                coord1 = self.parse_coord()
                radius = self.parse_int()
                self.add_filter_in(coord1, radius)
            elif token == '--found' or token == '-f':
                self.add_filter_found(True)
            elif token == '--not-found' or token == '-F':
                self.add_filter_found(False)
            elif token == '-w' or token == '--was-downloaded':
                self.add_filter_has_details(True)
            elif token == '-s' or token == '--size':
                op = self.parse_minmax()
                size = self.parse_size()
                self.add_filter_size(op, size)
            elif token == '-d' or token == '--difficulty':
                op = self.parse_minmax()
                diff = self.parse_decimal()
                self.add_filter_difficulty(op, diff)
            elif token == '-t' or token == '--terrain':
                op = self.parse_minmax()
                terr = self.parse_decimal()
                self.add_filter_terrain(op, terr)
            elif token == '-T' or token == '--type':
                types = self.parse_types()
                self.add_filter_types(types)
            elif token == '-o' or token == '--owner':
                owner = self.parse_string()
                self.add_filter_owner(owner)
            elif token == '-n' or token == '--name':
                name = self.parse_string()
                self.add_filter_name (name)
            elif token == '-i' or token == '--id':
                id = self.parse_string()
                self.add_filter_id (id)
            elif token == '--new':
                self.caches = self.new_caches
            else:
                # undo what we did.
                self.nt -= 1 
                return
                
    def parse_actions(self):
        self.check_caches_retrieved()
        self.nt += 1
        if not self.has_next():
            raise ParseError("Expected actions.")
        while self.has_next():
            token = sys.argv[self.nt]
            self.nt += 1
            if token == '--print':
                self.action_print()
            elif token == '--fetch-details':
                self.action_fetch_details()
            elif token == '--export-html':
                folder = self.parse_string()
                self.action_export_html(folder)
            elif token == '--export-gpx':
                folder = self.parse_string()
                self.action_export_gpx(folder)
            elif token == '--export-single-gpx':
                filename = self.parse_string()
                self.action_export_single_gpx(filename)
            elif token == '--draw-map':
                zoom = self.parse_integer()
                filename = self.parse_string()
                self.action_draw_map(zoom, filename)
            elif token == '--draw-maps':
                zoom = self.parse_integer()
                folder = self.parse_string()
                self.action_draw_maps(zoom, folder)
            elif token == '--command':
                cmd = self.parse_string()
                self.action_command(cmd)
            else:
                raise ParseError("Unknown export action: %s" % token)
                
    def has_next(self):
        # if we have 5 tokens
        # then 1..4 are valid tokens (0 is command)
        # "5" is len(tokens)
        # so we have a next token, if nt < len(tokens)-1
        return (self.nt < len(sys.argv))
        
    def parse_coord(self):
        if not self.has_next():
            raise ParseError("Expected Coordinate but there was none.", self.nt-1)
        text = sys.argv[self.nt]
        self.nt += 1
        if text.startswith('q:'):
            query = text[2:]
            try:
                c = self.core.get_coord_by_name(query)
            except Exception as e:
                raise ParseError(e)
        else:
            try:
                c = geo.try_parse_coordinate(text)
            except Exception as e:
                raise ParseError(e)
            
        return c
        
    def parse_string(self):
        if not self.has_next():
            raise ParseError("Expected some Input, found nothing", self.nt-1)
        text = sys.argv[self.nt]
        self.nt += 1
        return text.strip()
        
    def parse_int(self):
        if not self.has_next():
            raise ParseError("Expected a number, found nothing.", self.nt-1)
        text = sys.argv[self.nt]
        self.nt += 1
        return int(text)
        
    def parse_size(self):
        if not self.has_next():
            raise ParseError("Expected a size (1..4/micro/small/regular/huge/other), found nothing.", self.nt-1)
        text = sys.argv[self.nt].lower()
        self.nt += 1
        if text in ['1', '2', '3', '4', '5']:
            return int(text)
        elif text == 'micro':
            return 1
        elif text == 'small':
            return 2
        elif text in ['normal', 'regular']:
            return 3
        elif text in ['huge', 'big']:
            return 4
        elif text == 'other':
            return 5
        else:
            raise ParseError('Unknown size: %s' % text)
            
    def parse_types(self):
        if not self.has_next():
            raise ParseError("Expected geocache type, found not even an electronic sausage.", self.nt-1)
        text = sys.argv[self.nt].lower()
        self.nt += 1
        
        types = text.split(',')
        output = []
        for i in types:
            if i in geocaching.GeocacheCoordinate.TYPES:
                output.append(i)
            else:
                raise ParseError("Unknown Type: %s (expected one of: %s)" % (i, ', '.join(geocaching.GeocacheCoordinate.TYPES)))
        return output
                
        
    def parse_operator(self):
        text = sys.argv[self.nt]
        if text == 'min':
            self.nt += 1
            return self.MIN
        elif text == 'max':
            self.nt += 1
            return self.MAX
        else:
            return self.EQ
        
    def parse_decimal(self):
        if not self.has_next():
            raise ParseError("Expected a number", self.nt - 1)
        text = sys.argv[self.nt]
        try:
            return 10 * float(text)
        except:
            raise ParseError("Could not parse '%s' as a valid number." % text)

    def set_username(self, string):
        self.settings['options_username'] = string
        self.core.on_config_changed(self.settings)

    def set_password(self, string):
        self.settings['options_password'] = string
        self.core.on_config_changed(self.settings)
        
    def import_points(self, c1, c2):
        if isinstance(c2, geo.Coordinate):
            print "* Downloading Caches between %s and %s" % (c1, c2)
            self.caches, self.new_caches = self.core.on_download((c1, c2))
        else:
            # try to calculate some points northwest and southeast to the
            # given point with approximately correct distances
            new_c1 = c1.transform(-45, c2 * 1000 * math.sqrt(2))
            new_c2 = c1.transform(-45 + 180, c2 * 1000 * math.sqrt(2))
            print "* Downloading Caches in %d km distance to %s" % (c2, c1)
            print "* Approximation: Caches between %s and %s" % (new_c1, new_c2)
            self.caches, self.new_caches = self.core.on_download((new_c1, new_c2))

        
    def add_filter_in(self, coord1, coord2):
        if isinstance(coord2, geo.Coordinate):
            self.caches = filter(lambda x: self.filter_in(coord1, coord2, x), self.caches)
        else:
            self.caches = filter(lambda x: self.filter_in_radius(coord1, coord2, x), self.caches)
        print "* filter in radius/coordinates: %d left" % len(self.caches)
        
    def filter_in(self, c1, c2, check):
        return (check.lat > min(c1.lat, c2.lat) 
            and check.lat < max(c1.lat, c2.lat)
            and check.lon > min(c1.lon, c2.lon)
            and check.lon < max(c1.lon, c2.lon))
            
            
    def filter_in_radius(self, coord1, radius, check):
        return check.distance_to(coord1) <= radius * 1000
            
    def add_filter_found(self, found):
        self.caches = filter(lambda x: x.found == found, self.caches)
        print "* filter width found: %d left" % len(self.caches)
        
    def add_filter_has_details(self, has_details):
        self.caches = filter(lambda x: x.was_downloaded() == has_details, self.caches)
        print "* filter with 'has details': %d left" % len(self.caches)
        
    def add_filter_size(self, op, size):
        if op == self.EQ:
            self.caches = filter(lambda x: x.size == size, self.caches)
        elif op == self.MIN:
            self.caches = filter(lambda x: x.size >= size, self.caches)
        elif op == self.MAX:
            self.caches = filter(lambda x: x.size <= size, self.caches)
        else:
            raise RunError("What Happen? Somebody set us up the geocache.")
        print "* filter with size: %d left" % len(self.caches)
        
    def add_filter_difficulty(self, op, diff):
        if op == self.EQ:
            self.caches = filter(lambda x: x.diff == diff, self.caches)
        elif op == self.MIN:
            self.caches = filter(lambda x: x.diff >= diff, self.caches)
        elif op == self.MAX:
            self.caches = filter(lambda x: x.diff <= diff, self.caches)
        else:
            raise RunError("What Happen? Somebody set us up the geocache.")
        print "* filter with difficulty: %d left" % len(self.caches)
            
    def add_filter_terrain(self, op, terr):
        if op == self.EQ:
            self.caches = filter(lambda x: x.terr == terr, self.caches)
        elif op == self.MIN:
            self.caches = filter(lambda x: x.terr >= terr, self.caches)
        elif op == self.MAX:
            self.caches = filter(lambda x: x.terr <= terr, self.caches)
        else:
            raise RunError("What Happen? Somebody set us up the geocache.")
        print "* filter with terrain: %d left" % len(self.caches)
            
    def add_filter_types(self, types):
        self.caches = filter(lambda x: x.type in types, self.caches)
        print "* filter with types: %d left" % len(self.caches)
        
    def add_filter_owner(self, owner):
        self.caches = filter(lambda x: owner.lower() in x.owner.lower(), self.caches)
        print "* filter with owner: %d left" % len(self.caches)
        
    def add_filter_name (self, name):
        self.caches = filter(lambda x: name.lower() in x.title.lower(), self.caches)
        print "* filter with name: %d left" % len(self.caches)
    
    def add_filter_id (self, idstring):
        self.caches = filter(lambda x: idstring.lower() in x.name.lower(), self.caches)
        print "* filter with id: %d left" % len(self.caches)
    
    def action_print (self):
        for c in self.caches:
            print "%s\t%s (%s)" % (c.name, c.title, c.type)
            
    def action_fetch_details(self):
        i = 1 
        for c in self.caches:
            print "* (%d of %d)\tDownloading '%s'" % (i, len(self.caches), c.title)
            self.core.on_download_cache(c)
            i += 1
    
    def action_export_html(self, folder):
        i = 1 
        for c in self.caches:
            print "* (%d of %d)\tExporting '%s'" % (i, len(self.caches), c.title)
            self.core.on_export_cache(c, folder)
            i += 1
    
    def action_export_gpx(self):
        pass

    def action_command(self, commandline):
        import unicodedata
        if len(self.caches) == 0:
            print "* Not running command (no geocaches left)"
            return
        list = " -- ".join(["%s (%s)" % (a.title, a.type) for a in self.caches])
        list_ascii = unicodedata.normalize('NFKD', list).encode('ascii','ignore')
        os.system(commandline % ('"%s"' % list_ascii.encode('string-escape')))
        
    def set_download_progress(self, some, thing):
        pass
        
    def hide_progress(self):
        pass
        
    def show_error(self, message):
        raise RunError(message)
