""" Experimental frame-by-frame renderer, using pygame

	Author: Alastair Hughes
"""

import shapefile
import numpy
import pygame.draw #TODO: Move to the example code section!
from shapes import render_shape

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
		render_shape(screen, shape, transform, (255, 0, 0))
	pygame.display.update()
	
	# Wait for a quit event.
	running = True
	while running:
		event = pygame.event.wait()
		if event.type == pygame.QUIT:
			running = False
