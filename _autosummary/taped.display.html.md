# taped.display

Display utilities for audio waveforms.

This module provides functions for visualizing and playing audio waveforms
in Jupyter notebooks and other Python environments. It relies on matplotlib
for visualization and IPython.display.Audio for playback.

Functions:
: getmodulename(obj, default=’’): Get the name of an object’s module.
  plot_wf(wf, sr=None, \*\*kwargs): Plot a waveform against time using matplotlib.
  disp_wf(wf, sr=44100, autoplay=False, wf_plot_func=plt.specgram):
  <br/>
  > Display a waveform visualization and return an Audio widget.
  <br/>
  play_wf(wf, sr=44100, autoplay=True): Play a waveform using IPython’s Audio widget.

#### NOTE
There appears to be an incomplete import statement in the module.

### Functions

| `disp_wf`(wf[, sr, autoplay, wf_plot_func])                                    |                                   |
|--------------------------------------------------------------------------------|-----------------------------------|
| [`getmodulename`](#taped.display.getmodulename)(obj[, default]) | Get name of module of object      |
| [`play_wf`](#taped.display.play_wf)(wf[, sr, autoplay])   | Play waveform using IPython Audio |
| `plot_wf`(wf[, sr])                                                            |                                   |

### taped.display.getmodulename(obj, default='')

Get name of module of object

### taped.display.play_wf(wf, sr=44100, autoplay=True)

Play waveform using IPython Audio
