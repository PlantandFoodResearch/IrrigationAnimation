""" Animate a given set of CSV data ontop of a GIS file, and display it in
	a semi-elegant form.

	Future improvements:
	- Removing all of the TODO's...
	- CLI/GUI interfaces (cli option parsing)
		- All options exposed
		- pygame/tkinter interactions fixed?
	- Speed ups
	- Code cleanups
	- Packaging
	- Some way to work around 'clipping' in the various widgets
	- More transformation functions/options + combining transformations
	- Documentation
		- A usage tutorial
		- Design notes
	- Work on making specifying custom transformations easier
	- Marker on scale to represent the current values (maybe a textual indicator?)
	- Some kind of relative time indicator, with monthly markers?
	- Remove pygame dependency?
	- String value support (eg plant stage)
	- Pausing support for the dynamic viewer
	- Avoiding lag with the dynamic viewer
	- Different colours for the different values renderings
	- Resizing for ValuesWidget currently is broken if edge rendering is
	  disabled

	Author: Alastair Hughes
"""

# Import the other modules...
from display import preview
from transforms import times
from constants import DEFAULT_COLOUR, BORDER, SCALE_WIDTH
from models import Model, Values
from widgets import TextWidget, DynamicTextWidget, ScaleWidget, ValuesWidget
# We use pygame for font rendering...
import pygame.font

def gen_render_frame(values, text_height, header, timewarp, edge_render):
	""" Given a list of values, return a render_frame function showing them,
		and the number of frames.
	"""

	# Init the fonts.
	pygame.font.init()
	font = pygame.font.Font(None, text_height)
	
	# Combine the dates and check that they are the same for all the values.
	dates = None
	for value in values:
		if dates == None:
			dates = value.model.dates
		elif dates != value.model.dates:
			raise ValueError("All models must have the same set of dates!")
	
	# Init the widgets.
	maps = []
	scales = []
	descriptions = []
	for i in values:
		maps.append(ValuesWidget(i, edge_render))
		scales.append(ScaleWidget(i, font))
		descriptions.append(TextWidget(i.description(), font))
	label = TextWidget(header, font)
	date = DynamicTextWidget(lambda time: dates[time], font)
	
	# Generate the render_frame function.
	frame_map = times[timewarp](values)
	def render_frame(surface, frame):
		""" Render a frame """
		
		index = frame_map[frame]
		surface.fill(DEFAULT_COLOUR)
		surf_w = surface.get_width()
		surf_h = surface.get_height()
		
		# Render the maps and scales.
		map_size = [i - (2 * BORDER) for i in (surf_w / len(maps), surf_h)]
		for i in range(len(values)):
			map, scale, desc = maps[i], scales[i], descriptions[i]
			
			x_offset = (surf_w / len(maps)) * i + BORDER
		
			# Render the map.
			map.render(surface, index, \
				lambda size: (x_offset + (map_size[0] / 2) - (size[0] / 2), \
					(surf_h / 2) - (size[1] / 2)), \
				map_size)
			
			# Render the scale.
			scale.render(surface, index, \
				lambda size: (x_offset, surf_h - (BORDER + size[1])), \
				(SCALE_WIDTH, surf_h / 3))
				
			# Render the description.
			desc.render(surface, index, \
				lambda size: (x_offset + (map_size[0] / 2) - (size[0] / 2), \
					BORDER))
		
		# Render the date and label.
		date.render(surface, index, \
			lambda size: (surf_w -(BORDER + size[0]), BORDER))
		label.render(surface, index, lambda size: (BORDER, BORDER))
		
	return render_frame, len(frame_map)


if __name__ == "__main__":

	# File paths:
	gis_files = "H:/My Documents/vis/gis/SmallPatches"
	csv_dir = "H:/My Documents/vis/csv/small"
	movie_filename = "H:/My Documents/vis/movie.mp4"

	# Animation options:
	field_of_interest = "Soil.SoilWater.Drainage"
	value2value = 'field_delta' # Value transformation function
	header = "Model render" # Header displayed
	timewarp = 'delta' # Time warp method used

	# Display options:
	edge_render = True # Whether or not to render edges (plot edges, terrain).
	fps = 4 # Frames per second
	movie_size = (1280, 1024)
	text_height = 30 # The height for any fonts.

	# Create a Model.
	model = Model(gis_files, csv_dir)
	# Create the values.
	values = [Values(model, field_of_interest, transform=value2value),
		Values(model, field_of_interest)]
		
	render_frame, frames = gen_render_frame(values, text_height, header, \
		timewarp, edge_render)
	
	# Play the animation.
	preview(render_frame, frames, fps, movie_size, header)
	