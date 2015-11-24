""" Widget wrapper code for the various elements that can be displayed.

	Widgets need to provide a render function, accepting a surface to
	render to, a time, and a function that generates the correct position to
	render at.
	
	Dynamically sized widgets (size == None) will be given an area to render
	into (a size variable).
	Statically sized widgets are expected to have a size variable which
	approximates how much space they will take up when rendered.
	
	The function given to render is assumed to accept the size of the rendered
	image, and the surface being rendered onto. It will return an offset from
	the top-left corner of the surface to render the top-left corner at.
	
	Author: Alastair Hughes
"""

from config import TEXT_AA, TEXT_COLOUR, SCALE_WIDTH, SCALE_DECIMAL_PLACES

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
		self.size = self.gen_size()
		
	def render(self, surface, time, pos_func):
		""" Render self """
		
		x, y = pos_func(self.size)
		for line in self.lines:
			surface.blit(line, (x, y))
			y += self.linesize
			
	def gen_size(self):
		""" Return self's size """
		width = max((line.get_width() for line in self.lines))
		height = self.linesize * len(self.lines)
		return width, height

		
class DynamicTextWidget(TextWidget):
	""" A dynamic, left aligned text widget """
	
	def __init__(self, text_func, font):
		""" Initialise self """
		
		self.font = font
		self.linesize = font.get_linesize()
		self.text_func = text_func
		self.time = None # Time for the cached text.
		self.update_text(0)
		self.size = self.gen_size()
		
	def update_text(self, time):
		""" Generate the text for self at the given time, if required """
		
		if time != self.time:
			# Generate the text.
			self.lines = [self.font.render(line, TEXT_AA, TEXT_COLOUR) \
				for line in self.text_func(time).split('\n')]
			# Update self's size, and save it.
			self.size = self.gen_size()
			# Update the last rendered time.
			self.time = time
		
	def render(self, surface, time, pos_func):
		""" Render self """
		self.update_text(time)
		TextWidget.render(self, surface, time, pos_func)
	

class ScaleWidget():
	""" A dynamically sized widget representing a scale """
	
	def __init__(self, values, font):
		""" Initialise self """
		
		self.font = font
		self.values = values
		self.size = None

	def render(self, surface, time, pos_func, size):
		""" Render self """
		# TODO: Can/should this be cached?
		# TODO: Custom scale spacing (for exponential data) and custom mapping
		# 		of labels would be nice.
		# TODO: '0.0' is not always rendered; that should probably be included!
		# TODO: We currently ignore the x dimension of the given size; we
		#		should probably do something about it.
		
		# Find the initial offsets.
		min_x, y_offset = pos_func(size)
		# Calculate the height, in pixels, of the scale.
		height = size[1] - self.font.get_linesize()
		# Calculate the base height.
		base_height = y_offset + size[1] - (self.font.get_linesize() / 2)
		# Calculate the x borders of the scale.
		max_x = min_x + SCALE_WIDTH

		def row2value(row):
			""" Convert from a given row to a value """
			return (float(row) / height) * (self.values.max - self.values.min) \
				+ self.values.min

		# Draw the scale.
		for row in range(height + 1):
			# Calculate the height to draw the row at.
			y = base_height - row
			# Calculate the colour for this row.
			colour = self.values.value2colour(row2value(row))
			# Draw the row.
			pygame.draw.line(surface, colour, (min_x, y), (max_x, y))

		# Render the text on the scale.
		# We use the font linespace as the minimum gap between reference points

		def render_text(row):
			""" Render a value label next to the scale at the given row """
			# Render the text.
			value = str(round(row2value(row), SCALE_DECIMAL_PLACES))
			text = self.font.render(value, TEXT_AA, TEXT_COLOUR)
			# Calculate the y offset.
			y = base_height - row
			# Blit the text onto the surface.
			#TODO: Figure out how to remove the hardcoded offset..
			surface.blit(text, (max_x + 5, y - (text.get_height() / 2)))
			# Draw a marker.
			pygame.draw.line(surface, TEXT_COLOUR, (min_x, y), (max_x + 2, y))

		# Render the min and max values.
		render_text(0)
		render_text(height)

		# Render the remaining values that we have space for.
		remaining = height - (2 * self.font.get_linesize())
		markers = int(remaining / (2 * self.font.get_linesize()))
		for mark in range(markers):
			row = (float(remaining) / markers) * (mark + 1)
			render_text(row)

	
