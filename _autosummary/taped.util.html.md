# taped.util

Utilities for audio processing and streaming in the taped package.

This module provides tools for:

- Converting between audio bytes and waveforms
- Managing audio input devices and streams
- Chunking data for efficient processing
- Working with audio formats and configurations

Main components:

- Audio format conversion: bytes_to_waveform, waveform_to_bytes
- Device management: find_a_default_input_device_index, ensure_source_input_device_index, list_recording_device_index_names
- Data chunking utilities: simple_chunker, rechunker, chunk_indices
- Constants for default audio parameters (DFLT_SR, DFLT_N_CHANNELS, etc.)

The module is designed to support audio recording, processing, and streaming operations
with a focus on customizable chunking and device handling.

Dependencies:

- numpy: For array manipulation
- soundfile: For audio file operations
- audiostream2py: For audio stream handling
  Utils for taped

```pycon
>>> # Example of working with audio data slices: Create a live waveform reader
>>> wf = LiveWf()
>>> # Get the last 1 second of audio (assuming 44100 sample rate)
>>> last_second = wf[-44100:]
>>> # Will be up to 44100 samples:
>>> len(last_second)
>>>
>>> # Example of converting between formats
>>> from audiostream2py import AudioSegment
>>> # Create a sample AudioSegment (this is just an example structure)
>>> segment = AudioSegment(
...     waveform=b'sample audio data',
...     start_date=1234567890.0,
...     end_date=1234567891.0,
...     frame_count=1000,
...     status_flags=0
... )
>>> # Convert to BufferItemOutput
>>> buffer_item = audio_segment_to_buffer_item_output(segment)
>>> buffer_item.timestamp == 1234567890.0
True
>>> buffer_item.bytes == b'sample audio data'
True
>>>
>>> # Example of positive_slice_version function
>>> positive_slice_version(slice(-5, None), 10)
slice(5, None, None)
>>> positive_slice_version(slice(3, 8, 2), 10)
slice(3, 8, 2)
```

### Module Attributes

