# taped.tools

Recording and playback tools for audio data.

The main entry point is [`record()`](#taped.tools.record), a one-call interface over the layered
`BufferItems -> ByteChunks -> WfChunks -> LiveWf` stack of [`taped.base`](taped.base.html.md#module-taped.base).
It records from a microphone and hands you back a waveform (a list of samples),
optionally bounded by a duration, optionally post-processed by an `egress`.

### Module Attributes

| [`SUPPORTED_SAMPLE_WIDTHS`](#taped.tools.SUPPORTED_SAMPLE_WIDTHS)    | the device can be opened at that width *and* the decoder reads back what the device then sends.                 |
|-----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| [`DURATION_UNIT_TO_N_SAMPLES`](#taped.tools.DURATION_UNIT_TO_N_SAMPLES) | Conversion of a `(duration, sample_rate)` pair to a number of samples, one entry per supported `duration_unit`. |

### Functions

| [`record`](#taped.tools.record)([duration, duration_unit, sr, ...])   | Record audio and return waveform data.   |
|-----------------------------------------------------------------------------------------------|------------------------------------------|
| `record_some_sound`(save_to_file[, ...])                                                      |                                          |

### taped.tools.DURATION_UNIT_TO_N_SAMPLES *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[float](https://docs.python.org/3/builtins/functions.html#float), [int](https://docs.python.org/3/builtins/functions.html#int)], [int](https://docs.python.org/3/builtins/functions.html#int)]]* *= {'minutes': <function <lambda>>, 'samples': <function <lambda>>, 'seconds': <function <lambda>>}*

Conversion of a `(duration, sample_rate)` pair to a number of samples, one
entry per supported `duration_unit`. Adding a unit means adding an entry
here – no branching in `record` to edit.

### taped.tools.SUPPORTED_SAMPLE_WIDTHS *= (2, 3, 4)*

the device can be opened at
that width *and* the decoder reads back what the device then sends.

Two authorities have a say, and only one of them lives in this package: PyAudio
picks the *capture* format from the width, and
`taped.util.read_kwargs_for_sample_width` says how to *decode* the result.
A width only belongs here when the two agree – which is why this is derived
from the decode table but not defined by it alone. See
`taped.util.subtype_for_sample_width` for the capture side, and
`test_decode_subtype_matches_the_captured_format_at_every_width` for the
check that keeps them honest.

* **Type:**
  Sample widths (in bytes) that work end to end

### taped.tools.record(duration=None, \*, duration_unit='seconds', sr=44100, egress=None, ignore_exceptions=(<class 'KeyboardInterrupt'>, ), input_device_index=None, sample_width=2, chk_size=4096, stream_buffer_size_s=60, verbose=False)

Record audio and return waveform data.

Records from a microphone until `duration` worth of samples have been
collected, or – when `duration` is `None` – until interrupted. Any
exception listed in `ignore_exceptions` (`KeyboardInterrupt` by default)
ends the recording cleanly and the samples collected *so far* are returned;
every other exception propagates.

* **Parameters:**
  * **duration** ([`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Length of recording. If None, records until interrupted.
  * **duration_unit** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'seconds'`, `'samples'`, `'minutes'`]) – Unit for duration (‘seconds’, ‘samples’, or ‘minutes’).
  * **sr** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Sample rate (Hz).
  * **egress** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Function to process the waveform before returning it, or a
    filepath (a string) to save the waveform to. When a filepath is
    given the waveform is still what is returned.
  * **ignore_exceptions** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`type`](https://docs.python.org/3/builtins/functions.html#type)[[`BaseException`](https://docs.python.org/3/builtins/exceptions.html#BaseException)], [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]) – Exception types to catch and exit cleanly on,
    returning the partial waveform.
  * **input_device_index** ([`int`](https://docs.python.org/3/builtins/functions.html#int) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Index (or name) of the input device to record from.
    None uses the default device.
  * **sample_width** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Sample width in bytes. One of `SUPPORTED_SAMPLE_WIDTHS`.
    The dtype of the returned samples follows from the format PyAudio
    opens the device with at that width, which is not the obvious
    mapping: 2 gives int16, 3 gives float64, and 4 gives **float32**
    (PyAudio captures 4-byte samples as float32, not as int32).
  * **chk_size** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Number of frames read from the device per chunk.
  * **stream_buffer_size_s** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – How many seconds of audio the underlying stream
    buffer keeps (i.e. how far into the past it can see).
  * **verbose** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to print status messages (also silences the input
    device discovery printout).
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  The recorded waveform (a list of samples), as processed by `egress`.

```pycon
>>> # Record 0.1 seconds of audio
>>> sample = record(0.1, verbose=False)
```
