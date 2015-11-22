""" Animate a given set of CSV data ontop of a GIS file.

	Current todo:
	- Improve the flexibility of the transformations

	Future improvements:
	- Displaying dates for each datapoint at the top-left or similar
	- More output formats
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups

	Author: Alastair Hughes
"""

# Config
#TODO: Figure out a more flexible way of doing this...
GIS_FILES = "H:/My Documents/vis/gis/SmallPatches"
CSV_DIR = "H:/My Documents/vis/csv"
FIELD_OF_INTEREST = "Soil.SoilWater.Drainage"
FPS = 20 # Note that 1 does not appear to work?

# Import the other modules...
import display, render, data
from shapes import bounding_box
# colorsys is used for the gradients
import colorsys

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
		hue = ((value - min) / (max - min)) # 0-1
		return [int(i*255) for i in colorsys.hsv_to_rgb(hue / 3, 1.0, 1.0)]
		
	return value2colour


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
	patch_files = data.find_patch_files(csv)
	values = data.load_values(patch_files, field)
	shapes, patches = data.load_shapes(gis)
	
	# Generate some transformation functions.
	value2colour = gen_colour_transform(values)
	centering = gen_point_transform(shapes)
	
	# Transform the data as required.
	for index in values:
		for patch in values[index]:
			values[index][patch] = value2colour(values[index][patch])

	# Create a render_frame function.
	def render_frame(surface, time):
		# Render the frame
		surface.fill((255, 255, 255))
		render.render(surface, values, shapes, centering, patches, time)
	
	# Play the animation
	display.play(render_frame, frames=len(values), fps=FPS)

if __name__ == "__main__":
	main(GIS_FILES, CSV_DIR, FIELD_OF_INTEREST)
	