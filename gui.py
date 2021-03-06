#!/usr/bin/env python2
""" User interface code for the animation renderer.

    Future:
    - Hanging without any indications is still broken.
    - There is at least one hard-to-reproduce threading-related bug...
    - Rendering tab/pane for controlling running render jobs.
    - Saving existing setups.
    - Custom code integration.

    Author: Alastair Hughes
"""

# Local imports.
from display import preview, render
from animate import gen_render_frame
from models import Model, Values, Graphable, Graph, Domain
from constants import MAP_COLOUR_LIST, MAX_FPS, MIN_FPS, MAX_TEXT_HEIGHT, \
    MIN_TEXT_HEIGHT, FIELD_NO_FIELD
from transforms import field_delta_value, time_delta_value, time_culm_value, \
    exponential_value, log_value, per_field_value, patch_filter, times
from helpers import Job, ThreadedDict, FuncVar, ListVar

# Tkinter imports
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import ttk

# traceback is used for formatting tracebacks nicely.
import traceback

# os.path is used for checking whether a movie already exists.
import os.path

# Threading imports.
from threading import Thread, Lock

# Available transformations.
# Format: {key: [func, arg1, ...]}
# Arguments are optional, and are special strings.
transformations = {
    'field_delta': [field_delta_value],
    'time_delta': [time_delta_value],
    'time_culm': [time_culm_value],
    'exponential': [exponential_value],
    'log': [log_value],
    'per_field': [per_field_value, 'fields'],
}

def get_transform_tuple(transform_config, model):
    """ Generate the transformation tuple """

    transforms = []
    names = []
    for values in transform_config:
        # Find and save the name.
        name = values['Name'].get()
        names.append(name)

        # Add the transformation.
        func = transformations[name][0]
        mandatory_args = [] # Mandatory arguments for the given transform.
        for arg in transformations[name][1:]:
            if arg == 'fields':
                mandatory_args.append(model.get_patch_fields())
            else:
                raise ValueError("Unknown transform arg {}!".format(arg))
        # Create the transformation.
        transforms.append(lambda v: func(v, *mandatory_args))

    return tuple(transforms), names

class Options(ttk.Frame):

    def __init__(self, master):
        """ Init self """
        
        ttk.Frame.__init__(self, master)
        # Give the second column some weight...
        self.grid_columnconfigure(2, weight = 1)
        
        # Options added.
        self.options = {} # name: get_func
        
    def add_entry(self, name, var, result = lambda x: x):
        """ Add an option """
        
        row = self.grid_size()[1]
        
        # Create a wrapper callback.
        def wrapper(*args):
            try:
                return result(var.get())
            except Exception as e:
                var.set("")
                if len(args) == 0:
                    # Raise the exception if this is not being called in a
                    # callback.
                    raise e

        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Create an entry.
        entry = ttk.Entry(self, textvariable = var)
        entry.grid(row = row, column = 2, sticky = 'e')
        entry.bind('<Return>', wrapper)
        
        # Add the option to the options array.
        self.options[name] = wrapper
        
    def add_text(self, name, var):
        """ Add a textbox option """
        
        row = self.grid_size()[1]
        
        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Create a textbox.
        text = tk.Text(self, width = 40, height = 5)
        text.insert('0.0', var.get())
        text.grid(row = self.grid_size()[1], column = 2, sticky = 'e')
        text.tk.call(text._w, 'edit', 'modified', 0) # Set the 'modified' flag.
        # Define a callback to reset the modified variable.
        self.text_option_modified = False
        def modified_callback(event):
            """ Changing the 'modified' flag triggers the callback... """
            if self.text_option_modified == False:
                var.set(text.get('0.0', 'end'))
                # Reset the flag
                self.text_option_modified = True
                text.tk.call(text._w, 'edit', 'modified', 0)
                self.text_option_modified = False
        # Add the callback.
        text.bind('<<Modified>>', modified_callback)
        
        # Add the option.
        self.options[name] = lambda: text.get('0.0', 'end')
        
    def add_combobox(self, name, var, options, postcommand = lambda box: None):
        """ Add a combobox option """
        
        row = self.grid_size()[1]
        
        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Create the combobox.
        box = ttk.Combobox(self, textvariable = var, values = list(options), \
            postcommand = lambda: postcommand(box), validate='all', \
            validatecommand = \
                (self.register(lambda n: n in box['values']), "%P"))
        box.grid(row = row, column = 2, sticky = 'e')
        
        # Add the option to the options array.
        self.options[name] = var.get
        
    def add_file(self, name, filevar, function):
        """ Add a file selection option.
            filevar is the current selection (a string variable).
            function is a function returning the new filename.
        """
        
        row = self.grid_size()[1]
        
        # Create a frame to hold the label and filename.
        frame = ttk.Frame(self)
        frame.grid(row = row, column = 1, columnspan = 2, sticky = 'ew')
        frame.columnconfigure(2, weight=1) # Make the middle column expand.
        
        # Create a label.
        label = ttk.Label(frame, text = name + ": ")
        label.grid(row = 1, column = 1, sticky = 'w')
        # Create the callback for the name.
        file_label = ttk.Label(frame, textvariable = filevar)
        file_label.grid(row = 1, column = 2, sticky = 'e')
        
        # Create a button to change the file.
        def set_file():
            filename = function()
            # Ignore blank filenames; anything else is assumed to be valid.
            if filename != '':
                filevar.set(filename)
        # Make and grid the button.
        button = ttk.Button(frame, text = "Change", command = set_file)
        button.grid(row = 1, column = 3, sticky = 'e')
        
        # Add the option to the options array.
        self.options[name] = filevar.get

    def add_itemlist(self, name, var, function, default, *args, **kargs):
        """ Creates a new ItemList attached to the given variable """

        itemlist = ItemList(self, name, function, var, default, *args, **kargs)
        itemlist.grid(row = self.grid_size()[1], column = 1, columnspan = 2, \
            sticky = 'nesw')

        self.options[name] = var.get

    def get(self, name):
        """ Get the value of the given variable """
        
        return self.options[name]()
        

