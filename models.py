""" Data wrapper classes.
	
	Author: Alastair Hughes
"""

# We currently use data functions for loading data into a model.
#TODO: Move those functions from data into the model code.
import data, shapes
from config import DATE_FIELD, transformations
# colorsys is used for the gradients
import colorsys

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


class Values():
	""" Wrapper class to contain transformed data from a specific model """
	
	def __init__(self, model, field, data_type='float', transform='basic'):
		""" Initialise self """
		
		self.model = model
		
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
			
		orig_values = self.model.extract_field(field, process)
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
			#TODO: Data with large jumps does not work well with this :(
			hue = ((value - self.min) / (self.max - self.min)) # 0-1
			return [int(i*255) for i in colorsys.hsv_to_rgb(hue / 3, 1.0, 1.0)]
		
		self.value2colour = value2colour
		
		# Convert all of the values into colours.
		for index in new_values:
			for patch in new_values[index]:
				new_values[index][patch] = value2colour(new_values[index][patch])
		self.values = new_values

		

		