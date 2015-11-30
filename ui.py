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

# Configuration option defaults.
# File paths:
gis_files = "H:/My Documents/vis/gis/SmallPatches"
csv_dir = "H:/My Documents/vis/csv/small"
movie_filename = "H:/My Documents/vis/movie.mp4"
# Animation options:
field_of_interest = "Soil.SoilWater.Drainage" # Look at a CSV file to find this?


class InvalidOption(ValueError):
	""" Error to be raised if an option is invalid """
	
	def __init__(self, name, value):
		ValueError.__init__(self, \
			"Option '{}' has an invalid value of '{}'!".format(name, value))

	
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
		
	def add_raw_option(self, name, result, default, event = "<Return>"):
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
		entry.bind(event, wrapper)
		entry.insert(0, default)
		
		# Create a get function.
		def get():
			try:
				return result(entry.get())
			except:
				entry.delete(0, 'end')
				raise InvalidOption(name, entry.get())
		
		# Add the option to the options array.
		self.options[name] = (entry, get)
		
	def add_combobox_option(self, name, options, default):
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
			yield (name, get())
		raise StopIteration
		
	def get(self, name):
		""" Get the value of the given variable """
		
		return self.options[name][1]()
	
class ItemList(ttk.Frame):
	""" An itemlist with flexible per-item options """
	
	def __init__(self, master, name, function, *args, **kargs):
		""" Initialise self """
		
		# Init self.
		ttk.Frame.__init__(self, master, *args, **kargs)
		
		# Add the label.
		labelframe = ttk.Frame(self)
		labelframe.grid(row = 1, column = 1, sticky = 'nw')
		label = ttk.Label(labelframe, text = name)
		label.grid(row = 1, sticky = 'nw')

		# Add the listbox.
		# Create the frame holding both.
		listframe = ttk.Frame(self)
		listframe.grid(row = 1, column = 2, rowspan = 3, sticky = 'nes')
		# Create the scrollbar and listbox.
		scroll = ttk.Scrollbar(listframe, orient = 'vertical')
		box = tk.Listbox(listframe, selectmode = 'extended', \
			exportselection = False, yscrollcommand = scroll.set)
		scroll.config(command = box.yview)
		scroll.pack(side = 'right', fill = 'y', expand = True)
		box.pack(side = 'left', fill = 'both', expand = True)
		
		# Items.
		self.items = {} # name: {key: value}
		
		# Create callbacks for selection changes, to change the
		# context-dependent options.
		context = {'frame': None, 'cleanup': {}}
		def change_active(event):
			
			def remove_old(new_active):
				""" Save the contents, and remove the old frame """
				frame = context['frame']
				if frame != None:
					# Save the contents.
				
					# Destroy the old frame.
					frame.grid_forget()
					frame.destroy()
					context['frame'] = None
					
			# Remove and remake as required.
			# We cannot use get('active') because active appears to lag behind
			# the current selection :(
			if len(box.curselection()) > 0:
				index = box.curselection()[0]
				active = box.get(index)
			
				remove_old(active)
				# We actually create an 'Options' frame.
				frame = context['frame'] = Options(self)
				
				# Add a rename option.
				# Create the callback.
				def rename_item(name, index):
					""" Rename an existing item """
					
					if len(name) > 0 and name not in self.items:
						box.insert(index + 1, name)
						# Update selection, if required.
						if index in box.curselection():
							box.selection_set(index + 1)
						box.delete(index)
					
				frame.add_raw_option("Name", lambda n: rename_item(n, index), \
					active)
				
				# Add the custom buttons.
				function(frame, active)
				
				# Add a 'delete' button.
				# Create the callback.
				def delete_item():
					""" Delete the currently selected items """
					selected = box.curselection()
					while len(selected) != 0:
						item = box.get(selected[0])
						del(self.items[item])
						box.delete(selected[0])
						selected = box.curselection()
					remove_old(None) # Nothing left selected...
				# Create a delete button.
				delete_button = ttk.Button(frame, text = "Delete", \
					command = delete_item)
				delete_button.grid(row = frame.grid_size()[1], column = 1, \
					sticky = 'w')
					
				# Grid the frame in.
				frame.grid(row = 3, column = 1, sticky = 'sw')
		
		# Bind select events to updating the active element.
		box.bind("<<ListboxSelect>>", change_active)

		# Add a 'new' button.
		def add_new():
			""" Add a new item to the listbox """
			# Find a unique name
			id = 0
			name = 'new'
			while name in self.items:
				id += 1
				name = 'new-' + str(id)
			# Add the item.
			self.items[name] = {}
			box.insert('end', name)
			# Clear the existing selection.
			for selected in box.curselection():
				box.selection_clear(selected)
			# Set the selection to the new item.
			box.selection_set(first = 'end')
			# Activate the new item.
			box.activate('end')
			# 'see' the new item.
			box.see('end')
			# Update the active element.
			change_active("add")
		# Create a new button.
		button = ttk.Button(labelframe, text = 'New', command = add_new)
		button.grid(row = 2, sticky = 'nw')
			
		
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
		self.options.add_raw_option("Title", lambda x: x, "")
		def check_int(i, min, max):
			if min <= int(i) <= max:
				return int(i)
			else:
				raise ValueError("{} not within [{}, {}]!".format(i, min, max))
		self.options.add_raw_option("FPS", \
			lambda x: check_int(x, MIN_FPS, MAX_FPS), 4)
		def check_size(size):
			x, y = size.split('x')
			return int(x), int(y)
		self.options.add_raw_option("Movie dimensions", check_size, \
			"1280x1024")
		self.options.add_raw_option("Text size", \
			lambda x: check_int(x, MIN_TEXT_HEIGHT, MAX_TEXT_HEIGHT), 30)
		# Add the listbox options.
		self.options.add_combobox_option("Value transform", \
			transforms.transformations.keys(), 'basic')
		self.options.add_combobox_option("Timewarp", \
			transforms.times.keys(), 'basic')
		self.options.add_combobox_option("Edge render", ["True", "False"], \
			"True")
		# Add the file options.
		self.options.add_file_option("GIS files", \
			"H:/My Documents/vis/gis/SmallPatches")
		self.options.add_file_option("CSV directory", \
			"H:/My Documents/vis/csv/small")
		self.options.add_file_option("Movie filename", \
			"H:/My Documents/vis/movies/movie.mp4")
			
		# Add the Models object list.
		def model_options(master, active):
			""" Create the additional options for a specified value """
			
			master.add_file_option("GIS files", \
				"H:/My Documents/vis/gis/SmallPatches")
			master.add_file_option("CSV directory", \
				"H:/My Documents/vis/csv/small")
			# TODO: Having a deletion button should be controlled by whether or
			# 		not some value is using this particular model.
			
		model_list = ItemList(self, "Models", model_options)
		model_list.pack(expand = True, fill = 'both')

			# Add the Values object list.
		def value_options(master, active):
			""" Create the additional options for a specified value """
			
			# TODO: This should update when the one in model_list does.
			models = list(model_list.items.keys())
			if len(models) > 0:
				master.add_combobox_option("Model", model_list.items.keys(), models[0])
				master.add_combobox_option("Value transform", \
					transforms.transformations.keys(), 'basic')
				# TODO: Figure this out from the model.
				# TODO: This should update when the model is changed.
				master.add_combobox_option("Field", ["Soil.SoilWater.Drainage"], \
					"Soil.SoilWater.Drainage")
			
		value_list = ItemList(self, "Values", value_options)
		value_list.pack(expand = True, fill = 'both')


	def gen_frames(self):
		""" Return a render_frame function and frames variable """
		
		#TODO: We should allow more than one value...
		#TODO: This should be done elsewhere.
		# Create a Model.
		model = Model(self.options.get('GIS files'), self.options.get('CSV directory'))
		# Create the values.
		self.values = [Values(model, "Soil.SoilWater.Drainage")]
	
		# Create the frame rendering function.
		return gen_render_frame(self.values, self.options.get('Text size'), \
			self.options.get('Title'), self.options.get('Timewarp'), \
			self.options.get('Edge render') == "True")
		
	def preview(self):
		""" Preview! """
		
		# Generate the render_frame function and the frame count.
		render_frame, frames = self.gen_frames()
		
		# Play the animation.
		#TODO: This should be launched in another thread to avoid hanging tk?
		preview(render_frame, frames, self.options.get('FPS'), \
			self.options.get('Movie dimensions'), self.options.get('Title'))

		
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
	