class ScrolledListbox(ttk.Frame):
    """ Scrolled listbox """
    
    def __init__(self, master, *args, **kargs):
        """ Initialise self """
        
        ttk.Frame.__init__(self, master)
        
        # Create the scrollbar and listbox.
        scroll = ttk.Scrollbar(self, orient = 'vertical')
        box = tk.Listbox(self, selectmode = 'extended', \
            exportselection = False, yscrollcommand = scroll.set, *args, \
            **kargs)
        scroll.config(command = box.yview)
        scroll.pack(side = 'right', fill = 'y', expand = True)
        box.pack(side = 'left', fill = 'both', expand = True)
        
        # Pass-through the listbox functions.
        self.curselection = lambda *args: box.curselection(*args)
        self.get = lambda *args, **kargs: box.get(*args, **kargs)
        self.delete = lambda *args, **kargs: box.delete(*args, **kargs)
        self.selection_set = \
            lambda *args, **kargs: box.selection_set(*args, **kargs)
        self.selection_clear = \
            lambda *args, **kargs: box.selection_clear(*args, **kargs)
        self.bind = lambda *args, **kargs: box.bind(*args, **kargs)
        self.see = lambda *args, **kargs: box.see(*args, **kargs)
        self.insert = lambda *args, **kargs: box.insert(*args, **kargs)
        self.size = lambda *args, **kargs: box.size(*args, **kargs)

    
