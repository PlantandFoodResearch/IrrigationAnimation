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
	- Different colouring functions?
	- More transformation functions/options
	- Documentation
		- A usage tutorial
		- Design notes
	- Work on making specifying custom transformations easier
	- Use positionable widgets? (Scale/graphs/date+time/...)
	- Marker on scale to represent the current values (maybe a textual indicator?)
	- Some kind of relative time indicator, with monthly markers?
	- Remove pygame dependency?
	- String value support (eg plant stage)

	Author: Alastair Hughes
"""

# Import the other modules...
import render
from display import play
from config import DEFAULT_COLOUR, TEXT_HEIGHT, VALUE2VALUE, GIS_FILES, \
	CSV_DIR, FIELD_OF_INTEREST, times, TIMEWARP, BORDER, HEADER
from models import Model, Values
from widgets import TextWidget, DynamicTextWidget
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
	
	# Init the widgets.
	params = TextWidget(HEADER + '\n' + values.description(), font)
	date = DynamicTextWidget(lambda time: model.dates[time], font)
	
	# Generate the render_frame function.
	frame_map = times[TIMEWARP]([values])
	def render_frame(surface, frame):
		index = frame_map[frame]
		# Render the frame.
		surface.fill(DEFAULT_COLOUR)
		render.render(surface, values, index)
		render.render_scale(surface, values, font)
		date.render(surface, index, \
			lambda size: (surface.get_width()-(BORDER+size[0]), BORDER))
		params.render(surface, index, lambda size: (BORDER, BORDER))
	
	# Play the animation.
	play(render_frame, frames=len(frame_map))

if __name__ == "__main__":
	main()
	