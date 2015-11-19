""" Test rendering code.
	
	Author: Alastair Hughes
"""

# Load the data...
import data
patch_files = data.find_patch_files("H:/My Documents/vis/csv")
data = data.load_patches(patch_files, "Soil.SoilWater.Drainage")
shapes = data.load_shapes("H:/My Documents/vis/gis/MediumPatches")

# Init pygame
import pygame, pygame.event

# Define some rendering functions
def make_frame(time):
	""" Render a single frame at the given time """

if __name__ == "__main__":
	pygame.init()
	# Run fullscreen.
	screen = pygame.display.set_mode()
	
	# Render!
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
