#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import geo
import string
import os

try:
	import Image
except:
	print "Not using image resize feature"
import re

from htmlentitydefs import name2codepoint as n2cp


class GeocacheCoordinate(geo.Coordinate):
	SQLROW = {'lat': 'REAL', 'lon' : 'REAL', 'name' : 'TEXT PRIMARY KEY', 'title' : 'TEXT', 'shortdesc' : 'TEXT', 'desc' : 'TEXT', 'hints' : 'TEXT', 'type' : 'TEXT', 'size' : 'INTEGER', 'difficulty' : 'INTEGER', 'terrain' : 'INTEGER', 'owner' : 'TEXT', 'found' : 'INTEGER', 'waypoints' : 'text', 'images' : 'text'}
	def __init__(self, lat, lon, name = ''):
		geo.Coordinate.__init__(self, lat, lon, name)
		# NAME = GC-ID
		self.title = ''
		self.shortdesc = ''
		self.desc = ''
		self.hints = ''
		self.type = '' # regular, multi, virtual, webcam,...
		self.size = -1
		self.difficulty = -1
		self.terrain = -1
		self.owner = ''
		self.found = False
		self.waypoints = []
		self.images = []

	def serialize(self):

		if self.found:
			found = 1
		else:
			found = 0
		return {'lat': self.lat, 'lon' : self.lon, 'name' : self.name, 'title' : self.title, 'shortdesc' : self.shortdesc, 'desc' : self.desc, 'hints' : self.hints, 'type' : self.type, 'size' : self.size, 'difficulty' : self.difficulty, 'terrain' : self.terrain, 'owner' : self.owner, 'found' : found, 'waypoints' : json.dumps(self.waypoints), 'images' : json.dumps(self.images)}
		
	def unserialize(self, data):
		self.lat = data['lat']
		self.lon = data['lon']
		self.name = data['name']
		self.title = data['title']
		self.shortdesc = data['shortdesc']
		self.desc = data['desc']
		self.hints = data['hints']
		self.type = data['type']
		self.size = data['size']
		self.difficulty = data['difficulty']
		self.terrain = data['terrain']
		self.owner = data['owner']
		self.found = (data['found'] == 1)
		self.waypoints = json.loads(data['waypoints'])
		self.images = json.loads(data['images'])
		
		
	def was_downloaded(self):
		return (self.shortdesc != '' or self.desc != '')


