""" Test rendering code.
	
	Author: Alastair Hughes
"""

# Load the data...
import data
patch_files = data.find_patch_files("H:/My Documents/vis/csv")
patches = data.load_patches(patch_files, "Soil.SoilWater.Drainage")
shapes = data.load_shapes("H:/My Documents/vis/gis/MediumPatches")
import shapefile

# Init pygame
import pygame, pygame.event

# Define some rendering functions
def make_frame(time, surface, data, shapes, etc):
	""" Render a single frame at the given time """
	
	# Note that t is in seconds; not very useful to us, since the dates are in days.
	
	#TODO: Remove hard-coded date.
	DATE='1998-07-01'
	
	# Render at the given date
	
	
def render_patch(surface, shape, shape_transform, value, value_transform,
	border_colour=(255, 0, 0)):
	""" Render the given patch.
		The points in the shape are transformed with shape_transform, and the value is
		transformed into a colour with value_transform.
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
	
	points = [transform(point) for point in shape.points]
	
	def draw(width, colour):
		for num, part in enumerate(shape.parts):
			start = part
			try:
				end = shape.parts[num + 1]
			except IndexError:
				end = -1
			pygame.draw.polygon(surface, colour, points[start:end], width)
	
	# Fill in.
	draw(0, value_transform(value))
	
	# Draw the border.
	#draw(1, border_colour)
	

if __name__ == "__main__":
	pygame.init()
	# Run fullscreen.
	screen = pygame.display.set_mode()
	
	# Render!
	#TODO: Remove hard-coded date.
	DATE='1998-07-01'
	offset = shapes[174].points[0]
	transform = lambda p: (p[0]-offset[0]+500, p[1]-offset[1]+700)
	for shape in shapes:
		render_patch(screen, shapes[patch], transform, patches[DATE].get(None, None), lambda p: (0, 255, 0))

	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False
