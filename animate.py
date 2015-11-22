""" Animate a given set of CSV data ontop of a GIS file.

	Future improvements:
	- Removing all of the TODO's...
	- More output formats
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups
	- Code cleanups
	- Packaging
	- Rendering of multiple plots with different values/transformation functions
	- More flexible time handling (days last more than one frame)
		This could be handy for changing the speed of the simulation to reflect
		changes (speeding up over boring bits...)
	- Different colourings?
	- Parameters rendered (field of interest, files)
	- More transformation functions/options
	- Documentation
	- Ways of easily specifying custom transformations
	- Dynamic viewer

	Author: Alastair Hughes
"""

# Value transformation functions
basic_value = lambda values, index, patch: float(values[index][patch])
# change_value
change_value = lambda values, index, patch: float(values[index][patch]) - \
	float(values.get(index - 1, {patch: values[index][patch]})[patch])
#TODO: Other useful functions might be exponential decay based
#	   (with min as the baseline, max as the max)

# Config
#TODO: Figure out a more flexible way of doing this...
GIS_FILES = "H:/My Documents/vis/gis/SmallPatches"
CSV_DIR = "H:/My Documents/vis/csv"
FIELD_OF_INTEREST = "Soil.SoilWater.Drainage"
DATE_FIELD = "Clock.Today" # Field name for the date
FPS = 2 # Note that 1 does not appear to work?
DEFAULT_COLOUR = (255, 255, 255)
FONT_HEIGHT = 30 # The height for any fonts.
VALUE2VALUE = basic_value # Value transformation function

# Import the other modules...
import display, render, data
from shapes import bounding_box
# colorsys is used for the gradients
import colorsys
# We use pygame for font rendering...
import pygame.font


def gen_colour_transform(values):
	""" Generate a transformation function transforming from a given value
		to a colour on a gradient for the data points.
	"""
	
	# Find the minimum and maximum values
	min = float("inf")
	max = -float("inf")
	for index in values:
		for patch in values[index]:
			value = values[index][patch]
			if value < min:
				min = value
			if value > max:
				max = value

	def value2colour(value):
		""" Convert from a given value to a colour """
		# Using this: http://stackoverflow.com/questions/10901085/range-values-to-pseudocolor/10907855#10907855	
		# Convert to something in the range of 0 to 120 degrees, fed into the
		# colorsys function (red..green in HSV)
		#TODO: Would it make more sense to use a single colour?
		#TODO: This cannot currently handle strings (would be nice if this
		# 	   could be custom-defined/overridden)
		#TODO: Data with large jumps does not work well with this :(
		hue = ((value - min) / (max - min)) # 0-1
		return [int(i*255) for i in colorsys.hsv_to_rgb(hue / 3, 1.0, 1.0)]
		
	return value2colour, min, max


def gen_point_transform(shapes):
	""" Return a function to transform the points so that they fit nicely
		in the given size, centered around the origin (0, 0).
	"""
	
	# Find the minimum and maximum values x and y values.
	min_x, min_y, max_x, max_y = bounding_box(shapes)
	center_x = (max_x + min_x) / 2
	center_y = (max_y + min_y) / 2
	width = max_x - min_x
	height = max_y - min_y

	def centering(vert, size):
		""" Transform the given vertex to fit nicely in relation to the
			given size
		"""
		
		# The scaling factor required to scale the image to fit nicely in
		# the given size.
		# This is the minimum of the x and y scaling to avoid clipping.
		x_scale = size[0]/width
		y_scale = size[1]/height
		scale = min(x_scale, y_scale)
		
		# Return a scaled and recentered vertex.
		return ((vert[0] - center_x)*scale, (vert[1] - center_y)*scale)
	
	return centering
	

def main(gis, csv, field):
	""" Generate and display the animation! """
	
	# Load the patches and values...
	print("Loading data...")
	patch_files = data.find_patch_files(csv)
	#TODO: It would be nice if I could extract all the data I wanted without
	# 	   having to load the same files multiple times...
	orig_values = data.load_values(patch_files, field)
	orig_dates = data.load_values(patch_files, DATE_FIELD)
	shapes, patches = data.load_shapes(gis)
	
	# Transform the values with the given transformation function.
	print("Transforming the data points...")
	values = {}
	for index in orig_values:
		values[index] = {}
		for patch in orig_values[index]:
			values[index][patch] = VALUE2VALUE(orig_values, index, patch)
	
	# Generate some transformation functions.
	# Minimum and maximum is required for the scale
	value2colour, min, max = gen_colour_transform(values)
	centering = gen_point_transform(shapes)
	
	# Turn the values into colours.
	print("Converting values to colours...")
	for index in values:
		for patch in values[index]:
			values[index][patch] = value2colour(values[index][patch])
			
	# Verify the dates, and compress into a row: date mapping.
	print("Verifying dates...")
	dates = {}
	for index in orig_dates:
		date = None
		for patch in orig_dates[index]:
			if date == None:
				date = orig_dates[index][patch]
			elif date != orig_dates[index][patch]:
				raise ValueError("Dates and rows do not line up for some CSV files!")
		dates[index] = date

	# Create a render_frame function.
	# Init the fonts.
	pygame.font.init()
	font = pygame.font.Font(None, FONT_HEIGHT)
	def render_frame(surface, frame):
		# Render the frame.
		surface.fill(DEFAULT_COLOUR)
		render.render(surface, values, shapes, centering, patches, frame)
		render.render_scale(surface, min, max, value2colour, font)
		render.render_date(surface, dates[frame], font)
	
	# Play the animation
	display.play(render_frame, frames=len(values), fps=FPS)

if __name__ == "__main__":
	main(GIS_FILES, CSV_DIR, FIELD_OF_INTEREST)
	