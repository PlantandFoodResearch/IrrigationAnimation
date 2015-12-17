#!/usr/bin/env python2
""" User interface code for the animation renderer.

    Current TODO's:
    - Error reporting is broken/non-existant.
    - There is no validation before trying to render, so no nice error
      messages.
    - Clicking on 'model' currently cans the field.
    - There are *lots* of TODO's.
    - Hanging without any indications is still broken
    - We should clear any invalid fields at render time
    - The open file/dir dialogs do not have any customisation.
    - We currently happily overwrite existing videos without any kind of
      warning.
    - The whole split model/values thing is broken; the two should be combined
      to reduce the number of bugs.
    - There are *lots* of bugs...
    - Not all of the configurables are wrapped.

    Future:
    - Saving existing setups.
    - Custom code integration.

    Author: Alastair Hughes
"""

# Local imports.
from display import preview, render
from animate import gen_render_frame
from models import Model, Values, Graphable
from constants import MAP_COLOUR_LIST, MAX_FPS, MIN_FPS, MAX_TEXT_HEIGHT, \
    MIN_TEXT_HEIGHT, FIELD_NO_FIELD
import transforms
from helpers import Job, ThreadedDict, FuncVar

# Tkinter imports
import Tkinter as tk
import tkFileDialog
import ttk

# Threading imports.
from threading import Thread, Lock

class InvalidOption(ValueError):
    """ Error to be raised if an option is invalid """
    
    def __init__(self, name, value, error = None):
        ValueError.__init__(self, \
            "Option '{}' has an invalid value of '{}' (original exception: {})!".format(name, value, error))
        
class Options(ttk.Frame):

    def __init__(self, master):
        """ Init self """
        
        self.master = master
        ttk.Frame.__init__(self, self.master)
        
        # Options added.
        self.options = {} # name: (entry, get)
        
    def add_raw_option(self, name, var, result = lambda x: x):
        """ Add an option """
        
        row = self.grid_size()[1]
        
        # Create a wrapper callback.
        def wrapper(event):
            try:
                result(var.get())
            except:
                var.set("")

        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Create an entry.
        # TODO: Add validation support?
        entry = ttk.Entry(self, textvariable = var)
        entry.grid(row = row, column = 2, sticky = 'e')
        entry.bind('<Return>', wrapper)
        
        # Create a get function.
        def get():
            current = var.get()
            try:
                return result(current)
            except Exception as e:
                var.set("")
                raise InvalidOption(name, current, e)
        
        # Add the option to the options array.
        self.options[name] = (entry, get)
        
    def add_text_option(self, name, default):
        """ Add a textbox option """
        
        row = self.grid_size()[1]
        
        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Create a textbox.
        text = tk.Text(self)
        text.insert('0.0', default)
        text.grid(row = self.grid_size()[1], column = 2, sticky = 'e')
        
        # Add the option.
        self.options[name] = (text, lambda: text.get('0.0', "end"))
        
    def add_combobox_option(self, name, var, options, \
        callback = lambda old, new: None, \
        postcommand = lambda box: None):
        """ Add a combobox option """
        
        row = self.grid_size()[1]
        
        # Create a label.
        label = ttk.Label(self, text = name + ':')
        label.grid(row = row, column = 1, sticky = 'w')
        
        # Define a validator command and callback.
        def valid(old, new, reason):
            if new in box['values']:
                if old != new or reason == "focusin":
                    callback(old, new)
                return True
            return False
            
        # Create the combobox.
        box = ttk.Combobox(self, textvariable = var, values = list(options), \
            postcommand = lambda: postcommand(box), validate='all', \
            validatecommand = (self.register(valid), "%s", "%P", "%V"))
        box.grid(row = row, column = 2, sticky = 'e')
        
        # Add the option to the options array.
        self.options[name] = (box, lambda: var.get())
        
    def add_file_option(self, name, filevar, \
        function = tkFileDialog.asksaveasfilename):
        """ Add a file selection option.
            filevar is the current selection (a string variable).
            Function is the Tk chooser function to call.
        """
        
        row = self.grid_size()[1]
        
        # Create a frame to hold the label and filename.
        frame = ttk.Frame(self)
        frame.grid(row = row, column = 1, columnspan = 2, sticky = 'ew')
        
        # Create a label.
        label = ttk.Label(frame, text = name + ": ")
        label.pack(side = 'left')
        # Create the callback for the name.
        file_label = ttk.Label(frame, textvariable = filevar)
        file_label.pack(side = 'right')
        
        # Create a button to change the file.
        # TODO: Add sanity checking of the resulting filename.
        button = ttk.Button(self, text = "Change", \
            command = lambda: filevar.set(function()))
        button.grid(row = row, column = 3)
        
        # Add the option to the options array.
        self.options[name] = (filevar, lambda: filevar.get())
    
    def __iter__(self):
        """ Iterate through the existing options """
        
        for name, (entry, get) in self.options.items():
            yield (name, get)
        raise StopIteration
        
    def get(self, name):
        """ Get the value of the given variable """
        
        return self.options[name][1]()
        
