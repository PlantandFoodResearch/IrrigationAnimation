""" Configuration parameters/constants for various parts of the program.

	Author: Alastair Hughes
"""

# File paths:
GIS_FILES = "H:/My Documents/vis/gis/SmallPatches"
CSV_DIR = "H:/My Documents/vis/csv"
MOVIE_FILENAME = "H:/My Documents/vis/movie.mp4"

# Animation options:
FIELD_OF_INTEREST = "Soil.SoilWater.Drainage"
VALUE2VALUE = 'basic' # Value transformation function

# Display constants:
FPS = 2 # Note that 1 does not appear to work?
MOVIE_SIZE = (1280, 1024)
DEFAULT_COLOUR = (255, 255, 255)
BROKEN_COLOUR = (0, 0, 255)
BORDER = 20 # Empty space around the image, in pixels.
EDGE_COLOUR = (0, 0, 0)
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
RENDER_EDGES = False # Whether or not to render edges (plot edges, terrain).
SCALE_WIDTH = 20 # Width of the scale, in pixels.
SCALE_DECIMAL_PLACES = 2 # Decimal places to display on the scale.
TEXT_COLOUR = (0, 0, 0) # The colour of any text.
TEXT_HEIGHT = 30 # The height for any fonts.
TEXT_AA = False # Whether or not to antialias the text.

# Other:
DATE_FIELD = "Clock.Today" # Field name for dates.

# Transformations:
basic_value = lambda values, index, patch: values[index][patch]
# change_value
change_value = lambda values, index, patch: values[index][patch] - \
	values.get(index - 1, {patch: values[index][patch]})[patch]
#TODO: Other useful functions might be exponential decay based
#	   (with min as the baseline, max as the max)
transformations = {'basic': basic_value,
	'delta': change_value,
	}