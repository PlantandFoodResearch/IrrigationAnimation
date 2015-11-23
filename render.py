""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

import shapefile
import pygame.draw
from config import BROKEN_COLOUR, BORDER, EDGE_COLOUR, EDGE_THICKNESS, \
	EDGE_RENDER, SCALE_WIDTH, TEXT_COLOUR, TEXT_AA, SCALE_DECIMAL_PLACES

def render(surface, values, frame):
	""" Render the given values class onto a surface """
	
	# Transformation function for the point.
	# This also converts the result into pygame coordinates (from cartesian),
	# and adds a border.
	def transform_wrap(point):
		size = surface.get_size()
		point = values.model.centering(point, [i - (2*BORDER) for i in size])
		return ((size[0]/2) + point[0], (size[1]/2) - point[1])

	# Render patches (filled)
	for patch in values.model.patches:
		try:
			value = values.values[frame][patch]
		except KeyError:
			print("WARNING: Failed to get data for patch {} for frame {}!".format(patch, frame))
			value = BROKEN_COLOUR
		render_shape(surface, values.model.patches[patch]['shape'], transform_wrap, value, 0)
	# Render shapes (not filled, just for the outlines)
	if EDGE_RENDER:
		#TODO: Can/should this be cached?
		for shape in values.model.shapes:
			render_shape(surface, shape, transform_wrap, EDGE_COLOUR, EDGE_THICKNESS)


def render_scale(surface, values, font):
	""" Draw a scale in the bottom-left corner """
	#TODO: Make this more flexible.
	#TODO: Can/should this be cached?
	#TODO: Exponential data will not work well with this?
	#TODO: '0.0' is not rendered; we should probably include that!
	
	# Calculate the height, in pixels, of the scale.
	#TODO: The height calculation needs tweaking so that it doesn't clip with
	#	   the main animation.
	height = (surface.get_height()/3) - BORDER
	base_height = surface.get_height() - BORDER
	# Calculate the x borders
	min_x = BORDER
	max_x = BORDER + SCALE_WIDTH
	
	def row2value(row):
		""" Convert from a given row to a value """
		return (float(row) / height) * (values.max - values.min) + values.min
	
	# Draw the scale.
	for row in range(height + 1):
		# Calculate the height to draw the row at.
		y = base_height - row
		# Calculate the colour for this row.
		colour = values.value2colour(row2value(row))
		# Draw the row.
		pygame.draw.line(surface, colour, (min_x, y), (max_x, y))
		
	# Render the text on the scale.
	# We use the font linespace as the minimum gap between reference points
	
	def render_text(row):
		""" Render a value label next to the scale at the given row """
		# Render the text.
		value = str(round(row2value(row), SCALE_DECIMAL_PLACES))
		text = font.render(value, TEXT_AA, TEXT_COLOUR)
		# Calculate the y offset.
		y = base_height - row
		# Blit the text onto the surface.
		#TODO: Figure out how to remove the hardcoded offset..
		surface.blit(text, (max_x + 5, y - (text.get_height() / 2)))
		# Draw a marker.
		pygame.draw.line(surface, TEXT_COLOUR, (min_x, y), (max_x + 2, y))
	
	# Render the min and max values.
	render_text(0)
	render_text(height)
	
	# Render the remaining values that we have space for.
	remaining = height - (2 * font.get_linesize())
	markers = int(remaining / (2 * font.get_linesize()))
	for mark in range(markers):
		row = (float(remaining) / markers) * (mark + 1)
		render_text(row)
		

def render_date(surface, date, font):
	""" Draw the date value into the top left hand corner """
	
	text = font.render(date, TEXT_AA, TEXT_COLOUR)
	surface.blit(text, (BORDER, BORDER))

	
def render_shape(surface, shape, transform, colour, width=1):
	""" Render the given shape onto the given surface.
		If width == 0, then the shape will be filled.
		transform is applied to all of the points in the shape.
	"""
	
	# This is not the shape you are looking for!
	#TODO: Supporting at least NULL shapes would probably be a good thing,
	#		although the generated files don't seem to have other shapes.
	if shape.shapeType != shapefile.POLYGON:
		raise ValueError("Unknown shape type %s" %shape.shapeType)
	
	# We render the polygon!
	# Polygons are made of different "parts", which are ordered sets of points
	# that are assumed to join up, so we render them part-by-part.
	#TODO: Remove pygame dependency, clean up!
	
	for num, part in enumerate(shape.parts):
		if num + 1 >= len(shape.parts):
			end = len(shape.points)
		else:
			end = shape.parts[num + 1]
		pygame.draw.polygon(surface, colour,
			[transform(point) for point in shape.points[part:end]], width)
