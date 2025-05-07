"""
Recording and playback tools for audio data.
"""

from typing import Callable, Iterable, List, Literal, Optional, Tuple, Union
from itertools import islice
import soundfile as sf
from taped.base import BaseBufferItems, LiveWf
from taped.util import DFLT_SR, DFLT_SAMPLE_WIDTH, DFLT_CHK_SIZE, DFLT_STREAM_BUF_SIZE_S


def record(
    duration: Optional[float] = None,
    *,
    duration_unit: Literal["seconds", "samples", "minutes"] = "seconds",
    sr: int = DFLT_SR,
    egress: Optional[Union[str, Callable]] = None,
    ignore_exceptions: Tuple[Exception, ...] = (KeyboardInterrupt,),
    input_device_index: Optional[int] = None,
    sample_width: int = DFLT_SAMPLE_WIDTH,
    chk_size: int = DFLT_CHK_SIZE,
    stream_buffer_size_s: float = DFLT_STREAM_BUF_SIZE_S,
    verbose: bool = False,
) -> List:
    """Record audio and return waveform data.

    Args:
        duration: Length of recording. If None, records until interrupted.
        duration_unit: Unit for duration ('seconds', 'samples', or 'minutes').
        sr: Sample rate.
        egress: Function to process waveform before returning or filename to save to.
        ignore_exceptions: Exceptions to catch and exit cleanly.
        input_device_index: Index of input device to use.
        sample_width: Sample width in bytes.
        chk_size: Chunk size for reading audio.
        stream_buffer_size_s: Buffer size in seconds.
        verbose: Whether to print status messages.

    Returns:
        Recorded waveform data, potentially processed by egress function.

    >>> # Record 0.1 seconds of audio
    >>> sample = record(0.1, verbose=False)  # doctest: +SKIP
    """

    def _log(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    def _save_to_file(waveform, filename):
        """Save waveform to file and return the waveform."""
        sf.write(filename, waveform, samplerate=sr)
        return waveform

    def _convert_duration(value, unit):
        """Convert duration from given unit to number of samples."""
        if value is None:
            return None

        if unit == "seconds":
            return int(value * sr)
        elif unit == "minutes":
            return int(value * 60 * sr)
        elif unit == "samples":
            return int(value)
        else:
            raise ValueError(f"Unknown duration unit: {unit}")

    # Convert duration to samples
    n_samples = _convert_duration(duration, duration_unit)

    # Determine egress function
    if egress is None:
        _egress = lambda wf: wf
    elif isinstance(egress, str):
        _egress = lambda wf: _save_to_file(wf, egress)
    else:
        _egress = egress

    # Initialize empty waveform before trying anything
    waveform = []

    try:
        if input_device_index is None and sample_width == DFLT_SAMPLE_WIDTH:
            # Use the simpler LiveWf approach when possible
            _log("Starting recording with LiveWf...")
            with LiveWf(sr=sr) as live_wf:
                # Accumulate samples but be prepared for interruption
                if n_samples is not None:
                    live_iter = islice(live_wf, n_samples)
                else:
                    live_iter = live_wf

                # Collect samples one by one to ensure we keep what we have on interrupt
                for sample in live_iter:
                    waveform.append(sample)
        else:
            # Use the more configurable BaseBufferItems approach
            _log("Starting recording with BaseBufferItems...")
            buffer_items = BaseBufferItems(
                input_device_index=input_device_index,
                sr=sr,
                sample_width=sample_width,
                chk_size=chk_size,
                stream_buffer_size_s=stream_buffer_size_s,
            )

            count = 0

            with buffer_items:
                _log("Recording started (interrupt to stop)...")
                for item in buffer_items:
                    waveform.extend(item.data)
                    count += len(item.data)

                    if n_samples is not None and count >= n_samples:
                        # Trim to exact length if needed
                        waveform = waveform[:n_samples]
                        break

    except ignore_exceptions as e:
        _log(f"Recording stopped by {type(e).__name__}")
    except Exception as e:
        _log(f"Error during recording: {type(e).__name__}: {e}")
        raise

    _log(f"Recorded {len(waveform)} samples")
    return _egress(waveform)


# TODO: Deprecate record_some_sound
def record_some_sound(
    save_to_file,
    input_device_index=None,
    sr=DFLT_SR,
    sample_width=DFLT_SAMPLE_WIDTH,
    chk_size=DFLT_CHK_SIZE,
    stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S,
    verbose=True,
):
    def get_write_file_stream():
        if isinstance(save_to_file, str):
            return open(save_to_file, "wb")  # Shouldn't this be 'ab', for appends?
        else:
            return save_to_file  # assume it's already a stream

    def clog(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    buffer_items = BaseBufferItems(
        input_device_index=input_device_index,
        sr=sr,
        sample_width=sample_width,
        chk_size=chk_size,
        stream_buffer_size_s=stream_buffer_size_s,
    )
    with buffer_items:
        """keep open and save to file until stop event"""
        clog("starting the recording (you can KeyboardInterrupt at any point)...")
        with get_write_file_stream() as write_stream:
            for item in buffer_items:
                try:
                    write_stream.write(item.bytes)
                except KeyboardInterrupt:
                    clog("stopping the recording...")
                    break

    clog("Done.")
