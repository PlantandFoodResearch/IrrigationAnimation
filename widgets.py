""" Widget wrapper code for the various elements that can be displayed.

    Widgets need to provide a render function, accepting a surface to
    render to, a time, and a function that generates the correct position to
    render at.
    
    Dynamically sized widgets (size == None) will be given an area to render
    into (a size variable).
    Statically sized widgets are expected to have a size variable which
    approximates how much space they will take up when rendered.
    Both are expected to return a Rect covering the actual area rendered to.
    
    The function given to render is assumed to accept the size of the rendered
    image, and the surface being rendered onto. It will return an offset from
    the top-left corner of the surface to render the top-left corner at.
    
    Author: Alastair Hughes
"""

from constants import ANCHOR_FORCE, BROKEN_COLOUR, EDGE_COLOUR, \
    EDGE_THICKNESS, GRAPH_ALPHA, GRAPH_COLOUR_LIST, ITERATION_MULTIPLIER, \
    PLACEMENT_CONSTANT, OVERLAP_FORCE, SCALE_SF, SCALE_MARKER_SIZE, \
    SCALE_SPACING, SCALE_TEXT_OFFSET, SCALE_WIDTH, TEXT_AA, TEXT_COLOUR

import pygame, pygame.draw # We currently render using pygame...
import shapefile # For the shape constants
import colorsys # For value2colour

# We define a helper function to round to n significant digits:
# This is from: http://stackoverflow.com/questions/3410976/how-to-round-a-number-to-significant-figures-in-python
from math import floor, log10
def round_sf(v, n):
    if v == 0:
        return int(0)
    else:
        rounded = round(v, -int(floor(log10(abs(v)))) + (n - 1))
        if rounded % 1 == 0:
            return int(rounded)
        return rounded

# We also define a helper function to generate a value2colour function for a
# given values and colour_range.
def gen_value2colour(values, colour_range):
    # Create the colour mapping function.
    def value2colour(value):
        """ Convert from a given value to a colour """
        # Using this: 
        # http://stackoverflow.com/questions/10901085/range-values-to-pseudocolor/10907855#10907855 
        # We scale to a specific colour range (in HSV, from 0 to 1).
        try:
            hue = ((value - values.min) / (values.max - values.min)) # 0-1
        except ZeroDivisionError:
            hue = 0
        # Convert the hue into something in the given range.
        value = hue * (colour_range[1] - colour_range[0]) + colour_range[0]
        # Return a RGB version of that colour.
        return [int(i*255) for i in colorsys.hsv_to_rgb(value, 1.0, 1.0)]
    return value2colour


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
        
        dirty = []
        
        x, y = pos_func(self.size)
        for line in self.lines:
            dirty.append(surface.blit(line, (x, y)))
            y += self.linesize
            
        return merge_rects(dirty)
            
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
        return TextWidget.render(self, surface, time, pos_func)
    

