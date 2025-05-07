"""
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


>>> # Example of working with audio data slices: Create a live waveform reader
>>> wf = LiveWf()  # doctest: +SKIP
>>> # Get the last 1 second of audio (assuming 44100 sample rate)
>>> last_second = wf[-44100:]  # doctest: +SKIP
>>> # Will be up to 44100 samples:
>>> len(last_second)  # doctest: +SKIP
>>>
>>> # Example of converting between formats
>>> from audiostream2py import AudioSegment
>>> # Create a sample AudioSegment (this is just an example structure)
>>> segment = AudioSegment(  # doctest: +SKIP
...     waveform=b'sample audio data',
...     start_date=1234567890.0,
...     end_date=1234567891.0,
...     frame_count=1000,
...     status_flags=0
... )
>>> # Convert to BufferItemOutput
>>> buffer_item = audio_segment_to_buffer_item_output(segment)  # doctest: +SKIP
>>> buffer_item.timestamp == 1234567890.0  # doctest: +SKIP
True
>>> buffer_item.bytes == b'sample audio data'  # doctest: +SKIP
True
>>>
>>> # Example of positive_slice_version function
>>> positive_slice_version(slice(-5, None), 10)  # doctest: +SKIP
slice(5, None, None)
>>> positive_slice_version(slice(3, 8, 2), 10)  # doctest: +SKIP
slice(3, 8, 2)

"""

from functools import partial
import functools
from io import BytesIO
from itertools import chain
from typing import Iterable, Union, Callable, List, Tuple

import numpy as np
import soundfile as sf
from audiostream2py import PyAudioSourceReader, get_input_device_index

# TODO: (wish) service this will builtins only


# DFLT_INPUT_DEVICE_INDEX = find_a_default_input_device_index()
DFLT_SR = 44100
DFLT_N_CHANNELS = 1
DFLT_SAMPLE_WIDTH = 2
DFLT_CHK_SIZE = 1024 * 4
DFLT_STREAM_BUF_SIZE_S = 60
read_kwargs_for_sample_width = {
    2: dict(format="RAW", subtype="PCM_16", dtype="int16"),
    3: dict(format="RAW", subtype="PCM_24"),  # what dtype?
    4: dict(format="RAW", subtype="PCM_32", dtype="int32"),
}

# monkey patching WRAPPER_ASSIGNMENTS to get "proper" wrapping (adding defaults and kwdefaults

wrapper_assignments = (
    "__module__",
    "__name__",
    "__qualname__",
    "__doc__",
    "__annotations__",
    "__defaults__",
    "__kwdefaults__",
)

update_wrapper = functools.update_wrapper
update_wrapper.__defaults__ = (functools.WRAPPER_ASSIGNMENTS, functools.WRAPPER_UPDATES)
wraps = functools.wraps
wraps.__defaults__ = (functools.WRAPPER_ASSIGNMENTS, functools.WRAPPER_UPDATES)


def bytes_to_waveform(
    b, sr=DFLT_SR, n_channels=DFLT_N_CHANNELS, sample_width=DFLT_SAMPLE_WIDTH
):
    """
    Convert raw bytes to a numpy array cast to dtype

    :param b: bytes
    :param sr: sample rate
    :param n_channels: number of channels
    :param sample_width: sample byte width [2, 3, 4]

    :return: numpy.array or ints
    """
    return sf.read(
        BytesIO(b),
        samplerate=sr,
        channels=n_channels,
        **read_kwargs_for_sample_width[sample_width],
    )[0]


def waveform_to_bytes(wf, sr=DFLT_SR, sample_width=DFLT_SAMPLE_WIDTH):
    """
    Convert raw bytes to a numpy array cast to dtype

    :param wf: iterable of ints
    :param sr: sample rate
    :param n_channels: number of channels
    :param sample_width: sample byte width [2, 3, 4]

    :return: bytes
    """
    b = BytesIO()
    subtype = read_kwargs_for_sample_width[sample_width]["subtype"]
    sf.write(b, wf, samplerate=sr, format="RAW", subtype=subtype)
    b.seek(0)
    return b.read()


def bytes_to_waveform_old(
    b: bytes, sr: int, n_channels: int, sample_width: int, dtype="int16"
) -> np.array:
    """Convert raw bytes to a numpy array cast to dtype

    :param b: bytes
    :param sr: sample rate
    :param n_channels: number of channels
    :param sample_width: sample byte width [2, 3, 4]
    :param dtype: data type used by numpy, i.e. dtype=np.int16 is the same as dtype='int16'
    :return: numpy.array
    """
    sample_width_to_subtype = {
        2: "PCM_16",
        3: "PCM_24",
        4: "PCM_32",
    }
    return sf.read(
        BytesIO(b),
        samplerate=sr,
        channels=n_channels,
        format="RAW",
        subtype=sample_width_to_subtype[sample_width],
        dtype=dtype,
    )[0]


def list_recording_device_index_names() -> List[Tuple[int, str]]:
    """List (index, name) of available recording devices"""
    return sorted(
        (d["index"], d["name"])
        for d in PyAudioSourceReader.list_device_info()
        if d["maxInputChannels"] > 0
    )


