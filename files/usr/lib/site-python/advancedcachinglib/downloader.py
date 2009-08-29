#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import cookielib

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
		response = urllib2.urlopen(req)
		page = response.read()
		if 'combination does not match' in page:
			raise Exception("Passwort oder Benutzername falsch!")
			
	def get_reader(self, url, values = None):		
		if not self.logged_in:
			self.login()
		#headers = {'User-Agent' : self.USER_AGENT}
		if values == None:
			return urllib2.urlopen(urllib2.Request(url))
		else:
			data = urllib.urlencode(values)
			return urllib2.urlopen(urllib2.Request(url, data))
