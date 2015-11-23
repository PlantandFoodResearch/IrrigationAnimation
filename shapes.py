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
			end = len(shape.points)
		pygame.draw.polygon(surface, colour,
			[transform(point) for point in shape.points[part:end]], width)

			
def bounding_box(shapes):
	""" Returns the bounding box for all of the given shapes """
	
	mins = [float('inf'), float('inf')]
	maxs = [-float('inf'), -float('inf')]
	
	for shape in shapes:
		min_pos = [min(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
		max_pos = [max(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
		for i in range(2):
			if min_pos[i] < mins[i]:
				mins[i] = min_pos[i]
			if max_pos[i] > maxs[i]:
				maxs[i] = max_pos[i]
	
	return [mins[0], mins[1], maxs[0], maxs[1]]
	

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
	# Render patches (filled)
	for patch in patches:
		render_shape(screen, patches[patch]['shape'], transform, (0, 0, 255), 0)
	# Render shapes (not filled)
	for shape in shapes:
		render_shape(screen, shape, transform, (255, 0, 255), 1)
	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False

