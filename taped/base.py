"""
Base of taped objects

This module provides classes and functions for handling audio streams and buffers.
It includes tools for capturing live audio from microphones, buffering audio data,
and converting between different audio representations.

The layers, from the mic outwards:

- ``BaseBufferItems``: raw ``audiostream2py.AudioSegment`` objects off the device.
- ``BufferItems``: those segments as :class:`BufferItemOutput` named tuples --
  read that class's docstring for what each of the (PortAudio-inherited, and
  partly misleading) field names actually means today.
- ``ByteChunks``: just the PCM bytes of each chunk.
- ``WfChunks``: those bytes decoded into numerical waveform chunks.
- ``LiveWf``: the ``WfChunks`` flattened into one continuous live sample stream.

Examples
--------

"""

from itertools import chain
from typing import NamedTuple, Union, Optional
from dataclasses import dataclass

from stream2py.stream_buffer import StreamBuffer
from audiostream2py import PyAudioSourceReader, AudioSegment
from taped.util import (
    DFLT_SR,
    DFLT_SAMPLE_WIDTH,
    DFLT_CHK_SIZE,
    DFLT_STREAM_BUF_SIZE_S,
    bytes_to_waveform,
    ensure_source_input_device_index,
)

from itertools import islice
from creek import Creek


class BufferItemOutput(NamedTuple):
    """One item of a ``BufferItems`` stream: a chunk of mic bytes plus its metadata.

    The field names come from PortAudio (through PyAudio, then ``audiostream2py``),
    but two of them no longer mean what the PortAudio names suggest -- see
    ``time_info`` below. What follows is the *current* meaning of each field, as
    produced by :func:`audio_segment_to_buffer_item_output` from an
    ``audiostream2py.AudioSegment``.

    Fields
    ------
    timestamp:
        The ``AudioSegment.start_date``: when the *first* frame of this chunk was
        captured, as a number of **microseconds** since the epoch (not seconds,
        and not a PortAudio clock reading). This is the field to use to place a
        chunk on a wall-clock timeline. It is an ``int`` *or* a ``float``:
        ``AudioSegment`` declares ``start_date: int | float``, and live capture
        normally yields floats, because most chunk dates are interpolated from
        the frame rate rather than read off the host clock. Do not test it with
        ``isinstance(..., int)``, and do not assume integral microsecond
        arithmetic.
    bytes:
        The ``AudioSegment.waveform``: the raw PCM bytes of the chunk, exactly as
        the device produced them. Interpreting them as numbers needs the sample
        width and channel count the stream was opened with -- which is what
        ``ByteChunks``/``WfChunks`` do for you (see ``taped.util.bytes_to_waveform``).
    frame_count:
        Number of frames (samples per channel) in this chunk. With the default
        ``chk_size`` of 4096 and a sample width of 2, ``len(bytes) == 8192``, i.e.
        ``len(bytes) == frame_count * sample_width * n_channels``.
    time_info:
        **Not a PortAudio time-info dict.** This is the ``AudioSegment.end_date``:
        a single number, in the same microsecond-epoch unit (and of the same
        ``int | float`` type) as ``timestamp``, marking the end of the chunk. So
        ``time_info - timestamp`` is the chunk's duration in microseconds --
        itself often fractional -- and it is *not* subscriptable. PortAudio's
        ``PaStreamCallbackTimeInfo`` dict (``current_time``,
        ``input_buffer_adc_time``, ``output_buffer_dac_time``) used to land here
        in older versions; ``audiostream2py`` no longer surfaces it. See the
        "Historical" note below for what those keys meant.
    status_flags:
        A PortAudio status bitfield reporting stream health for this chunk.
        ``0`` means no error. Decode it with ``audiostream2py.PaStatusFlags``,
        an ``IntFlag`` whose members are ``paNoError``, ``paInputUnderflow``,
        ``paInputOverflow``, ``paOutputUnderflow``, ``paOutputOverflow``,
        ``paPrimingOutput`` and ``hostTimeSync``. For a worked example of acting
        on it (starting a new file whenever a chunk reports an error), see
        ``taped/examples/record_audio_to_files.py``.

    Historical: the PortAudio ``PaStreamCallbackTimeInfo`` fields
    -------------------------------------------------------------
    These are documented here because the ``time_info`` *name* comes from them,
    and older ``taped`` output (and the README examples that recorded it) shows
    them. They are **no longer available** through this class. All three are
    ``PaTime`` values on PortAudio's own stream clock -- seconds, monotonic-ish,
    with an arbitrary origin -- and so are not comparable with ``timestamp``.
    From http://portaudio.com/docs/v19-doxydocs/structPaStreamCallbackTimeInfo.html:

    - ``currentTime`` (``current_time``): the time when the stream callback was
      invoked.
    - ``inputBufferAdcTime`` (``input_buffer_adc_time``): the time when the first
      sample of the input buffer was captured at the ADC input.
    - ``outputBufferDacTime`` (``output_buffer_dac_time``): the time when the
      first sample of the output buffer will output the DAC. (Always ``0.0`` for
      an input-only stream, which is what ``taped`` opens.)

    Being a ``NamedTuple``, an item is both a 5-tuple and an attribute-access
    object, and it carries the usual ``_fields``/``_asdict`` helpers:

    >>> item = BufferItemOutput(1608336556178995, b'\\x09\\x00', 1, 1608336556271874, 0)
    >>> item.timestamp
    1608336556178995
    >>> item[1]
    b'\\t\\x00'
    >>> item.time_info - item.timestamp  # chunk duration, in microseconds
    92879
    >>> item._fields
    ('timestamp', 'bytes', 'frame_count', 'time_info', 'status_flags')

    The dates above are whole numbers only because they were written that way.
    Off a live device they usually are not, and neither is the duration:

    >>> item = BufferItemOutput(1608336556178995.2, b'\\x09\\x00', 1, 1608336556271875.0, 0)
    >>> item.time_info - item.timestamp
    92879.75
    """

    timestamp: int | float
    bytes: bytes
    frame_count: int
    time_info: int | float
    status_flags: int


