"""Mic-free tests for ``taped.tools.record`` and the buffer-item contract.

``record`` needs a microphone, so every test here replaces ``taped.tools.LiveWf``
with a fake: a context manager yielding a canned iterable of samples, which also
records the keyword arguments it was constructed with. That is enough to pin down
everything ``record`` promises without touching audio hardware:

- the ``duration_unit`` conversion,
- the "return the partial waveform on an ignored exception" contract,
- the ``egress`` contract,
- and, as regressions, that every documented parameter actually reaches the
  audio source and that no code path yields items lacking a ``.data`` attribute.
"""

import numpy as np
import pytest

from taped.base import BufferItemOutput, WfChunks, audio_segment_to_buffer_item_output
from taped.tools import record


class FakeLiveWf:
    """Stand-in for ``taped.base.LiveWf``: a context manager over fixed samples.

    Instances register themselves on the class so a test can inspect how (and how
    many times) ``record`` constructed the audio source.
    """

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.entered = False
        type(self).instances.append(self)

    # -- the source of samples; overridden per test via ``samples`` -------------
    samples = ()

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False  # never swallow: record() owns the exception policy

    def __iter__(self):
        return iter(self.samples)


def _install_fake_live_wf(monkeypatch, samples):
    """Point ``taped.tools.LiveWf`` at a fresh fake yielding ``samples``."""

    class _Fake(FakeLiveWf):
        instances = []

    _Fake.samples = samples
    monkeypatch.setattr("taped.tools.LiveWf", _Fake)
    return _Fake


def _interrupt_after(n, *, exception=KeyboardInterrupt):
    """An iterable of ``n`` samples (0..n-1) that then raises ``exception``."""

    def gen():
        yield from range(n)
        raise exception("simulated interruption")

    return gen()


# --- (i) duration_unit conversion --------------------------------------------


@pytest.mark.parametrize(
    "duration,duration_unit,sr,expected_n",
    [
        (0.1, "seconds", 100, 10),
        (2, "seconds", 50, 100),
        (0.1, "minutes", 10, 60),
        (1 / 60, "minutes", 100, 100),
        (7, "samples", 44100, 7),
        (10, "samples", 1, 10),
    ],
)
def test_duration_unit_conversion(monkeypatch, duration, duration_unit, sr, expected_n):
    _install_fake_live_wf(monkeypatch, samples=range(10000))
    waveform = record(duration, duration_unit=duration_unit, sr=sr)
    assert waveform == list(range(expected_n))


def test_duration_none_records_until_source_is_exhausted(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(5))
    assert record(None) == [0, 1, 2, 3, 4]


def test_unknown_duration_unit_raises_informatively(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(10))
    with pytest.raises(ValueError, match="Unknown duration unit"):
        record(1, duration_unit="fortnights")


# --- (ii) ignored exceptions return the partial waveform ----------------------


def test_keyboard_interrupt_mid_iteration_returns_partial_waveform(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=_interrupt_after(4))
    # duration is None: the only way out is the interruption
    assert record(None) == [0, 1, 2, 3]


def test_keyboard_interrupt_before_requested_duration_returns_partial(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=_interrupt_after(3))
    # asks for 100 samples, source dies after 3
    assert record(100, duration_unit="samples") == [0, 1, 2]


def test_exception_not_in_ignore_exceptions_propagates(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=_interrupt_after(3, exception=RuntimeError))
    with pytest.raises(RuntimeError):
        record(None)


def test_ignore_exceptions_is_configurable(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=_interrupt_after(3, exception=RuntimeError))
    assert record(None, ignore_exceptions=(RuntimeError,)) == [0, 1, 2]

    _install_fake_live_wf(monkeypatch, samples=_interrupt_after(3))
    with pytest.raises(KeyboardInterrupt):
        record(None, ignore_exceptions=(RuntimeError,))


# --- (iii) egress -------------------------------------------------------------


def test_egress_none_returns_waveform_unchanged(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(10))
    assert record(5, duration_unit="samples") == [0, 1, 2, 3, 4]


def test_egress_callable_is_applied(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(10))
    assert record(5, duration_unit="samples", egress=sum) == 10


def test_egress_str_calls_sf_write_and_still_returns_waveform(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(10))
    calls = []

    def fake_write(file, data, samplerate, *args, **kwargs):
        calls.append(dict(file=file, data=list(data), samplerate=samplerate))

    monkeypatch.setattr("taped.tools.sf.write", fake_write)

    waveform = record(5, duration_unit="samples", sr=8000, egress="some_output.wav")

    assert waveform == [0, 1, 2, 3, 4], "the waveform, not the filename, is returned"
    assert len(calls) == 1
    assert calls[0] == dict(
        file="some_output.wav", data=[0, 1, 2, 3, 4], samplerate=8000
    )


