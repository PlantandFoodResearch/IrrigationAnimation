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
	

def main(gis, csv, field):
	""" Generate and display the animation! """
	
	# Load the patches and values...
	patch_files = data.find_patch_files(csv)
	values = data.load_values(patch_files, field)
	shapes, patches = data.load_shapes(gis)
	
	# Generate some transformation functions.
	value2colour = gen_colour_transform(values)
	
	# Transform the data as required.
	for index in values:
		for patch in values[index]:
			values[index][patch] = value2colour(values[index][patch])

	# Create a render_frame function.
	def render_frame(surface, time):
		# Render the frame
		surface.fill((255, 255, 255))
		render.render(surface, values, shapes, patches, time)
	
	# Play the animation
	display.play(render_frame, frames=len(values), fps=FPS)

if __name__ == "__main__":
	main(GIS_FILES, CSV_DIR, FIELD_OF_INTEREST)
	