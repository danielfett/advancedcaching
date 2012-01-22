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


import logging
logger = logging.getLogger('downloader')
import connection

class FileDownloader():
    USER_AGENT = 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.15 (KHTML, like Gecko) Ubuntu/11.10 Chromium/18.0.997.0 Chrome/18.0.997.0 Safari/535.15'
    opener_installed = False

    def __init__(self, username, password, cookiefile, login_callback):
        self.username = username
        self.password = password
        self.cookiefile = cookiefile
        self.logged_in = False
        from socket import setdefaulttimeout
        setdefaulttimeout(30)
        self.opener_installed = False
        self.login_callback = login_callback

    def update_userdata(self, username = None, password = None):
        from os import path, remove
        if username != None:
            self.username = username
        if password != None:
            self.password = password
        self.logged_in = False
        if path.exists(self.cookiefile):
            try:
                remove(self.cookiefile)
            except:
                logger.error("Could not remove cookie file?!")
                pass


    def login(self):
        if connection.offline:
            raise Exception("Can't connect in offline mode.")
        if self.username == '' or self.password == '':
            raise Exception("Please configure your username/password and restart the application")
        logger.info("Checking Login status")
        from cookielib import LWPCookieJar
        cj = LWPCookieJar(self.cookiefile)

        if not self.opener_installed:
            from urllib2 import build_opener, install_opener, HTTPCookieProcessor
            opener = build_opener(HTTPCookieProcessor(cj))
            install_opener(opener)
            self.opener_installed = True

        try:
            cj.load()
            logger.info("Loaded cookie file")
        except IOError, e:
            logger.info("Couldn't load cookie file")
        else:
            logger.info("Checking if still logged in...")
            url = 'http://www.geocaching.com/seek/nearest.aspx'
            page = self.get_reader(url, login = False)
            for line in page:
                if 'Hello, ' in line:
                    self.logged_in = True
                    logger.info("Seems as we're still logged in")
                    page.close()
                    return
                elif 'Welcome, Visitor!' in line:
                    logger.info("Nope, not logged in anymore")
                    page.close()
                    break
        
        logger.info("Logging in")
        url, values = self.login_callback(self.username, self.password)

        page = self.get_reader(url, values, login = False)

        for line in page:
            if 'You are logged in as' in line:
                break
            elif 'combination does not match' in line:
                raise Exception("Wrong password or username!")
        else:
            logger.info("Seems as if the language is set to something other than english")
            raise Exception("Please go to geocaching.com and set the website language to english!")

        logger.info("Great success.")
        self.logged_in = True
        try:
            cj.save()
        except Exception, e:
            logger.info("Could not save cookies: %s" % e)


    def get_reader(self, url, values=None, data=None, login = True):
        logger.debug("Sending request to %s" % url)
        if connection.offline:
            raise Exception("Can't connect in offline mode.")
        from urllib import urlencode
        from urllib2 import Request, urlopen
        if login and not self.logged_in:
            self.login()

        if values == None and data == None:
            req = Request(url)
            self.add_headers(req)
            resp = urlopen(req)

        elif data == None:
            if (isinstance(values, dict)):
                values = urlencode( values)
            req = Request(url, values)
            self.add_headers(req)
            resp = urlopen(req)
        elif values == None:
            content_type, body = data
            req = Request(url)
            req.add_header('Content-Type', content_type)
            req.add_header('Content-Length', len(str(body)))
            self.add_headers(req)
            req.add_data(body)
            resp = urlopen(req)
        if resp.info().get('Content-Encoding') == 'gzip':
            from StringIO import StringIO
            import gzip
            buf = StringIO(resp.read())
            logger.debug("Got gzip encoded answer")
            return gzip.GzipFile(fileobj=buf)
        else:
            logger.debug("Got unencoded answer")
            return resp
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
        req.add_header('Accept-Encoding', 'gzip')
