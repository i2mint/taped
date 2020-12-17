from io import BytesIO

import numpy as np
import soundfile as sf
from stream2py.sources.audio import PyAudioSourceReader

# TODO: (wish) service this will builtins only


# DFLT_INPUT_DEVICE_INDEX = find_a_default_input_device_index()
DFLT_SR = 44100
DFLT_N_CHANNELS = 1
DFLT_SAMPLE_WIDTH = 2
DFLT_CHK_SIZE = 1024 * 4
DFLT_STREAM_BUF_SIZE_S = 60
read_kwargs_for_sample_width = {
    2: dict(format='RAW', subtype='PCM_16', dtype='int16'),
    3: dict(format='RAW', subtype='PCM_24'),  # what dtype?
    4: dict(format='RAW', subtype='PCM_32', dtype='int32'),
}


def bytes_to_waveform(b, sr=DFLT_SR, n_channels=DFLT_N_CHANNELS, sample_width=DFLT_SAMPLE_WIDTH):
    """
    Convert raw bytes to a numpy array cast to dtype

    :param b: bytes
    :param sr: sample rate
    :param n_channels: number of channels
    :param sample_width: sample byte width [2, 3, 4]

    :return: numpy.array or ints
    """
    return sf.read(BytesIO(b), samplerate=sr, channels=n_channels, **read_kwargs_for_sample_width[sample_width])[0]


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
    subtype = read_kwargs_for_sample_width[sample_width]['subtype']
    sf.write(b, wf, samplerate=sr, format='RAW', subtype=subtype)
    b.seek(0)
    return b.read()


def bytes_to_waveform_old(b: bytes, sr: int, n_channels: int, sample_width: int, dtype='int16') -> np.array:
    """Convert raw bytes to a numpy array cast to dtype

    :param b: bytes
    :param sr: sample rate
    :param n_channels: number of channels
    :param sample_width: sample byte width [2, 3, 4]
    :param dtype: data type used by numpy, i.e. dtype=np.int16 is the same as dtype='int16'
    :return: numpy.array
    """
    sample_width_to_subtype = {
        2: 'PCM_16',
        3: 'PCM_24',
        4: 'PCM_32',
    }
    return sf.read(BytesIO(b), samplerate=sr, channels=n_channels, format='RAW',
                   subtype=sample_width_to_subtype[sample_width], dtype=dtype)[0]


def list_recording_device_index_names():
    """List (index, name) of available recording devices"""
    return sorted((d['index'], d['name']) for d in PyAudioSourceReader.list_device_info() if d['maxInputChannels'] > 0)


# TODO: Merge with find_a_device_index
def find_a_default_input_device_index(verbose=True):
    for index, name in list_recording_device_index_names():
        if 'microphone' in name.lower():
            if verbose:
                print(f"Found {name}. Will use it as the default input device. It's index is {index}")
            return index
    for index, name in list_recording_device_index_names():
        if 'mic' in name.lower():
            if verbose:
                print(f"Found {name}. Will use it as the default input device. It's index is {index}")
            return index


# TODO: Test and merge with find_a_default_input_device_index
def find_a_device_index(filt='microphone', dflt=None):
    if isinstance(filt, str):
        match_str = filt

        def filt(x):
            return match_str in x.get('name', match_str).lower()
    match = next(filter(filt, PyAudioSourceReader.list_device_info()), None)
    return (match is not None and match['index']) or dflt


def ensure_source_input_device_index(input_device_index=None):
    if input_device_index is None:
        input_device_index = find_a_default_input_device_index()
    if input_device_index is not None:
        if isinstance(input_device_index, int):
            return input_device_index
        elif isinstance(input_device_index, str):
            input_name = input_device_index
            for index, name in list_recording_device_index_names():
                if name == input_name:
                    return index
            raise ValueError(f"name not found in list of recording devices: {input_name}")
        elif isinstance(input_device_index, tuple) and len(input_device_index) == 2:
            index, name = input_device_index
            assert isinstance(index, int), f"expecting first element of tuple to be an int: {input_device_index}"
            assert isinstance(name, str), f"expecting second element of tuple to be a string: {input_device_index}"
            return index
        else:
            raise ValueError(f"couldn't resolve input_device_index: {input_device_index}")
    else:
        # TODO: Nicer way to print info (perhaps only relevant info, formated as table)
        print("Need a valid input_device_index. Calling live_audio_chks.list_device_info() to information about the "
              "devices I can detect:\n")
        for item in PyAudioSourceReader.list_device_info():
            print(item)
            print("")
        print("---> Look in the list above and choose an input_device_index (it's called index in the printout above) "
              "that seems to be right for you!")
        raise ValueError("Need a valid input_device_index")
