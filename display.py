""" Functions to render or preview an animation.

	Author: Alastair Hughes
"""

# We currently use MoviePy for rendering; import that.
from moviepy.editor import VideoClip
# We use pygame for rendering... and lots of other things.
import pygame, pygame.surfarray, pygame.transform, pygame.event, \
	pygame.display, pygame.time
pygame.init()
# We need some constants
from constants import MAX_FPS, MIN_FPS

def preview(render_frame, frames, fps, size, caption):
	""" Preview a movie in pygame, in real time.
		The builtin MoviePy one seems broken, and this skips
		rendering a video... usefull for development.
	"""
	#TODO: Add widget to allow rapidly switching between frames.
	screen = pygame.display.set_mode(size, pygame.RESIZABLE)
	pygame.display.set_caption(caption)
	# Render an initial frame.
	frame = 0
	render_frame(screen, 0)

	# Render all the remaining frames.
	while frame < (frames - 1):
		last_time = pygame.time.get_ticks()
		pygame.display.update()
		
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
				pygame.display.update()
		
		# Render the current frame.
		frame += 1
		render_frame(screen, frame)
		# Wait.
		elapsed_time = pygame.time.get_ticks() - last_time
		time_per_frame = 1000 / fps
		if elapsed_time > time_per_frame:
			print("WARNING: allowed time per frame exceeded")
		else:
			pygame.time.wait(int(time_per_frame - elapsed_time))

def render(render_frame, frames, fps, size, filename):
	""" Create a movie using the given render_frame function """
	
	# Wrapper so that the render function gets passed a surface to draw to,
	# and a frame number.
	def make_frame(t):
		surface = pygame.Surface(size)
		render_frame(surface, int(t*fps))
		# Flip the surface around it's x/y axis (main diagonal), to account for display
		# issues with the movie rendering.
		surface = pygame.transform.rotate(surface, -90)
		surface = pygame.transform.flip(surface, True, False)
		return pygame.surfarray.pixels3d(surface)
	
	# Create the animation...
	animation = VideoClip(make_frame, duration=frames/fps)

	# Write to the movie file...
	animation.write_videofile(filename, fps=fps)

	