""" Data wrapper classes, and processing functions.
    
    Author: Alastair Hughes
"""

from constants import AREA_FIELD, DATE_FIELD, FIELD_NO_FIELD, \
    PATCH_NUMBER_FIELD

# To find and load the CSV model files, we need some functions.
from os import listdir
import os.path
import re
import csv
from helpers import ThreadedGroup, cache

# shapefile is used to open the GIS files.
import shapefile


class Model():
    """ Wrapper class to contain raw data about the models """
    
    def __init__(self, gis, csv):
        """ Load the data from the CSV and GIS files, and generate some
            overview information.
        """
        
        # Load the data.
        print("Loading data...")
        
        # Load the GIS data.
        self.gis = gis
        self.patches = load_shapes(self.gis)
        
        # Load the CSV files.
        self.csv = csv
        patch_files = find_patch_files(self.csv)
        self.data = raw_patches(patch_files)
        dates = self.extract_field(DATE_FIELD)
        
        # Verify the dates, and compress into a row: date mapping.
        print("Verifying dates...")
        self.dates = {}
        for index in dates:
            date = None
            for patch in dates[index]:
                if date == None:
                    date = dates[index][patch]
                elif date != dates[index][patch]:
                    raise ValueError("For some CSV files ({}, index = {}), the dates are not on equal rows!".format(csv, index))
            self.dates[index] = date

        print("Finished loading the model")

    # This function is cached, which provides a small speedup. 
    # TODO: Ideally, I would refactor so this function was never called
    #       multiple times with the same arguments anyway...
    @cache
    def extract_field(self, field, process=lambda v: v):
        """ Extract a single field from the loaded data, and optionally
            apply a function 'process' to each piece of data.
        """
        
        result = {}
        for index in self.data:
            result[index] = {}
            for patch in self.data[index]:
                result[index][patch] = \
                    process(self.data[index][patch][field].strip())

        return result

    def fields(self):
        """ Return a list of possible fields """
        
        fields = set()
        for index in self.data:
            for patch in self.data[index]:
                for field in self.data[index][patch].keys():
                    if field not in fields:
                        fields.add(field)
        return fields

    @cache
    def get_patch_fields(self):
        """ Return a map of field numbers to a list of patches in that field.
        """

        # TODO: It would be nice if the methodology here could be made more
        #       generic?

        values = self.extract_field(FIELD_NO_FIELD, lambda v: int(float(v)))
        fields = {}
        # There should be at least one row...
        for patch in values[0]:
            if values[0][patch] not in fields:
                fields[values[0][patch]] = []
            fields[values[0][patch]].append(patch)
        return fields



def find_patch_files(dir):
    """ Generates a dict mapping from patch numbers to absolute filenames """
    
    # Get a list of all of the files in the given directory.
    files = listdir(dir)
    
    # Find all of those files which look like CSV patch files, and add them
    # to the dict.
    patches = {}
    for file in files:
        # Check that the file name is in a sane format (ie looks like a CSV patch file).
        match = re.search(r"(Report)([1-9][0-9]*)(\.csv)$", file)
        
        if match:
            # Extract the patch number (second field) and the full file path
            patches[int(match.group(2))] = os.path.join(dir, file)
        else:
            print("Ignoring file in patch directory '%s'!" %file)
    
    return patches

    
def raw_patches(files):
    """ Open the given patch files and extract all of the data """
    
    # Create the processing group.
    group = ThreadedGroup()
    # Create the wrapper function to load a patch file.
    def load_patch(patch_dict, file_name):
        # Parse the patch file.
        with open(file_name) as patch:
            for index, row in enumerate(csv.DictReader(patch)):
                # Insert the values into the dict.
                patch_dict[index] = row
    # Create the patch dict and load into it.
    patches = {} # patch: {index: value}
    for patch_no in files:
        patches[patch_no] = {}
        # Start a job loading another patch file.
        group.start(load_patch, patches[patch_no], files[patch_no])
    # Wait for the jobs to finish.
    group.wait()
    
    # Turn the resulting data into a index[patch[value]] format, and strip the
    # data.
    result = {} # index: {patch: values}
    for patch in patches:
        for index in patches[patch]:
            if index not in result:
                result[index] = {}
            result[index][patch] = {field.strip(): value \
                for field, value in patches[patch][index].items()}
            
    return result
    
def load_shapes(shape_file):
    """ Generate a list of shapes, and a map from patches to information about
        the patches.
    """
    
    sf = shapefile.Reader(shape_file)
    
    # Map for patches
    patches = {} # patch: {key: value}
    
    # Create a map from field numbers to field names.
    fields = {}
    for index, field in enumerate(sf.fields[1:]):
        # field[0] is the name of the field ('Area', 'Zone', etc).
        # We offset by one because the first entry in fields is 'DeletionFlag'
        # which is not in the record for a given patch.
        fields[field[0]] = index
    
    # Iterate through the records and fill in the datatypes.
    for id in range(sf.numRecords):
        record = sf.record(id)
        # pyshp returns None is a record has been deleted, so ignore those
        # records.
        if record != None:
            # Extract the patch number.
            patch = record[fields[PATCH_NUMBER_FIELD]]
            if patch in patches:
                raise ValueError("Patch {} referenced twice!".format(patch))
            # Add the patch to the map.
            patches[patch] = {'shape': sf.shape(id)}
            # Add the remaining data.
            for field in fields:
                patches[patch][field] = record[fields[field]]
    
    # Close the reader; there is no function for doing so, we just close the
    # files.
    for file in sf.shp, sf.shx:
        file.close()
    
    return patches
        

