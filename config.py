""" Configuration parameters/constants for various parts of the program.

	Author: Alastair Hughes
"""

# File paths:
GIS_FILES = "H:/My Documents/vis/gis/SmallPatches"
CSV_DIR = "H:/My Documents/vis/csv"
MOVIE_FILENAME = "H:/My Documents/vis/movie.mp4"

# Animation options:
FIELD_OF_INTEREST = "Soil.SoilWater.Drainage"
VALUE2VALUE = 'field_delta' # Value transformation function
HEADER = "Model render" # Header displayed
TIMEWARP = 'delta' # Time warp method used

# Display constants:
AUTOPLAY = "Pygame"
BORDER = 20 # Empty space around the image, in pixels.
BROKEN_COLOUR = (0, 0, 255)
DEFAULT_COLOUR = (255, 255, 255)
EDGE_COLOUR = (0, 0, 0)
EDGE_THICKNESS = 1 # Some integer greater than or equal to one.
EDGE_RENDER = True # Whether or not to render edges (plot edges, terrain).
FPS = 4 # 1 does not appear to work for MoviePy?
MAX_FPS = 24 # Maximum allowed FPS
MIN_FPS = 1 # Minimum allowed FPS
MAX_FRAMES_PER_DAY = 5 # Maximum number of frames per day
MIN_FRAMES_PER_DAY = 1 # Minimum number of frames per day
MOVIE_SIZE = (1280, 1024)
SCALE_WIDTH = 20 # Width of the scale, in pixels.
SCALE_DECIMAL_PLACES = 2 # Decimal places to display on the scale.
TEXT_COLOUR = (0, 0, 0) # The colour of any text.
TEXT_HEIGHT = 30 # The height for any fonts.
TEXT_AA = False # Whether or not to antialias the text.

# Other:
DATE_FIELD = "Clock.Today" # Field name for dates.

# Transformation functions:
# These are applied to the data as preprocessing. For instance, change_value
# returns the delta between the current and previous value. Other useful
# functions might scale the data, or remove anomalies.
basic_value = lambda values, index, patch: values[index][patch]
# Time delta uses the delta between a value and the previous day's result.
time_delta_value = lambda values, index, patch: values[index][patch] - \
	values.get(index - 1, {patch: values[index][patch]})[patch]
# Field delta uses the relative delta between a value and the maximum and
# minimums on one specific day.
#TODO: This is quite inefficient...
def field_delta_value(values, index, patch):
	min_day, max_day = min(values[index].values()), max(values[index].values())
	try:
		return ((values[index][patch] - min_day) / (max_day - min_day))
	except ZeroDivisionError:
		return 0

#TODO: Other useful functions might be exponential decay based
#	   (with min as the baseline, max as the max)
transformations = {'basic': basic_value,
	'time_delta': time_delta_value,
	'field_delta': field_delta_value,
	}

# Time mapping functions:
# Basic time map functions; these are functions that accept a list of Values
# and use that to generate a map from a frame to a particular index in the
# values.
def map_basic(values):
	""" Direct map from frames to dates """
	one_value = None
	for value in values:
		if one_value == None:
			one_value = value
		elif one_value.model.dates != value.model.dates:
			raise ValueError("All models must have the same set of dates!")
	return {i: i for i in one_value.model.dates}
	
def map_delta(values):
	""" Map from frames to dates, with the frame count per date largely
		changing with respect to the maximum delta that day.
	"""
	#TODO: This is not at all smoothed!
	
	# Validate the values.
	dates = map_basic(values)
	
	def max_day(v, date):
		""" Return the max value for a given date.
			If the given date does not exist, return the max delta for
			the date +1 in the future.
		"""
		if date not in v.values:
			date += 1
		return max((abs(v.actual_values[date][patch]) \
			for patch in v.actual_values[date]))
	
	# Generate a map of maximum deltas per day.
	max_deltas = {}
	for date in dates:
		max_deltas[date] = max((abs(max_day(v, date) - max_day(v, date - 1)) \
			for v in values))
		
	# Find the minimum and maximum deltas (positive values only!)
	max_delta = abs(max(max_deltas.values()))
	min_delta = abs(min(max_deltas.values()))
	
	frames = {}
	cur_frame = 0
	# We assume that dates can be sorted sensibly.
	# Iterate through the dates, adding them and increasing the number of
	# frames for days with large deltas.
	for date in sorted(dates.values()):
		relative_delta = (max_deltas[date]-min_delta) / (max_delta-min_delta)
		frame_count = int((MAX_FRAMES_PER_DAY - MIN_FRAMES_PER_DAY) \
			* relative_delta + MIN_FRAMES_PER_DAY)
		for i in range(frame_count):
			frames[cur_frame] = date
			cur_frame += 1
			
	return frames
	
# Map from time warp type to the actual function.
times = {'basic': map_basic,
	'delta': map_delta}
