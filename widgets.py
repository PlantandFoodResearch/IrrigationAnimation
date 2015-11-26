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

from config import BROKEN_COLOUR, EDGE_COLOUR, EDGE_THICKNESS, \
	EDGE_RENDER, SCALE_DECIMAL_PLACES, SCALE_MARKER_SIZE, SCALE_TEXT_OFFSET, \
	TEXT_AA, TEXT_COLOUR

import pygame.draw # We currently render using pygame...
import shapefile # For the shape constants

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
	
	def __init__(self, values, font, labelling=None, row2value=None):
		""" Initialise self.
		
			The given scale labelling function is assumed to take a height, and
			return a map from rows to string values.
			
			The given row2value function is assumed to take a row and height,
			and return the value at that row.
			
			If None is passed for either functions, the default will be used.
		"""
		# NOTE: We currently do not always render '0.0'. Unfortunately, this
		#		is fairly difficult to remedy; we would really need a value2row
		#		function as well. If we did have that function, we should be
		#		able to work backwards and position the remaining positive and
		#		negative values, if applicable, and figure out where they
		#		should all go.
		
		if row2value == None:
			row2value = lambda row, height: (float(row) / height) * \
				(self.values.max - self.values.min) + self.values.min
		if labelling == None:
			# We use the font linespace as the minimum gap between markers.
			def labelling(height):
				# Labels to be added.
				labels = {}

				# Calculate the number of markers required.
				# We always render at least two markers.
				markers = max(int(height / (2 * font.get_linesize())) + 1, 2)
				
				for mark in range(markers):
					# Calculate the row to render the marker on.
					row = (float(height) / (markers - 1)) * mark
					# Calculate the value for that row.
					value = str(round(self.row2value(row, height), \
						SCALE_DECIMAL_PLACES))
					# Add it to the map.
					labels[row] = value

				return labels
		
		self.font = font
		self.values = values
		self.labelling = labelling # Scale labelling function.
		self.row2value = row2value # Row to value conversion function.
		self.size = None # The scale is *mostly* dynamically sized.

	def render(self, surface, time, pos_func, size):
		""" Render self """
		
		# Find the initial offsets.
		# We can scale dynamically in both dimensions (to a point) so we just
		# use the given size.
		min_x, y_offset = pos_func(size)
		# Calculate the height, in pixels, of the scale.
		height = size[1] - self.font.get_linesize()
		# Calculate the base height.
		base_height = y_offset + size[1] - (self.font.get_linesize() / 2)
		
		# Render the values, and save them.
		rows = {} # row: text
		max_text_width = 0 # Record the maximum text width for future reference.
		for row, value in self.labelling(height).items():
			# Render and save.
			rows[row] = self.font.render(value, TEXT_AA, TEXT_COLOUR)
			# Update the maximum text width.
			max_text_width = max(rows[row].get_width(), max_text_width)
			
		# Calculate the maximum x border of the scale.
		max_x = (min_x + size[0]) - (max_text_width + SCALE_TEXT_OFFSET)

		# Draw the scale.
		for row in range(height + 1):
			# Calculate the height to draw the row at.
			y = base_height - row
			# Calculate the colour for this row.
			colour = self.values.value2colour(self.row2value(row, height))
			# Draw the row.
			pygame.draw.line(surface, colour, (min_x, y), (max_x, y))

		# Blit the rendered text onto the scale.
		# NOTE: Text rendered here may overlap. Unfortunately, fixing that is
		#		tricky, especially as there may not be enough space, and
		# 		the scale height may have to be resized if the text needs to be
		#		shifted too much.
		#		A simple bottom-up algorithm unfortunately won't do a very good
		# 		job for those reasons...
		#		Fixing this might allow simpler labelling algorithms, though.
		for row, text in rows.items():
			# Calculate the y offset.
			y = base_height - row
			# Blit the text onto the surface.
			surface.blit(text, \
				(max_x + SCALE_TEXT_OFFSET, y - (text.get_height() / 2)))
			# Draw a marker.
			pygame.draw.line(surface, TEXT_COLOUR, (min_x, y), \
				(max_x + SCALE_MARKER_SIZE, y))

	
class ModelWidget():
	""" A model widget, representing a specific model """
	
	def __init__(self, model):
		""" Initialise self """
		
		# TODO: This partially crosses over with models.Model; it would be nice
		# 		to clarify what belonged where.
		
		self.model = model
		self.size = None
		
	def gen_transform(self, pos_func, size):
		""" Generate a transformation function to adjust the points in the model """
		
		# The scaling factor required to scale the image to fit nicely in
		# the given size.
		# This is the minimum of the x and y scaling to avoid clipping.
		scale = min([float(size[i])/self.model.size[i] for i in range(2)])
		
		# Calculate the offset with the *real* size.
		real_size = [self.model.size[i]*scale for i in range(2)]
		offset = pos_func(real_size)
		
		def transform(vert):
			# Calculate a scaled and recentered vertex.
			point = [(vert[i] - self.model.center[i])*scale for i in range(2)]
			
			# Transform the recentered vertex into offset pygame coordinates.
			return ((real_size[0]/2) + point[0] + offset[0], \
				(real_size[1]/2) - point[1] + offset[1])
			
		return transform
		
	def render(self, surface, time, pos_func, size):
		""" Render self """
		
		for shape in self.model.shapes:
			self.render_shape(surface, self.gen_transform(pos_func, size), \
				shape, EDGE_COLOUR, EDGE_THICKNESS)
			
	def render_shape(self, surface, transform, shape, colour, width):
		""" Render the given shape onto the given surface, applying the given
			transformation. If width == 0, then the shape will be filled.
		"""
		
		# This is not the shape you are looking for!
		if shape.shapeType != shapefile.POLYGON and \
			shape.shapeType != shapefile.NULL:
			# If this happens, you will probably need to go and investigate the
			# spec:
			# http://www.esri.com/library/whitepapers/pdfs/shapefile.pdf
			# The library that we are using doesn't have much documentation, so
			# dir() and help() are your friends, or the source, which is online
			# at https://github.com/GeospatialPython/pyshp.
			# Hopefully this never stops working!
			raise ValueError("Unknown shape type %s" %shape.shapeType)
			
		if shape.shapeType == shapefile.NULL:
			# Nothing to render...
			return
		
		# We have a polygon!
		# Polygons are made of different "parts", which are ordered sets of points
		# that are assumed to join up, so we render them part-by-part.
		for num, part in enumerate(shape.parts):
			if num + 1 >= len(shape.parts):
				end = len(shape.points)
			else:
				end = shape.parts[num + 1]
			pygame.draw.polygon(surface, colour,
				[transform(point) for point in shape.points[part:end]], width)
				

class ValuesWidget(ModelWidget):
	""" Widget for a specific Values """
	
	def __init__(self, values):
		""" Initialise self """
		
		ModelWidget.__init__(self, values.model)
		self.values = values
		
	def render(self, surface, time, pos_func, size):
		""" Render the given values class onto a surface """
	
		# Render patches (filled)
		for patch in self.model.patches:
			try:
				value = self.values.values[time][patch]
			except KeyError:
				print("WARNING: Failed to get data for patch {} for time {}!".format(patch, time))
				value = BROKEN_COLOUR
			self.render_shape(surface, self.gen_transform(pos_func, size), \
				self.model.patches[patch]['shape'], value, 0)
		# Render shapes (not filled, just for the outlines)
		if EDGE_RENDER:
			ModelWidget.render(self, surface, time, pos_func, size)

