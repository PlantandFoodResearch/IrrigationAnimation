""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

import shapefile
import numpy
import pygame.draw #TODO: Move to the example code section!

def render(shape, surface, transform):
	""" Draw the given shape onto the given surface, with the given
		transformation function applied to all of the points.
		TODO: Fix the reliance on pygame surfaces...
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
		start = part
		try:
			end = shape.parts[num + 1]
		except IndexError:
			end = -1
		pygame.draw.polygon(surface, (255, 0, 0),
			[transform(point) for point in shape.points[start:end]], 1)

			
if __name__ == "__main__":
	""" Render and display an example GIS file """

	# GIS file/s
	GIS_FILES = "H:/My Documents/vis/gis/MediumPatches"
	#TODO: Figure out how to close the files...
	sf = shapefile.Reader(GIS_FILES)

	# We use pygame for displaying; import and init.
	import pygame, pygame.event
	pygame.init()
	# Run fullscreen.
	screen = pygame.display.set_mode()
	
	# Render!
	shapes = sf.shapes()
	#TODO: This is a workaround for offsets...
	offset = shapes[0].points[0]
	transform = lambda p: (p[0]-offset[0]+500, p[1]-offset[1]+700)
	for shape in shapes:
		render(shape, screen, transform)
	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False
