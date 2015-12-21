#!/usr/bin/env python2
""" Animate a given set of CSV data ontop of a GIS file, and display it in
    a semi-elegant form.

    Future improvements:
    - GUI tweaking (1)
    - Transformations
        - Intergrate with the scale
    - Code cleanups (2)
    - Removing all of the TODO's... (2)
    - Speed ups + profiling
    - Weather integration (3)
    - Render an irrigator
    - Render the description text using 'place'
    - Documentation
        - Design notes/walk through
    - Additional widgets
        - Simple value marker/s (on scale, or just as a value)
    - Labels on existing widgets (eg units for a scale)
    - Pausing support for the dynamic viewer
    - Avoiding lag with the dynamic viewer
    
    Stretch goals:
    - Packaging?
    - Remove pygame dependency?
    - String value support (eg plant stage)?
    - CLI interface

    Author: Alastair Hughes
"""

# Import the other modules...
from display import preview
from transforms import times, basic_value, time_delta_value, \
	field_delta_value, per_field_value
from constants import DEFAULT_COLOUR, BORDER, SCALE_WIDTH, GRAPH_RATIO, \
    GRAPH_MAX_HEIGHT, MAP_COLOUR_LIST
from models import Model, Values, Graphable, Graph, Domain
from widgets import TextWidget, DynamicTextWidget, ScaleWidget, ValuesWidget, \
    GraphWidget
# We use pygame for font rendering...
import pygame.font


def combined_dates(date_list):
    """ Combine the given dates """
    dates = None
    for date in date_list:
        if dates == None:
            dates = date
        elif date != dates:
            raise ValueError("All models must have the same set of dates!")
    return dates

def gen_widgets(panels, dates, font, edge_render):
    """ Generate the widgets from the given panels """

    widgets = []
    i = 0
    for panel in panels:
        # Create the shared dict.
        widget_dict = {}
        # Add the normal items.
        value = panel['values']
        if value.domain.value2colour == None:
            value.domain.init_value2colour(MAP_COLOUR_LIST[i])
            i += 1
        widget_dict['map'] = ValuesWidget(value, edge_render)
        widget_dict['scale'] = ScaleWidget(value.domain, font)
        widget_dict['desc'] = TextWidget(panel.get('desc', ""), font)
        
        # Add the graph.
        if 'graphs' in panel:
            widget_dict['graph'] = GraphWidget(panel['graphs'], dates, font)

        # Save the widgets.
        widgets.append(widget_dict)
    
    return widgets


