
class Cli():
	def __init__(self):
		self.nt = 1
		pass
		
	def show(self):
		self.parse_inpurt()

	def parse_input (self):
		while self.has_next():
			if sys.argv[self.nt] == 'import':
				self.parse_import()
			elif sys.argv[self.nt] == 'filter':
				self.parse_filter()
			elif sys.argv[self.nt] == 'do':
				self.parse_do()
			else: 
				self.parse_error("Expected 'import', 'filter' or 'do'")
			
		
	def parse_import(self):
		self.nt += 1
		if not self.has_next():
			self.parse_error("Expected import actions.")
		
		token = sys.argv[self.next_token]
		if token == '--fetch-index':	
			self.nt += 1
			coord1 = self.parse_coord()
			self.nt += 1
			coord2 = self.parse_coord()
			self.import(coord1, coord2)
		elif token == '--fetch-index-radius':
			self.nt += 1
			coord1 = self.parse_coord()
			self.nt += 1
			radius = self.parse_radius()
			self.import(coord1, radius)
		else:
			return
		
	def parse_filter(self):
		if not self.has_next():
			self.parse_error("Expected filter options.")
		while self.has_next():
			token = sys.argv[self.next_token]
			self.nt += 1
			if token == '--in':
				coord1 = self.parse_coord()
				coord2 = self.parse_coord()
				self.add_filter_in(coord1, coord2)
			elif token == '--in-radius':
				coord1 = self.parse_coord()
				radius = self.parse_radius()
				self.add_filter_in(coord1, coord2)
			elif token == '--found' or token == '-f':
				self.add_filter_found(True)
			elif token == '--not-found' or token == '-F':
				self.add_filter_found(False)
			elif token == '-w':
				self.add_filter_has_details(True)
			elif token == '-s' or token == '--size':
				size = self.parse_size()
				self.add_filter_size(size)
			elif token == '-d' or token == '--difficulty':
				diff = self.parse_difficulty()
				self.add_filter_difficulty(diff)
			elif token == '-t' or token == '--terrain':
				terr = self.parse_terrain()
				self.add_filter_terrain(terr)
			elif token == '-T' or token == '--type':
				types = self.parse_types()
				self.add_filter_types(types)
			elif token == '-o' or token == '--owner':
				owner = self.parse_string()
				self.add_filter_owner(owner)
			elif token == '-n' or token == '--name':
				name = self.parse_string()
				self.add_filter_name (name)
			elif token == '-i' or token == '--id':
				id = self.parse_string()
				self.add_filter_id (id)
			else:
				return
				
	def parse_actions(self):
		if not self.has_next():
			self.parse_error("Expected actions.")
		while self.has_next():
			token = sys.argv[self.next_token]
			self.nt += 1
			if token == '--print':
				self.action_print()
			elif token == '--fetch-details':
				self.action_fetch_details()
			elif token == '--export-html':
				folder = self.parse_string()
				self.action_export_html(folder)
			elif token == '--export-gpx':
				folder = self.parse_string()
				self.action_export_gpx(folder)
			elif token == '--export-single-gpx':
				filename = self.parse_string()
				self.action_export_single_gpx(filename)
			elif token == '--draw-map':
				zoom = self.parse_integer()
				filename = self.parse_string()
				self.action_draw_map(zoom, filename)
			elif token == '--draw-maps':
				zoom = self.parse_integer()
				folder = self.parse_string()
				self.action_draw_maps(zoom, folder)
			else:
				self.parse_error("Unknown export action: %s" % token)
				
				
			
			
				
				
		
		
	def has_next(self):
		# if we have 5 tokens
		# then 1..4 are valid tokens (0 is command)
		# "5" is len(tokens)
		# so we have a next token, if next_token < len(tokens)-1
		return (self.next_token < len(sys.argv)-1)
