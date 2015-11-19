""" Animate a given set of CSV data ontop of a GIS file.

	Current todo:
	- Render a field onto a single frame
	- Load the CSV files
	- Animate!

	Future improvements:
	- More output formats
	- CLI/GUI interfaces (cli option parsing)
	- Speed ups

	Author: Alastair Hughes
"""

# Config
#TODO: Figure out a more flexible way of doing this...
GIS_FILES="H:/My Documents/vis/gis"
CSV_DIR="H:/My Documents/vis/csv"
MOVIE_FILENAME="H:/My Documents/vis/movie.mp4"
AUTOPLAY="VLC"
FPS=24

# We currently use MoviePy; import that.
from moviepy.editor import VideoClip
# We use numpy to provide an array type.
from numpy import array
# We also need to normalize the given paths.
import os.path # Use os.path.normpath



def make_frame(t):
    """ Generate a frame """
    return array([[(t*10) % 255]*100]*100)

if __name__ == "__main__":
	animation = VideoClip(make_frame, duration=100)
	
	if AUTOPLAY == "iPython":
		# We don't need to write to a file, just play in iPython!
		from moviepy.editor import ipython_display
		ipython_display(animation, width=300, fps=FPS)
	else:
		# Write to the movie file...
		MOVIE_FILENAME=os.path.normpath(MOVIE_FILENAME)
		animation.write_videofile(MOVIE_FILENAME, fps=FPS)
		
		# Autoplay the animation with VLC.
		if AUTOPLAY == "VLC":
			print("Playing with VLC...")
			import subprocess
			#TODO: A stripped down viewer might be better.
			subprocess.call(["C:/Program Files/VideoLAN/VLC/VLC.exe",
				"--play-and-exit", MOVIE_FILENAME])
		
		# Play with Windows Media Player.
		elif AUTOPLAY == "WMP":
			print("Playing with Windows Media Player...")
			import subprocess
			#TODO: This doesn't seem to close as expected after playing?
			subprocess.call(["C:/Program Files/Windows Media Player/wmplayer.exe",
				"/play", "/close", MOVIE_FILENAME])
			
		# Either None (just write to file, don't display), or an 
		# unknown autoplay type!
		elif AUTOPLAY != "None":
			raise ValueError("Invalid AUTOPLAY value!")
