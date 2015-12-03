""" User interface code for the animation renderer.

	Author: Alastair Hughes
"""

# Local imports.
from display import preview, render
from animate import gen_render_frame
from models import Model, Values
from constants import MAX_FPS, MIN_FPS, MAX_TEXT_HEIGHT, MIN_TEXT_HEIGHT
import transforms

# Tkinter imports
import Tkinter as tk
import tkFileDialog
import ttk

# Threading imports.
from threading import Thread, Semaphore

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
		
	def add_combobox_option(self, name, var, options, \
		callback = lambda old, new: None, \
		postcommand = lambda box: None):
		""" Add a combobox option """
		
		row = self.grid_size()[1]
		
		# Create a label.
		label = ttk.Label(self, text = name + ':')
		label.grid(row = row, column = 1, sticky = 'w')
		
		# Define a validator command and callback.
		def valid(old, new):
			callback(old, new)
			return new in box['values']
			
		# Create the combobox.
		box = ttk.Combobox(self, textvariable = var, values = list(options), \
			postcommand = lambda: postcommand(box), validate='all', \
			validatecommand = (self.register(valid), "%s", "%P"))
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
		
		# Create a label.
		label = ttk.Label(self)
		label.grid(row = row, column = 1, columnspan = 2, \
			sticky = 'w')
		
		# Create a callback for changing the label.
		def label_callback(var_name, index, operation):
			label.config(text = "{}: {}".format(name, filevar.get()))
		# Add the callback.
		filevar.trace('w', label_callback)
		# Call the callback to init the label.
		label_callback('', 0, 'w')
			
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
		
	def update_active(self, callback = lambda: True):
		""" Update the first selected item.
			We cannot use the 'active' item because that appears to lag
			behind the current selection :(
		"""
		
		# Remove any existing frame.
		self.remove_frame()
		
		# Create a new frame, if required.
		selected = self.box.curselection()
		if len(selected) > 0:
			self.create_frame(selected[0])
			
	def update_deleteable(self):
		""" Force an update for the deletion button """
		
		if self.delete_button != None and self.active != None:
			if self.deleteable(self.active):
				self.delete_button.config(state = 'enabled')
			else:
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
		self.models = {}
		# Values.
		self.values = {}
		
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
			# 		order to return a sane error message.
			
			# Disable the button in question.
			button.config(state = "disabled")
			
			try:
				# Generate the render_frame function and the frame count.
				print("Getting frame")
				render_frame, frames = gen_render_frame(self.get_values(), \
					self.options.get('Text size'), \
					self.options.get('Title'), self.options.get('Timewarp'), \
					self.options.get('Edge render') == "True")
				print("Creating a job")

				# Create the job.
				semaphore = Semaphore()
				job = ThreadedJob(semaphore, func, render_frame, frames, \
					*[self.options.get(arg) for arg in args])
					
				# Create a helper function for the end of the job.
				def check_ended():
					""" Check whether the process has finished or not; clean up if
						it has.
					"""
					if semaphore.acquire(False):
						button.config(state = "normal")
					else:
						self.master.after(100, check_ended)
				
				# Start the job.
				job.start()

				# Add a check for the job finishing.
				self.master.after(100, check_ended)
			except Exception as e:
				# We reset the button's state, and then re-raise the error.
				button.config(state = 'normal')
				# Unfortunately, we can't use 'finally', as we only want the
				# button to be activated after the render finishes.
				raise e
			
		# Create the buttons.
		# Preview button.
		# TODO: Currently, this hangs the UI (something to do with the
		#		interaction between pygame and tkinter?), so we set it to
		# 		disabled by default.
		preview_button = ttk.Button(lower, text='Preview', state='disabled', \
			command=lambda: render_wrapper(preview_button, preview, 'FPS', \
				'Dimensions', 'Title'))
		preview_button.pack(side='left')
		
		# Render button.
		render_button = ttk.Button(lower, text='Render', \
			command=lambda: render_wrapper(render_button, render, 'FPS', \
				'Dimensions', 'Movie filename'))
		render_button.pack(side='right')
		
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
		self.options.add_raw_option("Text size", tk.IntVar(value = 30), \
			lambda x: check_int(x, MIN_TEXT_HEIGHT, MAX_TEXT_HEIGHT))
		# Add the listbox options.
		self.options.add_combobox_option("Timewarp", \
			tk.StringVar(value = 'basic'), transforms.times.keys())
		self.options.add_combobox_option("Edge render", \
			tk.StringVar(value = "True"), ["True", "False"])
		# Add the file option.
		movie_filename = tk.StringVar(value = "H:/My Documents/vis/movies/movie.mp4")
		self.options.add_file_option("Movie filename", movie_filename)
		
	def create_lists(self):
		""" Create the lists """
		
		# Create a dummy value_list.
		value_list = None
		
		# Create a callback for when things are renamed so that any values
		# using the name of the model are also updated.
		# TODO: I *should* be able to get rid of this? (shared StringVar)
		def renamecallback(original, name):
			""" Deal with a model being renamed by updating all of the values
				that refer to that model.
				We ignore the active item, as this will be called in the middle
				of updating the current dynamic textboxes, so there is no
				'active' item.
			"""
			
			for item in value_list:
				current = item['Model'].get()
				if original == current:
					item['Model'].set(name)
		
		# Create a deleteable callback for model_list.
		def deleteable(active):
			""" Helper function, returning true if the current active item is
				deleteable.
			"""
			for item_values in value_list:
				if item_values['Model'].get() == active:
					return False
					used = True
			return True
		
		# Create the actual model_list.
		def model_options(master, active, values):
			""" Create the additional options for a specified value """
			
			def add_file(name, default, *args):
				if name not in values:
					values[name] = tk.StringVar(value = default)
				master.add_file_option(name, values[name], *args)
			
			add_file("GIS files", "H:/My Documents/vis/gis/SmallPatches", \
				tkFileDialog.askopenfilename)
			add_file("CSV directory", "H:/My Documents/vis/csv/small", \
				tkFileDialog.askdirectory)

		model_list = ItemList(self, "Models", model_options, \
			renamecallback = renamecallback, deleteable = deleteable)
		model_list.pack(expand = True, fill = 'both')
		
		# Generate the function for the value_list.
		def value_options(master, active, values):
			""" Create the additional options for a specified value """
			
			def add_combo(name, options, default, **kargs):
				if name not in values:
					values[name] = tk.StringVar(value = default)
				master.add_combobox_option(name, values[name], options, \
					**kargs)
					
			def update_model_callback(old, new):
				""" Update the delete button and the field """
				model_list.update_deleteable()
				# Reset the field value (it may now be invalid).
				values['Field'].set("")
				# Load the appropriate model.
				# TODO: This should be done async, to avoid hanging the UI.
				# post_field({})
					
			def post_model(box):
				""" Callback function for updating the list of models """
				models = sorted(list(model_list.items.keys()))
				box['values'] = models

			def post_field(box):
				""" Callback function for updating the list of fields """
				# TODO: This hangs for a bit if the model is not cached.
				try:
					model_values = model_list[values['Model'].get()]
					fields = self.get_model(model_values['GIS files'].get(), \
						model_values['CSV directory'].get()).fields()
				except KeyError:
					fields = []
				box['values'] = sorted(list(fields))
			
			add_combo("Model", [], "", \
				callback = update_model_callback, postcommand = post_model)
			add_combo("Value transform", transforms.transformations.keys(), \
				'basic')
			add_combo("Field", [], "", postcommand = post_field)
		
		# Create the actual Values list. 
		value_list = ItemList(self, "Values", value_options, \
			deletecallback = lambda name: model_list.update_deleteable(), \
			)
		value_list.pack(expand = True, fill = 'both')
		
		# Create the helper generator functions.
		# TODO: These should be dynamically updated.
		def get_values():
			values = []
			for config in value_list:
				model_values = model_list[config['Model'].get()]
				model = self.get_model(model_values['GIS files'].get(), \
					model_values['CSV directory'].get())
				field = config['Field'].get()
				transform = config['Value transform'].get()
				values.append(Values(model, field, transform=transform))
			return values
		self.get_values = get_values
		
	def load_model(self, gis, csv):
		""" Load the given model """
		# TODO: It would be nice if this could be run in the background...
		self.models[(gis, csv)] = Model(gis, csv)
		
	def get_model(self, gis, csv):
		""" Return the model associated with the given csv and gis files,
			loading it if required.
		"""
		
		if (gis, csv) not in self.models:
			# TODO: It would be nice if this could be run in the background...
			self.load_model(gis, csv)
		return self.models[(gis, csv)]
		
class ThreadedJob(Thread):
	""" Threaded job class """
	
	def __init__(self, semaphore, function, *args, **kargs):
		""" Initialise self """
		
		Thread.__init__(self)
		self.semaphore = semaphore
		self.function = function
		self.args = args
		self.kargs = kargs
		
	def run(self):
		""" Run the function """
		
		self.semaphore.acquire()
		try:
			self.function(*self.args, **self.kargs)
		finally:
			self.semaphore.release()

if __name__ == "__main__":
	root = tk.Tk()
	ui = Main(root, width=600, height=600)
	ui.mainloop()
	