"""
Recording and playback tools for audio data.

The main entry point is :func:`record`, a one-call interface over the layered
``BufferItems -> ByteChunks -> WfChunks -> LiveWf`` stack of :mod:`taped.base`.
It records from a microphone and hands you back a waveform (a list of samples),
optionally bounded by a duration, optionally post-processed by an ``egress``.
"""

from typing import Any, Literal
from collections.abc import Callable
from itertools import islice

import soundfile as sf

from taped.base import BufferItems, LiveWf
from taped.util import (
    DFLT_SR,
    DFLT_SAMPLE_WIDTH,
    DFLT_CHK_SIZE,
    DFLT_STREAM_BUF_SIZE_S,
    read_kwargs_for_sample_width,
)

DurationUnit = Literal["seconds", "samples", "minutes"]

SECONDS_PER_MINUTE = 60

#: Sample widths (in bytes) that work end to end: the device can be opened at
#: that width *and* the decoder reads back what the device then sends.
#:
#: Two authorities have a say, and only one of them lives in this package: PyAudio
#: picks the *capture* format from the width, and
#: ``taped.util.read_kwargs_for_sample_width`` says how to *decode* the result.
#: A width only belongs here when the two agree -- which is why this is derived
#: from the decode table but not defined by it alone. See
#: ``taped.util.subtype_for_sample_width`` for the capture side, and
#: ``test_decode_subtype_matches_the_captured_format_at_every_width`` for the
#: check that keeps them honest.
SUPPORTED_SAMPLE_WIDTHS = tuple(sorted(read_kwargs_for_sample_width))

#: Conversion of a ``(duration, sample_rate)`` pair to a number of samples, one
#: entry per supported ``duration_unit``. Adding a unit means adding an entry
#: here -- no branching in ``record`` to edit.
DURATION_UNIT_TO_N_SAMPLES: dict[str, Callable[[float, int], int]] = {
    "samples": lambda duration, sr: int(duration),
    "seconds": lambda duration, sr: int(duration * sr),
    "minutes": lambda duration, sr: int(duration * SECONDS_PER_MINUTE * sr),
}


def _duration_to_n_samples(
    duration: float | None, duration_unit: DurationUnit, sr: int
) -> int | None:
    """Number of samples a ``duration`` of ``duration_unit`` amounts to at ``sr``.

    ``None`` means "unbounded" and is passed straight through.

    >>> _duration_to_n_samples(None, 'seconds', 44100) is None
    True
    >>> _duration_to_n_samples(2, 'seconds', 100)
    200
    >>> _duration_to_n_samples(0.5, 'minutes', 100)
    3000
    >>> _duration_to_n_samples(7, 'samples', 44100)
    7
    >>> _duration_to_n_samples(1, 'fortnights', 44100)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: Unknown duration unit: 'fortnights'. Expected one of: ...
    """
    if duration is None:
        return None
    to_n_samples = DURATION_UNIT_TO_N_SAMPLES.get(duration_unit)
    if to_n_samples is None:
        expected = ", ".join(map(repr, DURATION_UNIT_TO_N_SAMPLES))
        raise ValueError(
            f"Unknown duration unit: {duration_unit!r}. Expected one of: {expected}"
        )
    return to_n_samples(duration, sr)


def _resolve_egress(egress: str | Callable | None, *, sr: int) -> Callable:
    """Make a waveform-to-output function out of the ``egress`` argument.

    ``None`` gives the identity, a callable is used as is, and a string is taken
    to be a filepath to save the waveform to (the waveform itself is still what
    is returned, so that saving is a side effect and not a substitution).

    >>> _resolve_egress(None, sr=44100)([1, 2, 3])
    [1, 2, 3]
    >>> _resolve_egress(sum, sr=44100)([1, 2, 3])
    6
    """
    if egress is None:
        return lambda wf: wf
    if isinstance(egress, str):

        def save_to_file(wf):
            sf.write(egress, wf, samplerate=sr)
            return wf

        return save_to_file
    return egress


