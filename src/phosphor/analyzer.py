from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.signal import lfilter, resample_poly, windows


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

        # BS.1770 loudness pipeline state.
        self._lufs_sr = 48000
        self._mom_len = int(self._lufs_sr * 0.4)
        self._short_len = int(self._lufs_sr * 3.0)
        self._block_size = self._mom_len
        self._hop_size = int(self._block_size * 0.25)  # 75% overlap
        self._momentary_sq = np.zeros(0, dtype=np.float64)
        self._shortterm_sq = np.zeros(0, dtype=np.float64)
        self._block_buffer = np.zeros(0, dtype=np.float64)
        self._block_powers: list[float] = []
        self._lufs_history: deque[float] = deque(maxlen=200)

        # ITU-R BS.1770 K-weighting (48 kHz coefficients).
        self._k_b_pre = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285], dtype=np.float64)
        self._k_a_pre = np.array([1.0, -1.69065929318241, 0.73248077421585], dtype=np.float64)
        self._k_b_rlb = np.array([1.0, -2.0, 1.0], dtype=np.float64)
        self._k_a_rlb = np.array([1.0, -1.99004745483398, 0.99007225036621], dtype=np.float64)
        self._zi_pre = np.zeros(max(len(self._k_a_pre), len(self._k_b_pre)) - 1, dtype=np.float64)
        self._zi_rlb = np.zeros(max(len(self._k_a_rlb), len(self._k_b_rlb)) - 1, dtype=np.float64)

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

        lufs_m, lufs_st, lufs_i = self._process_lufs(mono)
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

    def _process_lufs(self, mono: np.ndarray) -> tuple[float, float, float]:
        weighted = self._k_weight(mono)
        if weighted.size == 0:
            return -70.0, -70.0, -70.0

        squares = weighted * weighted
        self._momentary_sq = self._append_tail(self._momentary_sq, squares, self._mom_len)
        self._shortterm_sq = self._append_tail(self._shortterm_sq, squares, self._short_len)
        self._block_buffer = np.concatenate((self._block_buffer, squares))

        while self._block_buffer.size >= self._block_size:
            block = self._block_buffer[: self._block_size]
            self._block_powers.append(float(np.mean(block)))
            self._block_buffer = self._block_buffer[self._hop_size :]

        lufs_m = self._power_to_lkfs(float(np.mean(self._momentary_sq))) if self._momentary_sq.size else -70.0
        lufs_st = self._power_to_lkfs(float(np.mean(self._shortterm_sq))) if self._shortterm_sq.size else -70.0
        lufs_i = self._integrated_lkfs()
        return lufs_m, lufs_st, lufs_i

    def _k_weight(self, mono: np.ndarray) -> np.ndarray:
        signal = mono.astype(np.float64, copy=False)
        if self._sample_rate != self._lufs_sr:
            signal = resample_poly(signal, self._lufs_sr, self._sample_rate)

        if signal.size == 0:
            return signal

        y, self._zi_pre = lfilter(self._k_b_pre, self._k_a_pre, signal, zi=self._zi_pre)
        y, self._zi_rlb = lfilter(self._k_b_rlb, self._k_a_rlb, y, zi=self._zi_rlb)
        return y

    def _integrated_lkfs(self) -> float:
        if not self._block_powers:
            return -70.0

        powers = np.array(self._block_powers, dtype=np.float64)
        abs_gate = self._lkfs_to_power(-70.0)
        powers = powers[powers > abs_gate]
        if powers.size == 0:
            return -70.0

        ungated = self._power_to_lkfs(float(np.mean(powers)))
        rel_gate = self._lkfs_to_power(ungated - 10.0)
        gated = powers[powers > rel_gate]
        if gated.size == 0:
            return -70.0
        return self._power_to_lkfs(float(np.mean(gated)))

    def _append_tail(self, current: np.ndarray, new: np.ndarray, max_len: int) -> np.ndarray:
        if current.size == 0:
            out = new
        else:
            out = np.concatenate((current, new))
        if out.size > max_len:
            out = out[-max_len:]
        return out

    def _power_to_lkfs(self, power: float) -> float:
        return -0.691 + 10.0 * np.log10(max(power, 1e-12))

    def _lkfs_to_power(self, lkfs: float) -> float:
        return float(10.0 ** ((lkfs + 0.691) / 10.0))

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
