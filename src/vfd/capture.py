from __future__ import annotations

import numpy as np
import sounddevice as sd

from vfd.ring_buffer import RingBuffer


class DeviceNotFoundError(Exception):
    """Raised when requested capture device cannot be found."""


class AudioCapture:
    def __init__(
        self,
        device_name: str,
        sample_rate: int = 44100,
        channels: int = 2,
        buffer_size: int = 8192,
    ):
        self._sample_rate = sample_rate
        self._channels = channels
        self._ring = RingBuffer(capacity=buffer_size, channels=channels)

        devices = sd.query_devices()
        device_idx = self._find_device(devices, device_name)
        if device_idx is None:
            raise DeviceNotFoundError(
                f"Device '{device_name}' not found.\n"
                "Run `vfd --list-devices` to see available devices.\n"
                "Run `vfd --setup` for setup instructions."
            )

        self._stream = sd.InputStream(
            device=device_idx,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=self._callback,
        )

    def _find_device(self, devices, name: str):
        for i, device in enumerate(devices):
            if name.lower() in device["name"].lower() and device["max_input_channels"] > 0:
                return i
        return None

    def _callback(self, indata, frames, time, status):  # pragma: no cover - callback
        self._ring.write(indata.copy())

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()
        self._stream.close()

    def read(self, n: int) -> np.ndarray:
        return self._ring.read(n)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels
