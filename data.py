""" Module to load and manipulate the data in the gis and model files into
	something useful.
	
	The model data needs to be in a date[patch[value]] format.
	The shape data needs to be in a patch[shape] format.
	
	Author: Alastair Hughes
"""

# We need to know the field name for dates.
DATE_NAME = "Clock.Today"

# To find and load the CSV model files, we need some functions.
from os import listdir
import os.path
import re
import csv

# shapefile is used to open the GIS files.
import shapefile


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
		#TODO: Create some tests to check that this is working properly...
		match = re.search(r"(Report)([1-9][0-9]*)(\.csv)$", file)
		
		if match:
			# Extract the patch number (second field) and the full file path
			patches[int(match.group(2))] = os.path.join(dir, file)
		else:
			print("Ignoring file in patch directory '%s'!" %file)
	
	return patches
	
	
def load_values(files, data_name):
	""" Loads the data from the patch files, and turns it into the required
		format.
	"""
	
	# Open and load each patch file.
	patches = {} # patch_no: {date: value}
	for patch_no in files:
		patches[patch_no] = {}
		# Parse the patch file.
		with open(files[patch_no]) as patch:
			for index, row in enumerate(csv.DictReader(patch)):
				# Insert the values into the dict.
				# The fields need to be stripped to remove excess spaces...
				# We exploit the fact that the rows are in order...
				patches[patch_no][index] = row[data_name].strip()
	
	# Turn the resulting data into a date[patch[value]] format.
	result = {} # date: {patch: value}
	for patch in patches:
		for index in patches[patch]:
			if index not in result:
				result[index] = {}
			result[index][patch] = patches[patch][index]
			
	return result


def load_shapes(shape_file):
	""" Load the patches from the given shape file prefix, and return a dict
		in the form of {patch_no: shape}.
	"""
	
	# Init the patch shapes...
	#TODO: Should the shapes be anything special??? Easily renderable??
	patches = {} # patch_no: shape
	
	#TODO: Do I need to/can I close the shape file?
	sf = shapefile.Reader(shape_file)
	# Load the items.
	items = sf.shapeRecords()
	
	# Extract the information from the records.
	#TODO: Do we really only need the patch no? What about the soil type?
	#	   Or field? Or the irrigator? Or the manager?
	for item in items:
		#TODO: This is hard coded, but we should be able to extract the correct
		# 	   field number via inspection of sf.fields.
		#TODO: Check that we don't loose records by accident...
		patches[item.record[5]] = item.shape
		
	return patches
	
	
def load_shapes(shape_file):
	""" Generate a list of shapes, and a map from patches to information about
		the patches.
	"""
	
	#TODO: Do I need to/can I close the shape file?
	sf = shapefile.Reader(shape_file)
	
	# Data structures
	shapes = [] # List of shapes
	# Map for patches
	patches = {} # patch: {key: value}
	
	# Iterate through the records and fill in the datatypes.
	for id in range(sf.numRecords):
		shapes.append(sf.shape(id))
		record = sf.record(id)
		if record != None:
			# Extract the patch number.
			#TODO: We only record the shape associated with the patch; should
			#	   we record more? Soil type? Field no? ???
			#TODO: This is hard coded, but we should be able to extract the correct
			# 	   field number via inspection of sf.fields.patch = record[5]
			patch = record[5]
			if patch in patches:
				raise ValueError("Patch {} referenced twice!".format(patch))
			# Add it to the map
			patches[patch] = {'shape': shapes[-1]}
	
	return shapes, patches
	

if __name__ == "__main__":
	patch_files = find_patch_files("H:/My Documents/vis/csv")
	values = load_values(patch_files, "Soil.SoilWater.Drainage")
	
	shapes, patches = load_shapes("H:/My Documents/vis/gis/MediumPatches")
	