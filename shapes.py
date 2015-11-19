""" Shape handling functions

	Provides functions for rendering and filling shapes, currently using
	pygame surfaces.
	
	Author: Alastair Hughes
"""

# Import pygame (for drawing and examples)
import pygame.draw
# Import shapefile (needed for rendering shapes)
import shapefile

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
		try:
			end = shape.parts[num + 1]
		except IndexError:
			end = -1
		pygame.draw.polygon(surface, colour,
			[transform(point) for point in shape.points[part:end]], width)

if __name__ == "__main__":
	# Load up a GIS file and display it.

	# GIS file/s
	GIS_FILES = "H:/My Documents/vis/gis/MediumPatches"
	import data
	shapes, patches = data.load_shapes(GIS_FILES)

	# We use pygame for displaying; import and init.
	import pygame, pygame.event
	pygame.init()
	# Run "fullscreen".
	screen = pygame.display.set_mode()
	
	# Render!
	#TODO: This is a workaround for offsets...
	offset = shapes[0].points[0]
	transform = lambda p: (p[0]-offset[0]+500, p[1]-offset[1]+700)
	for shape in shapes:
		render_shape(screen, shape, transform, (255, 0, 0), 1)
	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False

