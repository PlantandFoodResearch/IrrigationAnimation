""" Data wrapper classes.
	
	Author: Alastair Hughes
"""

import data, shapes
from config import DATE_FIELD

class Model():
	""" Wrapper class to contain raw data about the models """
	
	def __init__(self, gis, csv):
		""" Load the data from the CSV and GIS files, and generate some
			overview information.
		"""
		
		# Load the data.
		print("Loading data...")
		
		# Load the GIS data.
		self.shapes, self.patches = data.load_shapes(gis)
		# Find the bounding box, center, and size for the gis shapes.
		self.bbox = shapes.bounding_box(self.shapes)
		self.center = [((self.bbox[i] + self.bbox[i+2]) / 2) for i in range(2)]
		self.size = [(self.bbox[i+2] - self.bbox[i]) for i in range(2)]
		
		# Load the CSV files.
		patch_files = data.find_patch_files(csv)
		self.data = data.raw_patches(patch_files)
		dates = self.extract_field(DATE_FIELD)
		
		# Verify the dates, and compress into a row: date mapping.
		print("Verifying dates...")
		self.dates = {}
		for index in dates:
			date = None
			for patch in dates[index]:
				if date == None:
					date = dates[index][patch]
				elif date != dates[index][patch]:
					#TODO: Try to clarify the error message...
					raise ValueError("Dates and rows do not line up for some CSV files!")
			self.dates[index] = date
			
			
	def extract_field(self, field, process=lambda v: v):
		""" Extract a single field from the loaded data, and optionally
			apply a function 'process' to each piece of data.
		"""
	
		result = {}
		for index in self.data:
			result[index] = {}
			for patch in self.data[index]:
				result[index][patch] = process(self.data[index][patch][field].strip())
	
		return result
		
	def gen_fit(self):
		""" Generate a function for fitting vertices from the shapes into a
			given area, centered around the origin.
		"""

		def centering(vert, size):
			""" Transform the given vertex to fit nicely in relation to the
				given size, center it around the origin, and scale it.
			"""
			
			# The scaling factor required to scale the image to fit nicely in
			# the given size.
			# This is the minimum of the x and y scaling to avoid clipping.
			scale = min([float(size[i])/self.size[i] for i in range(2)])
			
			# Return a scaled and recentered vertex.
			return [(vert[i] - self.center[i])*scale for i in range(2)]
		
		return centering
			