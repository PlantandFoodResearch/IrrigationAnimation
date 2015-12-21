""" A small library of transformation functions.

    transformation: Data transformations
    times:          Time mapping transformations

    Author: Alastair Hughes
"""

from constants import MAX_FRAMES_PER_DAY, MIN_FRAMES_PER_DAY
import math

# Transformation functions:
# These accept a map 'values' of the form values[row index][patch no], and
# returns another map 'values' suitably transformed.
# These are applied to the data as preprocessing. For instance, change_value
# returns the delta between the current and previous value. Other useful
# functions might scale the data, or remove anomalies.
basic_value = lambda values: values # No transform.
# Time delta uses the delta between a value and the previous day's result.
def time_delta_value(values):
    new_values = {}
    for index in values:
        new_values[index] = {}
        for patch in values[index]:
            new_values[index][patch] = values[index][patch] - \
                values.get(index - 1, {patch: values[index][patch]})[patch]
    return new_values
# Field delta uses the relative delta between a value and the maximum and
# minimums on one specific day.
def field_delta_value(values):
    new_values = {}
    for index in values:
        new_values[index] = {}
        min_day = min(values[index].values())
        max_day = max(values[index].values())
        for patch in values[index]:
            try:
                new_values[index][patch] = \
                    ((values[index][patch] - min_day) / (max_day - min_day))
            except ZeroDivisionError:
                new_values[index][patch] = 0
    return new_values
# Per field normalises the data relative to specific fields.
def per_field_value(values, fields):
    """ This normalises all patches relative to their field.
        'fields' is a map of field numbers to a list of patches in that field.
    """

    field_list = list(fields.values())

    # We calculate the maximum and minimum values for each field.
    maxs = [max((values[index][patch] for index in values \
                for patch in field)) for field in field_list]
    mins = [min((values[index][patch] for index in values \
                for patch in field)) for field in field_list]

    new_values = {}
    for field_id, field in enumerate(field_list):
        f_max = maxs[field_id]
        f_min = mins[field_id]
        for index in values:
            if index not in new_values:
                new_values[index] = {}
            for patch in field:
                try:
                    scaled_value = float(values[index][patch] - f_min) / \
                        (f_max - f_min)
                except ZeroDivisionError:
                    scaled_value = 0
                new_values[index][patch] = scaled_value

    return new_values
# Exponential scaling.
def exponential_value(values, v = math.e):
    new_values = {}
    for index in values:
        new_values[index] = {}
        for patch in values[index]:
            new_values[index][patch] = v**(values[index][patch])
    return new_values
# Logarithmic scaling.
def log_value(values, v = math.e):
    new_values = {}
    for index in values:
        new_values[index] = {}
        for patch in values[index]:
            new_values[index][patch] = math.log(values[index][patch], v)
    return new_values
# Filter by patch_no.
def patch_filter(values, patches):
    new_values = {}
    for index in values:
        new_values[index] = {}
        for patch in patches:
            new_values[index][patch] = values[index][patch]
    return new_values


# TODO: Some functions might accept arguments, so cannot be currently listed
#       here...
transformations = {'basic': basic_value,
    'time_delta': time_delta_value,
    'field_delta': field_delta_value,
    'exponential': exponential_value,
    'log': log_value,
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
    # TODO: This is not at all smoothed!
    
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
        try:
            relative_delta = (max_deltas[date]-min_delta) / (max_delta-min_delta)
        except ZeroDivisionError:
            relative_delta = 0
        frame_count = int((MAX_FRAMES_PER_DAY - MIN_FRAMES_PER_DAY) \
            * relative_delta + MIN_FRAMES_PER_DAY)
        for i in range(frame_count):
            frames[cur_frame] = date
            cur_frame += 1
            
    return frames
    
# Map from time warp type to the actual function.
times = {'basic': map_basic,
    'delta': map_delta}
