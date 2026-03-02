from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.signal import windows


@dataclass
class AnalysisResult:
    spectrum_db: List[float]
    rms_db: float
    peak_db: float
    lufs_momentary: float
    lufs_shortterm: float
    lufs_integrated: float
    lufs_history: List[float]


class SpectrumAnalyzer:
    def __init__(self, sample_rate: int, bands: int, channels: int):
        self._sample_rate = sample_rate
        self._bands = bands
        self._channels = channels
        self._fft_size = 2048
        self._window = windows.hann(self._fft_size)
        self._freq_bins = np.fft.rfftfreq(self._fft_size, d=1.0 / sample_rate)
        self._band_edges = self._log_band_edges(bands, 20.0, 20000.0)

        self._momentary_buf = deque(maxlen=int(sample_rate * 0.4))
        self._shortterm_buf = deque(maxlen=int(sample_rate * 3.0))
        self._integrated_sum_sq = 0.0
        self._integrated_compensation = 0.0
        self._integrated_count = 0
        self._lufs_history: deque[float] = deque(maxlen=200)

    def process(self, pcm: np.ndarray) -> AnalysisResult:
        if pcm.ndim == 1:
            mono = pcm.astype(np.float32)
        else:
            mono = pcm.mean(axis=1).astype(np.float32)

        if len(mono) >= self._fft_size:
            chunk = mono[-self._fft_size :]
        else:
            chunk = np.pad(mono, (self._fft_size - len(mono), 0), mode="constant")

        spectrum = np.abs(np.fft.rfft(chunk * self._window))
        spectrum_db = self._bin_to_bands(spectrum)

        rms = np.sqrt(np.mean(mono**2)) if len(mono) else 0.0
        peak = np.max(np.abs(mono)) if len(mono) else 0.0
        rms_db = 20 * np.log10(max(float(rms), 1e-9))
        peak_db = 20 * np.log10(max(float(peak), 1e-9))

        squares_np = mono**2
        squares = squares_np.tolist()
        self._momentary_buf.extend(squares)
        self._shortterm_buf.extend(squares)
        self._kahan_add(float(np.sum(squares_np, dtype=np.float64)))
        self._integrated_count += len(squares_np)

        lufs_m = self._lkfs(list(self._momentary_buf))
        lufs_st = self._lkfs(list(self._shortterm_buf))
        lufs_i = self._lkfs_integrated(self._integrated_sum_sq, self._integrated_count)
        self._lufs_history.append(lufs_st)

        return AnalysisResult(
            spectrum_db=spectrum_db,
            rms_db=rms_db,
            peak_db=peak_db,
            lufs_momentary=lufs_m,
            lufs_shortterm=lufs_st,
            lufs_integrated=lufs_i,
            lufs_history=list(self._lufs_history),
        )

    def _log_band_edges(self, bands: int, f_low: float, f_high: float):
        return np.logspace(np.log10(f_low), np.log10(f_high), bands + 1)

    def set_bands(self, bands: int) -> None:
        if bands == self._bands:
            return
        self._bands = bands
        self._band_edges = self._log_band_edges(bands, 20.0, 20000.0)

    def _bin_to_bands(self, spectrum: np.ndarray) -> List[float]:
        out: List[float] = []
        for i in range(self._bands):
            lo, hi = self._band_edges[i], self._band_edges[i + 1]
            mask = (self._freq_bins >= lo) & (self._freq_bins < hi)
            val = float(np.mean(spectrum[mask])) if mask.any() else 1e-9
            out.append(20 * np.log10(max(val, 1e-9)))
        return out

    def _lkfs(self, squares: List[float]) -> float:
        if not squares:
            return -70.0
        mean_sq = float(np.mean(squares))
        return -0.691 + 10 * np.log10(max(mean_sq, 1e-9))

    def _lkfs_integrated(self, total_sum_sq: float, count: int) -> float:
        if count <= 0:
            return -70.0
        mean_sq = total_sum_sq / count
        return -0.691 + 10 * np.log10(max(mean_sq, 1e-9))

    def _kahan_add(self, value: float) -> None:
        y = value - self._integrated_compensation
        t = self._integrated_sum_sq + y
        self._integrated_compensation = (t - self._integrated_sum_sq) - y
        self._integrated_sum_sq = t
