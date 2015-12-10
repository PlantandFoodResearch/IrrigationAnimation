""" Various animation constants.

	Author: Alastair Hughes
"""

# Display constants:
BORDER = 20 # Empty space around the image, in pixels.
BROKEN_COLOUR = (0, 0, 255) # Colour for patches missing data.
DEFAULT_COLOUR = (255, 255, 255)
EDGE_COLOUR = (0, 0, 0)
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
GRAPH_ALPHA = 150 # Alpha of shading on the graph.
KEY_LABEL = "Key:" # Label on the key for the graph.
MAX_FPS = 24 # Maximum allowed FPS
MIN_FPS = 1 # Minimum allowed FPS
MAX_FRAMES_PER_DAY = 5 # Maximum number of frames per day
MIN_FRAMES_PER_DAY = 1 # Minimum number of frames per day
MAX_TEXT_HEIGHT = 60 # Maximum text height
MIN_TEXT_HEIGHT = 5 # Minimum text height
SCALE_MARKER_SIZE = 2 # Marker size, in pixels.
SCALE_SPACING = 15 # Space between the values in a scale.
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
SCALE_DECIMAL_PLACES = 4 # Decimal places to display on the scale.
GRAPH_HEIGHT = 100 # Space to leave for the graph.
