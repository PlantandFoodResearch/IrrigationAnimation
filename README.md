# IrrigationAnimation #

## Using ##

Currently, we have two interfaces; a tkinter GUI, and the builtin pygame UI.

### Tkinter GUI ###

Run gui.py for the Tkinter GUI, which should be largely self-explanatory.

  $ python gui.py

### Pygame UI ###

Edit animate.py to adjust the configurables, number of Values, etc.
Running animate.py should bring up the pygame previewer.

  $ python animate.py

The pygame previewer has a few keybindings:
- Up: Skip forward 10 frames
- Down: Skip backward 10 frames
- Page Up: Skip forward 50 frames
- Page Down: Skip backward 50 frames
- Left: Slow down
- Right: Speed up

## Dependencies ##

- pygame (for rendering, displaying a preview)
- PyMovie (for generating movies)
- pyshp (for parsing the GIS files)

When installing packages, it is essential to use anaconda's python!
Either launch Anaconda's CLI, or launch the command prompt and type 'anaconda'.

### Pygame ###

Pygame can be downloaded from the main website, unfortunately it is a 32 bit
version which does not play nicely with anaconda's 64 bit python.
64 bit Windows builds can be found online; download one and install it.
From memory, I had to jump through a few hoops; the files are .whl (wheel)
files, and so installing them is slightly convoluted.
See also:
https://pip.pypa.io/en/latest/user_guide/#installing-from-wheels
https://www.webucator.com/blog/2015/03/installing-the-windows-64-bit-version-of-pygame/

Note that the 'wheel' package must be installed using pip to install other
wheel packages.

### PyMovie ###

PyMovie can be installed via Anaconda's PIP:

$ pip install pymovie

### PySHP ###

PySHP can be installed via Anaconda's PIP:

$ pip install pyshp


