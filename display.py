""" Modules to help create and play the given animation!

	Author: Alastair Hughes
"""

# Configuration constants.
MOVIE_SIZE = (40,40)
MOVIE_FILENAME = "H:/My Documents/vis/movie.mp4"
FPS = 24

# We currently use MoviePy; import that.
from moviepy.editor import VideoClip
# We use pygame for rendering...
#TODO: Figure out how to get rid of pygame dependency?
import pygame, pygame.surfarray
# We also need to normalize the given paths.
import os.path # Use os.path.normpath


def play(render_frame, autoplay="VLC"):
	""" Create a movie using the given render_frame function, and
		display it.
	"""
	
	# Wrapper so that the render function gets passed a surface to draw to.
	def make_frame(t):
		surface = pygame.Surface(MOVIE_SIZE)
		render_frame(surface, t)
		return pygame.surfarray.pixels2d(surface)
	
	# Create the animation...
	#TODO: Remove hardcoded durations, screen size
	animation = VideoClip(make_frame, duration=100)

	if autoplay == "iPython":
		# We don't need to write to a file, just play in iPython!
		from moviepy.editor import ipython_display
		ipython_display(animation, width=300, fps=FPS)
	else:
		# Write to the movie file...
		file = os.path.normpath(MOVIE_FILENAME)
		animation.write_videofile(file, fps=FPS)
		
		# Autoplay the animation with VLC.
		if autoplay == "VLC":
			print("Playing with VLC...")
			import subprocess
			#TODO: A stripped down viewer might be better.
			subprocess.call(["C:/Program Files/VideoLAN/VLC/VLC.exe",
				"--play-and-exit", file])
		
		# Play with Windows Media Player.
		elif autoplay == "WMP":
			print("Playing with Windows Media Player...")
			import subprocess
			#TODO: This doesn't seem to close as expected after playing?
			subprocess.call(["C:/Program Files/Windows Media Player/wmplayer.exe",
				"/play", "/close", file])
			
		# Either None (just write to file, don't display), or an 
		# unknown autoplay type!
		elif autoplay != "None":
			raise ValueError("Invalid autoplay value!")
			
if __name__ == "__main__":
	def render_frame(surface, t):
		""" Generate a frame """
		surface.fill((t*10, t*10, t*10))

	play(render_frame)