class ItemList(ttk.Frame):
    """ An itemlist with flexible per-item options """
    
    def __init__(self, master, name, function, items, default, *args, **kargs):
        """ Initialise self """
        
        # Init self.
        ttk.Frame.__init__(self, master, borderwidth = 2, relief = 'raised')
        # Save the name, function, and default name.
        self.name = name
        self.function = function
        self.default = default # The default name.
        # Map for items in the list.
        self.items = items # [{key: var}]
        # The index of the currently active element.
        self.active = None
        
        # Create the widgets.
        self.create_widgets(*args, **kargs)
        # Add any existing items.
        for item in self.items:
            self.box.insert('end', item['Name'].get())
        
    def create_widgets(self, *args, **kargs):
        """ Create the widgets for self """

        # Add a weight so that things grow properly.
        self.grid_columnconfigure(1, weight = 1)
        
        # Add the label.
        labelframe = ttk.Frame(self)
        labelframe.grid(row = 1, column = 1, sticky = 'nw')
        label = ttk.Label(labelframe, text = self.name)
        label.grid(row = 1, sticky = 'nw')

        # Add a 'new' button.
        button = ttk.Button(labelframe, text = 'New', command = self.add_item)
        button.grid(row = 2, sticky = 'sw')

        # Add the listbox.
        self.box = ScrolledListbox(self, *args, **kargs)
        self.box.grid(row = 1, column = 2, rowspan = 2, sticky = 'nes')
    
        # Bind select events to updating the active element.
        self.box.bind("<<ListboxSelect>>", lambda event: self.update_active())
        
    def add_item(self):
        """ Add a new item to the listbox """
        
        # Add the item to the box.
        self.box.insert('end', self.default)
        values = {}
        self.items.append(values)

        # Create a textvariable for the item's name.
        var = tk.StringVar(value = self.default)
        var.trace("w", lambda *args: self.rename_item(self.active, \
            self.items[self.active]['Name'].get().strip()))
        values['Name'] = var

        # Create the options widget for this item.
        widget = Options(self)
        # Add the custom buttons.
        self.function(widget, values)
        # Create the extra buttons.
        frame = ttk.Frame(widget)
        frame.grid(row = widget.grid_size()[1], column = 1, columnspan = 2, \
            sticky = 'sw')
        # Add a 'delete' button at the bottom.
        delete = ttk.Button(frame, text = "Delete", command = \
            self.delete_selected)
        delete.grid(row = 1, column = 1, sticky = 'w')
        # Add a 'move up' and a 'move down' button.
        up = ttk.Button(frame, text = 'Up', command = \
            lambda: self.swap_active((self.active - 1) % self.box.size()))
        up.grid(row = 1, column = 2)
        down = ttk.Button(frame, text = 'Down', command = \
            lambda: self.swap_active((self.active + 1) % self.box.size()))
        down.grid(row = 1, column = 3, sticky = 'e')
        # Save the widget.
        values['Widgets'] = widget

        # Clear the existing selection.
        for selected in self.box.curselection():
            self.box.selection_clear(selected)
        
        # Set the selection to the new item.
        self.box.selection_set(first = 'end')
        
        # 'see' the new item.
        self.box.see('end')
        
        # Update the active element.
        self.update_active()

    def delete_item(self, index):
        """ Remove the item at the given index from the listbox """
        
        # Reset self.active, if need be.
        if index == self.active:
            self.remove_frame()
            self.active = None
        
        # Remove the item from self.items and the listbox.
        del(self.items[index])
        self.box.delete(index)
        
    def rename_item(self, index, name):
        """ Rename the given item """
        
        # Only rename if required.
        if name != self.box.get(index) and name != "":
            # Add the newly named item.
            self.box.insert(index + 1, name)
            # Update selection, if required.
            if index in self.box.curselection():
                self.box.selection_set(index + 1)
            # Remove the old item.
            self.box.delete(index)

    def swap_active(self, second):
        """ Swap the active item with the one at the given index """

        # Rename the two boxes.
        active_name = self.box.get(self.active)
        self.rename_item(self.active, self.box.get(second))
        self.rename_item(second, active_name)
        # Swap the two item lists.
        active_items = self.items[self.active]
        self.items[self.active] = self.items[second]
        self.items[second] = active_items
        # Update the active and selected item.
        if second not in self.box.curselection():
            self.box.selection_clear(self.active)
            self.box.selection_set(first = second)
        self.active = second
            
    def delete_selected(self):
        """ Delete any currently selected items """
        
        # Delete any currently selected items.
        selected = sorted(self.box.curselection())
        while len(selected) != 0:
            self.delete_item(selected.pop())
        
    def create_frame(self, index):
        """ Create a new frame for the given index """
        
        # Add the widgets in.
        self.items[index]['Widgets'].grid(row = 2, column = 1, sticky = 'nsew')
 
        # Note the current active item.
        self.active = index
        
    def remove_frame(self):
        """ Remove the context-specific frame, if one exists """
        
        if self.active != None:
            # Forget the old frame.
            self.items[self.active]['Widgets'].grid_forget()
            
            # Update the active element.
            self.active = None
        
    def update_active(self):
        """ Update the first selected item.
            We cannot use the 'active' item because that appears to lag
            behind the current selection :(
        """
        
        selected = self.box.curselection()
        if len(selected) > 0:
            if selected[0] != self.active:
                self.remove_frame()
                self.create_frame(selected[0])
        else:
            self.remove_frame()
                
    def __iter__(self):
        """ Iterate through self's items """
        for variables in self.items:
            yield variables
        raise StopIteration()
    

