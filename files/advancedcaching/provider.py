import math
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

#import downloader
import sqlite3

import copy



class PointProvider():
    USER_AGENT = 'User-Agent: Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.0.12) Gecko/2009070811  Windows NT Firefox/3.1'

    def __init__(self, filename, downloader, ctype, table):

        self.filterstack = []
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.conn.text_factory = str
        self.ctype = ctype
        self.downloader = downloader
        self.cache_table = table
        self.filterstring = []
        self.filterargs = []
        c = self.conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS %s (%s)' % (self.cache_table, ', '.join([' '.join(m) for m in self.ctype.SQLROW.items()])))
        self.check_table()
        c.execute('CREATE INDEX IF NOT EXISTS %s_latlon ON %s (lat ASC, lon ASC)' % (self.cache_table, self.cache_table))
        c.close()

    def check_table(self):
        c = self.conn.cursor()
        fields = copy.copy(self.ctype.SQLROW)
        c.execute('PRAGMA TABLE_INFO(%s)' % self.cache_table)
        for row in c:
            del fields[row[1]]

        # add all remaining fields
        for name, type in fields.items():
            cmd = 'ALTER TABLE %s ADD COLUMN %s %s' % (self.cache_table, name, type)
            print "Updating your Database, adding Column %s to Table %s:\n%s" % (name, self.cache_table, cmd)
            c.execute(cmd)
        self.save()
                
    def save(self):
        self.conn.commit()
                
    def __del__(self):
        self.conn.commit()
        self.conn.close()
                
    def add_point(self, p, replace=False):
                
        if replace:
            self.conn.execute("INSERT OR REPLACE INTO %s (`%s`) VALUES (%s)" % (self.cache_table, '`, `'.join(self.ctype.SQLROW.keys()), ', '.join([':%s' % k for k in self.ctype.SQLROW.keys()])), p.serialize())
        else:
            if p.found:
                found = 1
            else:
                found = 0
            c = self.conn.cursor()
            c.execute("SELECT found FROM %s WHERE name = ?" % self.cache_table, (p.name,))
            existing = (len(c.fetchall()) == 1)
            c.close()
            if existing:
                self.conn.execute("UPDATE %s SET found = ? WHERE name = ?" % self.cache_table, (p.found, p.name))
            else:
                self.conn.execute("INSERT INTO %s (`%s`) VALUES (%s)" % (self.cache_table, '`, `'.join(self.ctype.SQLROW.keys()), ', '.join([':%s' % k for k in self.ctype.SQLROW.keys()])), p.serialize())
            return
                
                
    # should be used with caution :-)
    def get_all(self):
        c = self.conn.cursor()

        c.execute('SELECT * FROM %s' % self.cache_table)
        points = []
        for row in c:
            coord = self.ctype(row['lat'], row['lon'])
            coord.unserialize(row)
            points.append(coord)
        c.close()
        return points
                
    def get_points(self, c1, c2):
                
        c = self.conn.cursor()

        c.execute('SELECT * FROM %s WHERE (lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?)' % self.cache_table, (min(c1.lat, c2.lat), max(c1.lat, c2.lat), min(c1.lon, c2.lon), max(c1.lon, c2.lon)))
        points = []
        for row in c:
            coord = self.ctype(row['lat'], row['lon'])
            coord.unserialize(row)
            points.append(coord)
        c.close()
        return points
                
    def get_titles_and_names(self):
        c = self.conn.cursor()
        c.execute('SELECT name, title FROM %s' % self.cache_table)
        strings = []
        for row in c:
            strings.append(row['name'])
            strings.append(row['title'])
        c.close()
        return strings
            
    def get_new_fieldnotes_count(self):
        c = self.conn.cursor()

        c.execute('SELECT count(*) AS cnt FROM %s WHERE logas != %d' % (self.cache_table, self.ctype.LOG_NO_LOG))
        for row in c:
            return row['cnt']
        return 0

    def get_new_fieldnotes(self):
        c = self.conn.cursor()

        c.execute('SELECT * FROM %s WHERE logas != %d' % (self.cache_table, self.ctype.LOG_NO_LOG))
        points = []
        for row in c:
            coord = self.ctype(row['lat'], row['lon'])
            coord.unserialize(row)
            points.append(coord)
        c.close()
        return points

        
    def get_nearest_point_filter(self, center, c1, c2):
        filterstring = copy.copy(self.filterstring)
        filterargs = copy.copy(self.filterargs)
                
        filterstring.append('((lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?))')
        filterargs.append(min(c1.lat, c2.lat))
        filterargs.append(max(c1.lat, c2.lat))
        filterargs.append(min(c1.lon, c2.lon))
        filterargs.append(max(c1.lon, c2.lon))
                        
        c = self.conn.cursor()
        # we don't have 'power' or other advanced mathematic operators
        # in sqlite, so doing distance calculation in python
        query = 'SELECT * FROM %s WHERE %s' % (self.cache_table, " AND ".join(filterstring))
                
        c.execute(query, tuple(filterargs))

        mindist = () # we use this as positive infinity
        mindistrow = None
        for row in c:
            # we have points very close to each other
            # for the sake of performance, using simpler
            # distance calc here
            dist = math.sqrt((row['lat'] - center.lat) ** 2 + (row['lon'] - center.lon) ** 2 )
            if dist < mindist:
                mindistrow = row
                mindist = dist
        if mindistrow == None:
            return None
        coord = self.ctype(mindistrow['lat'], mindistrow['lon'])
        coord.unserialize(mindistrow)
        return coord
                
    def set_filter(self, found=None, has_details=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, adapt_filter=False, distance_filter=None):
        # a value "None" means: apply no filtering on this value
                
        if adapt_filter:
            filterstring = copy.copy(self.filterstring)
            filterargs = copy.copy(self.filterargs)
        else:
            filterstring = []
            filterargs = []
                
        if found == True:
            filterstring.append('(found = 1)')
        elif found == False:
            filterstring.append('(found = 0)')
                
        if has_details == True:
            filterstring.append("(desc != '' or shortdesc != '')")
        elif has_details == False:
            filterstring.append("NOT (desc != '' or shortdesc != '')")
                        
        if owner_search != None and len(owner_search) > 2:
            filterstring.append("(owner LIKE '%%%s%%')" % owner_search)
                        
        if name_search != None and len(name_search) > 2:
            filterstring.append("((name LIKE '%%%s%%') OR (title LIKE '%%%s%%'))" % (name_search, name_search))
                        
        if size != None:
            filterstring.append('(size IN (%s))' % (", ".join([str(b) for b in size])))

        if terrain != None:
            filterstring.append('(terrain >= ?) AND (terrain <= ?)')
            filterargs.append(terrain[0] * 10)
            filterargs.append(terrain[1] * 10)
                        
        if diff != None:
            filterstring.append('(difficulty >= ?) AND (difficulty <= ?)')
            filterargs.append(diff[0] * 10)
            filterargs.append(diff[1] * 10)
                        
        if ctype != None:
            if len(ctype) > 0:
                filterstring.append('(type IN (%s))' % (", ".join(['?' for b in ctype])))
                for b in ctype:
                    filterargs.append(b)
                                        
        if len(filterstring) == 0:
            filterstring.append('1')
                
        self.filterstring = filterstring
        self.filterargs = filterargs
                
    def push_filter(self):
        self.filterstack.append((self.filterstring, self.filterargs))
                
    def pop_filter(self):
        self.filterstring, self.filterargs = self.filterstack.pop()
                
    def get_points_filter(self, location=None):
        filterstring = copy.copy(self.filterstring)
        filterargs = copy.copy(self.filterargs)
                
        if location != None:
            c1, c2 = location
            filterstring.append('(lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?)')
            filterargs.append(min(c1.lat, c2.lat))
            filterargs.append(max(c1.lat, c2.lat))
            filterargs.append(min(c1.lon, c2.lon))
            filterargs.append(max(c1.lon, c2.lon))
                        
        c = self.conn.cursor()
        query = 'SELECT * FROM %s WHERE %s' % (self.cache_table, " AND ".join(filterstring))

        c.execute(query, tuple(filterargs))
        points = []
        for row in c:
            coord = self.ctype(row['lat'], row['lon'])
            coord.unserialize(row)
            points.append(coord)
        c.close()
        return points
                
    def find_by_string(self, string):
        query = 'SELECT * FROM %s WHERE name LIKE ? OR title LIKE ? LIMIT 2' % self.cache_table
        c = self.conn.cursor()
        c.execute(query, (string, string))
        row = c.fetchone()
        coord = self.ctype(row['lat'], row['lon'])
        coord.unserialize(row)
                
        # we cannot reliably determine # of results, so using workaround here
        if c.fetchone() != None:
            return None
        return coord
                
    def update_field(self, coordinate, field, newvalue):
        query = 'UPDATE %s SET %s = ? WHERE name = ?' % (self.cache_table, field)
        c = self.conn.cursor()
        c.execute(query, (newvalue, coordinate.name))
        self.save()
