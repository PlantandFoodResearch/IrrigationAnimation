""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

from shapes import render_shape
import pygame.draw
from config import BROKEN_COLOUR, BORDER, EDGE_COLOUR, EDGE_THICKNESS, \
	RENDER_EDGES, SCALE_WIDTH, TEXT_COLOUR, SCALE_DECIMAL_PLACES

def render(surface, values, shapes, transform, patches, frame):
	""" Render onto the given surface.
		The transformation function is passed a point and the size of the
		surface.
	"""
	
	# Transformation function for the point.
	# This also converts the result into pygame coordinates (from cartesian),
	# adds a border, and corrects the orientation.
	def transform_wrap(point):
		point = transform(point, [i-(2*BORDER) for i in surface.get_size()])
		return ((surface.get_width()/2)+point[0],
			(surface.get_height()/2)-point[1])

	# Render patches (filled)
	for patch in patches:
		try:
			value = values[frame][patch]
		except KeyError:
			print("WARNING: Failed to get data for patch {} for frame {}!".format(patch, frame))
			value = BROKEN_COLOUR
		render_shape(surface, patches[patch]['shape'], transform_wrap, value, 0)
	# Render shapes (not filled, just for the outlines)
	if RENDER_EDGES:
		#TODO: Can/should this be cached?
		for shape in shapes:
			render_shape(surface, shape, transform_wrap, EDGE_COLOUR, EDGE_THICKNESS)


def render_scale(surface, min, max, value2colour, font):
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
		return (float(row) / height) * (max - min) + min
	
	# Draw the scale.
	for row in range(height + 1):
		# Calculate the height to draw the row at.
		y = base_height - row
		# Calculate the colour for this row.
		colour = value2colour(row2value(row))
		# Draw the row.
		pygame.draw.line(surface, colour, (min_x, y), (max_x, y))
		
	# Render the text on the scale.
	# We use the font linespace as the minimum gap between reference points
	
	def render_text(row):
		""" Render a value label next to the scale at the given row """
		# Render the text.
		value = str(round(row2value(row), SCALE_DECIMAL_PLACES))
		text = font.render(value, True, TEXT_COLOUR)
		# Calculate the y offset.
		y = base_height - row
		# Blit the text onto the surface.
		#TODO: Figure out how to remove the hardcoded offset..
		surface.blit(text, (max_x + 5, y - (text.get_height() / 2)))
		# Draw a marker.
		pygame.draw.line(surface, TEXT_COLOUR, (max_x + 1, y), (max_x + 2, y))
	
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
	
	text = font.render(date, True, TEXT_COLOUR)
	surface.blit(text, (BORDER, BORDER))