class ScrolledListbox(ttk.Frame):
    """ Scrolled listbox """
    
    def __init__(self, master, *args, **kargs):
        """ Initialise self """
        
        ttk.Frame.__init__(self, master, *args, **kargs)
        
        # Create the scrollbar and listbox.
        scroll = ttk.Scrollbar(self, orient = 'vertical')
        box = tk.Listbox(self, selectmode = 'extended', \
            exportselection = False, yscrollcommand = scroll.set)
        scroll.config(command = box.yview)
        scroll.pack(side = 'right', fill = 'y', expand = True)
        box.pack(side = 'left', fill = 'both', expand = True)
        
        # Pass-through the listbox functions.
        self.curselection = lambda *args: box.curselection(*args)
        self.get = lambda *args: box.get(*args)
        self.delete = lambda *args: box.delete(*args)
        self.selection_set = \
            lambda *args, **kargs: box.selection_set(*args, **kargs)
        self.selection_clear = \
            lambda *args, **kargs: box.selection_clear(*args, **kargs)
        self.bind = lambda *args: box.bind(*args)
        self.see = lambda *args: box.see(*args)
        self.insert = lambda *args: box.insert(*args)
        
    
class ItemList(ttk.Frame):
    """ An itemlist with flexible per-item options """
    
    def __init__(self, master, name, function, \
        renamecallback=lambda name, newname: True, \
        deletecallback=lambda name: True, \
        addcallback=lambda name: True, \
        deleteable=lambda active: True, *args, **kargs):
        """ Initialise self """
        
        # Init self.
        ttk.Frame.__init__(self, master, *args, **kargs)
        self.name = name
        self.function = function
        # Map for items in the list.
        self.items = {} # name: {key: var}
        # Current context frame.
        self.context = None
        # The index of the currently active element.
        self.active = None
        # The current delete button.
        self.delete_button = None
        # Callback function for checking whether or not the current item can
        # be deleted.
        self.deleteable = deleteable
        # Generic callbacks.
        self.renamecallback = renamecallback
        self.deletecallback = deletecallback
        self.addcallback = addcallback
        
        # Create the widgets.
        self.create_widgets()
        
    def create_widgets(self):
        
        # Add the label.
        labelframe = ttk.Frame(self)
        labelframe.grid(row = 1, column = 1, sticky = 'nw')
        label = ttk.Label(labelframe, text = self.name)
        label.grid(row = 1, sticky = 'nw')

        self.box = ScrolledListbox(self)
        self.box.grid(row = 1, column = 2, rowspan = 3, sticky = 'nes')
    
        # Bind select events to updating the active element.
        self.box.bind("<<ListboxSelect>>", lambda event: self.update_active())

        # Add a 'new' button.
        button = ttk.Button(labelframe, text = 'New', \
            command = self.add_item)
        button.grid(row = 2, sticky = 'nw')
        
    def add_item(self):
        """ Add a new item to the listbox """
        
        # Find a unique name
        id = 0
        name = 'new'
        while name in self.items:
            id += 1
            name = 'new-' + str(id)
        
        # Add the item.
        self.items[name] = {}
        self.box.insert('end', name)
        
        # Clear the existing selection.
        for selected in self.box.curselection():
            self.box.selection_clear(selected)
        
        # Set the selection to the new item.
        self.box.selection_set(first = 'end')
        
        # 'see' the new item.
        self.box.see('end')
        
        # Update the active element.
        self.update_active()
        
        # Call the custom callback.
        self.addcallback(name)
        
    def delete_item(self, index):
        """ Remove the item at the given index from the listbox """
        
        # Reset self.active, if need be.
        if index == self.active:
            self.active = None
        
        # Remove the item from self.items and the listbox.
        name = self.box.get(index)
        del(self.items[name])
        self.box.delete(index)
        
        # Call the custom callback.
        self.deletecallback(name)
        
    def rename_item(self, name, index):
        """ Rename the item at the given index """
        
        # Only rename if required.
        original = self.box.get(index)
        if name != original:

            # Validate the name
            if name in self.items:
                raise ValueError("{} is already used!".format(name))
            elif name == "":
                raise ValueError("Name must contains something!")

            # Add the newly named item.
            self.box.insert(index + 1, name)
            # Update selection, if required.
            if index in self.box.curselection():
                self.box.selection_set(index + 1)
            # Remove the old item.
            self.box.delete(index)
            # Update self.items
            self.items[name] = self.items[original]
            del(self.items[original])
            # Update the active marker, if required.
            if self.active == original:
                self.active = name
            # Call the custom callback.
            self.renamecallback(original, name)
            
    def delete_selected(self):
        """ Delete any currently selected items """
        
        # Delete any currently selected items.
        # We do this in a convoluted way because the index numbers move as
        # things are removed.
        selected = self.box.curselection()
        while len(selected) != 0:
            self.delete_item(selected[0])
            selected = self.box.curselection()
            
        # Update the active item.
        self.update_active()
        
    def create_frame(self, index):
        """ Create a new frame for the given index """
        
        # Find the name for that index.
        name = self.box.get(index)
        
        # Create the context.
        self.context = Options(self)
        self.context.grid(row = 3, column = 1, sticky = 'sw')
        
        # Add a rename option.
        var = tk.StringVar(value = name)
        var.trace("w", lambda *args: self.rename_item(var.get(), index))
        self.items[name]["Name"] = var
        self.context.add_raw_option("Name", var)
        
        # Add the custom buttons.
        self.function(self.context, name, self.items[name])
        
        # Add a 'delete' button at the bottom.
        self.delete_button = ttk.Button(self.context, text = "Delete", \
            command = self.delete_selected)
        self.delete_button.grid(row = self.context.grid_size()[1], column = 1, \
            sticky = 'sw')
            
        # Note the current active item.
        self.active = name
        
        # Update the delete button's status.
        self.update_deleteable()
        
    def remove_frame(self):
        """ Remove the context-specific frame, if one exists """
        
        if self.context != None:
            # Unset the delete button.
            self.delete_button = None
            
            # Destroy the old frame.
            self.context.grid_forget()
            self.context.destroy()
            
            # Update the active frame and element.
            self.context = None
            self.active = None
        
    def update_active(self):
        """ Update the first selected item.
            We cannot use the 'active' item because that appears to lag
            behind the current selection :(
        """
        
        selected = self.box.curselection()
        if len(selected) > 0:
            if self.box.get(selected[0]) != self.active:
                self.remove_frame()
                self.create_frame(selected[0])
        else:
            self.remove_frame()
            
    def update_deleteable(self):
        """ Force an update for the deletion button """
        
        if self.delete_button != None:
            # Check for all of the selected items.
            self.delete_button.config(state = 'enabled')
            for selected in self.box.curselection():
                if not self.deleteable(self.box.get(selected)):
                    self.delete_button.config(state = 'disabled')
                
    def __iter__(self):
        """ Iterate through self's items """
        for item in self.items.values():
            yield item
        raise StopIteration()
        
    def __getitem__(self, name):
        """ Get the given item """
        return self.items[name]
    

