#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
import urllib2
#from urllib2_file import *
import cookielib
import mimetypes

class FileDownloader():
	USER_AGENT='User-Agent: Mozilla/5.0 (X11; U; Linux i686; de; rv:1.9.0.12) Gecko/2009070811  Windows NT Firefox/3.1'
	
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.logged_in = False
		
	def update_userdata(self, username, password):
		self.username = username
		self.password = password
		self.logged_in = False
		print "Up"
	
	def login(self):
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		urllib2.install_opener(opener)
		
		url = 'http://www.geocaching.com/Default.aspx'
		values = {'ctl00$MiniProfile$loginUsername':self.username,
			'ctl00$MiniProfile$loginPassword':self.password,
			'ctl00$MiniProfile$loginRemember': 'on',
			'ctl00$MiniProfile$LoginBtn' : 'Go',
			'__EVENTTARGET' : '',
			'__EVENTARGUMENT' : ''
		}
		
		#headers = {'User-Agent' : self.USER_AGENT}
		data = urllib.urlencode(values)
		req = urllib2.Request(url, data)
		req.add_header('User-Agent', self.USER_AGENT)
		response = urllib2.urlopen(req)
		page = response.read()
		if 'combination does not match' in page:
			raise Exception("Passwort oder Benutzername falsch!")
			
	def get_reader(self, url, values = None, data = None):
		if not self.logged_in:
			self.login()
		#req.add'User-Agent' : self.USER_AGENT}
		if values == None and data == None:
			req = urllib2.Request(url)
			req.add_header('User-Agent', self.USER_AGENT)
			return urllib2.urlopen(req)
		    
		elif data == None:
			values = urllib.urlencode(values)
			req = urllib2.Request(url, values)
			req.add_header('User-Agent', self.USER_AGENT)
			return urllib2.urlopen(req)
		elif values == None:
			content_type, body = data
			req = urllib2.Request(url)
			req.add_header('Content-Type', content_type)
			req.add_header('Content-Length', len(str(body)))
			req.add_header('User-Agent', self.USER_AGENT)
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

	def get_content_type(self, filename):
	        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'