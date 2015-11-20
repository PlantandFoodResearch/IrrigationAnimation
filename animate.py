""" Animate a given set of CSV data ontop of a GIS file.

	Current todo:
	- Improve the flexibility of the transformations
	- Add gradients to the rendering
	- Ani

	Future improvements:
	- More output formats
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups

	Author: Alastair Hughes
"""

# Config
#TODO: Figure out a more flexible way of doing this...
GIS_FILES="H:/My Documents/vis/gis/SmallPatches"
CSV_DIR="H:/My Documents/vis/csv"
FIELD_OF_INTEREST="Irrigation.IrrigationApplied"

import display, render, data

def main(gis, csv, field):
	""" Generate and display the animation! """
	
	# Load the patches and values...
	patch_files = data.find_patch_files(csv)
	values = data.load_values(patch_files, field)
	shapes, patches = data.load_shapes(gis)
	
	# Generate some transformation functions.

	# Create a render_frame function.
	def render_frame(surface, time):
		# Render the frame
		surface.fill((255, 255, 255))
		render.render(surface, values, shapes, patches, int(time))
	
	# Play the animation
	display.play(render_frame, frames=len(values), fps=5)

if __name__ == "__main__":
	main(GIS_FILES, CSV_DIR, FIELD_OF_INTEREST)
	