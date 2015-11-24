""" Data wrapper classes, and processing functions.
	
	Author: Alastair Hughes
"""

from config import DATE_FIELD, transformations, PATCH_NUMBER_FIELD
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
		self.shapes, self.patches = load_shapes(self.gis)
		# Find the bounding box, center, and size for the gis shapes.
		self.bbox = bounding_box(self.shapes)
		self.center = [((self.bbox[i] + self.bbox[i+2]) / 2) for i in range(2)]
		self.size = [(self.bbox[i+2] - self.bbox[i]) for i in range(2)]
		
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

		
def find_patch_files(dir):
	""" Generates a dict mapping from patch numbers to absolute filenames """
	
	# Get a list of all of the files in the given directory.
	files = listdir(dir)
	
	# Find all of those files which look like CSV patch files, and add them
	# to the dict.
	patches = {}
	for file in files:
		# Check that the file name is in a sane format (ie looks like a CSV patch file).
		#TODO: We make some assumptions here about the format of the file names
		#	   which may or may not be accurate.
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
	
	# Turn the resulting data into a index[patch[value]] format.
	result = {} # index: {patch: values}
	for patch in patches:
		for index in patches[patch]:
			if index not in result:
				result[index] = {}
			result[index][patch] = patches[patch][index]
			
	return result
	
def load_shapes(shape_file):
	""" Generate a list of shapes, and a map from patches to information about
		the patches.
	"""
	
	sf = shapefile.Reader(shape_file)
	
	# Data structures
	shapes = [] # List of shapes
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
		shapes.append(sf.shape(id))
		record = sf.record(id)
		if record != None:
			# Extract the patch number.
			patch = record[fields[PATCH_NUMBER_FIELD]]
			if patch in patches:
				raise ValueError("Patch {} referenced twice!".format(patch))
			# Add the patch to the map.
			patches[patch] = {'shape': shapes[-1]}
			# Add the remaining data.
			for field in fields:
				patches[patch][field] = record[fields[field]]
	
	# Close the reader; there is no function for doing so, we just close the
	# files.
	for file in sf.shp, sf.shx:
		file.close()
	
	return shapes, patches

def bounding_box(shapes):
	""" Returns the bounding box for all of the given shapes """
	
	mins = [float('inf'), float('inf')]
	maxs = [-float('inf'), -float('inf')]
	
	for shape in shapes:
		min_pos = [min(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
		max_pos = [max(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
		for i in range(2):
			if min_pos[i] < mins[i]:
				mins[i] = min_pos[i]
			if max_pos[i] > maxs[i]:
				maxs[i] = max_pos[i]
	
	return [mins[0], mins[1], maxs[0], maxs[1]]
		

class Values():
	""" Wrapper class to contain transformed data from a specific model """
	
	def __init__(self, model, field, data_type='float', transform='basic'):
		""" Initialise self """
		
		self.model = model
		self.transform = transform
		
		if data_type == 'float':
			process = lambda v: float(v)
		else:
			#TODO: Implement more data types... string is one obvious one.
			# 	   Even better, get to a point where we don't have to care
			#	   about it here...
			# 	   A different colour mapping function will be required, and
			#	   maximums and minimums are different and not really
			#	   applicable. The scale code would have to change...
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
			# Using this: http://stackoverflow.com/questions/10901085/range-values-to-pseudocolor/10907855#10907855	
			# Convert to something in the range of 0 to 120 degrees, fed into
			# the colorsys function (red..green in HSV)
			#TODO: Would it make more sense to use a single colour?
			hue = ((value - self.min) / (self.max - self.min)) # 0-1
			return [int(i*255) for i in colorsys.hsv_to_rgb(hue / 3, 1.0, 1.0)]
		
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
		
		return "Field of interest: " + self.field + '\n' + \
			"GIS: " + self.model.gis + '\n' + \
			"CSV: " + self.model.csv + '\n' + \
			"Transformation type: " + self.transform
		
				