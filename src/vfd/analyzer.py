from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.signal import windows


@dataclass
class AnalysisResult:
    spectrum_db: List[float]
    spectrum_db_l: List[float]
    spectrum_db_r: List[float]
    rms_db: float
    peak_db: float
    rms_db_l: float
    rms_db_r: float
    peak_db_l: float
    peak_db_r: float
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
        self._band_bin_ranges = self._compute_band_bin_ranges()

        self._momentary_buf = deque(maxlen=int(sample_rate * 0.4))
        self._shortterm_buf = deque(maxlen=int(sample_rate * 3.0))
        self._integrated_sum_sq = 0.0
        self._integrated_compensation = 0.0
        self._integrated_count = 0
        self._lufs_history: deque[float] = deque(maxlen=200)

    def process(self, pcm: np.ndarray) -> AnalysisResult:
        if pcm.ndim == 1:
            mono = pcm.astype(np.float32)
            left = mono
            right = mono
        else:
            mono = pcm.mean(axis=1).astype(np.float32)
            left = pcm[:, 0].astype(np.float32)
            right = pcm[:, 1].astype(np.float32) if pcm.shape[1] > 1 else left

        chunk = self._windowed_chunk(mono)
        chunk_l = self._windowed_chunk(left)
        chunk_r = self._windowed_chunk(right)

        spectrum = np.abs(np.fft.rfft(chunk * self._window))
        spectrum_l = np.abs(np.fft.rfft(chunk_l * self._window))
        spectrum_r = np.abs(np.fft.rfft(chunk_r * self._window))
        spectrum_db = self._bin_to_bands(spectrum)
        spectrum_db_l = self._bin_to_bands(spectrum_l)
        spectrum_db_r = self._bin_to_bands(spectrum_r)

        rms = np.sqrt(np.mean(mono**2)) if len(mono) else 0.0
        peak = np.max(np.abs(mono)) if len(mono) else 0.0
        rms_db = 20 * np.log10(max(float(rms), 1e-9))
        peak_db = 20 * np.log10(max(float(peak), 1e-9))
        rms_l = np.sqrt(np.mean(left**2)) if len(left) else 0.0
        rms_r = np.sqrt(np.mean(right**2)) if len(right) else 0.0
        peak_l = np.max(np.abs(left)) if len(left) else 0.0
        peak_r = np.max(np.abs(right)) if len(right) else 0.0
        rms_db_l = 20 * np.log10(max(float(rms_l), 1e-9))
        rms_db_r = 20 * np.log10(max(float(rms_r), 1e-9))
        peak_db_l = 20 * np.log10(max(float(peak_l), 1e-9))
        peak_db_r = 20 * np.log10(max(float(peak_r), 1e-9))

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
            spectrum_db_l=spectrum_db_l,
            spectrum_db_r=spectrum_db_r,
            rms_db=rms_db,
            peak_db=peak_db,
            rms_db_l=rms_db_l,
            rms_db_r=rms_db_r,
            peak_db_l=peak_db_l,
            peak_db_r=peak_db_r,
            lufs_momentary=lufs_m,
            lufs_shortterm=lufs_st,
            lufs_integrated=lufs_i,
            lufs_history=list(self._lufs_history),
        )

    def _log_band_edges(self, bands: int, f_low: float, f_high: float):
        return np.logspace(np.log10(f_low), np.log10(f_high), bands + 1)

    def _windowed_chunk(self, signal: np.ndarray) -> np.ndarray:
        if len(signal) >= self._fft_size:
            return signal[-self._fft_size :]
        return np.pad(signal, (self._fft_size - len(signal), 0), mode="constant")

    def set_bands(self, bands: int) -> None:
        if bands == self._bands:
            return
        self._bands = bands
        self._band_edges = self._log_band_edges(bands, 20.0, 20000.0)
        self._band_bin_ranges = self._compute_band_bin_ranges()

    def _bin_to_bands(self, spectrum: np.ndarray) -> List[float]:
        out: List[float] = []
        for lo_idx, hi_idx in self._band_bin_ranges:
            val = float(np.mean(spectrum[lo_idx:hi_idx]))
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

    def _compute_band_bin_ranges(self) -> List[tuple[int, int]]:
        ranges: List[tuple[int, int]] = []
        max_idx = len(self._freq_bins) - 1
        for i in range(self._bands):
            lo_hz, hi_hz = self._band_edges[i], self._band_edges[i + 1]
            lo_idx = int(np.searchsorted(self._freq_bins, lo_hz, side="left"))
            hi_idx = int(np.searchsorted(self._freq_bins, hi_hz, side="left"))
            lo_idx = max(0, min(lo_idx, max_idx))
            hi_idx = max(lo_idx + 1, min(hi_idx, max_idx + 1))
            ranges.append((lo_idx, hi_idx))
        return ranges
