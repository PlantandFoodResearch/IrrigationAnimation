""" Animate a given set of CSV data ontop of a GIS file, and display it in
	a semi-elegant form.

	Future improvements:
	- Removing all of the TODO's...
	- More output formats?
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups
	- Code cleanups
	- Packaging
	- Rendering of multiple plots with different values/transformation functions
		A more flexible rendering system, generally!
	- More flexible time handling (days last more than one frame)
		This could be handy for changing the speed of the simulation to reflect
		changes (speeding up over boring bits...)
	- Different colouring functions?
	- Parameters rendered (field of interest, files)
	- More transformation functions/options
	- Documentation
	- Ways of easily specifying custom transformations
	- Use positionable widgets? (Scale/graphs/date+time/...)
	- Marker on scale to represent the current values (maybe a textual indicator?)
	- Remove pygame dependency?

	Author: Alastair Hughes
"""

# Import the other modules...
import render
from display import play
from config import DEFAULT_COLOUR, TEXT_HEIGHT, VALUE2VALUE, \
	GIS_FILES, CSV_DIR, FIELD_OF_INTEREST
from models import Model, Values
# We use pygame for font rendering...
import pygame.font

def main():
	""" Generate and display the animation! """
	
	# Create a Model.
	model = Model(GIS_FILES, CSV_DIR)
	# Create a Values object.
	values = Values(model, FIELD_OF_INTEREST, transform=VALUE2VALUE)
	
	# Init the fonts.
	pygame.font.init()
	font = pygame.font.Font(None, TEXT_HEIGHT)
	
	# Generate the render_frame function.
	def render_frame(surface, frame):
		# Render the frame.
		surface.fill(DEFAULT_COLOUR)
		render.render(surface, values, frame)
		render.render_scale(surface, values, font)
		render.render_date(surface, model.dates[frame], font)
		render.render_params(surface, values, font)
	
	# Play the animation.
	play(render_frame, frames=len(values.values))

if __name__ == "__main__":
	main()
	