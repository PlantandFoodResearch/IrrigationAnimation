""" Various animation constants.

	Author: Alastair Hughes
"""

# Display constants:
BORDER = 20 # Empty space around the image, in pixels.
BROKEN_COLOUR = (0, 0, 255) # Colour for patches missing data.
DEFAULT_COLOUR = (255, 255, 255)
EDGE_COLOUR = (0, 0, 0)
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
MAX_FPS = 24 # Maximum allowed FPS
MIN_FPS = 1 # Minimum allowed FPS
MAX_FRAMES_PER_DAY = 5 # Maximum number of frames per day
MIN_FRAMES_PER_DAY = 1 # Minimum number of frames per day
MAX_TEXT_HEIGHT = 60 # Maximum text height
MIN_TEXT_HEIGHT = 5 # Minimum text height
TEXT_COLOUR = (0, 0, 0) # The colour of any text.
TEXT_AA = False # Whether or not to antialias the text.

# Other:
DATE_FIELD = "Clock.Today" # Field name for dates.
PATCH_NUMBER_FIELD = 'PN' # Field name for patch numbers (in the GIS files).

# Temporary constants:
# TODO: Make these configurable.
SCALE_DECIMAL_PLACES = 2 # Decimal places to display on the scale.
SCALE_MARKER_SIZE = 2 # Marker size, in pixels.
SCALE_TEXT_OFFSET = 5 # Offset of text from the scale, in pixels.
SCALE_WIDTH = 60 # Width of the scale, in pixels, including text.
