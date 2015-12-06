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
	- String value support (eg plant stage)?
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
		
		index = frame_map[frame] # Figure out the row index in the CSV.
		surface.fill(DEFAULT_COLOUR) # Fill the surface.
		# Cache the surface width and height for readability purposes.
		surf_w = surface.get_width()
		surf_h = surface.get_height()
		
		# Record a list of 'dirty' rects.
		dirty = []
		
		# Render the maps and scales.
		map_size = [i - (2 * BORDER) for i in (surf_w / len(maps), surf_h)]
		for i in range(len(values)):
			map, scale, desc = maps[i], scales[i], descriptions[i]
			
			x_offset = (surf_w / len(maps)) * i + BORDER
			
			# Render the scale.
			dirty.append(scale.render(surface, index, \
				lambda size: (x_offset, surf_h - (BORDER + size[1])), \
				(SCALE_WIDTH, surf_h / 3)))
				
			# Render the description.
			dirty.append(desc.render(surface, index, \
				lambda size: (x_offset + (map_size[0] / 2) - (size[0] / 2), \
					BORDER)))
					
			# Render the map.
			dirty.append(map.render(surface, index, \
				lambda size: (x_offset + (map_size[0] / 2) - (size[0] / 2), \
					(surf_h / 2) - (size[1] / 2)), \
				map_size))
		
		# Render the date and label.
		dirty.append(date.render(surface, index, \
			lambda size: (surf_w -(BORDER + size[0]), BORDER)))
		dirty.append(label.render(surface, index, \
			lambda size: (BORDER, BORDER)))
		
		# Check for intersections, and print a warning if any are found.
		if len(dirty) != 0:
			for index, widget in enumerate(dirty):
				intersects = widget.collidelistall(dirty[index + 1:])
				for collision in intersects:
					print("WARNING: Widgets intersect! ({}, {})".format(index, \
						collision + index + 1))
		
	return render_frame, len(frame_map)


if __name__ == "__main__":

	# Create a Model.
	model = Model("H:/My Documents/vis/gis/SmallPatches", \
		"H:/My Documents/vis/csv/small")
	# Create the values.
	#values = [Values(model, "Soil.SoilWater.Drainage", transform='field_delta'),
	#	Values(model, "Soil.SoilWater.Drainage")]
	values = [Values(model, "Soil.SoilWater.Drainage")]
		
	# Create the render_frame function and frame count.
	header = "Model render" # Header displayed
	timewarp = 'delta' # Time warp method used
	edge_render = False # Whether or not to render edges (plot edges, terrain).
	text_height = 30 # The height for any fonts.
	render_frame, frames = gen_render_frame(values, text_height, header, \
		timewarp, edge_render)
	
	# Play the animation.
	fps = 4 # Frames per second
	display_size = (1280, 1024) # Default size.
	preview(render_frame, frames, fps, display_size, header)
	