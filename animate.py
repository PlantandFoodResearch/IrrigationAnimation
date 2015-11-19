""" Animate a given set of CSV data ontop of a GIS file.

	Current todo:
	- Render a field onto a single frame
	- Load the CSV files
	- Animate!

	Future improvements:
	- More output formats
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups

	Author: Alastair Hughes
"""

# Config
#TODO: Figure out a more flexible way of doing this...
GIS_FILES="H:/My Documents/vis/gis"
CSV_DIR="H:/My Documents/vis/csv"
FIELD_OF_INTEREST="SWTotal"

import display, transform, render, data

def main(gis, csv, field):
	""" Generate and display the animation! """
	
	# Create a render_frame function.
	def render_frame(t):
		render_day
	
	# Play the animation
	display.play(render_frame)

if __name__ == "__main__":
	main(GIS_FILES, CSV_DIR, FIELD_OF_INTEREST)
	