| [`pa_format_to_subtype`](#taped.util.pa_format_to_subtype)         | The `soundfile` RAW subtype that losslessly represents each PortAudio sample format.   |
|-------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`read_kwargs_for_sample_width`](#taped.util.read_kwargs_for_sample_width) | How to decode a chunk of raw mic bytes, per sample width.                              |

### Functions

| [`bytes_to_waveform`](#taped.util.bytes_to_waveform)(b[, sr, n_channels, ...])       | Convert raw bytes to a numpy array cast to dtype                              |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`bytes_to_waveform_old`](#taped.util.bytes_to_waveform_old)(b, sr, n_channels, ...)     | Convert raw bytes to a numpy array cast to dtype                              |
| [`chunk_indices`](#taped.util.chunk_indices)(chk_size[, chk_step, ...])          | Yields upper and integer lower bounds of integer size and step chunks.        |
| `ensure_source_input_device_index`([...])                                                          |                                                                               |
| `find_a_default_input_device_index`([verbose])                                                     |                                                                               |
| `find_a_device_index`([filt, dflt])                                                                |                                                                               |
| [`list_recording_device_index_names`](#taped.util.list_recording_device_index_names)()               | List (index, name) of available recording devices                             |
| [`rechunker`](#taped.util.rechunker)(chks, chunker)                          | Generate fixed sized non-overlapping chunks of an iterable of chunks.         |
| [`simple_chunker`](#taped.util.simple_chunker)(a, chk_size)                       | Generate fixed sized non-overlapping chunks of an iterable `a`.               |
| [`subtype_for_sample_width`](#taped.util.subtype_for_sample_width)(sample_width, \*[, ...]) | The `soundfile` subtype matching the format PyAudio *captures* at this width. |
| [`waveform_to_bytes`](#taped.util.waveform_to_bytes)(wf[, sr, sample_width])         | Convert raw bytes to a numpy array cast to dtype                              |

### taped.util.bytes_to_waveform(b, sr=44100, n_channels=1, sample_width=2)

Convert raw bytes to a numpy array cast to dtype

* **Parameters:**
  * **b** – bytes
  * **sr** – sample rate
  * **n_channels** – number of channels
  * **sample_width** – sample byte width [2, 3, 4]
* **Returns:**
  numpy.array or ints

### taped.util.bytes_to_waveform_old(b, sr, n_channels, sample_width, dtype='int16')

Convert raw bytes to a numpy array cast to dtype

#### WARNING
Superseded by [`bytes_to_waveform()`](#taped.util.bytes_to_waveform), and kept only for the scripts in
`taped/scrap`. Its `sample_width` table below is a *second* authority
on how to decode, and it disagrees with the capture side at width 4: the
device is opened as `paFloat32` there (see
[`subtype_for_sample_width()`](#taped.util.subtype_for_sample_width)), not as 32-bit PCM. Use
[`bytes_to_waveform()`](#taped.util.bytes_to_waveform) for anything reading from a live stream.

* **Parameters:**
  * **b** ([`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)) – bytes
  * **sr** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – sample rate
  * **n_channels** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – number of channels
  * **sample_width** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – sample byte width [2, 3, 4]
  * **dtype** – data type used by numpy, i.e. dtype=np.int16 is the same as dtype=’int16’
* **Return type:**
  `array`
* **Returns:**
  numpy.array

### taped.util.chunk_indices(chk_size, chk_step=None, start_idx=0, end_idx=None)

Yields upper and integer lower bounds of integer size and step chunks.

```pycon
>>> it = chunk_indices(5)
>>> next(it)
(0, 5)
>>> next(it)
(5, 10)
>>> list(chunk_indices(chk_size=5, chk_step=3, start_idx=0, end_idx=15))
[(0, 5), (3, 8), (6, 11), (9, 14)]
```

### taped.util.list_recording_device_index_names()

List (index, name) of available recording devices

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### taped.util.pa_format_to_subtype *= {1: 'FLOAT', 4: 'PCM_24', 8: 'PCM_16', 16: 'PCM_S8', 32: 'PCM_U8'}*

The `soundfile` RAW subtype that losslessly represents each PortAudio sample
format. This is the bridge between the two authorities involved in a sample
width, which are *not* the same table:

- the **capture** side: PyAudio derives the stream format from the sample
  width (`pyaudio.get_format_from_width`), and
  `audiostream2py.BasePyAudioSourceReader` opens the input stream with
  exactly that format;
- the **decode** side: `soundfile` turns the resulting raw bytes back into
  numbers, given a subtype.

A disagreement between the two is silent – the bytes decode into numbers of
the wrong kind rather than raising – so they are pinned against each other by
a test rather than merely kept in sync by hand.

### taped.util.read_kwargs_for_sample_width *= {2: {'dtype': 'int16', 'format': 'RAW', 'subtype': 'PCM_16'}, 3: {'format': 'RAW', 'subtype': 'PCM_24'}, 4: {'dtype': 'float32', 'format': 'RAW', 'subtype': 'FLOAT'}}*

How to decode a chunk of raw mic bytes, per sample width. Every `subtype`
here must equal `subtype_for_sample_width(width)`: what we decode has to be
what the device was opened to capture.

|   width | capture format   | decoded as                                |
|---------|------------------|-------------------------------------------|
|       2 | `paInt16`        | `int16`                                   |
|       3 | `paInt24`        | `float64` (soundfile has no 24-bit dtype) |
|       4 | `paFloat32`      | `float32`                                 |

Width 1 (`paUInt8`/`paInt8`) is deliberately absent: soundfile offers no
8-bit dtype, so there is no lossless decode target. An entry here is a promise
that the whole capture-to-waveform path works at that width – it is what
`taped.tools.SUPPORTED_SAMPLE_WIDTHS` is derived from – so an untested
width does not get one.

### taped.util.rechunker(chks, chunker)

Generate fixed sized non-overlapping chunks of an iterable of chunks.
That is, the rechunker applies a chunker to an unraveled stream of chunks,
or more generally of iterables since they can be of varied sizes and types.

```pycon
>>> from functools import partial
>>> chunker = partial(simple_chunker, chk_size=3)
>>> chks = [[0], (1, 2, 3), [4, 5], iter((6, 7))]  # iterable of (different types of) iterables
>>> list(rechunker(chks, chunker))
[(0, 1, 2), (3, 4, 5)]
```

### taped.util.simple_chunker(a, chk_size)

Generate fixed sized non-overlapping chunks of an iterable `a`.

```pycon
>>> list(simple_chunker(range(7), 3))
[(0, 1, 2), (3, 4, 5)]
```

Most of the time, you’ll want to fix the parameters of the chunker like this:

```pycon
>>> from functools import partial
>>> chunker = partial(simple_chunker, chk_size=3)
>>> list(chunker(range(7)))
[(0, 1, 2), (3, 4, 5)]
```

Note, the type of the chunks is always tuples, but you can easily change that using `map`.
For example, to change the type to be list:

```pycon
>>> list(map(list, chunker(range(7))))
[[0, 1, 2], [3, 4, 5]]
```

```pycon
>>> a = range(6)
>>> list(simple_chunker(a, 3))
[(0, 1, 2), (3, 4, 5)]
>>> list(simple_chunker(a, 2))
[(0, 1), (2, 3), (4, 5)]
>>> list(simple_chunker(a, 1))
[(0,), (1,), (2,), (3,), (4,), (5,)]
```

### taped.util.subtype_for_sample_width(sample_width, , unsigned=True)

The `soundfile` subtype matching the format PyAudio *captures* at this width.

Note that the width-to-format map is not the obvious one: 4 bytes is
**float32**, not a 32-bit integer format.

```pycon
>>> subtype_for_sample_width(2)
'PCM_16'
>>> subtype_for_sample_width(4)
'FLOAT'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### taped.util.waveform_to_bytes(wf, sr=44100, sample_width=2)

Convert raw bytes to a numpy array cast to dtype

* **Parameters:**
  * **wf** – iterable of ints
  * **sr** – sample rate
  * **n_channels** – number of channels
  * **sample_width** – sample byte width [2, 3, 4]
* **Returns:**
  bytes
