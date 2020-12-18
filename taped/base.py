from functools import partial
from itertools import chain
from contextlib import contextmanager
from typing import Iterable, Union, Callable, Optional

from stream2py.stream_buffer import StreamBuffer
from stream2py.sources.audio import PyAudioSourceReader
from taped.util import DFLT_SR, DFLT_SAMPLE_WIDTH, DFLT_CHK_SIZE, \
    DFLT_STREAM_BUF_SIZE_S, bytes_to_waveform, ensure_source_input_device_index

from itertools import islice
from dataclasses import dataclass
from creek import Creek


# TODO: revise wrapping so it shows this module and name, not some <locals> stuff
@Creek.wrap
@dataclass
class BufferItems(StreamBuffer):
    """A generator of live chunks of audio bytes taken from a stream sourced from specified microphone.

    :param input_device_index: Index of Input Device to use. Unspecified (or None) uses default device.
    :param sr: Specifies the desired sample rate (in Hz)
    :param sample_bytes: Sample width in bytes (1, 2, 3, or 4)
    :param sample_width: Specifies the number of frames per buffer.
    :param stream_buffer_size_s: How many seconds of data to keep in the buffer (i.e. how far in the past you can see)
    """
    input_device_index: Optional[int] = None
    sr: int = DFLT_SR
    sample_width: int = DFLT_SAMPLE_WIDTH
    chk_size: int = DFLT_CHK_SIZE
    stream_buffer_size_s: Union[float, int] = DFLT_STREAM_BUF_SIZE_S

    def __post_init__(self):
        self.input_device_index = ensure_source_input_device_index(self.input_device_index)
        seconds_per_read = self.chk_size / self.sr

        self.maxlen = int(self.stream_buffer_size_s / seconds_per_read)
        self.source_reader = PyAudioSourceReader(rate=self.sr, width=self.sample_width,
                                                 unsigned=True,
                                                 input_device_index=self.input_device_index,
                                                 frames_per_buffer=self.chk_size)

        super().__init__(source_reader=self.source_reader, maxlen=self.maxlen)

    # # Adding these so they show up in tab-completion and dir TODO: Make Creek.wrap do that automatically.
    # start = StreamBuffer.start
    # stop = StreamBuffer.stop


class ByteChunks(BufferItems):
    def data_to_obj(self, data):
        return data[1]


# TODO: chain from ByteChunks instead of BufferItems
# TODO: use more stable and flexible bytes_to_waveform
class WfChunks(ByteChunks):
    sample_width = 2

    def data_to_obj(self, data):
        data = super().data_to_obj(data)
        return bytes_to_waveform(data, sample_width=self.sample_width)


# TODO: chain from ByteChunks instead of BufferItems
# TODO: use more stable and flexible bytes_to_waveform
class LiveWf(WfChunks):
    def post_iter(self, obj):
        return chain.from_iterable(obj)

    def __getitem__(self, item):
        if not isinstance(item, slice):
            item = slice(item, item + 1)  # to emulate usual list[i] interface
        return list(islice(self, item.start, item.stop, item.step))


def simple_chunker(a: Iterable,
                   chk_size: int):
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


def rechunker(chks: Iterable[Iterable],
              chunker: Union[Callable, int]):
    """Generate fixed sized non-overlapping chunks of an iterable of chunks.
    That is, the rechunker applies a chunker to an unraveled stream of chunks,
    or more generally of iterables since they can be of varied sizes and types.

    >>> from functools import partial
    >>> chunker = partial(simple_chunker, chk_size=3)
    >>> chks = [[0], (1, 2, 3), [4, 5], iter((6, 7))]  # iterable of (different types of) iterables
    >>> list(rechunker(chks, chunker))
    [(0, 1, 2), (3, 4, 5)]

    """
    if isinstance(chunker, int):  # if chunker is an int, take it to be a the chk_size of a simple_chunker
        chk_size = chunker
        chunker = partial(simple_chunker, chk_size)
    yield from chunker(chain.from_iterable(chks))


def record_some_sound(save_to_file,
                      input_device_index=None,
                      sr=DFLT_SR,
                      sample_width=DFLT_SAMPLE_WIDTH,
                      chk_size=DFLT_CHK_SIZE,
                      stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S, verbose=True,
                      ):
    def get_write_file_stream():
        if isinstance(save_to_file, str):
            return open(save_to_file, 'wb')
        else:
            return save_to_file  # assume it's already a stream

    def clog(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    seconds_per_read = chk_size / sr
    maxlen = int(stream_buffer_size_s / seconds_per_read)

    with LiveWf(input_device_index=input_device_index, maxlen=maxlen) as stream_buffer:
        """keep open and save to file until stop event"""
        clog("starting the recording (you can KeyboardInterrupt at any point)...")
        with get_write_file_stream() as write_stream:
            while True:
                try:
                    chk = source_reader.read()
                    print(type(chk), len(chk))
                except KeyboardInterrupt:
                    clog("stopping the recording...")
                    break


    source_reader = PyAudioSourceReader(rate=sr, width=sample_width, unsigned=True,
                                        input_device_index=input_device_index,
                                        frames_per_buffer=chk_size)

    # with StreamBuffer(source_reader=source_reader, maxlen=maxlen) as stream_buffer:
    #     """keep open and save to file until stop event"""
    #     clog("starting the recording (you can KeyboardInterrupt at any point)...")
    #     with get_write_file_stream() as write_stream:
    #         while True:
    #             try:
    #                 chk = source_reader.read()
    #                 print(type(chk), len(chk))
    #             except KeyboardInterrupt:
    #                 clog("stopping the recording...")
    #                 break

    clog('Done.')