def test_egress_str_actually_writes_a_readable_file(monkeypatch, tmp_path):
    import soundfile as sf

    samples = [np.int16(i * 100) for i in range(16)]
    _install_fake_live_wf(monkeypatch, samples=samples)
    filepath = tmp_path / "recorded.wav"

    waveform = record(16, duration_unit="samples", sr=8000, egress=str(filepath))

    assert waveform == samples
    assert filepath.is_file()
    read_back, read_sr = sf.read(str(filepath), dtype="int16")
    assert read_sr == 8000
    assert list(read_back) == samples


# --- (iv) regressions ---------------------------------------------------------
#
# Both of these guard the same defect from two sides. `record` used to branch:
# the default path used `LiveWf`, and *any* non-default `input_device_index` or
# `sample_width` fell to a second path built on `BaseBufferItems`. That second
# path did `waveform.extend(item.data)`, but `BaseBufferItems` does not override
# `data_to_obj`, so it yields raw `AudioSegment`s, which have no `.data`. The
# branch therefore raised `AttributeError` before collecting a single sample --
# which meant it was dead code, and meant the four parameters only it read could
# never influence a call that returned.


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(input_device_index=3),
        dict(sample_width=4),
        dict(input_device_index="MacBook Pro Microphone"),
        dict(input_device_index=0, sample_width=3, chk_size=512, stream_buffer_size_s=7),
    ],
)
def test_record_does_not_crash_on_non_default_device_or_sample_width(
    monkeypatch, kwargs
):
    fake = _install_fake_live_wf(monkeypatch, samples=range(10))
    assert record(5, duration_unit="samples", **kwargs) == [0, 1, 2, 3, 4]
    # exactly one audio source was built, and it was the (faked) LiveWf
    assert len(fake.instances) == 1


def test_every_documented_parameter_reaches_the_audio_source(monkeypatch):
    """No documented parameter may be inert: each must reach the audio source."""
    fake = _install_fake_live_wf(monkeypatch, samples=range(100))

    record(
        10,
        duration_unit="samples",
        sr=16000,
        input_device_index=3,
        sample_width=4,
        chk_size=512,
        stream_buffer_size_s=7,
        verbose=False,
    )

    assert len(fake.instances) == 1
    assert fake.instances[0].kwargs == dict(
        input_device_index=3,
        sr=16000,
        sample_width=4,
        chk_size=512,
        stream_buffer_size_s=7,
        verbose=False,
    )


def test_unsupported_sample_width_fails_fast_and_informatively(monkeypatch):
    _install_fake_live_wf(monkeypatch, samples=range(10))
    with pytest.raises(ValueError, match="Unsupported sample_width"):
        record(5, duration_unit="samples", sample_width=5)


def test_wf_chunks_decodes_with_the_stream_s_sample_width():
    """``WfChunks`` must decode with the width the stream was opened with.

    A ``sample_width = 2`` class attribute on ``WfChunks`` used to shadow the
    constructed value, so a 32-bit capture was silently decoded as 16-bit.
    Built mic-free: only ``data_to_obj`` is exercised, on a hand-made segment.
    """
    from types import SimpleNamespace

    from audiostream2py import AudioSegment

    # 2 frames of 32-bit PCM: 1 and 2 (little endian)
    waveform_bytes = (1).to_bytes(4, "little") + (2).to_bytes(4, "little")
    segment = AudioSegment(
        start_date=0,
        end_date=1000,
        waveform=waveform_bytes,
        frame_count=2,
        status_flags=0,
    )

    chunks = WfChunks.__new__(WfChunks)  # no device: we only need data_to_obj
    chunks.stream = SimpleNamespace(sample_width=4)

    decoded = chunks.data_to_obj(segment)

    assert len(decoded) == 2, (
        "decoded 8 bytes as 4 int16 samples instead of 2 int32 ones: "
        "the stream's sample_width was ignored"
    )
    assert list(decoded) == [1, 2]


# --- issue #3: the documented meaning of the buffer-item fields ---------------


def test_buffer_item_output_field_meanings():
    """Pin the field order and the (surprising) source of each field's value."""
    from audiostream2py import AudioSegment

    assert BufferItemOutput._fields == (
        "timestamp",
        "bytes",
        "frame_count",
        "time_info",
        "status_flags",
    )

    segment = AudioSegment(
        start_date=1608336556178995,
        end_date=1608336556271874,
        waveform=b"\x01\x00\x02\x00",
        frame_count=2,
        status_flags=0,
    )
    item = audio_segment_to_buffer_item_output(segment)

    assert item.timestamp == segment.start_date
    assert item.bytes == segment.waveform
    assert item.frame_count == segment.frame_count
    # The trap this docstring exists to warn about: time_info is the segment's
    # end_date, NOT a PortAudio time-info dict, and is therefore not subscriptable.
    assert item.time_info == segment.end_date
    assert isinstance(item.time_info, int)
    with pytest.raises(TypeError):
        item.time_info["input_buffer_adc_time"]
    assert item.status_flags == segment.status_flags
