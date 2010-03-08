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
import socket
import os
import cookielib
import urllib
import urllib2
socket.setdefaulttimeout(30)
class FileDownloader():
    USER_AGENT = 'User-Agent: Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.0.12) Gecko/2009070811  Windows NT Firefox/3.1'

    def __init__(self, username, password, cookiefile):
        self.username = username
        self.password = password
        self.cookiefile = cookiefile
        self.logged_in = False

    def update_userdata(self, username, password):
        self.username = username
        self.password = password
        self.logged_in = False
        if os.path.exists(self.cookiefile):
            try:
                os.remove(self.cookiefile)
            except:
                print "* Could not remove cookie file?!"
                pass


    def login(self):
        if self.username == '' or self.password == '':
            raise Exception("Please configure your username/password and restart the application")
        print "+ Checking Login status"
        cj = cookielib.LWPCookieJar(self.cookiefile)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)

        try:
            cj.load()
            print "+ Loaded cookie file"
        except:
            print "+ Couldn't load cookie file"
        else:
            print "+ Checking if still logged in..."
            url = 'http://www.geocaching.com/seek/nearest.aspx'
            page = self.get_reader(url, login = False)
            for line in page:
                if 'You are logged in as' in line:
                    self.logged_in = True
                    print "+ Seems as we're still logged in"
                    return
                elif 'You are not logged in.' in line:
                    print "+ Nope, not logged in anymore"
                    break
        
        print "+ Logging in"
        url = 'http://www.geocaching.com/Default.aspx'
        values = {'ctl00$MiniProfile$loginUsername':self.username,
            'ctl00$MiniProfile$loginPassword':self.password,
            'ctl00$MiniProfile$loginRemember': 'on',
            'ctl00$MiniProfile$LoginBtn': 'Go',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': ''
        }

        page = self.get_reader(url, values, login = False).read()

        if 'combination does not match' in page:
            raise Exception("Wrong password or username!")
        print "+ Great success."
        self.logged_in = True
        try:
            cj.save()
        except Exception, e:
            print "+ Could not save cookies:", e


    def get_reader(self, url, values=None, data=None, login = True):
        if login and not self.logged_in:
            self.login()

        if values == None and data == None:
            req = urllib2.Request(url)
            self.add_headers(req)
            return urllib2.urlopen(req)

        elif data == None:
            if (isinstance(values, dict)):
                values = urllib.urlencode( values)
            req = urllib2.Request(url, values)
            self.add_headers(req)
            return urllib2.urlopen(req)
        elif values == None:
            content_type, body = data
            req = urllib2.Request(url)
            req.add_header('Content-Type', content_type)
            req.add_header('Content-Length', len(str(body)))
            self.add_headers(req)
            req.add_data(body)
            return urllib2.urlopen(req)

    def encode_multipart_formdata(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % self.get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body
    
    @staticmethod
    def get_content_type(filename):
        import mimetypes
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    def add_headers(self, req):
        req.add_header('User-Agent', self.USER_AGENT)
        req.add_header('Cache-Control', 'no-cache')
        req.add_header('Pragma', 'no-cache')
