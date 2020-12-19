from itertools import chain
from typing import Union, Optional
from collections import namedtuple
from dataclasses import dataclass

from stream2py.stream_buffer import StreamBuffer
from stream2py.sources.audio import PyAudioSourceReader
from taped.util import DFLT_SR, DFLT_SAMPLE_WIDTH, DFLT_CHK_SIZE, \
    DFLT_STREAM_BUF_SIZE_S, bytes_to_waveform, ensure_source_input_device_index

from itertools import islice
from creek import Creek

BufferItemOutput = namedtuple(typename='BufferItemOutput',
                              field_names=['timestamp', 'bytes', 'frame_count', 'time_info', 'status_flags'])


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
    input_device_index: Optional[int] = None
    sr: int = DFLT_SR
    sample_width: int = DFLT_SAMPLE_WIDTH
    chk_size: int = DFLT_CHK_SIZE
    stream_buffer_size_s: Union[float, int] = DFLT_STREAM_BUF_SIZE_S

    def __post_init__(self):
        self.input_device_index = ensure_source_input_device_index(self.input_device_index)
        seconds_per_read = self.chk_size / self.sr

        self.maxlen = int(self.stream_buffer_size_s / seconds_per_read)
        self.source_reader = PyAudioSourceReader(rate=self.sr,
                                                 width=self.sample_width,
                                                 unsigned=True,
                                                 input_device_index=self.input_device_index,
                                                 frames_per_buffer=self.chk_size)

        super().__init__(source_reader=self.source_reader, maxlen=self.maxlen)


class BufferItems(BaseBufferItems):
    def data_to_obj(self, data):
        return BufferItemOutput(*data)


class ByteChunks(BufferItems):
    def data_to_obj(self, data):
        return super().data_to_obj(data).bytes


# TODO: use more stable and flexible bytes_to_waveform
class WfChunks(ByteChunks):
    sample_width = 2

    def data_to_obj(self, data):
        data = super().data_to_obj(data)
        return bytes_to_waveform(data, sample_width=self.sample_width)


# TODO: use more stable and flexible bytes_to_waveform
class LiveWf(WfChunks):
    def post_iter(self, obj):
        return chain.from_iterable(obj)

    def __getitem__(self, item):
        if not isinstance(item, slice):
            item = slice(item, item + 1)  # to emulate usual list[i] interface
        return list(islice(self, item.start, item.stop, item.step))
