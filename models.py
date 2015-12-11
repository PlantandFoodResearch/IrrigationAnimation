""" Data wrapper classes, and processing functions.
	
	Author: Alastair Hughes
"""

from constants import AREA_FIELD, DATE_FIELD, FIELD_NO_FIELD, \
	PATCH_NUMBER_FIELD
from transforms import transformations
# colorsys is used for the gradients
import colorsys

# To find and load the CSV model files, we need some functions.
from os import listdir
import os.path
import re
import csv

# shapefile is used to open the GIS files.
import shapefile


class Model():
	""" Wrapper class to contain raw data about the models """
	
	def __init__(self, gis, csv):
		""" Load the data from the CSV and GIS files, and generate some
			overview information.
		"""
		
		# Load the data.
		print("Loading data...")
		
		# Load the GIS data.
		self.gis = gis
		self.patches = load_shapes(self.gis)
		
		# Load the CSV files.
		self.csv = csv
		patch_files = find_patch_files(self.csv)
		self.data = raw_patches(patch_files)
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
					raise ValueError("For some CSV files ({}, index = {}), the dates are not on equal rows!".format(csv, index))
			self.dates[index] = date

	def extract_field(self, field, process=lambda v: v):
		""" Extract a single field from the loaded data, and optionally
			apply a function 'process' to each piece of data.
		"""
	
		result = {}
		for index in self.data:
			result[index] = {}
			for patch in self.data[index]:
				result[index][patch] = process(self.data[index][patch][field])
	
		return result

	def fields(self):
		""" Return a list of possible fields """
		
		fields = set()
		for index in self.data:
			for patch in self.data[index]:
				for field in self.data[index][patch].keys():
					if field not in fields:
						fields.add(field)
		return fields

def find_patch_files(dir):
	""" Generates a dict mapping from patch numbers to absolute filenames """
	
	# Get a list of all of the files in the given directory.
	files = listdir(dir)
	
	# Find all of those files which look like CSV patch files, and add them
	# to the dict.
	patches = {}
	for file in files:
		# Check that the file name is in a sane format (ie looks like a CSV patch file).
		# TODO: We make some assumptions here about the format of the file names
		#	    which may or may not be accurate.
		match = re.search(r"(Report)([1-9][0-9]*)(\.csv)$", file)
		
		if match:
			# Extract the patch number (second field) and the full file path
			patches[int(match.group(2))] = os.path.join(dir, file)
		else:
			print("Ignoring file in patch directory '%s'!" %file)
	
	return patches
	
def raw_patches(files):
	""" Open the given patch files and extract all of the data """
	
	# Open and load each patch file.
	patches = {} # patch: {index: value}
	for patch_no in files:
		patches[patch_no] = {}
		# Parse the patch file.
		with open(files[patch_no]) as patch:
			for index, row in enumerate(csv.DictReader(patch)):
				# Insert the values into the dict.
				patches[patch_no][index] = row
	
	# Turn the resulting data into a index[patch[value]] format, and strip the
	# data.
	result = {} # index: {patch: values}
	for patch in patches:
		for index in patches[patch]:
			if index not in result:
				result[index] = {}
			result[index][patch] = {field.strip(): value.strip() \
				for field, value in patches[patch][index].items()}
			
	return result
	
def load_shapes(shape_file):
	""" Generate a list of shapes, and a map from patches to information about
		the patches.
	"""
	
	sf = shapefile.Reader(shape_file)
	
	# Map for patches
	patches = {} # patch: {key: value}
	
	# Create a map from field numbers to field names.
	fields = {}
	for index, field in enumerate(sf.fields[1:]):
		# field[0] is the name of the field ('Area', 'Zone', etc).
		# We offset by one because the first entry in fields is 'DeletionFlag'
		# which is not in the record for a given patch.
		fields[field[0]] = index
	
	# Iterate through the records and fill in the datatypes.
	for id in range(sf.numRecords):
		record = sf.record(id)
		# pyshp returns None is a record has been deleted, so ignore those
		# records.
		if record != None:
			# Extract the patch number.
			patch = record[fields[PATCH_NUMBER_FIELD]]
			if patch in patches:
				raise ValueError("Patch {} referenced twice!".format(patch))
			# Add the patch to the map.
			patches[patch] = {'shape': sf.shape(id)}
			# Add the remaining data.
			for field in fields:
				patches[patch][field] = record[fields[field]]
	
	# Close the reader; there is no function for doing so, we just close the
	# files.
	for file in sf.shp, sf.shx:
		file.close()
	
	return patches
		