class Main(ttk.Frame):
    """ The main window """
    
    def __init__(self, master, *args, **kargs):
        """ Init self """
        
        self.master = master
        ttk.Frame.__init__(self, self.master, *args, **kargs)
        self.pack(expand = True, fill = 'both')
        
        # Models.
        self.models = ThreadedDict(lambda name: Model(*name))
        # Values.
        # Don't bother with early caching for this; rendering takes quite a bit
        # longer anyway...
        self.values = ThreadedDict(lambda name: Values(self.models[name[0]], \
            name[1], transforms = [transforms.transformations[name[2]]], \
            colour_range = name[3]))
        
        # Create the widgets...
        self.create_buttons()
        # Create the options...
        self.create_options()
        # Create the lists...
        self.create_lists()
        
    def create_buttons(self):
        """ Create the button widgets """

        # Create the holder frame.
        lower = ttk.Frame(self)
        lower.pack(side='bottom', fill='x')
        # Create the helper function...
        def render_wrapper(button, func, *args):
            """ Helper render wrapper """
            
            # TODO: We really should validate the fields before starting in
            #       order to return a sane error message.
            
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
                else:
                    self.master.after(100, check_ended)
            
            try:
                # Create and save the panels.
                panels = []
                for index, config in enumerate(self.panel_list):
                    gis = config['GIS files'].get()
                    csv = config['CSV directory'].get()
                    field = config['Field'].get()
                    transform = config['Value transform'].get()
                    graph = config["Graph statistics"].get()
                    per_field = config["Per-field"].get()
                    name = config["Name"].get()
                    # TODO: Add full graph support.
                    # TODO: Should we use the panel name anywhere?
                    value = self.values[((gis, csv), field, \
                        transform, MAP_COLOUR_LIST[index])]
                    panel = {'values': value}
                    if graph != 'None':
                        graphs = []
                    
                        # Generate a list of statistics.
                        statistics = []
                        for stat in graph.split("+"):
                            statistics.append(stat.strip().lower())
                        stat_name = " (" + ", ".join(statistics) + ")"
                            
                        if per_field == 'False':
                            # Just one graph.
                            graphs.append(Graphable(value.model, field, field + \
                                stat_name, statistics = statistics))
                        else:
                            # Multiple, per-field graphs.
                            # Figure out the available fields.
                            fields = value.model.extract_field(FIELD_NO_FIELD, \
                                lambda v: int(float(v)))
                            # Generate a graph for each field.
                            for field_no in set(fields[0].values()):
                                graphs.append(Graphable(value.model, field, \
                                    str(field_no), field_nos = [field_no], \
                                    statistics = statistics))
                            # Set the graph label.
                            panel['graph_label'] = "Fields" + stat_name
                        
                        # Add the graph to the panel.
                        panel['graphs'] = graphs
                    # Add the description.
                    panel['desc'] = config["Description string"].get().format(\
                        name = name, field = field, csv = csv, gis = gis, \
                        transform = config['Value transform'].get())

                    panels.append(panel)
                
                # Generate the render_frame function and frame count
                render_frame, frames = gen_render_frame(panels, \
                    (None, self.options.get('Text size')), \
                    self.options.get('Title'), self.options.get('Timewarp'), \
                    self.options.get('Edge render') == "True")
                    
                # Create a job wrapper to hold the lock.
                def wrap_render(*args, **kargs):
                    with lock:
                        func(*args, **kargs)

                # Create and start the job.
                job = Job(wrap_render, render_frame, frames, \
                    *[self.options.get(arg) for arg in args])
                job.start()
            finally:
                # Call the cleanup function, which will reschedule itself as
                # required.
                check_ended()

            
        # Create the buttons.
        # Preview button.
        # TODO: Currently, this hangs the UI (something to do with the
        #       interaction between pygame and tkinter?), so we set it to
        #       disabled by default.
        preview_button = ttk.Button(lower, text='Preview', state='disabled', \
            command=lambda: render_wrapper(preview_button, preview, 'FPS', \
                'Dimensions', 'Title'))
        preview_button.pack(side='left')
        
        # Render button.
        render_button = ttk.Button(lower, text='Render', \
            command=lambda: render_wrapper(render_button, render, 'FPS', \
                'Dimensions', 'Movie filename'))
        render_button.pack(side='right')
        
        # Create the progress bar (shares the same frame).
        self.create_progressbar(lower)
        
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
        self.options.add_raw_option("Title", tk.StringVar())
        def check_int(i, min, max):
            if min <= i <= max:
                return i
            else:
                raise ValueError("{} not within [{}, {}]!".format(i, min, max))
        self.options.add_raw_option("FPS", tk.IntVar(value = 4), \
            lambda x: check_int(x, MIN_FPS, MAX_FPS))
        def check_size(size):
            x, y = size.split('x')
            return int(x), int(y)
        self.options.add_raw_option("Dimensions", \
            tk.StringVar(value = "1280x1024"), check_size)
        self.options.add_raw_option("Text size", tk.IntVar(value = 25), \
            lambda x: check_int(x, MIN_TEXT_HEIGHT, MAX_TEXT_HEIGHT))
        # Add the listbox options.
        self.options.add_combobox_option("Timewarp", \
            tk.StringVar(value = 'basic'), transforms.times.keys())
        self.options.add_combobox_option("Edge render", \
            tk.StringVar(value = "True"), ["True", "False"])
        # Add the file option.
        movie_filename = tk.StringVar(value = "movies/movie.mp4")
        self.options.add_file_option("Movie filename", movie_filename)
        
    def create_lists(self):
        """ Create the lists """
        
        # Create the actual model_list.
        def panel_options(master, active, values):
            """ Create the additional options for a specified value """
            
            def cache_model():
                """ Cache the given model (async) """
                try:
                    self.models.cache((values['GIS files'].get(), \
                        values['CSV directory'].get()))
                except KeyError:
                    pass

            def add_file(name, default, *args):
                if name not in values:
                    values[name] = tk.StringVar(value = default)
                    values[name].trace("w", lambda *args: cache_model())
                    cache_model()
                master.add_file_option(name, values[name], *args)
                
            def add_combo(name, options, default, **kargs):
                if name not in values:
                    values[name] = tk.StringVar(value = default)
                master.add_combobox_option(name, values[name], options, \
                    **kargs)

            def add_text(name, default):
                if name not in values:
                    values[name] = FuncVar(lambda: master.get(name))
                master.add_text_option(name, default)

            def post_field(box):
                """ Callback function for updating the list of fields """
                try:
                    fields = self.models[(values['GIS files'].get(), \
                        values['CSV directory'].get())].fields()
                except KeyError:
                    fields = []
                box['values'] = sorted(list(fields))
                
            add_file("GIS files", "gis/SmallPatches.shp", \
                tkFileDialog.askopenfilename)
            add_file("CSV directory", "csv/small", \
                tkFileDialog.askdirectory)
            add_combo("Value transform", transforms.transformations.keys(), \
                'basic')
            add_combo("Field", [], "", postcommand = post_field)
            add_combo("Graph statistics", ["Mean", "Min", "Max", "Min + Max", \
                "Min + Mean + Max", "Sum", "None"], "None")
            add_combo("Per-field", ['True', 'False'], 'False')
            # Add a description string option.
            add_text("Description string", """{name}:
    Field of interest: {field}
    CSV: {csv}
    GIS: {gis}
    Transform: {transform}""")

        self.panel_list = ItemList(self, "Panels", panel_options)
        self.panel_list.pack(expand = True, fill = 'both')


if __name__ == "__main__":
    ui = Main(tk.Tk(), width=600, height=600)
    ui.mainloop()
    
