""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

DEFAULT_COLOUR = (0, 0, 0)
BORDER = 20 # Border around the image, in pixels.
EDGE_COLOUR = (0, 0, 0)
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
RENDER_EDGES = False # Whether or not to render edges (plot edges, terrain)

from shapes import render_shape
import data
import pygame, pygame.event

def render(surface, values, shapes, transform, patches, date):
	""" Render onto the given surface.
		The transformation function is passed a point and the size of the
		surface.
	"""
	
	# Transformation function for the point.
	# This also converts the result into pygame coordinates (from cartesian),
	# adds a border, and corrects the orientation.
	def transform_wrap(point):
		point = transform(point, [i-(2*BORDER) for i in surface.get_size()])
		return ((surface.get_width()/2)-point[1],
			point[0]+(surface.get_height()/2))

	# Render patches (filled)
	for patch in patches:
		try:
			value = values[date][patch]
		except KeyError:
			print("WARNING: Failed to get data for patch {} for frame {}!".format(patch, date))
			value = DEFAULT_COLOUR
		render_shape(surface, patches[patch]['shape'], transform_wrap, value, 0)
	# Render shapes (not filled, just for the outlines)
	if RENDER_EDGES:
		for shape in shapes:
			render_shape(surface, shape, transform_wrap, EDGE_COLOUR, EDGE_THICKNESS)
	

def main(gis_files, patch_dir, plot_value):
	""" Main loop """

	# Load the data...
	patch_files = data.find_patch_files(patch_dir)
	values = data.load_values(patch_files, plot_value)
	shapes, patches = data.load_shapes(gis_files)

	pygame.init()
	# Run "fullscreen".
	screen = pygame.display.set_mode()
	# White out the display
	screen.fill((255, 255, 255))
	
	# Render!
	# Convert the values to colours
	value2colour = lambda v: (255-(int(v*20) % 255), 255-(int(v*20) % 255), 255)
	for index in values:
		for patch in values[index]:
			values[index][patch] = value2colour(values[index][patch])	
	render(screen, values, shapes, patches, 17)
	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False
	

if __name__ == "__main__":
	# Render and display an example GIS file
	main("H:/My Documents/vis/gis/SmallPatches", "H:/My Documents/vis/csv",
		"SWTotal")