class Main(ttk.Frame):
    """ The main window """
    
    def __init__(self, master, *args, **kargs):
        """ Init self """
        
        # Initialise self.
        ttk.Frame.__init__(self, master, *args, **kargs)
        self.pack(expand = True, fill = 'both')

        # Add the general exception handler.
        master.report_callback_exception = lambda *args: \
            self.pretty_error("\n".join(traceback.format_exception(*args)))
        
        # Models.
        self.models = ThreadedDict(lambda name: Model(*name))
        # Values.
        # Don't bother with early caching for this; rendering takes quite a bit
        # longer anyway...
        self.values = ThreadedDict(lambda name: Values(self.models[name[0]], \
            name[1], transforms = name[2]))
        
        # Create the widgets...
        self.create_buttons()
        # Create the options...
        self.create_options()
        # Create the lists...
        self.create_lists()

        # Add the render job variable.
        self.render_job = None

    def pretty_error(self, message):
        """ Show a pretty error message """
        print("ERROR: {}".format(message))
        tkMessageBox.showerror('Error', message)
        
    def create_buttons(self):
        """ Create the button widgets """

        # Create the holder frame.
        lower = ttk.Frame(self)
        lower.pack(side='bottom', fill='x')

        # Create the helper function...
        def render_wrapper(button, func, *args):
            """ Helper render wrapper """
            
            if not self.sane_values():
                # Something is wrong!
                return
            
            # Disable the button in question.
            button.config(state = "disabled")
            # Start the progress bar.
            # TODO: Figure out how to use a 'determinate' mode for the bar.
            self.bar_start()
            # Create a lock.
            lock = Lock()
            
            # Create a cleanup helper function that waits for the job to finish
            # and then cleans up.
            def check_ended():
                if lock.acquire(False):
                    button.config(state = "normal")
                    self.bar_stop()
                    if self.render_job != None:
                        self.render_job.join()
                else:
                    self.after(100, check_ended)
            
            # This is wrapped to ensure that the cleanup function is always
            # run.
            try:
                # Generate self's panels.
                panels = self.create_panels()
                
                # Generate the render_frame function and frame count.
                render_frame, frames = gen_render_frame(panels, \
                    (None, self.options.get('Text size')), \
                    self.options.get('Title'), self.options.get('Timewarp'), \
                    self.options.get('Edge render') == "True", \
                    self.options.get('Significant figures'))
                    
                # Create a job wrapper to hold the lock.
                def wrap_render(*args, **kargs):
                    with lock:
                        func(*args, **kargs)

                # Create and start the job.
                self.render_job = Job(wrap_render, render_frame, frames, \
                    *[self.options.get(arg) for arg in args])
                self.render_job.start()
            finally:
                # Call the cleanup function, which will reschedule itself as
                # required.
                check_ended()
            
        # Create the buttons.
        # Preview button.
        # TODO: Currently, this hangs the UI (something to do with the
        #       interaction between pygame and tkinter?), so we set it to
        #       disabled by default.
        preview_button = ttk.Button(lower, text = 'Preview', \
            state = 'disabled', command = lambda: \
                render_wrapper(preview_button, preview, 'FPS', 'Dimensions', \
                'Title'))
        preview_button.pack(side = 'left')
        
        # Render button.
        render_button = ttk.Button(lower, text = 'Render', \
            command = lambda: render_wrapper(render_button, render, 'FPS', \
                'Dimensions', 'Movie filename'))
        render_button.pack(side = 'right')
        
        # Create the progress bar (shares the same frame).
        self.create_progressbar(lower)

    def sane_values(self):
        """ Sanitize the current values.
            Prints an error and returns false if the values are not sane.
        """

        def wrap_get(name, message = "{name} is invalid!"):
            """ Get the value, and if an error occured, print the message """
            try:
                self.options.get(name)
            except Exception as e:
                self.pretty_error(message.format(name = name))
                raise ValueError("Value {} is invalid!".format(name))

        try:
            wrap_get('Dimensions')
            wrap_get('Text size')
            wrap_get('FPS')
            wrap_get('Significant figures')
        except ValueError:
            return False

        if len(self.panel_list.items) == 0:
            self.pretty_error("No panels defined!")
            raise ValueError("There must be something to render!")
        for i, item in enumerate(self.panel_list.items):
            if item['Field'].get() == "":
                self.pretty_error("Panel {} has no field set!".format(i + 1))
                return False

            try:
                self.models[(item['GIS files'].get(), \
                    item['CSV directory'].get())]
            except ValueError as e:
                self.pretty_error(e)
                return False

            format_strings = ['name',
                'field',
                'csv',
                'gis',
                'transform'
            ]
            try:
                item["Description string"].get().format( \
                    **{format_string: '' for format_string in format_strings})
            except KeyError as e:
                raise e
                args = ["{" + arg + "}" for arg in format_strings]
                self.pretty_error("""Invalid format string: {}
Valid fields are {}.""".format(e, ", ".join(args[:-1]) + ", and " + args[-1]))
                return False

        # Check that the user *really* wants to overwrite the existing movie.
        movie = self.options.get('Movie filename')
        if os.path.exists(movie):
            return tkMessageBox.askokcancel("Confirm movie filename", \
                "Are you sure that you want to overwrite {}?".format(movie))
        return True

    def create_panels(self):
        """ Generate the panels from self's current config.
            This is called from within the render_wrapper function.
        """

        # Create and save the panels.
        panels = []
        domains = {} # id: ([items], colour)
        for index, config in enumerate(self.panel_list):
            gis = config['GIS files'].get()
            csv = config['CSV directory'].get()
            field = config['Field'].get()
            graph = config["Graph statistics"].get()
            per_field = config["Per-field"].get()
            map_domain_id = config["Same scales (map)"].get()
            if map_domain_id == "":
                map_domain_id = len(domains)
            graph_domain_id = config["Same scales (graph)"].get()
            if graph_domain_id == "":
                graph_domain_id = len(domains) + 1
            name = config["Name"].get()
            # Find the value transformations and names.
            value_trans, value_tran_names = \
                get_transform_tuple(config['Transforms'].get(), \
                self.models[(gis, csv)])
            value = self.values[((gis, csv), field, value_trans)]
            graph_trans, graph_tran_names = \
                get_transform_tuple(config['Graph transforms'].get(), \
                self.models[(gis, csv)])
            panel = {'values': value}
            if graph != 'None':
                graphs = []
            
                # Generate a list of statistics.
                stats = []
                for stat in graph.split("+"):
                    stats.append(stat.strip().lower())
                stat_name = " (" + ", ".join(stats) + ") (" + \
                    " + ".join(graph_tran_names) + ")"

                if per_field == 'False':
                    # Just one graph.
                    graph_value = self.values[((gis, csv), field, \
                        graph_trans)]
                    graphs.append(Graphable(graph_value, field + stat_name, \
                        statistics = stats))
                    graph_label = 'Key'
                else:
                    # Multiple, per-field graphs.
                    # Figure out the available fields.
                    fields = value.model.get_patch_fields().items()
                    # Generate a graph for each field.
                    for field_no, patch_set in fields:
                        graph_value = self.values[((gis, csv), field, \
                            tuple(list(graph_trans) + \
                                [lambda v: patch_filter(v, patch_set)]))]
                        graphs.append(Graphable(graph_value, str(field_no), \
                            statistics = stats))
                    # Set the graph label.
                    graph_label = "Fields" + stat_name
                
                # Add the graph to the panel.
                graph = Graph(graphs, label = graph_label)
                panel['graphs'] = graph
                # Add the graph to the domain list.
                if graph_domain_id in domains:
                    domains[graph_domain_id][0].append(graph)
                else:
                    domains[graph_domain_id] = ([graph], False)
            # Add the description.
            panel['desc'] = config["Description string"].get().format(\
                name = name, field = field, csv = csv, gis = gis, \
                transform = " + ".join(value_tran_names))

            # Add the map to the domains.
            domains[map_domain_id] = (domains.get(map_domain_id, \
                ([], True))[0] + [value], True)

            panels.append(panel)

        # Initialise the domains.
        i = 0
        for items, coloured in domains.values():
            if coloured:
                Domain(items, MAP_COLOUR_LIST[i])
                i += 1
            else:
                Domain(items)

        return panels
        
    def create_progressbar(self, frame):
        """ Create self's progress bar """

        # Do not pack; that will happen as required.
        bar = ttk.Progressbar(frame, mode = 'indeterminate')
        # Create the control variable.
        self.bar_running = 0
        # Create the two helper functions.
        def bar_start():
            """ Start the progress bar """
            if self.bar_running == 0:
                bar.start()
                bar.pack()
            self.bar_running += 1
        def bar_stop():
            """ Stop the progress bar """
            self.bar_running -= 1
            if self.bar_running <= 0:
                bar.stop()
                bar.pack_forget()
        # Add the functions to self.
        self.bar_start = bar_start
        self.bar_stop = bar_stop
        
    def create_options(self):
        """ Create self's options """

        self.options = Options(self)
        self.options.pack(expand = True, fill = 'both')
        # Add the 'raw' (string) options.
        self.options.add_entry("Title", tk.StringVar())
        def check_int(i, min, max):
            if min <= i <= max:
                return i
            else:
                raise ValueError("{} not within [{}, {}]!".format(i, min, max))
        self.options.add_entry("FPS", tk.IntVar(value = 4), \
            lambda x: check_int(x, MIN_FPS, MAX_FPS))
        def check_size(size):
            x, y = size.split('x')
            return int(x), int(y)
        self.options.add_entry("Dimensions", \
            tk.StringVar(value = "1280x1024"), check_size)
        self.options.add_entry("Text size", tk.IntVar(value = 25), \
            lambda x: check_int(x, MIN_TEXT_HEIGHT, MAX_TEXT_HEIGHT))
        self.options.add_entry("Significant figures", tk.IntVar(value = 2), \
            lambda x: check_int(x, 1, 8))
        # Add the listbox options.
        self.options.add_combobox("Timewarp", \
            tk.StringVar(value = 'basic'), times.keys())
        self.options.add_combobox("Edge render", \
            tk.StringVar(value = "True"), ["True", "False"])
        # Add the file option.
        movie_filename = tk.StringVar(value = "movies/movie.mp4")
        self.options.add_file("Movie filename", movie_filename, \
            lambda: tkFileDialog.asksaveasfilename( \
                title = 'Choose the movie filename', \
                filetypes = [('MP4', '.mp4')], defaultextension = '.mp4', \
                initialfile = 'movie'))

    def transform_options(self, master, values):
        """ Helper for panel_options that creates the options for some
            transformations.
        """

        master.add_combobox('Name', values['Name'], transformations.keys())

    def panel_options(self, master, values):
        """ Helper for create_list that creates the options for a specific
            item in the list.
        """

        def cache_model():
            """ Cache the given model (async) """
            try:
                self.models.cache((values['GIS files'].get(), \
                    values['CSV directory'].get()))
            except KeyError:
                pass

        def add_file(name, default, *args):
            values[name] = tk.StringVar(value = default)
            values[name].trace("w", lambda *args: cache_model())
            master.add_file(name, values[name], *args)
            
        def add_entry(name, default, **kargs):
            values[name] = tk.StringVar(value = default)
            master.add_entry(name, values[name], **kargs)

        def add_combo(name, options, default, **kargs):
            values[name] = tk.StringVar(value = default)
            master.add_combobox(name, values[name], options, **kargs)

        def add_text(name, default):
            values[name] = FuncVar(value = default)
            master.add_text(name, values[name])

        def add_itemlist(name, func, default):
            values[name] = ListVar()
            master.add_itemlist(name, values[name], func, default, height = 5)

        def post_field(box):
            """ Callback function for updating the list of fields """
            try:
                fields = self.models[(values['GIS files'].get(), \
                    values['CSV directory'].get())].fields()
            except ValueError as e:
                self.pretty_error(e)
                fields = []
            box['values'] = sorted(list(fields))

        # Add the rename option.
        master.add_entry("Name", values["Name"])

        # Add a description string option.
        add_text("Description string", """{name}:
    Field of interest: {field}
    CSV: {csv}
    GIS: {gis}
    Transform: {transform}""")

        # Add the Value options.
        add_file("GIS files", "gis/SmallPatches.shp", \
            lambda: tkFileDialog.askopenfilename( \
                filetypes = [('ESRI shapefile', '.shp')], \
                title = 'Choose a GIS file'))
        add_file("CSV directory", "csv/small", \
            lambda: tkFileDialog.askdirectory( \
                title = 'Choose the CSV directory'))
        cache_model()
        add_combo("Field", [], "", postcommand = post_field)
        add_entry("Same scales (map)", "")
        add_itemlist("Transforms", self.transform_options, \
            list(transformations.keys())[0])

        # Add the graph options.
        add_combo("Graph statistics", ["Mean", "Min", "Max", "Min + Max", \
            "Min + Mean + Max", "Sum", "None"], "None")
        add_combo("Per-field", ['True', 'False'], 'False')
        add_entry("Same scales (graph)", "")
        add_itemlist("Graph transforms", self.transform_options, \
            list(transformations.keys())[0])
        
    def create_lists(self):
        """ Create the lists """
        self.panel_list = ItemList(self, "Panels", self.panel_options, [], \
            'new')
        self.panel_list.pack(expand = True, fill = 'both')


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('600x750')
    Main(root).mainloop()
    
