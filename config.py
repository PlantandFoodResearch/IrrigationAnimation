""" Configuration parameters for various parts of the program, and the
	transformation functions.

	Author: Alastair Hughes
"""

from constants import MAX_FRAMES_PER_DAY, MIN_FRAMES_PER_DAY

# File paths:
gis_files = "H:/My Documents/vis/gis/SmallPatches"
csv_dir = "H:/My Documents/vis/csv/small"
movie_filename = "H:/My Documents/vis/movie.mp4"

# Animation options:
field_of_interest = "Soil.SoilWater.Drainage"
value2value = 'field_delta' # Value transformation function
header = "Model render" # Header displayed
timewarp = 'delta' # Time warp method used

# Display options:
edge_render = True # Whether or not to render edges (plot edges, terrain).
fps = 4 # Frames per second
movie_size = (1280, 1024)
text_height = 30 # The height for any fonts.

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
