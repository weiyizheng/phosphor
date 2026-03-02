from unittest.mock import patch

import numpy as np
import pytest

from vfd.capture import AudioCapture, DeviceNotFoundError


def test_raises_if_device_not_found():
    with patch("sounddevice.query_devices", return_value=[{"name": "Built-in Microphone", "max_input_channels": 1}]):
        with pytest.raises(DeviceNotFoundError):
            AudioCapture(device_name="BlackHole 2ch", sample_rate=44100, channels=2)


def test_find_device_index():
    devices = [
        {"name": "Built-in Microphone", "max_input_channels": 1},
        {"name": "BlackHole 2ch", "max_input_channels": 2},
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        capture = AudioCapture.__new__(AudioCapture)
        idx = capture._find_device(devices, "BlackHole 2ch")
        assert idx == 1


def test_read_returns_numpy_array():
    with patch("sounddevice.query_devices", return_value=[{"name": "BlackHole 2ch", "max_input_channels": 2}]), patch(
        "sounddevice.InputStream"
    ):
        capture = AudioCapture(device_name="BlackHole 2ch", sample_rate=44100, channels=2)
        data = capture.read(512)
        assert isinstance(data, np.ndarray)
        assert data.shape[1] == 2
