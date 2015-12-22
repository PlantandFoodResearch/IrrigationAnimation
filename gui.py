#!/usr/bin/env python2
""" User interface code for the animation renderer.

    Current TODO's:
    - Error reporting is broken/non-existant.
    - There is no validation before trying to render, so no nice error
      messages.
    - There are *lots* of TODO's.
    - Hanging without any indications is still broken
    - We should clear any invalid fields at render time
    - The open file/dir dialogs do not have any customisation.
    - We currently happily overwrite existing videos without any kind of
      warning.
    - There are *lots* of bugs...
    - The per-field transformation is not implemented in the GUI yet.
    - Rendering tab/pane for controlling running render jobs.

    Future:
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
import transforms
from helpers import Job, ThreadedDict, FuncVar, ListVar

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
        # Give the second column some weight...
        self.grid_columnconfigure(2, weight = 1)
        
        # Options added.
        self.options = {} # name: (entry, get)
        
    def add_entry(self, name, var, result = lambda x: x):
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
        self.options[name] = (text, lambda: text.get('0.0', 'end'))
        
    def add_combobox(self, name, var, options, \
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
        self.options[name] = (box, var.get)
        
    def add_file(self, name, filevar, \
        function = tkFileDialog.asksaveasfilename):
        """ Add a file selection option.
            filevar is the current selection (a string variable).
            Function is the Tk chooser function to call.
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
        # TODO: Add sanity checking of the resulting filename.
        button = ttk.Button(frame, text = "Change", \
            command = lambda: filevar.set(function()))
        button.grid(row = 1, column = 3, sticky = 'e')
        
        # Add the option to the options array.
        self.options[name] = (filevar, filevar.get)

    def add_itemlist(self, name, var, function, default):
        """ Creates a new ItemList attached to the given variable """

        itemlist = ItemList(self, name, function, var, default)
        itemlist.grid(row = self.grid_size()[1], column = 1, columnspan = 2, \
            sticky = 'nesw')

        self.options[name] = (var, var.get)

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
        ttk.Frame.__init__(self, master, *args, **kargs)
        self.name = name
        self.function = function
        self.default = default # The default name.
        # Map for items in the list.
        self.items = items # [{key: var}]
        # The index of the currently active element.
        self.active = None
        
        # Create the widgets.
        self.create_widgets()
        # Add any existing items.
        for item in self.items:
            self.box.insert('end', item['Name'].get())
        
    def create_widgets(self):
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
        self.box = ScrolledListbox(self)
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
        var.trace("w", lambda *args: self.rename_item(var))
        values['Name'] = var

        # Create the options widget for this item.
        widget = Options(self)
        # Add the custom buttons.
        self.function(widget, values)
        # Add a 'delete' button at the bottom.
        self.delete_button = ttk.Button(widget, text = "Delete", \
            command = self.delete_selected)
        self.delete_button.grid(row = widget.grid_size()[1], column = 1, \
            sticky = 'sw')
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
        
    def rename_item(self, var):
        """ Rename the item with the given text variable """

        # Find the index for the given variable.
        index = None
        for i, item in enumerate(self.items):
            if item['Name'] == var:
                index = i
        
        # Only rename if required.
        name = var.get().strip()
        if name != self.box.get(index):
            if name == "":
                raise ValueError("Invalid blank name!")
            # Add the newly named item.
            self.box.insert(index + 1, name)
            # Update selection, if required.
            if index in self.box.curselection():
                self.box.selection_set(index + 1)
            # Remove the old item.
            self.box.delete(index)
            
    def delete_selected(self):
        """ Delete any currently selected items """
        
        # Delete any currently selected items.
        # We do this in a convoluted way because the index numbers move as
        # things are removed.
        selected = self.box.curselection()
        while len(selected) != 0:
            self.delete_item(selected[0])
            selected = self.box.curselection()
        
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
        
        self.master = master
        ttk.Frame.__init__(self, self.master, *args, **kargs)
        self.pack(expand = True, fill = 'both')
        
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
                # Generate self's panels.
                panels = self.create_panels()
                
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
            value_transforms = [trans['Name'].get() \
                for trans in config['Transforms'].get()]
            graph = config["Graph statistics"].get()
            graph_transforms = [trans['Name'].get() \
                for trans in config['Graph transforms'].get()]
            per_field = config["Per-field"].get()
            map_domain_id = config["Same scales (map)"].get()
            if map_domain_id == "":
                map_domain_id = len(domains)
            graph_domain_id = config["Same scales (graph)"].get()
            if graph_domain_id == "":
                graph_domain_id = len(domains) + 1
            name = config["Name"].get()
            value = self.values[((gis, csv), field, \
                tuple([transforms.transformations[transform] \
                    for transform in value_transforms]))]
            panel = {'values': value}
            if graph != 'None':
                graphs = []
            
                # Generate a list of statistics.
                stats = []
                for stat in graph.split("+"):
                    stats.append(stat.strip().lower())
                stat_name = " (" + ", ".join(stats) + ") (" + \
                    " + ".join(graph_transforms) + ")"

                graph_transform_list = [transforms.transformations[transform] \
                    for transform in graph_transforms]
                    
                if per_field == 'False':
                    # Just one graph.
                    graph_value = self.values[((gis, csv), field, \
                        tuple(graph_transform_list))]
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
                            tuple(graph_transform_list + [lambda v: \
                                transforms.patch_filter(v, patch_set)]))]
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
                transform = " + ".join(value_transforms))
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
        # Add the listbox options.
        self.options.add_combobox("Timewarp", \
            tk.StringVar(value = 'basic'), transforms.times.keys())
        self.options.add_combobox("Edge render", \
            tk.StringVar(value = "True"), ["True", "False"])
        # Add the file option.
        movie_filename = tk.StringVar(value = "movies/movie.mp4")
        self.options.add_file("Movie filename", movie_filename)

    def transform_options(self, master, values):
        """ Helper for panel_options that creates the options for some
            transformations.
        """

        master.add_combobox('Name', values['Name'], \
            transforms.transformations.keys())

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
            master.add_itemlist(name, values[name], func, default)

        def post_field(box):
            """ Callback function for updating the list of fields """
            try:
                fields = self.models[(values['GIS files'].get(), \
                    values['CSV directory'].get())].fields()
            except KeyError:
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
            tkFileDialog.askopenfilename)
        add_file("CSV directory", "csv/small", tkFileDialog.askdirectory)
        cache_model()
        add_combo("Field", [], "", postcommand = post_field)
        add_entry("Same scales (map)", "")
        add_itemlist("Transforms", self.transform_options, 'basic')

        # Add the graph options.
        add_combo("Graph statistics", ["Mean", "Min", "Max", "Min + Max", \
            "Min + Mean + Max", "Sum", "None"], "None")
        add_combo("Per-field", ['True', 'False'], 'False')
        add_entry("Same scales (graph)", "")
        add_itemlist("Graph transforms", self.transform_options, 'basic')
        
    def create_lists(self):
        """ Create the lists """
        self.panel_list = ItemList(self, "Panels", self.panel_options, [], \
            'new')
        self.panel_list.pack(expand = True, fill = 'both')


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry('600x1000')
    Main(root).mainloop()
    