class ScaleWidget():
    """ A dynamically sized widget representing a scale """
    
    def __init__(self, values, value2colour, font, labelling=None, \
            row2value=None):
        """ Initialise self.
        
            The given scale labelling function is assumed to take a height, and
            return a map from rows to string values.
            
            The given row2value function is assumed to take a row and height,
            and return the value at that row.
            
            If None is passed for either functions, the default will be used.
        """
        # TODO: We currently do not always render '0.0'. Unfortunately, this
        #       is fairly difficult to remedy; we would really need a value2row
        #       function as well, and gen_labelling would have to be adjusted
        #       to handle being given a list of extra labels to always add.
        
        if row2value == None:
            row2value = lambda row, height: (float(row) / height) * \
                (self.values.max - self.values.min) + self.values.min
        if labelling == None:
            def labelling(height):
                # Generate a labelling (list of rows to put the marker on)
                # We use the font linespace as the minimum gap between markers.
                label_size = font.get_linesize()
                markers = gen_labelling(height, label_size, label_size)
                
                # Add the values to a map of labels.
                labels = {} # rows: values
                for row in markers:
                    # Calculate the value for that row.
                    value = str(round_sf(self.row2value(row, height), \
                        SCALE_SF))
                    # Add it to the map.
                    labels[row] = value

                return labels
        
        self.font = font
        self.values = values
        self.value2colour = value2colour
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
        max_x = min((min_x + size[0]) - (max_text_width + SCALE_TEXT_OFFSET), \
            min_x + SCALE_WIDTH)

        # Draw the scale.
        for row in range(height + 1):
            # Calculate the height to draw the row at.
            y = base_height - row
            # Calculate the colour for this row.
            colour = self.value2colour(self.row2value(row, height))
            # Draw the row.
            pygame.draw.line(surface, colour, (min_x, y), (max_x, y))
            
        # Initialise 'dirty' with a rect representing the scale.
        dirty = [pygame.Rect(min_x, base_height - height, \
            max_x - min_x, height)]

        # Blit the rendered text onto the scale.
        # We start by using 'place' to generate a list of placements for the
        # labels so that they do not overlap.
        # placement is a map from anchors (rows) to actual placement points.
        label_area = (-(self.font.get_linesize() / 2), \
            height + (self.font.get_linesize() / 2))
        placement = place(label_area, \
            {row: text.get_height() for row, text in rows.items()})
        # Now we actually blit the text onto the scale.
        for row, text in rows.items():
            # Calculate the y offset for the label.
            y = base_height - placement[row] - (text.get_height() / 2)
            # Blit the text onto the surface.
            dirty.append(surface.blit(text, \
                (max_x + SCALE_TEXT_OFFSET, y)))
            # Calculate the y offset for the marker.
            y = base_height - row
            # Draw a marker.
            pygame.draw.line(surface, TEXT_COLOUR, (min_x, y), \
                (max_x + SCALE_MARKER_SIZE, y))
                
        return merge_rects(dirty)
        

