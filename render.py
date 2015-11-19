""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

from shapes import render_shape
import data
import pygame, pygame.event

def render(surface, values, shapes, patches):
	""" Render onto the given surface """
	
	#TODO: This is a workaround for offsets...
	offset = shapes[0].points[0]
	transform = lambda p: ((p[0]-offset[0])*2+500, (p[1]-offset[1])*2+700)
	
	#TODO: Get rid of the hard-coded date.
	DATE='1998-07-18'
	value_2_colour = lambda v: (int(v) % 255, 0, 0)
	
	# Render patches (filled)
	for patch in patches:
		value = float(values[DATE].get(patch, 0))
		print(value)
		render_shape(surface, patches[patch]['shape'], transform, value_2_colour(value), 0)
	# Render shapes (not filled, just for the outlines)
	for shape in shapes:
		render_shape(surface, shape, transform, (0, 0, 0), 1)
	

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
	render(screen, values, shapes, patches)
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
