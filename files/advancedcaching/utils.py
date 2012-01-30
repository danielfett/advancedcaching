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


import re


class HTMLManipulations(object):
    COMMENT_REGEX = re.compile('<!--.*?-->', re.DOTALL)
    
    @staticmethod
    def _strip_html(text, soft = False):
        if not soft:
            return re.sub(r'<[^>]*?>', '', text)
        else:
            return re.sub(r'<[^>]*?>', ' ', text)

    @staticmethod
    def strip_html_visual(text, image_replace_callback = None):
        text = text.replace("\n", " ")
        if image_replace_callback != None:
            text = re.sub(r"""(?i)<img[^>]+alt=["']?([^'"> ]+)[^>]+>""", image_replace_callback, text)
        text = re.sub(r'(?i)<(br|p)[^>]*?>', "\n", text)
        text = re.sub(r'<[^>]*?>', '', text)
        text = HTMLManipulations._decode_htmlentities(text)
        text = re.sub(r'[\n\r]+\s*[\n\r]+', '\n', text)
        return text.strip()

    @staticmethod
    def _replace_br(text):
        return re.sub('<[bB][rR]\s*/?>|</?[pP]>', '\n', text)


    @staticmethod
    def _decode_htmlentities(string):
        def substitute_entity(match):
            from htmlentitydefs import name2codepoint as n2cp
            ent = match.group(3)
            if match.group(1) == "#":
                # decoding by number
                if match.group(2) == '':
                    # number is in decimal
                    return unichr(int(ent))
                elif match.group(2) == 'x':
                    # number is in hex
                    return unichr(int('0x' + ent, 16))
            else:
                # they were using a name
                cp = n2cp.get(ent)
                if cp:
                    return unichr(cp)
                else:
                    return match.group()

        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(substitute_entity, string)[0]
        
    
    @staticmethod
    def _rot13(text):
        # This handles unicode strings correctly and is available in Python 3, as opposed to encode('rot13')
        text = re.sub(u'[a-z]', lambda x: ((ord(x)-97)+13 % 26) + 97, text)
        text = re.sub(u'[A-Z]', lambda x: ((ord(x)-64)+13 % 26) + 65, text)
        return text
