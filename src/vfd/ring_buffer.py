from __future__ import annotations

import threading

import numpy as np


class RingBuffer:
    """Thread-safe ring buffer for PCM frames."""

    def __init__(self, capacity: int, channels: int):
        self._buf = np.zeros((capacity, channels), dtype=np.float32)
        self._capacity = capacity
        self._channels = channels
        self._write_pos = 0
        self._available = 0
        self._lock = threading.Lock()

    def write(self, data: np.ndarray) -> None:
        n = len(data)
        if n == 0:
            return

        if data.shape[1] != self._channels:
            raise ValueError(f"Expected {self._channels} channels, got {data.shape[1]}")

        with self._lock:
            if n >= self._capacity:
                self._buf[:] = data[-self._capacity :]
                self._write_pos = n % self._capacity
                self._available = self._capacity
                return

            write_idx = self._write_pos % self._capacity
            first = min(n, self._capacity - write_idx)
            self._buf[write_idx : write_idx + first] = data[:first]
            if first < n:
                self._buf[: n - first] = data[first:]

            self._write_pos = (write_idx + n) % self._capacity
            self._available = min(self._available + n, self._capacity)

    def read(self, n: int) -> np.ndarray:
        out = np.zeros((n, self._channels), dtype=np.float32)
        with self._lock:
            if self._available == 0:
                return out

            available = min(n, self._available)
            start = (self._write_pos - self._available) % self._capacity
            first = min(available, self._capacity - start)
            out[:first] = self._buf[start : start + first]
            if first < available:
                out[first:available] = self._buf[: available - first]
            return out
