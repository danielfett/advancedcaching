#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Copyright (C) 2012 Daniel Fett
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

from math import sqrt
from sqlite3 import connect, Row

from copy import copy


class PointProvider():
    """
    Stores information about geocaches.
    
    This class stores geocache information in an SQLite database.
    
    """
    MAX_RESULTS = 1000

    def __init__(self, filename, ctype):
        """
        Initialize this data provider. 
        
        filename -- Filename to save the data to, depends on the OS
        ctype -- Python type which represents a geocache
        
        """
        self.filterstack = []
        self.conn = connect(filename)
        self.conn.row_factory = Row
        self.conn.text_factory = unicode
        self.ctype = ctype
        self.cache_table = 'geocaches'
        self.filterstring = []
        self.filterargs = []

        # yes, the synchronous=off setting is a bit dangerous for the database,
        # but the advantages outbalance unlikely database corruption
        self.conn.executescript(
            'PRAGMA temp_store = MEMORY;' \
            'PRAGMA synchronous=OFF;' \
            'PRAGMA cache_size = -2048;' \
            'PRAGMA count_changes = OFF;' \
            'CREATE TABLE IF NOT EXISTS %s (%s);' % (self.cache_table, ', '.join('%s %s' % m for m in self.ctype.SQLROW.items())))
        self.check_table()
        self.conn.executescript(
            'CREATE INDEX IF NOT EXISTS %(table)s_latlon ON %(table)s (lat ASC, lon ASC);' \
            'DROP INDEX IF EXISTS %(table)s_name;'
            'CREATE UNIQUE INDEX IF NOT EXISTS %(table)s_name_unique ON %(table)s (name ASC);' \
            'CREATE INDEX IF NOT EXISTS %(table)s_fieldnote ON %(table)s (logas);' % {'table' : self.cache_table}
            )

        self.to_replace_string = ', '.join("%s=:%s" % (x, x) for x in self.ctype.NON_USER_ATTRS)

    def check_table(self):
        """
        Check the table schema and update it if necessary.
        
        Takes the information about the necessary table schema which is stored in self.ctype.SQLROW and checks whether the SQLite table actually matches this schema. If not, update the table.
        This makes updating the table schema painless.
        
        """
        c = self.conn.cursor()
        fields = copy(self.ctype.SQLROW)
        c.execute('PRAGMA TABLE_INFO(%s)' % self.cache_table)
        for row in c:
            if row[1] in fields:
                del fields[row[1]]

        # add all remaining fields
        for name, type in fields.items():
            cmd = 'ALTER TABLE %s ADD COLUMN %s %s' % (self.cache_table, name, type)
            print "Updating your Database, adding Column %s to Table %s:\n%s" % (name, self.cache_table, cmd)
            c.execute(cmd)
        self.save()
        
    def get_table_info(self):
        """
        Get information about the fields in the geocache table.
        
        This is currently only used in the command line interface to provide the user with information to build his/her own SQL queries.
        
        """
        c = self.conn.cursor()
        c.execute('PRAGMA TABLE_INFO(%s)' % self.cache_table)
        return c.fetchall()
                
    def save(self):
        """
        Commit changes to the table.
        
        Is not performed automatically to speed the interface up.
        
        """
        self.conn.commit()
                
    def __del__(self):
        self.conn.commit()
        self.conn.close()
                
    def add_point(self, p, replace=False):
        """
        Add a geocache to the database.
        
        p -- Geocache
        replace -- If False, update the existing geocache, but only the fields listed in self.ctype.NON_USER_ATTRS. This is useful when existing user data, such as notes, should not be overwritten. If True, replace existing geocaches, deleting user data (unless user data was manually retained).
        
        """
        if replace:
            self.conn.execute("INSERT OR REPLACE INTO %s (`%s`) VALUES (%s)" % (self.cache_table, '`, `'.join(self.ctype.SQLROW.keys()), ', '.join(':%s' % k for k in self.ctype.SQLROW.keys())), p.serialize())
            return None
        else:
            c = self.conn.cursor()
            c.execute("SELECT found FROM %s WHERE name = ?" % self.cache_table, (p.name,))
            num = len(c.fetchall())
            existing = (num == 1)
            c.close()
            
             
            if existing:
                self.conn.execute("UPDATE %s SET %s WHERE name=:name" % (self.cache_table, self.to_replace_string), p.__dict__)
                return False
            else:
                self.conn.execute("INSERT INTO %s (`%s`) VALUES (%s)" % (self.cache_table, '`, `'.join(self.ctype.SQLROW.keys()), ', '.join(':%s' % k for k in self.ctype.SQLROW.keys())), p.serialize())
                return True
                
                
    def get_all(self):
        """
        Return all geocaches in the database.
        
        Currently only used by the CLI. Should be used with caution ;-)
        
        """
        c = self.conn.cursor()

        c.execute('SELECT * FROM %s' % self.cache_table)
        return self._pack_result(c)
        
    def get_by_query(self, query):
        """
        Return all geocaches according to the SQL query given.
        
        WARNING! To avoid SQL injection attacks, this method should only be used with explicitely user provided queries. Should not be used in any regular context in the application.
        
        """
        c = self.conn.execute(query)
        return self._pack_result(c)
                
    def get_points(self, c1, c2, max_points = None):
        """
        Return points in the given boundaries.
        
        Returns all points within the boundaries given by the two corners c1 and c2. If max_points is given, return max_points or less.
        
        """
        query = 'SELECT * FROM %s WHERE (lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?)' % self.cache_table
        args = (min(c1.lat, c2.lat), max(c1.lat, c2.lat), min(c1.lon, c2.lon), max(c1.lon, c2.lon))
        if max_points != None:
            query = "%s LIMIT %d" % (query, max_points)
        c = self.conn.execute(query, args)
        return self._pack_result(c)
            
    def get_new_fieldnotes_count(self):
        """
        Return the number of geocaches which have pending fieldnotes.
        
        A pending fieldnote is when the field logas contains something different than self.ctype.LOG_NO_LOG, because this field is expected to be reset once the fieldnote was uploaded.
        
        """
        c = self.conn.execute('SELECT count(*) AS cnt FROM %s WHERE logas != %d' % (self.cache_table, self.ctype.LOG_NO_LOG))
        for row in c:
            return row['cnt']
        return 0

    def get_new_fieldnotes(self):
        """
        Return geocaches with pending fieldnotes.
        
        """
        c = self.conn.execute('SELECT * FROM %s WHERE logas != %d' % (self.cache_table, self.ctype.LOG_NO_LOG))
        return self._pack_result(c)

    def get_last_viewed(self, count):
        """
        Get the geocaches which were viewed recently.
        
        count -- Maximum number of results.
        
        """
        c = self.conn.execute('SELECT * FROM %s ORDER BY last_viewed DESC LIMIT %d' % (self.cache_table, count))
        return self._pack_result(c)
        
    def get_last_updated(self, count):
        """
        Get the last updated geocaches.
        
        count -- Maximum number of results.
        
        """
        c = self.conn.execute('SELECT * FROM %s ORDER BY updated DESC LIMIT %d' % (self.cache_table, count))
        return self._pack_result(c)
        
    def get_nearest_point_filter(self, center, c1, c2, found):
        """ 
        Get the geocache closest to center.
        
        The distance calculation is performed in python. First, all geocaches between c1 and c2 are retrieved from the database. Afterwards, the distance to center is calculated in python and the closest cache is selected. 
        center -- Center coordinate
        c1 -- Corner 
        c2 -- Corner
        found -- Retrieve only found/not found geocaches (None = all, True = only found, False = only not found)
        
        """
        filterstring = copy(self.filterstring)
        filterargs = copy(self.filterargs)
                
        filterstring.append('((lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?))')
        filterargs.append(min(c1.lat, c2.lat))
        filterargs.append(max(c1.lat, c2.lat))
        filterargs.append(min(c1.lon, c2.lon))
        filterargs.append(max(c1.lon, c2.lon))

        if found == True:
            filterstring.append('(found = 1)')
        elif found == False:
            filterstring.append('(found = 0)')
    
        
        # we don't have 'power' or other advanced mathematic operators
        # in sqlite, so doing distance calculation in python
        query = 'SELECT * FROM %s WHERE %s' % (self.cache_table, " AND ".join(filterstring))
                
        c = self.conn.execute(query, tuple(filterargs))

        mindist = () # we use this as positive infinity
        mindistrow = None
        for row in c:
            # we have points very close to each other
            # for the sake of performance, using simpler
            # distance calc here
            dist = sqrt((row['lat'] - center.lat) ** 2 + (row['lon'] - center.lon) ** 2)
            if dist < mindist:
                mindistrow = row
                mindist = dist
        if mindistrow == None:
            return None
        coord = self.ctype(mindistrow['lat'], mindistrow['lon'], '', mindistrow)
        return coord
                
    def set_filter(self, found=None, has_details=None, owner_search='', name_search='', size=None, terrain=None, diff=None, ctype=None, adapt_filter=False, marked=None):
        """
        This sets a filtering on geocaches which is then applied to the results of selected query methods.
        
        A value of None for any attribute means that no filtering is applied.
        adapt_filter -- Copy the filter which was in effect until now and change it. If False, start over with clean filter settings.
        
        """
        filter = copy(locals())
        del filter['self']
        self.filter = filter

        if adapt_filter:
            filterstring = copy(self.filterstring)
            filterargs = copy(self.filterargs)
        else:
            filterstring = []
            filterargs = []
                
        if found == True:
            filterstring.append('(found = 1)')
        elif found == False:
            filterstring.append('(found = 0)')

        if marked == True:
            filterstring.append('(marked = 1)')
        elif marked == False:
            filterstring.append('(marked = 0)')
                
        if has_details == True:
            filterstring.append("(desc != '' or shortdesc != '')")
        elif has_details == False:
            filterstring.append("NOT (desc != '' or shortdesc != '')")
                        
        if owner_search != None and len(owner_search) > 2:
            filterstring.append("(owner LIKE '%%%s%%')" % owner_search)
                        
        if name_search != None and len(name_search) > 2:
            filterstring.append("((name LIKE '%%%s%%') OR (title LIKE '%%%s%%'))" % (name_search, name_search))
                        
        if size != None:
            filterstring.append('(size IN (%s))' % (", ".join(str(b) for b in size)))

        if terrain != None:
            if type(terrain) == tuple:
                filterstring.append('(terrain >= ?) AND (terrain <= ?)')
                filterargs.append(terrain[0] * 10)
                filterargs.append(terrain[1] * 10)
            elif type(terrain) == list:
                filterstring.append('(terrain IN (%s))' % (", ".join('?' for b in terrain)))
                for b in terrain:
                    filterargs.append(b * 10)

                        
        if diff != None:
            if type(diff) == tuple:
                filterstring.append('(difficulty >= ?) AND (difficulty <= ?)')
                filterargs.append(diff[0] * 10)
                filterargs.append(diff[1] * 10)
            elif type(diff) == list:
                filterstring.append('(difficulty IN (%s))' % (", ".join('?' for b in diff)))
                for b in diff:
                    filterargs.append(b * 10)
                        
        if ctype != None:
            if len(ctype) > 0:
                filterstring.append('(type IN (%s))' % (", ".join('?' for b in ctype)))
                for b in ctype:
                    filterargs.append(b)
                                        
        if len(filterstring) == 0:
            filterstring.append('1')
                
        self.filterstring = filterstring
        self.filterargs = filterargs
                
    def push_filter(self):
        """
        Push the current filter settings to a stack of filter settings.
        
        """
        self.filterstack.append((self.filterstring, self.filterargs))
                
    def pop_filter(self):
        """ 
        Pop the topmost filter settings off the filter settings stack and apply it.
        
        """
        self.filterstring, self.filterargs = self.filterstack.pop()
                
    def get_points_filter(self, location=None, found=None, max_results=None):
        """
        Get geocaches according to the current filter.
        
        location -- Boundaries for the geographic location
        found -- Include found geocaches (None/True/False)
        max_results -- Maximum number of results (None = all)
        """
        filterstring = copy(self.filterstring)
        filterargs = copy(self.filterargs)

        if max_results == None:
            max_results = self.MAX_RESULTS
                
        if location != None:
            c1, c2 = location
            filterstring.append('(lat BETWEEN ? AND ?) AND (lon BETWEEN ? AND ?)')
            filterargs.append(min(c1.lat, c2.lat))
            filterargs.append(max(c1.lat, c2.lat))
            filterargs.append(min(c1.lon, c2.lon))
            filterargs.append(max(c1.lon, c2.lon))


        if found == True:
            filterstring.append('(found = 1)')
        elif found == False:
            filterstring.append('(found = 0)')

        
        query = 'SELECT * FROM %s WHERE %s LIMIT %s' % (self.cache_table, " AND ".join(filterstring), max_results)

        c = self.conn.execute(query, tuple(filterargs))
        return self._pack_result(c)

    def _pack_result(self, cursor):
        """
        Transform all results rows into Geocache objects
        
        """
        points = [self.ctype(None, None, None, row) for row in cursor]
        cursor.close()
        return points
                
    def update_field(self, coordinate, field, newvalue, save = True):
        """
        Update one field of one row in the geocache table.
        
        coordinate -- Geocache 
        field -- SQL field name
        newvalue -- New value
        save -- Commit changes (set to False to speed up multiple changes)
        
        """
        query = 'UPDATE %s SET %s = ? WHERE name = ?' % (self.cache_table, field)
        self.conn.execute(query, (newvalue, coordinate.name))
        if save:
            self.save()

    def get_by_name(self, gcname):
        """
        Return a geocache by its name (where name is the ID)
        
        Returns None if the geocache was not found.
        
        """
        query = 'SELECT * FROM %s WHERE name LIKE ? LIMIT 1' % self.cache_table
        c = self.conn.execute(query, (gcname,))
        row = c.fetchone()
        if row != None:
            coord = self.ctype(None, None, None, row)
            return coord
        else:
            return None

    def remove_geocaches(self, l):
        """
        Remove geocaches from the database.
        
        l -- List of coordinates
        
        """
        names = [x.name for x in l if x.name != '']
        query = 'DELETE FROM %s WHERE name IN (%s)' % (self.cache_table, (','.join('?' for x in names)))
        
        self.conn.execute(query, tuple(names))
        self.save()

    def optimize(self):
        """
        Perform maintenance on the database to speed up things. 
        
        Is not called automatically.
        
        """
        self.conn.execute('VACUUM')
