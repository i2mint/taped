from typing import Callable, Union, Optional
from functools import partial

from stream2py import SourceReader, BufferReader
from stream2py.stream_buffer import StreamBuffer
from audiostream2py import PyAudioSourceReader

from taped.util import bytes_to_waveform_old

DFLT_FRM_PER_BUFFER = 2048


class VisualizationStream(SourceReader):
    def __init__(self, mk_int16_array_gen: Callable, chk_to_viz: Callable):
        self.mk_int16_array_gen = mk_int16_array_gen
        self.chk_to_viz = chk_to_viz
        self._viz_gen = None

    def _mk_viz_gen(self):
        for i, a in enumerate(self.mk_int16_array_gen()):
            yield i, self.chk_to_viz(a)

    def open(self):
        """Setup data generator"""
        self._viz_gen = self._mk_viz_gen()

    def read(self):
        return next(self._viz_gen)

    def close(self):
        """Clean up if needed"""
        del self._viz_gen
        self._viz_gen = None

    @property
    def info(self):
        """Whatever info is useful to you
        StreamBuffer will record info right after open"""
        return dict(
            mk_int16_array_gen=str(self.mk_int16_array_gen),
            chk_to_viz=str(self.chk_to_viz),
        )

    def key(self, data):
        """Convert data to a sortable value that increases with each read.
        the enumerate index in this case
        """
        return data[0]


def device_info_by_index(index):
    try:
        return next(
            d for d in PyAudioSourceReader.list_device_info() if d["index"] == index
        )
    except StopIteration:
        raise ValueError(f"Not found for input device index: {index}")


def mk_pyaudio_to_int16_array_gen_callable(audio_reader: BufferReader):
    _info = audio_reader.source_reader_info
    specific_bytes_to_wf = partial(
        bytes_to_waveform_old,
        sr=_info["rate"],
        n_channels=_info["channels"],
        sample_width=_info["width"],
    )

    def mk_pyaudio_to_int16_array_gen():
        for timestamp, wf_bytes, frame_count, time_info, status_flags in audio_reader:
            yield specific_bytes_to_wf(wf_bytes)

    return mk_pyaudio_to_int16_array_gen


class AudioStreamBuffer(StreamBuffer):
    def __init__(
        self,
        *,
        buffer_size_seconds: Union[int, float] = 60.0,
        input_device_index=None,
        sr=44100,
        width=2,
        frames_per_buffer=DFLT_FRM_PER_BUFFER,
        sleep_time_on_read_none_s: Optional[Union[int, float]] = 0.05,
        auto_drop=True,
    ):
        _info = device_info_by_index(input_device_index)
        sr = sr or int(_info["defaultSampleRate"])
        channels = _info["maxInputChannels"]

        super().__init__(
            source_reader=PyAudioSourceReader(
                input_device_index=input_device_index,
                rate=sr,
                width=width,
                channels=channels,
                frames_per_buffer=frames_per_buffer,
                unsigned=False,
            ),
            maxlen=PyAudioSourceReader.audio_buffer_size_seconds_to_maxlen(
                buffer_size_seconds=buffer_size_seconds,
                rate=sr,
                frames_per_buffer=frames_per_buffer,
            ),
            sleep_time_on_read_none_s=sleep_time_on_read_none_s,
            auto_drop=auto_drop,
        )


# TODO: Reflect: Class versus function?
# def pyaudio_source_reader(
#         buffer_size_seconds: Union[int, float] = 60.0,
#         input_device_index: Optional[int] = None,
#         sr=44100,
#         width=2,
#         frames_per_buffer=2048,
#         sleep_time_on_read_none_s: Optional[Union[int, float]] = 0.05,
#         auto_drop=True
# ):
#     _info = device_info_by_index(input_device_index)
#     sr = sr or int(_info['defaultSampleRate'])
#     channels = _info['maxInputChannels']
#
#     return StreamBuffer(
#         source_reader=PyAudioSourceReader(input_device_index=input_device_index,
#                                           rate=sr,
#                                           width=width,
#                                           channels=channels,
#                                           frames_per_buffer=frames_per_buffer,
#                                           ),
#         maxlen=PyAudioSourceReader.audio_buffer_size_seconds_to_maxlen(
#             buffer_size_seconds=buffer_size_seconds,
#             rate=sr,
#             frames_per_buffer=frames_per_buffer,
#         ),
#         sleep_time_on_read_none_s=sleep_time_on_read_none_s,
#         auto_drop=auto_drop
#     )


def launch_audio_tracking(
    chk_callback: Callable,
    input_device_index: int,
    buffer_size_seconds=60,
    sr=None,
    width=2,
    frames_per_buffer=DFLT_FRM_PER_BUFFER,
):
    try:
        with AudioStreamBuffer(
            buffer_size_seconds=buffer_size_seconds,
            input_device_index=input_device_index,
            sr=sr,
            width=width,
            frames_per_buffer=frames_per_buffer,
            auto_drop=False,
            sleep_time_on_read_none_s=0.1,
        ) as audio_buffer:
            audio_reader = audio_buffer.mk_reader()

            with StreamBuffer(
                source_reader=VisualizationStream(
                    mk_int16_array_gen=mk_pyaudio_to_int16_array_gen_callable(
                        audio_reader
                    ),
                    chk_to_viz=chk_callback,
                ),
                maxlen=10,
            ) as viz_buffer:
                viz_reader = viz_buffer.mk_reader()

                yield from viz_reader
    except KeyboardInterrupt:
        print("KeyboardInterrupt: So I'm stopping the process")