class ValuesWidget():
    """ Widget for a specific Values """
    
    def __init__(self, values, value2colour, edge_render):
        """ Initialise self """

        self.size = None # This widget is dynamically sized.
        self.values = values
        self.value2colour = value2colour
        self.model = values.model
        self.edge_render = edge_render
        
        # Find the bounding box, center, and size for the patches.
        bbox = self.bounding_box()
        self.center = [((bbox[i] + bbox[i+2]) / 2) for i in range(2)]
        self.actual_size = [(bbox[i+2] - bbox[i]) for i in range(2)]
        
    def bounding_box(self):
        """ Return the bounding box of self's patches """
        
        # TODO: This should potentially be moved in Model, as it is only
        #       dependent on the model in use.
        
        mins = [float('inf'), float('inf')]
        maxs = [-float('inf'), -float('inf')]

        for patch in self.model.patches:
            shape = self.model.patches[patch]['shape']
            min_pos = [min(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
            max_pos = [max(shape.bbox[i], shape.bbox[i+2]) for i in range(2)]
            for i in range(2):
                if min_pos[i] < mins[i]:
                    mins[i] = min_pos[i]
                if max_pos[i] > maxs[i]:
                    maxs[i] = max_pos[i]

        return [mins[0], mins[1], maxs[0], maxs[1]]
        
    def gen_transform(self, pos_func, size):
        """ Generate a transformation function to adjust the points in the
            model.
        """
        
        # The scaling factor required to scale the image to fit nicely in
        # the given size.
        # This is the minimum of the x and y scaling to avoid clipping.
        scale = min([float(size[i])/self.actual_size[i] for i in range(2)])
        
        # Calculate the offset with the *real* size.
        real_size = [self.actual_size[i]*scale for i in range(2)]
        offset = pos_func(real_size)
        
        def transform(vert):
            # Calculate a scaled and recentered vertex.
            point = [(vert[i] - self.center[i])*scale for i in range(2)]
            
            # Transform the recentered vertex into offset pygame coordinates.
            return ((real_size[0]/2) + point[0] + offset[0], \
                (real_size[1]/2) - point[1] + offset[1])
            
        return transform
        
        
    def render(self, surface, time, pos_func, size):
        """ Render the given values class onto a surface """
        
        # Dirty rects.
        dirty = []
        
        # Transform function.
        trans = self.gen_transform(pos_func, size)
    
        # Render patches.
        for patch in self.model.patches:
            try:
                value = self.value2colour(self.values.values[time][patch])
            except KeyError:
                # We currently ignore this, to avoid spamming the console.
                value = BROKEN_COLOUR
            # Render the filled patch.
            dirty += self.render_shape(surface, trans, \
                self.model.patches[patch]['shape'], value, 0)
            # Render edges as required (not filled, just for the outlines).
            if self.edge_render:
                self.render_shape(surface, trans, \
                    self.model.patches[patch]['shape'], EDGE_COLOUR, \
                    EDGE_THICKNESS)
            
        return merge_rects(dirty)
            
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
            # Basically, there are many supported shapes, but I only expect to
            # encounter POLYGON's in a GIS file, and so have only written a
            # rendering routine for those.
            # The library that we are using doesn't have much documentation, so
            # dir() and help() are your friends, or the source, which is online
            # at https://github.com/GeospatialPython/pyshp.
            # Also, pygame has some helpful routines for rendering shapes which
            # might come in handy.
            # Hopefully this never stops working!
            raise ValueError("Unknown shape type %s" %shape.shapeType)
            
        if shape.shapeType == shapefile.NULL:
            # Nothing to render...
            return []
        
        # We have a polygon!
        # Polygons are made of different "parts", which are ordered sets of points
        # that are assumed to join up, so we render them part-by-part.
        dirty = [] # List of 'dirty' rects.
        for num, part in enumerate(shape.parts):
            if num + 1 >= len(shape.parts):
                end = len(shape.points)
            else:
                end = shape.parts[num + 1]
            if width != 1:
                dirty.append(pygame.draw.polygon(surface, colour,
                    [transform(point) for point in shape.points[part:end]], width))
            else:
                # Use aalines instead (smoothed lines).
                dirty.append(pygame.draw.aalines(surface, colour, True,
                    [transform(point) for point in shape.points[part:end]], width))
                
        return dirty
        
class GraphWidget():
    """ Widget for realtime graphs of a list of given Graphables """
    
    def __init__(self, graphable, dates, font, label):
        """ Initialise self """
        
        # Check that we have enough colours defined.
        if len(graphable) > len(GRAPH_COLOUR_LIST):
            raise ValueError("To many lines specified; not enough colours!")
        
        self.graphable = graphable
        self.dates = dates
        self.size = None
        self.font = font
        self.label = label + ": "
        
        # The 'global' minimum and maximum.
        self.min = min([g.min for g in self.graphable])
        self.max = max([g.max for g in self.graphable])
        
    def render(self, surface, time, pos_func, size):
        """ Render the given graphable class onto a surface """
        
        topleft = pos_func(size)
        dirty = pygame.Rect(topleft, size)
        
        # TODO: We need a label of some kind somewhere.

        # We start by rendering a scale...
        scale_size = [0, 0]
        row2date, scale_size[0], scale_size[1] = \
            self.render_scale(surface, topleft, size)
        size = [size[i] - scale_size[i] for i in range(2)]
        topleft = (topleft[0] + scale_size[0], topleft[1])
        
        # We render the lines.
        # Render the line.
        # TODO: We need some kind of text saying what the line is.
        for index, graph in enumerate(self.graphable):
            self.render_line(surface, graph, GRAPH_COLOUR_LIST[index], \
                topleft, size, row2date)
        
        # TODO: It would be nice to be able to *see* the actual value at 
        #       that time for each line.
        # TODO: The offset is not calculated accurately at the moment
        #       (slightly off).
        offset = ((float(time) / (len(self.dates) - 1)) * size[0]) + \
            topleft[0]
        pygame.draw.line(surface, TEXT_COLOUR, (offset, topleft[1]), \
            (offset, topleft[1] + size[1]))
        
        return dirty
        
    def render_scale(self, surface, topleft, size):
        """ Render the scale """
        
        # TODO: There is quite a bit of duplication here, with ScaleWidget and
        #       within the labelling routines. It would be nice if I could
        #       figure out how to remove that.
        
        # We start by generating and rendering some labels.
        line_space = self.font.get_linesize()
        date_height = line_space + SCALE_TEXT_OFFSET
        height = size[1] - (date_height + line_space)
        anchors = gen_labelling(height - 1, line_space, line_space)
        # We then render the labels.
        rows = {} # The rendered text (row: text)
        max_text_width = 0 # Record the maximum text width for future reference.
        for row in anchors:
            # Render and save.
            value = str(round_sf((float(row) / height) * \
                    (self.max - self.min) + self.min, SCALE_SF))
            rows[row] = self.font.render(value, TEXT_AA, TEXT_COLOUR)
            # Update the maximum text width.
            max_text_width = max(rows[row].get_width(), max_text_width)
        # Figure out the vertical scale line location (we use it for rendering
        # markers).
        width = SCALE_TEXT_OFFSET + max_text_width
        x_offset = topleft[0] + width
        # We generate a list of placements for the labels so that they do not
        # overlap.
        # placement is a map from anchors (rows) to actual placement points.
        label_area = (-(line_space / 2), height + (line_space / 2))
        placement = place(label_area, \
            {row: text.get_height() for row, text in rows.items()})
        # Now we actually blit the text onto the scale.
        for row, text in rows.items():
            # Calculate the y offset for the label.
            y = topleft[1] + height - placement[row] - (text.get_height() / 2)
            # Blit the text onto the surface.
            surface.blit(text, (topleft[0], y))
            # Calculate the y offset for the marker.
            y = topleft[1] + height - 1 - row
            # Draw a marker.
            pygame.draw.line(surface, TEXT_COLOUR, \
                (x_offset - SCALE_MARKER_SIZE, y), (x_offset, y))
        
        # Generate a row2date function (reused elsewhere).
        graph_width = size[0] - width
        row2date = lambda row: int(float(row * (len(self.dates) - 1)) / graph_width)
                
        # Render the dates.
        # First, generate the anchor locations.
        anchors = gen_labelling(graph_width - 1, \
            self.font.render(self.dates[0], TEXT_AA, TEXT_COLOUR).get_width(), \
            SCALE_SPACING, label_count=len(self.dates))
        # Render the text at those points.
        rows = {}
        for row in anchors:
            rows[row] = self.font.render(self.dates[row2date(row)], TEXT_AA, \
                TEXT_COLOUR)
        # Then, generate a map of placements (anchors: placement map)
        placement = place((-(SCALE_SPACING / 2), graph_width + \
            (SCALE_SPACING / 2)), {row: text.get_width() + SCALE_SPACING \
                for row, text in rows.items()})
        # Finally, blit the text onto the scale.
        for row, text in rows.items():
            x = topleft[0] + width
            surface.blit(text, (x + placement[row] - (text.get_width() / 2), \
                topleft[1] + height + SCALE_TEXT_OFFSET))
            pygame.draw.line(surface, TEXT_COLOUR, \
                (x + row, topleft[1] + height), \
                (x + row, topleft[1] + height + SCALE_MARKER_SIZE))
        
        # Draw the scale lines.
        # We don't want to draw right off the end, so we take one off the given
        # size.
        pygame.draw.lines(surface, TEXT_COLOUR, False, \
            [(x_offset, topleft[1]), \
                (x_offset, topleft[1] + (height - 1)), \
                (topleft[0] + (size[0] - 1), topleft[1] + (height - 1))])
                
        # Draw the key underneath, if required.
        y = topleft[1] + size[1]
        label = self.font.render(self.label, TEXT_AA, TEXT_COLOUR)
        rect = surface.blit(label, (topleft[0], y - label.get_height()))
        # Render the labels for the individual graphs.
        offset = rect.right + SCALE_SPACING
        for index, graph in enumerate(self.graphable):
            # TODO: Render this using 'place'.
            label = self.font.render(graph.label, TEXT_AA, \
                GRAPH_COLOUR_LIST[index])
            surface.blit(label, (offset, y - label.get_height()))
            offset += label.get_width() + SCALE_SPACING
    
        return row2date, width + 1, size[1] - (height - 1)

    def render_line(self, surface, graph, colour, topleft, size, row2date):
        """ Render a line onto the given surface """
        
        # Define a helper function to find the y-coord.
        # This scales and offsets the given value as required.
        def y(value):
            try:
                perc = ((value - graph.min) / (graph.max - graph.min))
            except ZeroDivisionError:
                perc = 0
            return topleft[1] + size[1] - (size[1] * perc)

        old = graph[0]
        for i in range(size[0]):
            # Find the current position to draw to.
            cur = graph[row2date(i)]
            # Draw the lines.
            x = topleft[0] + i
            for index in range(len(cur)):
                pygame.draw.aaline(surface, colour, \
                    (x - 1, y(old[index])), \
                    (x, y(cur[index])))
            # Save the current position.
            old = cur
            
def gen_labelling(size, label_size, spacing, label_count=float('inf')):
    """ Generate a labelling for the given size linear area.
        This returns a list of rows for placing the labels on.
    """
    
    # TODO: Allow specifiying which labels to render, to allow for adding 0.0 
    #       and suchlike.
    # TODO: This should also support having a reduced area to place labels
    #       within, eg a smaller area for the labels, but not for the markers.

    # Calculate the number of markers required.
    # We always render at least two markers.
    markers = max(int(size / (label_size + spacing)) + 1, 2)
    
    # Calculate the number of markers required.
    # TODO: Do something special for the discrete case.
    markers = max(int(size / (label_size + spacing)) + 1, 2)
    
    # We always render at least two markers.
    markers = max(markers, 2)
    
    # Return an evenly spaced set of marks.
    return ((float(size) / (markers-1)) * mark for mark in range(markers))
    
def place(size, labels):
    """ Try to optimise the placement of a given set of labels so that they
        are close to their anchor, but not overlapping and not outside of
        the total area.
        labels is assumed to be a map from anchors to sizes, where the anchors
        are assumed to be in the centers of the given sizes.
        The given size is assumed to be a range from the minimum to the maximum
        pos.
    """
    
    # TODO: Add 'spacing' for the labels to avoid cludgy workarounds at the
    #       edges.
    
    # Init the placements for the labels.
    placements = {anchor: anchor for anchor in labels.keys()}
    
    # Init the forces.
    forces = {anchor: PLACEMENT_CONSTANT for anchor in labels.keys()}
    iter = 1 # The current iteration.
    # Iterate until things settle.
    while sum((abs(int(v)) for v in forces.values())) >= PLACEMENT_CONSTANT:
        # Generate the forces for each label.
        forces = {anchor: 0 for anchor in labels.keys()}
        for anchor in placements:
            # Pull back towards the anchors.
            forces[anchor] += float(anchor - placements[anchor]) / ANCHOR_FORCE
            # Apply forces due to overlapping edges.
            if (placements[anchor] - (labels[anchor] / 2)) < size[0]:
                forces[anchor] += (size[0] - (placements[anchor] - \
                    (labels[anchor] / 2)))
            elif (placements[anchor] + (labels[anchor] / 2)) > size[1]:
                forces[anchor] += (size[1] - (placements[anchor] + \
                    (labels[anchor] / 2)))
            # Add forces from overlap.
            for other in placements:
                if anchor != other:
                    a_min = placements[anchor] - (labels[anchor] / 2)
                    a_max = placements[anchor] + (labels[anchor] / 2)
                    o_min = placements[other] - (labels[other] / 2)
                    o_max = placements[other] + (labels[other] / 2)
                    if a_min < o_min < a_max:
                        forces[anchor] += (o_min - a_max) / OVERLAP_FORCE
                    if a_min < o_max < a_max:
                        forces[anchor] += (o_max - a_min) / OVERLAP_FORCE
                        
        # Decrease the forces as appropriate.
        for anchor in forces:
            forces[anchor] = forces[anchor] / iter
        
        # Apply the forces to the labels.
        for anchor in placements:
            placements[anchor] += forces[anchor]
            
        # Increment the iteration.
        iter *= ITERATION_MULTIPLIER
    
    return placements

def merge_rects(dirty):
    """ Merges a list of rects into a single rect """
    
    # Ignore empty lists.
    if len(dirty) == 0:
        return None
    
    # Merge the remaining rects.
    first = dirty[0]
    return first.unionall(dirty[1:])
    
