#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import geo

class GpsReader():

	BEARING_HOLD_SPEED = 3

	EMPTY = {
			'position': None,
			'altitude': None,
			'bearing': None,
			'speed': None,
			'sats': 0,
			'sats_known': 0
		}

	def __init__(self, gui):
		self.gui = gui
		self.status = "connecting..."
		self.connected = False
		self.connect()
		self.last_bearing = None
		
	
	def connect(self):
		try:
			global gpsd_connection
			gpsd_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			gpsd_connection.connect(("127.0.0.1", 2947))
			self.status = "connected"
			self.connected = True
		except:
			self.status = "Could not connect to GPSD on Localhost, Port 2947"
			print "Could not connect"
			self.connected = False
		
	def get_data(self):
		try:
			if not self.connected:
				self.connect()
				if not self.connected:
					return self.EMPTY
			gpsd_connection.send("%s\r\n" % 'o')
			data = gpsd_connection.recv(512)
			gpsd_connection.send("%s\r\n" % 'y')
			quality_data = gpsd_connection.recv(512)
			# 1: Parse Quality Data
			
			# example output:
			# GPSD,Y=- 1243847265.000 10:32 3 105 0 0:2 36 303 20 0:16 9 65 26 
			#  1:13 87 259 35 1:4 60 251 30 1:23 54 60 37 1:25 51 149 24 0:8 2 
			#  188 0 0:7 33 168 24 1:20 26 110 28 1:
			
			if quality_data.strip() == "GPSD,Y=?":
				sats = 0
				sats_known = 0
			else:
				sats = 0
				groups = quality_data.split(':')
				sats_known = int(groups[0].split(' ')[2])
				for i in range(1, sats_known):
					if groups[i].split(' ')[4] == "1":
						sats = sats + 1
			
			if data.strip() == "GPSD,O=?":
				self.status = "No GPS signal"
				return {
					'position': None,
					'altitude': None,
					'bearing': None,
					'speed': None,
					'sats': sats,
					'sats_known': sats_known
				}

				
			# 2: Get current position, altitude, bearing and speed
			
			# example output:
			# GPSD,O=- 1243530779.000 ? 49.736876 6.686998 271.49 1.20 1.61 49.8566 0.050 -0.175 ? ? ? 3
			# GPSD,O=- 1251325613.000 ? 49.734453 6.686360 ? 10.55 ? 180.1476 1.350 ? ? ? ? 2

			# or
			# GPSD,O=?
			try:
				[tag, timestamp, time_error, lat, lon, alt, err_hor, err_vert, track, speed, delta_alt, err_track, err_speed, err_delta_alt, mode] = data.split(' ')
			except:
				print "GPSD Output: \n%s\n  -- cannot be parsed." % data
				self.status = "Could not read GPSD output."

			if speed < self.BEARING_HOLD_SPEED and self.last_bearing != None:
				track = self.last_bearing
			else:
				self.last_bearing = track
				
			return {
				'position': geo.Coordinate(float(lat), float(lon)),
				'altitude': self.to_float(alt),
				'bearing': self.to_float(track),
				'speed': self.to_float(speed),
				'sats': int(sats),
				'sats_known': sats_known
			}
		except Exception as e:
			print "Fehler beim Auslesen der Daten: %s " % e
			return self.EMPTY
			
	def to_float(self, string):
		try:
			return float(string)
		except:
			return 0.0
