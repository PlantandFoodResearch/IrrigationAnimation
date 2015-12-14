""" Various animation constants.

	Author: Alastair Hughes
"""

# Display constants:
ANCHOR_FORCE = 10 # Divisor for anchors, for place.
BORDER = 20 # Empty space around the image, in pixels.
BROKEN_COLOUR = (255, 255, 255) # Colour for patches missing data.
DEFAULT_COLOUR = (255, 255, 255) # Background colour.
DEFAULT_LABEL = "Key: " # Default label for graphs.
EDGE_COLOUR = (0, 0, 0) # Colour for the edges.
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
GRAPH_ALPHA = 150 # Alpha of shading on the graph.
GRAPH_COLOUR_LIST = ((255, 0, 0), # A list of colours to choose from.
	(0, 255, 0),
	(0, 0, 255),
	(100, 100, 0),
	(100, 0, 100),
	(0, 100, 100),
	(100, 100, 100),
	(0, 0, 0))
GRAPH_RATIO = .5 # Height to width ratio for the graph.
GRAPH_MAX_HEIGHT = .3 # Maximum height, as a ratio of graph/screen height.
ITERATION_MULTIPLIER = 2 # Multiplier for iteration; the larger the value,
						   # the quicker the place algorithm finishes.
MAP_COLOUR_LIST = ((0.02, 0.24), # A list of HSV colour ranges to choose from.
	(0.36, 0.63),
	(0.7, 0.95))
MAX_FPS = 24 # Maximum allowed FPS
MIN_FPS = 1 # Minimum allowed FPS
MAX_FRAMES_PER_DAY = 5 # Maximum number of frames per day
MIN_FRAMES_PER_DAY = 1 # Minimum number of frames per day
MAX_TEXT_HEIGHT = 60 # Maximum text height
MIN_TEXT_HEIGHT = 5 # Minimum text height
PLACEMENT_CONSTANT = 1 # Minimum activity before place bails.
OVERLAP_FORCE = 2 # Divisor for overlap for place.
SCALE_MARKER_SIZE = 2 # Marker size, in pixels.
SCALE_SPACING = 30 # Space between the values in a scale.
SCALE_TEXT_OFFSET = 5 # Offset of text from the scale, in pixels.
SCALE_WIDTH = 20 # Width of the scale, in pixels.
TEXT_COLOUR = (0, 0, 0) # The colour of any text.
TEXT_AA = True # Whether or not to antialias the text.

# Other:
AREA_FIELD = "Manager_P.Script.Patch_area" # Field name for the patch areas.
DATE_FIELD = "Clock.Today" # Field name for dates.
FIELD_NO_FIELD = "Manager_P.Script.This_field_no" # Field name for the field.
PATCH_NUMBER_FIELD = 'PN' # Field name for patch numbers (in the GIS files).

# Temporary constants:
# TODO: Make these configurable, or find ways to make them automatic.
SCALE_SF = 2 # Decimal places to display on the scale.
