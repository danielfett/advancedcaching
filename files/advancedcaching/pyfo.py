"""pyfo - Generate XML using native python data structures.

Created and maintained by Luke Arno <luke.arno@gmail.com>

See documentation of pyfo method in this module for details.

Copyright (C) 2006-2007  Central Piedmont Community College

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to 
the Free Software Foundation, Inc., 51 Franklin Street, 
Fifth Floor, Boston, MA  02110-1301  USA

Central Piedmont Community College
1325 East 7th St.
Charlotte, NC 28204, USA

Luke Arno can be found at http://lukearno.com/

"""

from xml.sax.saxutils import escape


def isiterable(it):
    """return True if 'it' is iterable else return False."""
    try:
        iter(it)
    except:
        return False
    else:
        return True


def make_attributes(dct):
    """Turn a dict into string of XML attributes."""
    return u"".join((' %s="%s"' % (x, escape(unicode(y))) 
                    for x, y in dct.iteritems()))


def pyfo(node, 
         prolog=False,
         pretty=False,
         indent_size=2,
         encoding='utf-8',
         collapse=True):
    """Generate XML using native python data structures.
   
    node structure like (name, contents) or (name, contents, attribs)
    accepts stings, callables, or another node structure.
   
    pyfo should be called with a tuple of two or three items like so:
    (element, contents, attributes) or a string.

    for a tuple:
    
        the first item:
            is the element name.
  
        the second item:
            if it is callable, it is called 
            and its return value .
    
            if it is a list, pyfo is called on all its members 
            and the results are concatenated to become the contents.

            otherwise it is run through 'unicode' and 'escape'.
    
        optional third item: 
            should be a dictionary used as xml attributes
    
    for a string:
        
        just return it as unicode.
    """
    if callable(node):
        node = node()
    if not node:
        return u""
    if pretty and pretty >= 0:
        if pretty is True: pretty = 1
        indent = '\n' + (" " * indent_size * pretty)
        unindent = '\n' + (" " * indent_size * (pretty-1))
        pretty += 1
    else:
        unindent = indent = ""
    if isinstance(node, basestring):
        return unicode(node)
    elif len(node) == 2:
        name, contents = node
        dct = {}
    else:
        name, contents, dct = node
    leaf = False
    if callable(contents):
        contents = contents()
    if isinstance(contents, dict):
        contents = contents.items()
    if isinstance(contents, tuple):
        contents = pyfo(contents, 
                        pretty=pretty,
                        indent_size=indent_size,
                        collapse=collapse)
    elif not isinstance(contents, basestring) and isiterable(contents):
        cgen = (pyfo(c, 
                pretty=pretty,
                indent_size=indent_size,
                collapse=collapse)
                for c in contents)
        contents = indent.join((c for c in cgen if c))
    elif contents not in [None, ""]:
        contents = escape(unicode(contents))
        leaf = True
    if leaf:
        indent = unindent = ""
    if prolog:
        prolog = u'<?xml version="1.0" encoding="%s"?>\n' % encoding
    else:
        prolog = u''
    if contents or not collapse:
        return u'%s<%s%s>%s%s%s</%s>' % (prolog, 
                                         name,
                                         make_attributes(dct),
                                         indent,
                                         contents or '',
                                         unindent,
                                         name)
    else:
        return u'%s<%s%s/>' % (prolog, 
                               name,
                               make_attributes(dct))