def _validate_sample_width(sample_width: int) -> None:
    """Fail early, and informatively, on a sample width we cannot decode.

    >>> _validate_sample_width(2)
    >>> _validate_sample_width(5)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: Unsupported sample_width: 5. Expected one of: ...
    """
    if sample_width not in SUPPORTED_SAMPLE_WIDTHS:
        expected = ", ".join(map(str, SUPPORTED_SAMPLE_WIDTHS))
        raise ValueError(
            f"Unsupported sample_width: {sample_width}. Expected one of: {expected}"
        )


def record(
    duration: float | None = None,
    *,
    duration_unit: DurationUnit = "seconds",
    sr: int = DFLT_SR,
    egress: str | Callable | None = None,
    ignore_exceptions: tuple[type[BaseException], ...] = (KeyboardInterrupt,),
    input_device_index: int | str | None = None,
    sample_width: int = DFLT_SAMPLE_WIDTH,
    chk_size: int = DFLT_CHK_SIZE,
    stream_buffer_size_s: float = DFLT_STREAM_BUF_SIZE_S,
    verbose: bool = False,
) -> Any:
    """Record audio and return waveform data.

    Records from a microphone until ``duration`` worth of samples have been
    collected, or -- when ``duration`` is ``None`` -- until interrupted. Any
    exception listed in ``ignore_exceptions`` (``KeyboardInterrupt`` by default)
    ends the recording cleanly and the samples collected *so far* are returned;
    every other exception propagates.

    Args:
        duration: Length of recording. If None, records until interrupted.
        duration_unit: Unit for duration ('seconds', 'samples', or 'minutes').
        sr: Sample rate (Hz).
        egress: Function to process the waveform before returning it, or a
            filepath (a string) to save the waveform to. When a filepath is
            given the waveform is still what is returned.
        ignore_exceptions: Exception types to catch and exit cleanly on,
            returning the partial waveform.
        input_device_index: Index (or name) of the input device to record from.
            None uses the default device.
        sample_width: Sample width in bytes. One of ``SUPPORTED_SAMPLE_WIDTHS``.
            The dtype of the returned samples follows from the format PyAudio
            opens the device with at that width, which is not the obvious
            mapping: 2 gives int16, 3 gives float64, and 4 gives **float32**
            (PyAudio captures 4-byte samples as float32, not as int32).
        chk_size: Number of frames read from the device per chunk.
        stream_buffer_size_s: How many seconds of audio the underlying stream
            buffer keeps (i.e. how far into the past it can see).
        verbose: Whether to print status messages (also silences the input
            device discovery printout).

    Returns:
        The recorded waveform (a list of samples), as processed by ``egress``.

    >>> # Record 0.1 seconds of audio
    >>> sample = record(0.1, verbose=False)  # doctest: +SKIP
    """

    def _log(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    _validate_sample_width(sample_width)
    n_samples = _duration_to_n_samples(duration, duration_unit, sr)
    _egress = _resolve_egress(egress, sr=sr)

    # Initialize empty waveform before trying anything, so that an interruption
    # at any point still has a (possibly empty) waveform to return.
    waveform = []

    try:
        _log("Starting recording with LiveWf...")
        live_wf = LiveWf(
            input_device_index=input_device_index,
            sr=sr,
            sample_width=sample_width,
            chk_size=chk_size,
            stream_buffer_size_s=stream_buffer_size_s,
            verbose=verbose,
        )
        with live_wf as wf:
            _log("Recording started (interrupt to stop)...")
            samples = wf if n_samples is None else islice(wf, n_samples)
            # Collect samples one by one so we keep what we have on interrupt
            for sample in samples:
                waveform.append(sample)
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

    # Note: BufferItems, not BaseBufferItems: only BufferItems overrides
    # data_to_obj, so only it yields items that have a ``.bytes``.
    buffer_items = BufferItems(
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
