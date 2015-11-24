""" Modules to help create and play the given animation!

	Author: Alastair Hughes
"""

# We currently use MoviePy; import that.
from moviepy.editor import VideoClip
# We use pygame for rendering... and lots of other things.
import pygame, pygame.surfarray, pygame.transform
# We also need to normalize the given paths, otherwise VLC/WMP will not like
# them.
import os.path # Use os.path.normpath
# We also need some constants
from config import MAX_FPS, MIN_FPS, MOVIE_SIZE, MOVIE_FILENAME, FPS, AUTOPLAY


def play(render_frame, autoplay=AUTOPLAY, frames=200, fps=FPS):
	""" Create a movie using the given render_frame function, and
		display it.
	"""
	
	if autoplay == "Pygame":
		# Pygame viewer (the builtin MoviePy one seems broken, and this skips
		# rendering a video)
		#TODO: Add widget to allow rapidly switching between frames.
		import pygame.event, pygame.display, pygame.time
		pygame.init()
		screen = pygame.display.set_mode(MOVIE_SIZE, pygame.RESIZABLE)
		pygame.display.set_caption("Video rendering...")
		# Render an initial frame.
		frame = 0
		render_frame(screen, 0)

		# Render all the remaining frames.
		while frame < (frames - 1):
			frame += 1
			last_time = pygame.time.get_ticks()
			pygame.display.update()
			# Render a frame, then check for events, wait.
			render_frame(screen, frame)
			
			# Get any events...
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
				elif event.type == pygame.KEYDOWN:
					if event.key == 273:
						frame += 10
					elif event.key == 274:
						frame = max(frame - 10, 0)
					elif event.key == 280:
						frame += 50
					elif event.key == 281:
						frame = max(frame - 50, 0)
					elif event.key == 276:
						fps = min(fps/2.0, MIN_FPS)
					elif event.key == 275:
						fps = max(fps*2, MAX_FPS)
				elif event.type == pygame.VIDEORESIZE:
					# Window has been resized!
					screen = pygame.display.set_mode(event.dict['size'], \
						pygame.RESIZABLE)
					# Rerender...
					render_frame(screen, frame)
			
			# Wait.
			elapsed_time = pygame.time.get_ticks() - last_time
			time_per_frame = 1000 / fps
			if elapsed_time > time_per_frame:
				print("WARNING: allowed time per frame exceeded")
			else:
				pygame.time.wait(int(time_per_frame - elapsed_time))
			
		return # End early; pygame is different anyhow.

	# Wrapper so that the render function gets passed a surface to draw to,
	# and a frame number.
	def make_frame(t):
		surface = pygame.Surface(MOVIE_SIZE)
		render_frame(surface, int(t*fps))
		# Flip the surface around it's x/y axis (main diagonal), to account for display
		# issues with the movie rendering.
		surface = pygame.transform.rotate(surface, -90)
		surface = pygame.transform.flip(surface, True, False)
		return pygame.surfarray.pixels3d(surface)
	
	# Create the animation...
	animation = VideoClip(make_frame, duration=frames/fps)

	if autoplay == "iPython":
		# We don't need to write to a file, just play in iPython!
		from moviepy.editor import ipython_display
		ipython_display(animation, width=MOVIE_SIZE[1], fps=fps)

	else:
		# Write to the movie file...
		file = os.path.normpath(MOVIE_FILENAME)
		animation.write_videofile(file, fps=fps)
		
		# Autoplay the animation with VLC.
		if autoplay == "VLC":
			print("Playing with VLC...")
			import subprocess
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
	# Example rendering...
	def render_frame(surface, t):
		""" Generate a frame """
		surface.fill((t*10 % 255, t*10 % 255, t*10 % 255))

	play(render_frame)
	