class Values():
    """ Wrapper class to contain transformed data from a specific model """
    
    def __init__(self, model, field, domain, data_type='float', transforms=()):
        """ Initialise self """
        
        self.model = model
        self.transforms = transforms
        self.domain = domain
        
        if data_type == 'float':
            process = float
        else:
            # TODO: Implement more data types... string is one obvious one.
            #       Even better, get to a point where we don't have to care
            #       about it here...
            #       A different colour mapping function will be required, and
            #       maximums and minimums are different and not really
            #       applicable.
            raise ValueError("Unknown data type {}".format(data_type))
            
        self.field = field
        orig_values = self.model.extract_field(self.field, process)
        # Apply the transformations.
        self.values = orig_values
        for transform in transforms:
            self.values = transform(self.values)
            
        # Find the minimum and maximum values.
        self.min = float("inf")
        self.max = -float("inf")
        for index in self.values:
            for patch in self.values[index]:
                value = self.values[index][patch]
                if value < self.min:
                    self.min = value
                if value > self.max:
                    self.max = value


class Graphable():
    """ Wrapper class for a model containing 'graphable' information - anything
        not tied to a specific patch.
    """
    
    def __init__(self, model, field, label, domain, field_nos = None, \
        statistics = ['min', 'mean', 'max']):
        """ Initialise self """
        
        self.model = model
        self.field = field
        self.label = label
        self.domain = domain
        
        # Create a helper loading function.
        if field_nos == None:
            # TODO: Explore supporting other data types?
            load_field = lambda field: self.model.extract_field(field, float)
        else:
            # TODO: I'd like to make this filtering more generic (so that it
            #       can be applied elsewhere).
            # We are only interested in specific fields.
            fields = self.model.get_patch_fields()
            patches = []
            for field in field_nos:
                patches += fields[field]
            # Define the helper function.
            def load_field(field):
                values = self.model.extract_field(field, float)
                filtered = {}
                for day in values:
                    filtered[day] = {}
                    for patch in patches:
                        filtered[day][patch] = values[day][patch]
                return filtered
        
        # Load the values.
        self.orig_values = load_field(self.field)
        
        # Get the areas and total area.
        simple_areas = load_field(AREA_FIELD)
        self.areas = {} # patch: area
        self.total_area = 0 # The total area.
        # We assume that areas remain the same, so pick the first area.
        for patch in simple_areas[0]:
            area = int(simple_areas[0][patch])
            self.areas[patch] = area
            self.total_area += area
            
        # Calculate the requested statistics, minimum, and maximum.
        self.calculate_statistics(statistics)

    def calculate_statistics(self, statistics):
        """ Calculate self's statistics """

        # Calculate the requested statistics.
        self.values = []
        for stat in statistics:
            if stat == 'mean':
                def day_func(index):
                    """ Calculate the weighted mean for the given day """
                    day = 0
                    for patch in self.orig_values[index]:
                        day += self.orig_values[index][patch] * \
                            self.areas[patch]
                    return day / self.total_area
            elif stat == 'min':
                day_func = lambda day: min((self.orig_values[day][patch] \
                    for patch in self.orig_values[day]))
            elif stat == 'max':
                day_func = lambda day: max((self.orig_values[day][patch] \
                    for patch in self.orig_values[day]))
            elif stat == 'sum':
                def day_func(index):
                    """ Calculate the weighted sum for the given day """
                    day = 0
                    for patch in self.orig_values[index]:
                        day += self.orig_values[index][patch] * \
                            self.areas[patch]
                    return day
            else:
                raise ValueError("Unknown statistic {}!".format(stat))
            self.values.append({day: day_func(day) \
                for day in self.orig_values})
                
        # Calculate the maximums and minimums.
        self.max = max([max(stat_values.values()) \
            for stat_values in self.values])
        self.min = min([min(stat_values.values()) \
            for stat_values in self.values])
        
    def __getitem__(self, date):
        """ Returns self's value on the given date.
            If it is a tuple, then it represents a range of values.
        """
        
        return [stat[date] for stat in self.values]
        

class Combination():
    """ Wrapper class containing related objects """

    def __init__(self, objects):
        """ Initialise self """

        # Save the list of objects.
        self.objects = objects

        # Find the shared domain.
        self.domain = None
        for obj in objects:
            if self.domain == None:
                self.domain = obj.domain
            elif obj.domain != self.domain:
                raise ValueError("Only objects with shared domains can be made into a combination!")

        # Generate the shared maximums and minimums.
        self.min = min((obj.min for obj in objects))
        self.max = max((obj.max for obj in objects))
 