def gen_render_frame(panels, font_desc, header, timewarp, edge_render):
    """ Given a list of panels, return a render_frame function showing them,
        and the number of frames.
    """

    # Init the font.
    pygame.font.init()
    font = pygame.font.Font(*font_desc)
    
    # Combine the dates and check that they are the same for all the values.
    dates = combined_dates([panel['values'].model.dates for panel in panels])
    
    # Init the widgets.
    widgets = gen_widgets(panels, dates, font, edge_render)
    label = TextWidget(header, font)
    date = DynamicTextWidget(lambda time: dates[time], font)
    
    # Generate the render_frame function.
    frame_map = times[timewarp]([panel['values'] for panel in panels])
    def render_frame(surface, frame):
        """ Render a frame """
        
        index = frame_map[frame] # Figure out the row index in the CSV.
        surface.fill(DEFAULT_COLOUR) # Fill the surface.
        # Cache the surface width and height for readability purposes.
        surf_w = surface.get_width()
        surf_h = surface.get_height()
        
        # Record a list of 'dirty' rects.
        dirty = []
        
        # TODO: Currently we manually place all the widgets, and attempt to be
        #       intelligent about their positioning so that they do not clip.
        #       It would be better if the widgets were smart enough to place
        #       themselves...
        
        # Render the date and label.
        date_rect = date.render(surface, index, \
            lambda size: (surf_w - (BORDER + size[0]), BORDER))
        label_rect = label.render(surface, index, \
            lambda size: (BORDER, BORDER))
        dirty += [label_rect, date_rect]
        
        # Render the maps and scales.
        # desc_offset is the current leftmost offset for a description,
        # calculated to avoid clipping.
        desc_offset = label_rect.right + BORDER
        # value_area is the area dedicated to a specific map/scale/description.
        # It is calculated as a fraction of the space available, where the
        # denominator is the number of values.
        value_area = [i - (2 * BORDER) for i in (surf_w / len(widgets), surf_h)]
        # Iterate through the values and render them.
        for i in range(len(panels)):
            map, scale, desc, graph = widgets[i]['map'], widgets[i]['scale'], \
                widgets[i]['desc'], widgets[i].get('graph', None)
            
            # The x offset is the leftmost start point for an item.
            x_offset = (surf_w / len(widgets)) * i + BORDER
            
            # Render the description.
            # We use the maximum of desc_offset and x_offset to avoid
            # clipping, if possible.
            desc_rect = desc.render(surface, index, \
                lambda size: (max(x_offset + (value_area[0] / 2) - \
                    (size[0] / 2), desc_offset), BORDER))
            # Update the description offset.
            desc_offset = desc_rect.right + BORDER
            # Add the rects.
            dirty.append(desc_rect)
            
            # Figure out the graph height.
            if graph == None:
                graph_height = 0
            else:
                graph_height = int(min(value_area[0] * GRAPH_RATIO, \
                    surf_h * GRAPH_MAX_HEIGHT))

            # Update the lowest point.
            lowest = desc_rect.bottom + BORDER
            
            if scale != None and map != None:
                # Render the scale.
                # TODO: We assume that the map is a square when calculating
                #       the scale size; it might not be, so account for that.
                scale_size = (float('inf'), \
                    min(value_area[0] - (BORDER + SCALE_WIDTH), \
                        value_area[1] - (desc_rect.height + BORDER * 2 + \
                        graph_height)))
                scale_rect = scale.render(surface, index, \
                    lambda size: (x_offset, (lowest + surf_h - \
                        (BORDER + graph_height) - size[1]) / 2), \
                    scale_size)

                # Render the map.
                # The map size is shrunk to avoid clipping with anything, and
                # offsets are calculated accordingly.
                map_size = (value_area[0] - (scale_rect.width + BORDER), \
                    value_area[1] - (desc_rect.height + BORDER * 2 + \
                    graph_height))
                map_rect = map.render(surface, index, \
                    lambda size: (scale_rect.right + BORDER + \
                            ((map_size[0] - size[0]) / 2), \
                        (lowest + surf_h - (BORDER + graph_height) - \
                            size[1]) / 2), \
                    map_size)
                
                # Update the lowest point.
                lowest = max(map_rect.bottom, scale_rect.bottom) + BORDER
                # Add the rects.
                dirty.append(map_rect)
                dirty.append(scale_rect)
                
            # Render the graph, if it is defined.
            if graph != None:
                graph_rect = graph.render(surface, index, \
                    lambda size: (x_offset, lowest), \
                    (value_area[0], max(surf_h - (lowest + BORDER), \
                        graph_height)))
                dirty.append(graph_rect)
    
        # Check for intersections, and print a warning if any are found.
        if len(dirty) != 0:
            for index, widget in enumerate(dirty):
                intersects = widget.collidelistall(dirty[index + 1:])
                for collision in intersects:
                    print("WARNING: Widgets intersect! ({}, {})".format(index, \
                        collision + index + 1))
            
    return render_frame, len(frame_map)


if __name__ == "__main__":
    import os.path
    localpath = os.path.dirname(__file__)

    # Create a couple of Models.
    dry = Model(os.path.join(localpath, "gis/MediumPatches"), \
        os.path.join(localpath, "csv/dry"))
    slow = Model(os.path.join(localpath, "gis/MediumPatches"), \
        os.path.join(localpath, "csv/slow"))

    # Create the Domains.
    domain_1 = Domain()
    domain_2 = Domain()
    # Create the values.
    values = [Values(dry, "SWTotal", domain_1, transforms = [field_delta_value]),
              Values(slow, "SWTotal", domain_1, transforms = [field_delta_value])]
    # Create the graphs.
    graphs = [Graph([Graphable(values[0].model, values[0].field, \
            values[0].field + " (min, mean, max)", \
            statistics = ['min', 'mean', 'max'])
        ], domain_1), \
        Graph([Graphable(values[1].model, values[1].field, \
            "Field #{}".format(i), statistics = ['mean'], field_nos = [i])
            for i in range(1, 5)], domain_1)
    ]
    # Create the description format strings...
    desc_format = """Field of interest: {field}
CSV: {csv}
GIS: {gis}
Transform: {transform}"""
    descriptions = []
    for value, transform in zip(values, ["None", "None"]):
        descriptions.append(desc_format.format(field = value.field, \
           csv = value.model.csv, gis = value.model.gis, \
           transform = transform))
    # Create and save the panels.
    panels = []
    for value, graph, desc in zip(values, graphs, descriptions):
        panels.append({'values': value, 'graphs': graph, 'desc': desc})
    
    # Create the render_frame function and frame count.
    header = "Model render" # Header displayed
    timewarp = 'basic' # Time warp method used
    edge_render = True # Whether or not to render edges (plot edges, terrain).
    font = (None, 25) # A (name, size) tuple for the font.
    # Actually run gen_render_frame.
    render_frame, frames = gen_render_frame(panels, font, header, timewarp, \
        edge_render)
    
    # Play the animation.
    fps = 4 # Frames per second
    display_size = (1280, 1024) # Default size.
    preview(render_frame, frames, fps, display_size, header)
    