class Values():
	""" Wrapper class to contain transformed data from a specific model """
	
	def __init__(self, model, field, data_type='float', transform='basic', \
		colour_range = [0.0, 1.0/4]):
		""" Initialise self """
		
		self.model = model
		self.transform = transform
		
		if data_type == 'float':
			process = float
		else:
			# TODO: Implement more data types... string is one obvious one.
			# 	   	Even better, get to a point where we don't have to care
			#	   	about it here...
			# 	   	A different colour mapping function will be required, and
			#	   	maximums and minimums are different and not really
			#	   	applicable.
			raise ValueError("Unknown data type {}".format(data_type))
			
		self.field = field
		orig_values = self.model.extract_field(self.field, process)
		# Transform the values with the given transformation function.
		transformation = transformations[transform]
		new_values = {}
		for index in orig_values:
			new_values[index] = {}
			for patch in orig_values[index]:
				new_values[index][patch] = transformation(orig_values, index, patch)
			
		# Find the minimum and maximum values.
		self.min = float("inf")
		self.max = -float("inf")
		for index in new_values:
			for patch in new_values[index]:
				value = new_values[index][patch]
				if value < self.min:
					self.min = value
				if value > self.max:
					self.max = value
		
		# Create the colour mapping function.
		def value2colour(value):
			""" Convert from a given value to a colour """
			# Using this: 
			# http://stackoverflow.com/questions/10901085/range-values-to-pseudocolor/10907855#10907855	
			# We scale to a specific colour range.
			# Convert to something in the range of 0 to 120 degrees, fed into
			# the colorsys function (red..green in HSV)
			try:
				hue = ((value - self.min) / (self.max - self.min)) # 0-1
			except ZeroDivisionError:
				hue = 0
			# Convert the hue into something in the given range.
			value = hue * (colour_range[1] - colour_range[0]) + colour_range[0]
			# Return a RGB version of that colour.
			return [int(i*255) for i in colorsys.hsv_to_rgb(value, 1.0, 1.0)]
		
		self.value2colour = value2colour
		
		# Convert all of the values into colours.
		self.values = {}
		self.actual_values = new_values
		for index in new_values:
			self.values[index] = {}
			for patch in new_values[index]:
				self.values[index][patch] = value2colour(new_values[index][patch])

	def description(self):
		""" Return a string description of self """
		
		# TODO: Make this configurable, ie string formatting (%f = field,
		#		%c = csv, etc)?
		
		return "Field of interest: " + self.field + '\n' + \
			"GIS: " + self.model.gis + '\n' + \
			"CSV: " + self.model.csv + '\n' + \
			"Transformation type: " + self.transform


class Graphable():
	""" Wrapper class for a model containing 'graphable' information - anything
		not tied to a specific patch.
	"""
	
	def __init__(self, model, field, label, field_nos = None, \
		statistics = ['min', 'mean', 'max']):
		""" Initialise self """
		
		self.model = model
		self.field = field
		self.label = label
		
		# Create a helper loading function.
		if field_nos == None:
			# TODO: Explore supporting other data types?
			load_field = lambda field: self.model.extract_field(field, float)
		else:
			# TODO: I'd like to make this filtering more generic (so that it
			#		can be applied elsewhere).
			# We are only interested in specific fields.
			fields = self.model.extract_field(FIELD_NO_FIELD, \
				lambda v: int(float(v)))
			# Get a list of patches that are in the right field.
			# We assume that the field nos remain the same.
			patches = []
			for patch in fields[0]:
				if fields[0][patch] in field_nos:
					patches.append(patch)
			# Define the helper function.
			def load_field(field):
				values = self.model.extract_field(field, float)
				filtered = {}
				for day in values:
					filtered[day] = {}
					for patch in patches:
						filtered[day][patch] = values[day][patch]
				return filtered
		
		# Load the values.
		values = load_field(self.field)
		
		# Get the areas and total area.
		simple_areas = load_field(AREA_FIELD)
		self.areas = {} # patch: area
		self.total_area = 0 # The total area.
		# We assume that areas remain the same, so pick the first area.
		# TODO: Add some checks for that.
		for patch in simple_areas[0]:
			area = int(simple_areas[0][patch])
			self.areas[patch] = area
			self.total_area += area
			
		# Calculate the requested statistics.
		# TODO: We should support weighting by area and not weighting by area.
		self.values = []
		for stat in statistics:
			if stat == 'mean':
				def day_func(index):
					""" Calculate the weighted mean for the given day """
					day = 0 # Weighted values for a given day.
					for patch in values[index]:
						day += values[index][patch] * self.areas[patch]
					return day / self.total_area
			elif stat == 'min':
				day_func = lambda day: min((values[day][patch] \
					for patch in values[day]))
			elif stat == 'max':
				day_func = lambda day: max((values[day][patch] \
					for patch in values[day]))
			elif stat == 'sum':
				day_func = lambda day: sum((values[day][patch] \
					for patch in values[day]))
			else:
				raise ValueError("Unknown statistic {}!".format(stat))
			self.values.append({day: day_func(day) for day in values})
				
		# Calculate the maximums and minimums.
		self.max = max([max(stat.values()) for stat in self.values])
		self.min = min([min(stat.values()) for stat in self.values])
		
	def __getitem__(self, date):
		""" Returns self's value on the given date.
			If it is a tuple, then it represents a range of values.
		"""
		
		return [stat[date] for stat in self.values]
		