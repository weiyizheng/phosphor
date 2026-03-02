from __future__ import annotations

import curses
from typing import List

import numpy as np

from phosphor.vfd_colors import meter_zone_attr_ratio

DECAY_RATE = 3.0
PEAK_HOLD_FRAMES = 45
PARTICLE_DIM = "⣀"
PARTICLE_MID = "⣶"
PARTICLE_HOT = "⣿"
PEAK_PARTICLE = "⠉"


class SpectrumMeter:
    def __init__(
        self,
        peak_hold: bool,
        decay: bool,
        glow: bool,
        db_labels: bool,
        freq_labels: bool,
        color: str,
    ):
        self._peak_hold = peak_hold
        self._decay = decay
        self._glow = glow
        self._db_labels = db_labels
        self._freq_labels = freq_labels
        self._color = color
        self._levels_l: List[float] = []
        self._peaks_l: List[float] = []
        self._peak_timers_l: List[int] = []
        self._levels_r: List[float] = []
        self._peaks_r: List[float] = []
        self._peak_timers_r: List[int] = []
        self._display_floor = -72.0
        self._display_ceil = -6.0

    def _bass_compensation(self, n: int) -> np.ndarray:
        # Reduce persistent LF dominance (common in mastered music) so lows
        # don't pin the left side while preserving visible bass dynamics.
        x = np.linspace(0.0, 1.0, n)
        main_tilt = 17.0 * (1.0 - x) ** 0.5
        sub_bass_trim = 4.0 * np.exp(-x * 10.0)  # extra attenuation for first few bins
        return main_tilt + sub_bass_trim

    def render(self, win, bands_db: List[float], palette, bands_db_r: List[float] | None = None) -> None:
        rows, cols = win.getmaxyx()
        n = len(bands_db)
        if n == 0 or rows <= 1 or cols <= 1:
            return

        if len(self._levels_l) != n:
            self._levels_l = list(bands_db)
            self._peaks_l = list(bands_db)
            self._peak_timers_l = [0] * n
        if bands_db_r is not None and len(self._levels_r) != n:
            self._levels_r = list(bands_db_r)
            self._peaks_r = list(bands_db_r)
            self._peak_timers_r = [0] * n

        self._update_display_range(bands_db, bands_db_r)

        if bands_db_r is None:
            self._render_lane(
                win,
                0,
                rows,
                bands_db,
                self._levels_l,
                self._peaks_l,
                self._peak_timers_l,
                palette,
            )
            return

        sep = 1 if rows >= 6 else 0
        top_rows = max((rows - sep) // 2, 1)
        bottom_rows = max(rows - top_rows - sep, 1)
        if sep:
            try:
                win.addstr(top_rows, 0, "─" * cols, palette.dim)
                win.addstr(0, 0, "L", palette.mid)
                win.addstr(top_rows + 1, 0, "R", palette.mid)
            except curses.error:
                pass

        self._render_lane(
            win,
            0,
            top_rows,
            bands_db,
            self._levels_l,
            self._peaks_l,
            self._peak_timers_l,
            palette,
        )
        self._render_lane(
            win,
            top_rows + sep,
            bottom_rows,
            bands_db_r,
            self._levels_r,
            self._peaks_r,
            self._peak_timers_r,
            palette,
        )

    def _update_display_range(self, bands_l: List[float], bands_r: List[float] | None) -> None:
        n = len(bands_l)
        if n == 0:
            return
        comp = self._bass_compensation(n)
        adjusted_l = [bands_l[i] - float(comp[i]) for i in range(n)]
        adjusted_r = [bands_r[i] - float(comp[i]) for i in range(n)] if bands_r is not None else []
        values = adjusted_l + adjusted_r
        if not values:
            return
        p95 = float(np.percentile(values, 95))
        p20 = float(np.percentile(values, 20))
        target_ceil = min(0.0, max(-18.0, p95 + 2.5))
        target_floor = min(target_ceil - 20.0, max(-92.0, p20 - 10.0))
        if target_ceil - target_floor < 20.0:
            target_floor = target_ceil - 20.0
        alpha = 0.2
        self._display_ceil = (1.0 - alpha) * self._display_ceil + alpha * target_ceil
        self._display_floor = (1.0 - alpha) * self._display_floor + alpha * target_floor

    def _render_lane(
        self,
        win,
        y0: int,
        lane_rows: int,
        bands_db: List[float],
        levels: List[float],
        peaks: List[float],
        peak_timers: List[int],
        palette,
    ) -> None:
        cols = win.getmaxyx()[1]
        n = len(bands_db)
        if lane_rows <= 0 or n == 0:
            return

        db_min = self._display_floor
        db_max = self._display_ceil
        bar_cols = max(cols, 1)
        starts = [int(i * bar_cols / n) for i in range(n)] + [bar_cols]
        tilt = self._bass_compensation(n)

        for i, target in enumerate(bands_db):
            target = target - float(tilt[i])
            x = starts[i]
            bar_width = max(1, starts[i + 1] - starts[i])
            if self._decay:
                levels[i] = max(target, levels[i] - DECAY_RATE)
            else:
                levels[i] = target

            if self._peak_hold:
                if target >= peaks[i]:
                    peaks[i] = target
                    peak_timers[i] = PEAK_HOLD_FRAMES
                elif peak_timers[i] > 0:
                    peak_timers[i] -= 1
                else:
                    peaks[i] = max(peaks[i] - DECAY_RATE, target)

            filled = int((levels[i] - db_min) / max(db_max - db_min, 1e-6) * lane_rows)
            filled = max(0, min(filled, lane_rows))

            for row_idx in range(lane_rows):
                if row_idx >= filled:
                    continue
                y = y0 + lane_rows - 1 - row_idx
                zone_ratio = row_idx / max(lane_rows - 1, 1)
                attr = meter_zone_attr_ratio(zone_ratio, palette)
                if self._glow and row_idx >= filled - 2 and attr not in (palette.warn, palette.clip):
                    attr = palette.bright
                char = PARTICLE_HOT if attr in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr == palette.mid else PARTICLE_DIM
                try:
                    win.addstr(y, x, char * min(bar_width, max(cols - x, 0)), attr)
                except curses.error:
                    pass

            if self._peak_hold and peak_timers[i] > 0:
                peak_row = lane_rows - 1 - int((peaks[i] - db_min) / max(db_max - db_min, 1e-6) * lane_rows)
                peak_row = max(0, min(peak_row, lane_rows - 1))
                y_peak = y0 + peak_row
                try:
                    win.addstr(y_peak, x, PEAK_PARTICLE * min(bar_width, max(cols - x, 0)), palette.peak)
                except curses.error:
                    pass