def find_a_default_input_device_index(verbose=True):
    return get_input_device_index(verbose=verbose)


def find_a_device_index(filt="microphone", dflt=None):
    if isinstance(filt, str):
        match_str = filt

        def filt(x):
            return match_str in x.get("name", match_str).lower()

    match = next(filter(filt, PyAudioSourceReader.list_device_info()), None)
    return (match is not None and match["index"]) or dflt


def ensure_source_input_device_index(input_device_index=None, verbose=True):
    if input_device_index is None:
        input_device_index = find_a_default_input_device_index(verbose=verbose)
    if input_device_index is not None:
        if isinstance(input_device_index, int):
            return input_device_index
        elif isinstance(input_device_index, str):
            input_name = input_device_index
            for index, name in list_recording_device_index_names():
                if name == input_name:
                    return index
            raise ValueError(
                f"name not found in list of recording devices: {input_name}"
            )
        elif isinstance(input_device_index, tuple) and len(input_device_index) == 2:
            index, name = input_device_index
            assert isinstance(
                index, int
            ), f"expecting first element of tuple to be an int: {input_device_index}"
            assert isinstance(
                name, str
            ), f"expecting second element of tuple to be a string: {input_device_index}"
            return index
        else:
            raise ValueError(
                f"couldn't resolve input_device_index: {input_device_index}"
            )
    else:
        # TODO: Nicer way to print info (perhaps only relevant info, formated as table)
        print(
            "Need a valid input_device_index. Calling live_audio_chks.list_device_info() to information about the "
            "devices I can detect:\n"
        )
        for item in PyAudioSourceReader.list_device_info():
            print(item)
            print("")
        print(
            "---> Look in the list above and choose an input_device_index (it's called index in the printout above) "
            "that seems to be right for you!"
        )
        raise ValueError("Need a valid input_device_index")


def simple_chunker(a: Iterable, chk_size: int):
    """Generate fixed sized non-overlapping chunks of an iterable ``a``.

    >>> list(simple_chunker(range(7), 3))
    [(0, 1, 2), (3, 4, 5)]

    Most of the time, you'll want to fix the parameters of the chunker like this:

    >>> from functools import partial
    >>> chunker = partial(simple_chunker, chk_size=3)
    >>> list(chunker(range(7)))
    [(0, 1, 2), (3, 4, 5)]

    Note, the type of the chunks is always tuples, but you can easily change that using ``map``.
    For example, to change the type to be list:

    >>> list(map(list, chunker(range(7))))
    [[0, 1, 2], [3, 4, 5]]

    >>> a = range(6)
    >>> list(simple_chunker(a, 3))
    [(0, 1, 2), (3, 4, 5)]
    >>> list(simple_chunker(a, 2))
    [(0, 1), (2, 3), (4, 5)]
    >>> list(simple_chunker(a, 1))
    [(0,), (1,), (2,), (3,), (4,), (5,)]

    """
    return zip(*([iter(a)] * chk_size))


def rechunker(chks: Iterable[Iterable], chunker: Union[Callable, int]):
    """Generate fixed sized non-overlapping chunks of an iterable of chunks.
    That is, the rechunker applies a chunker to an unraveled stream of chunks,
    or more generally of iterables since they can be of varied sizes and types.

    >>> from functools import partial
    >>> chunker = partial(simple_chunker, chk_size=3)
    >>> chks = [[0], (1, 2, 3), [4, 5], iter((6, 7))]  # iterable of (different types of) iterables
    >>> list(rechunker(chks, chunker))
    [(0, 1, 2), (3, 4, 5)]

    """
    if isinstance(
        chunker, int
    ):  # if chunker is an int, take it to be a the chk_size of a simple_chunker
        chk_size = chunker
        chunker = partial(simple_chunker, chk_size=chk_size)
    yield from chunker(chain.from_iterable(chks))


from itertools import count, islice


# TODO: Restricted by integer: Need float and decimal versions
def chunk_indices(chk_size, chk_step=None, start_idx=0, end_idx=None):
    """Yields upper and integer lower bounds of integer size and step chunks.

    >>> it = chunk_indices(5)
    >>> next(it)
    (0, 5)
    >>> next(it)
    (5, 10)
    >>> list(chunk_indices(chk_size=5, chk_step=3, start_idx=0, end_idx=15))
    [(0, 5), (3, 8), (6, 11), (9, 14)]
    """
    chk_step = chk_step or chk_size
    bt_start = start_idx
    tt_start = bt_start + chk_size
    chk_index_iterator = zip(count(start_idx, chk_step), count(tt_start, chk_step))
    if end_idx is None:
        # iterate forever
        return chk_index_iterator
    else:  # end_idx (the maximum that tt_start should have) is not None
        # so we want a finite number of iterators, so we computer the num of iterations
        n_iterations = 1 + int((end_idx - bt_start - chk_size) / chk_step)  # verify!
        return islice(chk_index_iterator, n_iterations)
