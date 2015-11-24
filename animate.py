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
from display import play
from config import DEFAULT_COLOUR, TEXT_HEIGHT, VALUE2VALUE, GIS_FILES, \
	CSV_DIR, FIELD_OF_INTEREST, times, TIMEWARP, BORDER, HEADER
from models import Model, Values
from widgets import TextWidget, DynamicTextWidget, ScaleWidget, ValuesWidget
# We use pygame for font rendering...
import pygame.font

def main():
	""" Generate and display the animation! """
	
	# Create a Model.
	model = Model(GIS_FILES, CSV_DIR)
	# Create the values.
	values = [Values(model, FIELD_OF_INTEREST, transform=VALUE2VALUE)]
	
	# Init the fonts.
	pygame.font.init()
	font = pygame.font.Font(None, TEXT_HEIGHT)
	
	# Init the widgets.
	maps = []
	scales = []
	for i in values:
		maps.append(ValuesWidget(i))
		scales.append(ScaleWidget(i, font))
	params = TextWidget(HEADER + '\n' + values[0].description(), font)
	date = DynamicTextWidget(lambda time: model.dates[time], font)
	
	# Generate the render_frame function.
	frame_map = times[TIMEWARP](values)
	def render_frame(surface, frame):
		""" Render a frame """
		
		index = frame_map[frame]
		surface.fill(DEFAULT_COLOUR)
		surf_w = surface.get_width()
		surf_h = surface.get_height()
		
		# Render the maps and scales.
		map_size = [i - (2 * BORDER) for i in (surf_w / len(maps), surf_h)]
		for index in range(len(maps)):
			map = maps[index]
			scale = scales[index]
			
			x_offset = (surf_w / len(maps)) * index
		
			# Render the map.
			map.render(surface, index, \
				lambda size: (x_offset + (surf_w/2) - (size[0] / 2), \
					(surf_h / 2) - (size[1] / 2)), \
				map_size)
			
			# Render the scale.
			scale.render(surface, index, \
				lambda size: (x_offset + BORDER, surf_h - (BORDER + size[1])), \
				(-1, surf_h / 3))
		
		# Render the date and parameters.
		date.render(surface, index, \
			lambda size: (surf_w -(BORDER + size[0]), BORDER))
		params.render(surface, index, lambda size: (BORDER, BORDER))
	
	# Play the animation.
	play(render_frame, frames=len(frame_map))

if __name__ == "__main__":
	main()
	