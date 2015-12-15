#!/usr/bin/env python
""" Animate a given set of CSV data ontop of a GIS file, and display it in
	a semi-elegant form.

	Future improvements:
	- GUI tweaking (1)
	- Transformations
		- Add per-field filters/transformations (2)
		- Add more by default (exponential/log/per-field)
		- Add support for combining transformations
		- Add support for specifying custom transformations
		- Intergrate with the scale
	- Code cleanups (3)
	- Removing all of the TODO's... (3)
	- Speed ups + profiling
	- Weather integration (4)
	- Render an irrigator
	- Render the description text using 'place'
	- Documentation
		- Design notes/walk through
	- Additional widgets
		- Simple value marker/s (on scale, or just as a value)
	- Labels on existing widgets (eg units for a scale)
=	- Pausing support for the dynamic viewer
	- Avoiding lag with the dynamic viewer
	
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
from constants import DEFAULT_COLOUR, BORDER, SCALE_WIDTH, GRAPH_RATIO, \
	GRAPH_MAX_HEIGHT, MAP_COLOUR_LIST, DEFAULT_LABEL
from models import Model, Values, Graphable
from widgets import TextWidget, DynamicTextWidget, ScaleWidget, ValuesWidget, \
	GraphWidget
# We use pygame for font rendering...
import pygame.font

def gen_render_frame(panels, font, header, timewarp, edge_render, desc_format):
	""" Given a list of panels, return a render_frame function showing them,
		and the number of frames.
	"""

	# Init the fonts.
	pygame.font.init()
	font = pygame.font.Font(*font)
	
	# Combine the dates and check that they are the same for all the values.
	dates = None
	for panel in panels:
		value = panel['values']
		if dates == None:
			dates = value.model.dates
		elif dates != value.model.dates:
			raise ValueError("All models must have the same set of dates!")
	
	# Init the widgets.
	maps = []
	scales = []
	descriptions = []
	graphs = []
	for panel in panels:
	
		# Add the normal items.
		value = panel['values']
		maps.append(ValuesWidget(value, edge_render))
		scales.append(ScaleWidget(value, font))
		desc = desc_format.format(field=value.field, csv=value.model.csv, \
			gis=value.model.gis, transform=value.transform)
		descriptions.append(TextWidget(desc, font))
		# TODO: Labelling should be more sophisticated.
		
		# Add the graph.
		g = panel.get('graphs', None)
		label = panel.get('graph_label', DEFAULT_LABEL)
		if g != None:
			graphs.append(GraphWidget(g, dates, font, label))
		else:
			# No graph.
			graphs.append(None)

	label = TextWidget(header, font)
	date = DynamicTextWidget(lambda time: dates[time], font)
	
	# Generate the render_frame function.
	frame_map = times[timewarp]([panel['values'] for panel in panels])
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
		for i in range(len(panels)):
			map, scale, desc, graph = maps[i], scales[i], descriptions[i], \
				graphs[i]
			
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
			# Add the rects.
			dirty.append(desc_rect)
			
			# Figure out the graph height.
			if graph == None:
				graph_height = 0
			else:
				graph_height = int(min(value_area[0] * GRAPH_RATIO, \
					surf_h * GRAPH_MAX_HEIGHT))
			
			if scale != None and map != None:
				# TODO: Center these properly if there is no graph.
				# Render the scale.
				scale_rect = scale.render(surface, index, \
					lambda size: (x_offset, desc_rect.bottom + BORDER), \
					(float('inf'), min(value_area[0] - (BORDER + SCALE_WIDTH), \
						value_area[1] - (desc_rect.height + BORDER * 2 + \
							graph_height))))

				# Render the map.
				# The map size is shrunk to avoid clipping with anything, and
				# offsets are calculated accordingly.
				map_size = (value_area[0] - (scale_rect.width + BORDER), \
					value_area[1] - (desc_rect.height + BORDER * 2 + \
					graph_height))
				map_rect = map.render(surface, index, \
					lambda size: (scale_rect.right + BORDER + \
							((map_size[0] - size[0]) / 2), \
						desc_rect.bottom + BORDER), \
					map_size)
				
				# Find the lowest point.
				lowest = max(map_rect.bottom, scale_rect.bottom)
				# Add the rects.
				dirty.append(map_rect)
				dirty.append(scale_rect)
			else:
				# Find the lowest point.
				lowest = desc_rect.bottom
				
			# Render the graph, if it is defined.
			if graph != None:
				graph_rect = graph.render(surface, index, \
					lambda size: (x_offset, lowest + BORDER), \
					(value_area[0], max(surf_h - (lowest + (BORDER * 2)), \
						graph_height)))
				dirty.append(graph_rect)
		
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
	values = [Values(model, "Wheat.AboveGround.Wt", \
			colour_range = MAP_COLOUR_LIST[0]),
		Values(model, "NO3Total", \
			colour_range = MAP_COLOUR_LIST[1])]
	# Create the graphs.
	graphs = [[Graphable(values[0].model, values[0].field, \
				values[0].field + " (min, mean, max)", \
				statistics = ['min', 'mean', 'max'])
		],
		[Graphable(values[1].model, values[1].field, 'Field #1', \
				statistics = ['mean'], field_nos = [1]),
			Graphable(values[1].model, values[1].field, 'Field #2', \
				statistics = ['mean'], field_nos = [2]),
			Graphable(values[1].model, values[1].field, 'Field #3', \
				statistics = ['mean'], field_nos = [3]),
			Graphable(values[1].model, values[1].field, 'Field #4', \
				statistics = ['mean'], field_nos = [4])
		]
	]
	# Create and save the panels.
	panels = []
	for value, graph in zip(values, graphs):
		panels.append({'values': value, 'graphs': graph})
	
	# Create the render_frame function and frame count.
	header = "Model render" # Header displayed
	timewarp = 'basic' # Time warp method used
	edge_render = True # Whether or not to render edges (plot edges, terrain).
	font = (None, 25) # A (name, size) tuple for the font.
	# Description format string.
	desc_format = """Field of interest: {field}
CSV: {csv}
GIS: {gis}
Transform: {transform}"""
	# Actually run gen_render_frame.
	render_frame, frames = gen_render_frame(panels, font, header, timewarp, \
		edge_render, desc_format)
	
	# Play the animation.
	fps = 4 # Frames per second
	display_size = (1280, 1024) # Default size.
	preview(render_frame, frames, fps, display_size, header)
	