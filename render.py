""" Helper render functions.

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
			
	
def render_shape(surface, shape, transform, colour, width=1):
	""" Render the given shape onto the given surface.
		If width == 0, then the shape will be filled.
		transform is applied to all of the points in the shape.
	"""
	
	# This is not the shape you are looking for!
	if shape.shapeType != shapefile.POLYGON and \
		shape.shapeType != shapefile.NULL:
		# If this happens, you will probably need to go and investigate the
		# spec:
		# http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf
		# The library that we are using doesn't have much documentation, so
		# dir() and help() are your friends, or the source, which is online
		# at https://github.com/GeospatialPython/pyshp.
		# Hopefully this never stops working!
		raise ValueError("Unknown shape type %s" %shape.shapeType)
	
	if shape.shapeType == shapefile.NULL:
		# Nothing to render...
		return
	
	# We have a polygon!
	# Polygons are made of different "parts", which are ordered sets of points
	# that are assumed to join up, so we render them part-by-part.
	
	for num, part in enumerate(shape.parts):
		if num + 1 >= len(shape.parts):
			end = len(shape.points)
		else:
			end = shape.parts[num + 1]
		pygame.draw.polygon(surface, colour,
			[transform(point) for point in shape.points[part:end]], width)
