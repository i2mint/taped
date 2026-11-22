"""Offline tests for taped.util: device-index resolution with a fake device list, waveform conversion, chunking."""

import numpy as np
import pytest

from taped import util

DEVICES = [
    {"index": 0, "name": "Built-in Speakers", "maxInputChannels": 0},
    {"index": 1, "name": "Built-in Microphone", "maxInputChannels": 1},
    {"index": 2, "name": "USB Audio Input", "maxInputChannels": 2},
]


@pytest.fixture
def fake_devices(monkeypatch):
    monkeypatch.setattr(
        util.PyAudioSourceReader, "list_device_info", staticmethod(lambda: DEVICES)
    )


def test_list_recording_devices_skips_outputs(fake_devices):
    assert util.list_recording_device_index_names() == [
        (1, "Built-in Microphone"),
        (2, "USB Audio Input"),
    ]


def test_find_a_device_index(fake_devices):
    assert util.find_a_device_index() == 1  # 'microphone' by default
    assert util.find_a_device_index("usb") == 2
    assert util.find_a_device_index("nonexistent", dflt=-1) == -1
    assert util.find_a_device_index(lambda d: d["index"] == 2) == 2


def test_ensure_source_input_device_index(fake_devices):
    f = util.ensure_source_input_device_index
    assert f(2) == 2
    assert f("USB Audio Input") == 2
    assert f((1, "anything")) == 1
    with pytest.raises(ValueError, match="name not found"):
        f("no such device")
    with pytest.raises(AssertionError):
        f(("one", "name"))
    with pytest.raises(ValueError, match="couldn't resolve"):
        f(3.5)


def test_ensure_index_falls_back_to_default_or_explains(
    fake_devices, monkeypatch, capsys
):
    monkeypatch.setattr(util, "get_input_device_index", lambda verbose=True: 7)
    assert util.ensure_source_input_device_index(None) == 7
    monkeypatch.setattr(util, "get_input_device_index", lambda verbose=True: None)
    with pytest.raises(ValueError, match="Need a valid input_device_index"):
        util.ensure_source_input_device_index(None)
    assert "Built-in Microphone" in capsys.readouterr().out


def test_waveform_bytes_roundtrip_and_old_decoder():
    wf = np.array([0, 1000, -1000, 32000], dtype="int16")
    b = util.waveform_to_bytes(wf, sr=8000, sample_width=2)
    assert len(b) == 2 * len(wf)
    back = util.bytes_to_waveform(b, sr=8000, n_channels=1, sample_width=2)
    assert np.allclose(np.asarray(back, dtype=float), wf, atol=1)
    old = util.bytes_to_waveform_old(b, sr=8000, n_channels=1, sample_width=2)
    assert list(old) == list(wf)


def test_chunking_helpers():
    assert list(util.simple_chunker(range(7), 3)) == [(0, 1, 2), (3, 4, 5)]
    assert list(util.rechunker([[0], (1, 2, 3), [4, 5]], 2)) == [(0, 1), (2, 3), (4, 5)]
    assert list(util.rechunker([[0, 1, 2, 3]], lambda s: iter([list(s)]))) == [
        [0, 1, 2, 3]
    ]
