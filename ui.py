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

class InvalidOption(ValueError):
	""" Error to be raised if an option is invalid """
	
	def __init__(self, name, value, e):
		ValueError.__init__(self, \
			"Option '{}' has an invalid value of '{}' (original exception: {})!".format(name, value, e))

	
class UI(ttk.Frame):
	
	def __init__(self, master, pages, *args, **kargs):
		""" Initialise self """
		
		self.master = master
		ttk.Frame.__init__(self, self.master, *args, **kargs)
		self.pack(expand=True, fill='both')
		
		# Create the tabs.
		self.windows = ttk.Notebook(self)
		for page in pages:
			self.windows.add(pages[page](self.windows), text=page)
		self.windows.pack(expand=True, fill='both')		
		
class Options(ttk.Frame):

	def __init__(self, master):
		""" Init self """
		
		self.master = master
		ttk.Frame.__init__(self, self.master)
		
		# Options added.
		self.options = {} # name: (entry, get)
		
	def add_raw_option(self, name, default, result):
		""" Add an option """
		
		row = self.grid_size()[1]
		
		# Create a wrapper callback.
		def wrapper(event):
			try:
				result(event.widget.get())
			except:
				event.widget.delete(0, 'end')

		# Create a label.
		label = ttk.Label(self, text = name + ':')
		label.grid(row = row, column = 1, sticky = 'w')
		
		# Create an entry.
		#TODO: Add validation support.
		entry = ttk.Entry(self)
		entry.grid(row = row, column = 2, sticky = 'e')
		entry.bind('<Return>', wrapper)
		entry.insert(0, default)
		
		# Create a get function.
		def get():
			current = entry.get()
			try:
				return result(current)
			except Exception as e:
				entry.delete(0, 'end')
				raise InvalidOption(name, current, e)
		
		# Add the option to the options array.
		self.options[name] = (entry, get)
		
	def add_combobox_option(self, name, default, options):
		""" Add a combobox option """
		
		row = self.grid_size()[1]
		
		# Create a label.
		label = ttk.Label(self, text = name + ':')
		label.grid(row = row, column = 1, sticky = 'w')
		
		# Create the combobox.
		box = ttk.Combobox(self)
		box.grid(row = row, column = 2, sticky = 'e')
		box['values'] = list(options)
		
		# Set the default.
		box.current(options.index(default))
		
		# Add the option to the options array.
		self.options[name] = (box, lambda: box.get())
		
	def add_file_option(self, name, default):
		""" Add a file selection option """
		
		row = self.grid_size()[1]
		
		# Create a string variable.
		file = tk.StringVar()
		
		# Create a label.
		label = ttk.Label(self)
		label.grid(row = row, column = 1, columnspan = 2, \
			sticky = 'w')
		
		# Create a callback for changing the label.
		def label_callback(var_name, index, operation):
			label.config(text = "{}: {}".format(name, file.get()))
		# Add the callback.
		file.trace('w', label_callback)
		# Set the default.
		file.set(default)
			
		# Create a button to change the file.
		button = ttk.Button(self, text = "Change", \
			command = lambda: file.set(tkFileDialog.askopenfilename()))
		button.grid(row = row, column = 3)
		
		# Add the option to the options array.
		self.options[name] = (file, lambda: file.get())
	
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
	
	def __init__(self, master, name, function, *args, **kargs):
		""" Initialise self """
		
		# Init self.
		ttk.Frame.__init__(self, master, *args, **kargs)
		self.name = name
		self.function = function
		# Map for items in the list.
		self.items = {} # name: {key: value}
		# Current context frame.
		self.context = None
		# The index of the currently active element.
		self.active = None
		
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
		# Create a new button.
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
		
	def delete_item(self, index):
		""" Remove the item at the given index from the listbox """
		
		if index == self.active:
			self.active = {}
		
		del(self.items[self.box.get(index)])
		self.box.delete(index)
		
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
		
		# Add a rename button.
		self.context.add_raw_option("Name", name, \
			lambda name: self.rename_item(name, index))
		
		# Add the custom buttons.
		self.function(self.context, name, self.items[name])
		
		# Add a 'delete' button at the bottom.
		delete_button = ttk.Button(self.context, text = "Delete", \
			command = self.delete_selected)
		delete_button.grid(row = self.context.grid_size()[1], column = 1, \
			sticky = 'sw')
			
		# Note the current active item.
		self.active = name
		
	def remove_frame(self):
		""" Remove the context-specific frame, if one exists """
		
		if self.context != None:
			# Save contents, if needed.
			if self.active in self.items:
				for name, get in self.context:
					try:
						self.items[self.active][name] = get()
					except Exception as e:
						print("WARNING: Exception {} occured".format(e))
						# Aborting here causes problems (the frame is not
						# destroyed like it should be), so don't do it!
						# We can just use the old values.
				
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
		
		# Remove any existing frame.
		self.remove_frame()
		
		# Create a new frame, if required.
		selected = self.box.curselection()
		if len(selected) > 0:
			self.create_frame(selected[0])
	

