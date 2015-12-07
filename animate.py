""" Animate a given set of CSV data ontop of a GIS file, and display it in
	a semi-elegant form.

	Future improvements:
	- Removing all of the TODO's...
	- GUI tweaking
	- Speed ups + profiling
	- Code cleanups
	- Transformations
		- Add more by default (exponential/log/per-field)
		- Add support for combining transformations
		- Add support for specifying custom transformations
		- Intergrate with the scale
	- Documentation
		- Design notes
	- Additional widgets
		- Simple value marker (on scale, or just as a value)
		- Time marker
		- Realtime graphs
	- Pausing support for the dynamic viewer
	- Avoiding lag with the dynamic viewer
	- Different colours for the different values renderings
	
	Stretch goals:
	- Packaging?
	- Remove pygame dependency?
	- String value support (eg plant stage)?
	- CLI interface

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
		
		# TODO: Currently we manually place all the widgets, and attempt to be
		#		intelligent about their positioning so that they do not clip.
		#		It would be better if the widgets were smart enough to place
		#		themselves...
		
		# Render the date and label.
		date_rect = date.render(surface, index, \
			lambda size: (surf_w - (BORDER + size[0]), BORDER))
		label_rect = label.render(surface, index, \
			lambda size: (BORDER, BORDER))
		dirty += [label_rect, date_rect]
		
		# Render the maps and scales.
		# desc_offset is the current leftmost offset for a description,
		# calculated to avoid clipping.
		desc_offset = label_rect.right + BORDER
		# value_area is the area dedicated to a specific map/scale/description.
		# It is calculated as a fraction of the space available, where the
		# denominator is the number of values.
		value_area = [i - (2 * BORDER) for i in (surf_w / len(maps), surf_h)]
		# Iterate through the values and render them.
		for i in range(len(values)):
			map, scale, desc = maps[i], scales[i], descriptions[i]
			
			# The x offset is the leftmost start point for an item.
			x_offset = (surf_w / len(maps)) * i + BORDER
			
			# Render the description.
			# We use the maximum of desc_offset and x_offset to avoid clipping, if
			# possible.
			desc_rect = desc.render(surface, index, \
				lambda size: (max(x_offset + (value_area[0] / 2) - \
					(size[0] / 2), desc_offset), BORDER))
			# Update the description offset.
			desc_offset = desc_rect.right + BORDER
			
			# Render the scale.
			scale_rect = scale.render(surface, index, \
				lambda size: (x_offset, \
					desc_rect.bottom + BORDER + \
						((value_area[1] - (desc_rect.height + BORDER) - \
						size[1]) / 2)), \
				(float('inf'), min(value_area[0] - (BORDER + SCALE_WIDTH), \
					value_area[1] - (desc_rect.height + BORDER))))

			# Render the map.
			# The map size is shrunk to avoid clipping with either the scale or
			# the description, and offsets are calculated accordingly.
			map_size = (value_area[0] - (scale_rect.width + BORDER), \
				value_area[1] - (desc_rect.height + BORDER))
			map_rect = map.render(surface, index, \
				lambda size: (scale_rect.right + BORDER + \
						((map_size[0] - size[0]) / 2), \
					desc_rect.bottom + BORDER + \
						((map_size[1] - size[1]) / 2)), \
				map_size)
				
			dirty += [map_rect, desc_rect, scale_rect]
		
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
	values = [Values(model, "Soil.SoilWater.Drainage", transform='field_delta'),
		Values(model, "Soil.SoilWater.Drainage")]
		
	# Create the render_frame function and frame count.
	header = "Model render" # Header displayed
	timewarp = 'delta' # Time warp method used
	edge_render = False # Whether or not to render edges (plot edges, terrain).
	text_height = 25 # The height for any fonts.
	render_frame, frames = gen_render_frame(values, text_height, header, \
		timewarp, edge_render)
	
	# Play the animation.
	fps = 4 # Frames per second
	display_size = (1280, 1024) # Default size.
	preview(render_frame, frames, fps, display_size, header)
	