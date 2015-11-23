""" Widget wrapper code for the various elements that can be displayed.

	Widgets need to provide a render function, accepting a surface to
	render to, and a function that generates the correct position to render at.
	
	Dynamically sized widgets (size == None) will be given an area to render
	into (a size variable).
	Statically sized widgets are expected to have a size variable which
	approximates how much space they will take up when rendered.
	
	The function given to render is assumed to accept the size of the rendered
	image, and the surface being rendered onto. It will return an offset from
	the top-left corner of the surface to render the top-left corner at.
	
	Author: Alastair Hughes
"""

from config import TEXT_AA, TEXT_COLOUR

import pygame.draw

class TextWidget():
	""" A static, left aligned text widget """
	
	def __init__(self, text, font):
		""" Initialise self """
		
		self.text = text
		# Rendered lines.
		self.lines = [font.render(line, TEXT_AA, TEXT_COLOUR) \
			for line in self.text.split('\n')]
			
		# Cache the linesize; we need it for rendering.
		self.linesize = font.get_linesize()
			
		# Calculate self's size
		width = max((line.get_width() for line in self.lines))
		height = self.linesize * len(self.lines)
		self.size = (width, height)
		
	def render(self, surface, pos_func):
		""" Render self """
		
		x, y = pos_func(surface, self.size)
		for line in self.lines:
			surface.blit(line, (x, y))
			y += self.linesize
		
		