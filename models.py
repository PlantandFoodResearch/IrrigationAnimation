""" Data wrapper classes.
	
	Author: Alastair Hughes
"""

import data
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
			