from functools import partial
from itertools import chain
from contextlib import contextmanager

from stream2py import StreamBuffer
from stream2py.sources.audio import PyAudioSourceReader
from taped.util import DFLT_SR, DFLT_N_CHANNELS, DFLT_SAMPLE_WIDTH, DFLT_CHK_SIZE, \
    DFLT_STREAM_BUF_SIZE_S, audio_pokes_version_of_bytes_to_waveform, ensure_source_input_device_index


@contextmanager
def live_audio_chks(input_device_index=None, sr=DFLT_SR, sample_width=DFLT_SAMPLE_WIDTH, n_channels=DFLT_N_CHANNELS,
                    chk_size=DFLT_CHK_SIZE, stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S):
    """A generator of live chunks of audio bytes taken from a stream sourced from specified microphone.

    :param input_device_index: Index of Input Device to use. Unspecified (or None) uses default device.
    :param sr: Specifies the desired sample rate (in Hz)
    :param sample_bytes: Sample width in bytes (1, 2, 3, or 4)
    :param n_channels: The desired number of input channels. Ignored if input_device is not specified (or None).
    :param sample_width: Specifies the number of frames per buffer.
    :param stream_buffer_size_s: How many seconds of data to keep in the buffer (i.e. how far in the past you can see)
    """
    input_device_index = ensure_source_input_device_index(input_device_index)

    seconds_per_read = chk_size / sr

    maxlen = int(stream_buffer_size_s / seconds_per_read)
    # print(maxlen)
    source_reader = PyAudioSourceReader(rate=sr, width=sample_width, channels=n_channels, unsigned=True,
                                        input_device_index=input_device_index,
                                        frames_per_buffer=chk_size)

    _bytes_to_waveform = partial(audio_pokes_version_of_bytes_to_waveform, sr=sr, n_channels=n_channels,
                                 sample_width=sample_width)
    with StreamBuffer(source_reader=source_reader, maxlen=maxlen) as stream_buffer:
        """keep open and save to file until stop event"""
        yield iter(stream_buffer)


live_audio_chks.list_device_info = PyAudioSourceReader.list_device_info


# TODO: live_wf_ctx and live_wf: Lot's of repeated code. Address this.
@contextmanager
def live_wf_ctx(input_device_index=None, sr=DFLT_SR, sample_width=DFLT_SAMPLE_WIDTH, n_channels=DFLT_N_CHANNELS,
                chk_size=DFLT_CHK_SIZE, stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S):
    """A context manager providing a generator of live waveform sample values taken from a stream sourced
    from specified microphone.

    :param input_device_index: Index of Input Device to use. Unspecified (or None) uses default device.
    :param sr: Specifies the desired sample rate (in Hz)
    :param sample_width: Sample width in bytes (1, 2, 3, or 4)
    :param n_channels: The desired number of input channels. Ignored if input_device is not specified (or None).
    :param stream_buffer_size_s: How many seconds of data to keep in the buffer (i.e. how far in the past you can see)

    >>> from time import sleep
    >>> from itertools import islice
    >>> # enter the id of your microphone and get a live waveform source!
    >>> # (if None, will try to figure it out)
    >>> with live_wf_ctx(input_device_index=None) as wf_gen:
    ...
    ...     # Now wait a bit, say some silly things, then ask for a few samples...
    ...     sleep(1.1)
    ...     wf = list(islice(wf_gen, 0, 44100 * 1))
    >>> # and now listen to that wf and be embarrassed...
    >>> # ... or just look at the size (less fun though)
    >>> len(wf)
    44100
    """
    with live_audio_chks(input_device_index=input_device_index,
                         sr=sr, sample_width=sample_width, n_channels=n_channels,
                         chk_size=chk_size,
                         stream_buffer_size_s=stream_buffer_size_s) as live_audio_chunks:
        _bytes_to_waveform = partial(audio_pokes_version_of_bytes_to_waveform, sr=sr, n_channels=n_channels,
                                     sample_width=sample_width)
        yield chain.from_iterable(map(lambda x: _bytes_to_waveform(x[1]), live_audio_chunks))
    live_audio_chunks.close()


def live_wf(input_device_index=None, sr=DFLT_SR, sample_width=DFLT_SAMPLE_WIDTH, n_channels=DFLT_N_CHANNELS,
            chk_size=DFLT_CHK_SIZE, stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S):
    """A generator of live waveform sample values taken from a stream sourced from specified microphone.

    :param input_device_index: Index of Input Device to use. Unspecified (or None) uses default device.
    :param sr: Specifies the desired sample rate (in Hz)
    :param sample_width: Sample width in bytes (1, 2, 3, or 4)
    :param n_channels: The desired number of input channels. Ignored if input_device is not specified (or None).
    :param stream_buffer_size_s: How many seconds of data to keep in the buffer (i.e. how far in the past you can see)

    >>> from time import sleep
    >>> from itertools import islice
    >>> # enter the id of your microphone and get a live waveform source!
    >>> # (if None, will try to figure it out)
    >>> wf_gen = live_wf(input_device_index=None)
    >>>
    >>> # Now wait a bit, say some silly things, then ask for a few samples...
    >>> sleep(1.2)
    >>> wf = list(islice(wf_gen, 0, 44100 * 1))
    >>> # and now listen to that wf and be embarrassed...
    >>> # ... or just look at the size (less fun though)
    >>> len(wf)
    44100

    Don't forget to close! (or use live_wf_ctx context manager).
    >>> wf_gen.close()

    After wf_gen is closed, you can still ask it for data.
    It just won't give you any.
    >>> wf = list(islice(wf_gen, 0, 44100 * 1))
    >>> len(wf)
    0

    Here wf_gen is a generator, so closing means: https://docs.python.org/2.5/whatsnew/pep-342.html
    """
    # TODO: Find a way to copy from containing function's signature and calling LiveAudioChunks with that
    with live_wf_ctx(input_device_index=input_device_index,
                     sr=sr, sample_width=sample_width, n_channels=n_channels,
                     chk_size=chk_size,
                     stream_buffer_size_s=stream_buffer_size_s) as live_wf:
        yield from live_wf


live_wf.list_device_info = PyAudioSourceReader.list_device_info


def simple_chunker(a, chk_size: int):
    return zip(*([iter(a)] * chk_size))


def rechunker(chks, chk_size):
    yield from simple_chunker(chain.from_iterable(chks), chk_size)


def record_some_sound(save_to_file,
                      input_device_index=None, sr=DFLT_SR, sample_width=DFLT_SAMPLE_WIDTH, n_channels=DFLT_N_CHANNELS,
                      chk_size=DFLT_CHK_SIZE, stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S, verbose=True,
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

    source_reader = PyAudioSourceReader(rate=sr, width=sample_width, channels=n_channels, unsigned=True,
                                        input_device_index=input_device_index,
                                        frames_per_buffer=chk_size)

    with StreamBuffer(source_reader=source_reader, maxlen=maxlen) as stream_buffer:
        """keep open and save to file until stop event"""
        clog("starting the recording...")
        with get_write_file_stream() as write_stream:
            while True:
                try:
                    chk = source_reader.read()
                    print(type(chk), len(chk))
                except KeyboardInterrupt:
                    clog("stopping the recording...")
                    break

    clog('Done.')