def audio_segment_to_buffer_item_output(segment: AudioSegment) -> BufferItemOutput:
    """Convert an ``audiostream2py.AudioSegment`` to a :class:`BufferItemOutput`.

    Note ``time_info=segment.end_date`` -- see :class:`BufferItemOutput` for why
    that field does not hold a PortAudio time-info dict.
    """
    return BufferItemOutput(
        timestamp=segment.start_date,
        bytes=segment.waveform,
        frame_count=segment.frame_count,
        time_info=segment.end_date,
        status_flags=segment.status_flags,
    )


@Creek.wrap
@dataclass
class BaseBufferItems(StreamBuffer):
    """A generator of live chunks of audio bytes taken from a stream sourced from specified microphone.

    :param input_device_index: Index of Input Device to use. Unspecified (or None) uses default device.
    :param sr: Specifies the desired sample rate (in Hz)
    :param sample_bytes: Sample width in bytes (1, 2, 3, or 4)
    :param sample_width: Specifies the number of frames per buffer.
    :param stream_buffer_size_s: How many seconds of data to keep in the buffer (i.e. how far in the past you can see)
    """

    input_device_index: int | str | None = None
    sr: int = DFLT_SR
    sample_width: int = DFLT_SAMPLE_WIDTH
    chk_size: int = DFLT_CHK_SIZE
    stream_buffer_size_s: float | int = DFLT_STREAM_BUF_SIZE_S
    verbose: bool = False

    def __post_init__(self):
        self.input_device_index = ensure_source_input_device_index(
            self.input_device_index, verbose=self.verbose
        )
        seconds_per_read = self.chk_size / self.sr

        self.maxlen = int(self.stream_buffer_size_s / seconds_per_read)
        self.source_reader = PyAudioSourceReader(
            rate=self.sr,
            width=self.sample_width,
            unsigned=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chk_size,
        )

        super().__init__(source_reader=self.source_reader, maxlen=self.maxlen)


class BufferItems(BaseBufferItems):
    def data_to_obj(self, data):
        return audio_segment_to_buffer_item_output(data)


class ByteChunks(BufferItems):
    def data_to_obj(self, data):
        return super().data_to_obj(data).bytes


# TODO: use more stable and flexible bytes_to_waveform
class WfChunks(ByteChunks):
    """Decode the byte chunks of ``ByteChunks`` into numerical waveform chunks.

    The width used to decode is the ``sample_width`` the stream was actually
    opened with. It is read through ``Creek``'s delegation to the wrapped
    stream, deliberately: a ``sample_width`` class attribute here would shadow
    the constructed value, so a ``WfChunks(sample_width=4)`` would capture
    32-bit frames and then decode them as 16-bit ones.
    """

    def data_to_obj(self, data):
        data = super().data_to_obj(data)
        return bytes_to_waveform(data, sample_width=self.sample_width)


# TODO: use more stable and flexible bytes_to_waveform
class LiveWf(WfChunks):
    def post_iter(self, obj):
        return chain.from_iterable(obj)

    @property
    def available_samples_in_buffer(self):
        """Returns the actual max number of samples available.
        This is maxlen * chk_size when buffer is full.
        """

        return len(self.source_buffer._buffer) * self.chk_size

    def __getitem__(self, item):
        if not isinstance(item, slice):
            item = slice(item, item + 1)  # to emulate usual list[i] interface
        item = positive_slice_version(item, self.available_samples_in_buffer)
        return list(islice(self, item.start, item.stop, item.step))


def positive_slice_version(slice_, sliced_obj_len):
    """Returns a slice where negative start and stops are replaced with their positive correspondence.
    This is because `itertools.islice` doesn't accept negative entries, so we need to tell it
    explicitly what we mean by -3 (we mean sliced_obj_len - 3).

    >>> positive_slice_version(slice(-7, -1, 3), 10)
    slice(3, 9, 3)
    >>> positive_slice_version(slice(2, -2), 7)
    slice(2, 5, None)
    """

    def positivize(x):
        if x is not None and x < 0:
            x += sliced_obj_len
        return x
        # return x if x is None or x > 0 else 0

    return slice(positivize(slice_.start), positivize(slice_.stop), slice_.step)