class Main(ttk.Frame):
	""" The main window """
	
	def __init__(self, master, *args, **kargs):
		""" Init self """
		
		self.master = master
		ttk.Frame.__init__(self, self.master, *args, **kargs)

		# Pack self.
		self.pack(expand=True, fill='both')
		
		# Models.
		self.models = []
		# Values.
		self.values = []
		
		# Create the widgets...
		
		# Run buttons.
		lower = ttk.Frame(self)
		lower.pack(side='bottom', fill='x')
		preview = ttk.Button(lower, text='Preview', command=self.preview)
		preview.pack(side='left')
		render = ttk.Button(lower, text='Render', command=self.render)
		render.pack(side='right')
		
		# Create the options...
		self.options = Options(self)
		self.options.pack(expand=True, fill='both')
		# Add the 'raw' (string) options.
		self.options.add_raw_option("Title", "", lambda x: x)
		def check_int(i, min, max):
			if min <= int(i) <= max:
				return int(i)
			else:
				raise ValueError("{} not within [{}, {}]!".format(i, min, max))
		self.options.add_raw_option("FPS", 4, \
			lambda x: check_int(x, MIN_FPS, MAX_FPS))
		def check_size(size):
			x, y = size.split('x')
			return int(x), int(y)
		self.options.add_raw_option("Dimensions", "1280x1024", \
			check_size)
		self.options.add_raw_option("Text size", 30, \
			lambda x: check_int(x, MIN_TEXT_HEIGHT, MAX_TEXT_HEIGHT))
		# Add the listbox options.
		self.options.add_combobox_option("Value transform", 'basic', \
			transforms.transformations.keys())
		self.options.add_combobox_option("Timewarp", 'basic', \
			transforms.times.keys())
		self.options.add_combobox_option("Edge render", "True", \
			["True", "False"])
		# Add the file options.
		self.options.add_file_option("Movie filename", \
			"H:/My Documents/vis/movies/movie.mp4")
			
		# Helper...
		add = lambda method, name, values, default, *args: \
			method(name, values.get(name, default), *args)
			
		# Add the Models object list.
		def model_options(master, active, values):
			""" Create the additional options for a specified value """
			
			add(master.add_file_option, "GIS files", values, \
				"H:/My Documents/vis/gis/SmallPatches")
			add(master.add_file_option, "CSV directory", values, \
				"H:/My Documents/vis/csv/small")
			# TODO: Having a deletion button should be controlled by whether or
			# 		not some value is using this particular model.
			
		model_list = ItemList(self, "Models", model_options)
		model_list.pack(expand = True, fill = 'both')
		# Define a helper accessor function.
		# TODO: This should be cached, so update dynamically?
		def get_models():
			models = {}
			for name, values in model_list.items.items():
				models[name] = Model(values['GIS files'], \
					values['CSV directory'])
			return models

		# Add the Values object list.
		def value_options(master, active, values):
			""" Create the additional options for a specified value """
			
			# TODO: This should update when the one in model_list does.
			models = list(model_list.items.keys())
			if len(models) > 0:
				# Remove outdated value.
				# TODO: This is a hack because changes to model_list do not
				# 		propogate properly yet.
				if 'Model' in values and values['Model'] not in models:
					del(values['Model'])
				add(master.add_combobox_option, "Model", values, models[0], \
					models)
				add(master.add_combobox_option, "Value transform", values, \
					'basic', transforms.transformations.keys())
				# TODO: Figure this out from the model.
				# TODO: This should update when the model is changed.
				add(master.add_combobox_option, "Field", values, \
					"Soil.SoilWater.Drainage", \
					["Soil.SoilWater.Drainage"])
			
		value_list = ItemList(self, "Values", value_options)
		value_list.pack(expand = True, fill = 'both')
		# TODO: This should also be dynamically updated...
		def get_values():
			models = get_models()
			values = []
			for value, config in value_list.items.items():
				model = models[config['Model']]
				field = config['Field']
				transform = config['Value transform']
				values.append(Values(model, field, transform=transform))
			return values
		self.get_values = get_values

	def gen_frames(self):
		""" Return a render_frame function and frames variable """
		
		# Create the frame rendering function.
		return gen_render_frame(self.get_values(), self.options.get('Text size'), \
			self.options.get('Title'), self.options.get('Timewarp'), \
			self.options.get('Edge render') == "True")
		
	def preview(self):
		""" Preview! """
		
		# Generate the render_frame function and the frame count.
		render_frame, frames = self.gen_frames()
		
		# Play the animation.
		#TODO: This should be launched in another thread to avoid hanging tk?
		preview(render_frame, frames, self.options.get('FPS'), \
			self.options.get('Dimensions'), self.options.get('Title'))

		
	def render(self):
		""" Render! """
		
		# Generate the render_frame function and the frame count.
		render_frame, frames = self.gen_frames()
		
		# Play the animation.
		#TODO: This should be launched in another thread to avoid hanging tk?
		#TODO: Progress bar?
		render(render_frame, frames, self.options.get('FPS'), \
			self.options.get('Movie dimensions'), self.options.get('Movie filename'))

		

if __name__ == "__main__":
	root = tk.Tk()
	ui = Main(root, width=600, height=600)
	ui.mainloop()
	