class CacheDownloader():
	
	
	def __init__(self, downloader):
		self.downloader = downloader	
	
	def rot13(self, text):
		trans = string.maketrans(
		'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM',
		'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
		return text.translate(trans)

	def strip_html(self, text):
		return re.sub(r'<[^>]*?>', '', text)

	def replace_br(self, text):
		return re.sub('(<[bB][rR]\s*/?>|</[pP]>', '\n', text)

	def treat_hints(self, hints):
		return self.strip_html(hints).strip()

	def treat_desc(self, desc):
		desc =  self.treat_html(desc.rsplit('\n', 5)[0])
		return desc.strip()
	
	def treat_shortdesc(self, desc):
		if desc.strip() == '':
			return ''
		desc =  self.treat_html(desc.rsplit('\n', 3)[0])
		return desc
	
	def treat_html(self, html):
		strip_comments = re.compile('<!--.*?-->', re.DOTALL)
	
		return strip_comments.sub('', html)
		
	def from_dm(self, direction, decimal, minutes):
		if direction == None or decimal == None or minutes == None:
			return -1
		if direction in "SsWw":
			sign = -1
		else:
			sign = 1
		
		return (float(decimal)+(float(minutes)/60.0)) * sign

	def treat_waypoints(self, data):

		waypoints = []
		finder = re.finditer(r'<tr bgcolor="#ffffff">\s+<td valign="top" align="center" width="16"><img [^>]+></td>\s*' +
				r'<td valign="top" align="center" width="16"><img [^>]+></td>\s*' +
				r'<td valign="top" align="left">(?P<id_prefix>[^<]+)</td>\s*' +
				r'<td valign="top" align="left">(?P<id>[^<]+)</td>\s*' +
				r'<td valign="top" align="left"><a href=[^>]+>(?P<name>[^<]+)</a>[^<]+</td>\s*' +
				r'<td valign="top" align="left">(\?\?\?|(?P<lat_sign>N|S) (?P<lat_d>\d+)° (?P<lat_m>[0-9\.]+) (?P<lon_sign>E|W) (?P<lon_d>\d+)° (?P<lon_m>[0-9\.]+))</td>\s*' +
				r'<td valign="top" align="left"></td>\s+</tr>\s*<tr bgcolor="#FFFFFF">\s+<td colspan="2" ' +
				r'valign="top">Note:</td>\s*<td valign="top" align="left" colspan="4">(?P<comment>.*?)</td>\s*<td>&nbsp;</td>\s*</tr> ', data, re.DOTALL)
		for m in finder:
			if m.group(1) == None:
				continue
			waypoints.append({
				'lat' : self.from_dm(m.group('lat_sign'), m.group('lat_d'), m.group('lat_m')), 
				'lon' : self.from_dm(m.group('lon_sign'), m.group('lon_d'), m.group('lon_m')), 
				'id' : "%s%s" % m.group('id_prefix', 'id'), 
				'name' : m.group('name'), 
				'comment' : m.group('comment')
			})

		return waypoints
	def treat_images(self, data):
		images = {}
		finder = re.finditer('<a href="([^"]+)" rel="lightbox"><img src="../images/stockholm/16x16/images.gif" align="absmiddle" border="0">([^<]+)</a>', data)
		for m in finder:
			if m.group(1) == None:
				continue
			images[m.group(1)] = m.group(2)
		return images
	
	 
	def __decode_htmlentities(self, string):
		def substitute_entity(match):
			ent = match.group(3)
			if match.group(1) == "#":
				# decoding by number
				if match.group(2) == '':
					# number is in decimal
					return unichr(int(ent))
				elif match.group(2) == 'x':
					# number is in hex
					return unichr(int('0x'+ent, 16))
			else:
			    # they were using a name
			    cp = n2cp.get(ent)
			    if cp: 
			    	return unichr(cp)
			    else: 
			    	return match.group()

		entity_re = re.compile(r'&(#?)(x?)(\w+);')
		return entity_re.subn(substitute_entity, string)[0]
		
	def update_coordinate(self, coordinate):
		response = self.get_cache_page(coordinate.name)
		return self.parse_cache_page(response, coordinate)
		#w = file('cachefile5.html', 'r')
		#return self.parse_cache_page(w, coordinate)
	
	def get_cache_page(self, cacheid):
		return self.downloader.get_reader('http://www.geocaching.com/seek/cache_details.aspx?wp=%s' % cacheid)
		
	def get_geocaches(self, location):
		c1, c2 = location
		url = 'http://www.geocaching.com/map/default.aspx?lat=49&lng=6'
		values = {'eo_cb_id':'ctl00_ContentBody_cbAjax',
			'eo_cb_param':'{"c": 1, "m": "", "d": "%f|%f|%f|%f"}' % (max(c1.lat, c2.lat), min(c1.lat, c2.lat), max(c1.lon, c2.lon), min(c1.lon, c2.lon)),
			'eo_version':'5.0.51.2'
		}
		response = self.downloader.get_reader(url, values)
		
		the_page = response.read()

		extractor = re.compile('.*<ExtraData><!\[CDATA\[(.*)\]\]>')
		match = extractor.match(the_page)
		if match == None:
			raise Exception('Seite konnte nicht abgerufen werden')
		text = match.group(1).replace("\\'", "'")
		print text
		a= json.loads(text)
		points = []
		for b in a['cs']['cc']:
			c = GeocacheCoordinate(b['lat'], b['lon'], b['gc'])
			c.title = b['nn']
			if b['ctid'] == 3:
				c.type = 'multi'
			elif b['ctid'] == 2:
				c.type = 'regular'
			elif b['ctid'] == 4:
				c.type = 'virtual'
			elif b['ctid'] == 6:
				c.type = 'event'
			elif b['ctid'] == 8:
				c.type = 'unknown'
			elif b['ctid'] == 11:
				c.type = 'webcam'
			else:
				c.type = 'unknown'
			c.found = b['f']
			points.append(c)
		return points
		
		
	def parse_cache_page(self, cache_page, coordinate):
		indesc = inshortdesc = inhints = inwaypoints = False
		inhead = True
		shortdesc = desc =  hints = waypoints = images = ''
		for line in cache_page:
			line = line.strip()
			#line = unicode(line, errors='replace')
	
			if line.startswith('<span id="ShortDescription">'):
				inhead = False
				inshortdesc = True
			elif line.startswith('<span id="LongDescription">'):
				inhead = False
				inshortdesc = False
				indesc = True
			elif line.startswith('<strong>Additional Hints&nbsp;(</strong>'):
				inhead = False
				inshortdesc = False
				indesc = False
				inhints = False
			elif line.startswith('<span id="Hints"'):
				inhead = False
				inshortdesc = False
				indesc = False
				inhints = True
			elif line.startswith('<span id="decryptHint"'):
				inhead = False
				inshortdesc = False
				indesc = False
				inhints = False
			elif line.startswith('<strong>Additional Waypoints</strong>'):
				inhead = False
				inshortdesc = False
				indesc = False
				inhints = False
				inwaypoints = True
			elif line.startswith('</table>') and inwaypoints:
				inwaypoints = False
			elif line.startswith('<span id="Images"'):
				images = line
					
			if inhead:
				if line.startswith('<span id="CacheOwner">'):
					owner = re.compile(".*by <[^>]+>([^<]+)</a>").match(line).group(1)
				elif line.startswith('<img src="../images/icons/container/'):
					size = re.compile(".*container/([^\\.]+)\\.").match(line).group(1)
				elif line.startswith('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Difficulty:'):
					difficulty = re.compile('.*"([0-9\\.]+) out of').match(line).group(1)
				elif line.startswith('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Terrain:'):
					terrain = re.compile('.*"([0-9\\.]+) out of').match(line).group(1)
				elif line.startswith('<a id="lnkPrintFriendly" class="lnk" href="cdpf.aspx?guid'):
					guid = re.compile('.*cdpf\\.aspx\?guid=([a-z0-9-]+)"').match(line).group(1)
			if inshortdesc:
				shortdesc += "%s\n" % line
		
			if indesc:
				desc += "%s\n" % line
		
			if inhints:
				hints += "%s\n" % line
		
			if inwaypoints:
				waypoints += "%s  " % line

		coordinate.owner = self.__decode_htmlentities(owner)
		if size == 'micro':
			coordinate.size = 1
		elif size == 'small':
			coordinate.size = 2
		elif size == 'regular':
			coordinate.size = 3
		elif size == 'big':
			coordinate.size = 4
		elif size == 'huge':
			coordinate.size = 5
		else:
			print "Size not known: %s" % size
			coordinate.size = 5
		coordinate.difficulty = 10*float(difficulty)
		coordinate.terrain = 10*float(terrain)
		coordinate.shortdesc = self.treat_shortdesc(shortdesc)
		coordinate.desc = self.treat_desc(desc)
		coordinate.hints = self.rot13(self.treat_hints(hints))
		coordinate.waypoints = self.treat_waypoints(waypoints)
		coordinate.images = self.treat_images(images)
		
		return coordinate
		
	
class HTMLExporter():
	def __init__(self, downloader, path, resize = None):
		self.downloader = downloader
		self.path = path
		self.resize = resize
		if not os.path.exists(path):
			try:
				os.mkdir(path)
			except:
				raise 
		
	def export(self, coordinate):
		if coordinate.name == '':
			raise Exception('Koordinate hat keinen Namen')
		filename = self.get_uri(coordinate)
		f = open(filename, 'w')
		self.write_html(f, coordinate)
		f.close()
		
	def get_uri(self, coordinate):
		return os.path.join(self.path, "%s%shtml" % (coordinate.name, os.extsep))
		
	def write_index(self, caches):
		b = [{'n' : c.name, 't' : c.title} for c in caches]
		caches = json.dumps(b)
		f = open(os.path.join(self.path, "index.html"), 'w')
		f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')
		f.write(' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
		f.write('<html xmlns="http://www.w3.org/1999/xhtml"> <head>')
		f.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
		f.write(' <title>Geocache suchen</title> <script type="text/javascript">\n')
		f.write(' var caches = %s;' % caches)
		f.write("""function refresh() {
	    s = document.getElementById('search'); t = s.value.toLowerCase(); ht = '';
   		if (t.length > 2) { for (var c in caches) {
   				if (caches[c]['t'].toLowerCase().indexOf(t) != -1 || caches[c]['n'].toLowerCase().indexOf(t) != -1) {
   					ht = ht + "<a href='" + caches[c]['n'] + ".html'>" + caches[c]['n'] + "|" + caches[c]['t'] + "<br>";
   				} }
   		} else { ht = "(Bitte mehr als 2 Zeichen eingeben)"; }
   		document.getElementById('res').innerHTML = ht; }
		  </script>
		 </head> <body>
		  <fieldset><legend>Geocache suchen</legend>
		  <input type="text" name="search" id="search" onkeyup="refresh()" />
		  </fieldset>
		  <fieldset><legend>Ergebnisse</legend>
		  <div id="res">Bitte Suchbegriff eingeben!</div>
		  </fieldset>  </body> </html>
		""")
		f.close()
		
		

	def write_html(self, f, coordinate):
		f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')
		f.write(' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
		f.write('<html xmlns="http://www.w3.org/1999/xhtml">\n <head>\n')
		f.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
		self.write_header(f, coordinate)
		f.write(' </head>\n <body>\n')
		self.write_body(f, coordinate)
		f.write(' </body>\n</html>\n')
	
	def write_header(self, f, coordinate):
		f.write('  <title>%s|%s</title>\n' % (coordinate.name, coordinate.title))
		
	def write_body(self, f, coordinate):
		f.write('  <h2>%s|%s</h2>\n' % (coordinate.name, coordinate.title))
		f.write('  <fieldset><legend>Daten</legend>\n')
		f.write('   <div style="display:inline-block;"><b>Size:</b> %s/5</div><br />\n' % coordinate.size)
		f.write('   <div style="display:inline-block;"><b>Difficulty:</b> %.1f/5</div><br />\n' % (coordinate.difficulty/10))
		f.write('   <div style="display:inline-block;"><b>Terrain:</b> %.1f/5</div><br />\n' % (coordinate.terrain/10))
		f.write('  </fieldset>\n')
		f.write('  <fieldset><legend>Koordinaten</legend>\n')
		f.write('   <div style="display:inline-block;"><b>MAIN:</b> <code>%s %s</code></div><br />\n' % (coordinate.get_lat(geo.Coordinate.FORMAT_DM), coordinate.get_lon(geo.Coordinate.FORMAT_DM)))
		if len(coordinate.waypoints) > 0:
			f.write('   <table>\n')
			for w in coordinate.waypoints:
				if not (w['lat'] == -1 and w['lon'] == -1):
					n = geo.Coordinate(w['lat'], w['lon'])
					latlon = "%s %s" % (n.get_lat(geo.Coordinate.FORMAT_DM), n.get_lon(geo.Coordinate.FORMAT_DM))
				else:
					latlon = "???"
				f.write('    <tr style="background-color:#bbf"><th>%s</th><td><code>%s</code></td></tr>\n' % (w['name'], latlon))
				f.write('    <tr style="background-color:#ddd"><td colspan="2">%s</tr>\n' % w['comment'])
			f.write('   </table>\n')
		f.write('  </fieldset>')
		f.write('  <fieldset><legend>Cachebeschreibung</legend>\n')
		f.write(self.find_images(coordinate))
		f.write('  </fieldset>')
		if len(coordinate.images) > 0:
			f.write('  <fieldset><legend>Bilder</legend>\n')
			for image, description in coordinate.images.items():
				f.write('   <em>%s:</em><br />\n' % description)
				f.write('   <img src="%s" />\n' % self.download(image))
				f.write('   <hr />\n')
			f.write('  </fieldset>')
		
	def find_images(self, coordinate):
		self.current_image = 1
		self.current_cache = coordinate.name
		self.found_images = {}
		return re.sub('(?is)(<img[^>]+src=["\']?)([^ >"\']+)([^>]+?>)', self.download_and_rewrite, coordinate.desc)
		
	def download_and_rewrite(self, m):
		url = m.group(2)
		print m.group(2)
		if not url.startswith('http://'):
			return m.group(0)
		return m.group(1) + self.download(url) + m.group(3)
		
	def download(self, url):
		if url in self.found_images.keys():
			return self.found_images[url]
		ext = url.rsplit('.', 1)[1]
		if not re.match('/^[a-zA-Z0-9]+$/', ext):
			ext = 'img'
		try:
			filename = os.path.join(self.path, "%s-image%d.%s" % (self.current_cache, self.current_image, ext))
			f = open(filename, 'wb')
			f.write(self.downloader.get_reader(url).read())
			f.close()
			if Image != None and self.resize != None and self.resize > 0:
				im = Image.open(filename)
				im.thumbnail((self.resize, self.resize), Image.ANTIALIAS)
				im.save(filename)
		except:
			print "could not download %s" % url
			
		self.found_images[url] = filename
		self.current_image += 1
		return filename
		
		
"""
class GpxReader():
	def __init__(self, pointprovider):
		self.pointprovider = pointprovider
		
	def read_file(self, filename):
		lat = lon = -1
		uid = name = comment = description = url = cachetype = ''
		found = intag = False
		locline = re.compile('<wpt lat="(\d+\.\d+)" lon="(\d+\.\d+)"')
		if os.path.exists(filename):
			for line in open(filename, 'r'):
				line = line.strip()
				if line.startswith('<wpt'):
					match = locline.match(line)
					lat = float(match.group(1))
					lon = float(match.group(2))
					intag = True
				elif line.startswith('<name>') and intag and lat != -1 and lon != -1:
					name = line.rpartition('</name>')[0][6:]
					currentcoord = GeocacheCoordinate(lat, lon, name)
				elif line.startswith('<cmt>') and intag:
					currentcoord.title = line.rpartition('</cmt>')[0][5:]
				elif line.startswith('<desc>') and intag:
					currentcoord.desc = line.rpartition('</desc>')[0][6:]
				elif line.startswith('<sym>') and intag:
					typestring = line.rpartition('</sym>')[0][5:].split('-')
					currentcoord.type = typestring[-1]
					if typestring[1] == 'ifound':
						currentcoord.found = True
						#found = False												
				elif line.startswith('</wpt>') and intag:
					self.pointprovider.add_point(currentcoord)
					currentcoord = None
					lat = lon = -1
					uid = name = comment = description = url = cachetype = ''
					found = intag = False
"""
