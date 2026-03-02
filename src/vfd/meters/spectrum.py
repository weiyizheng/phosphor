from __future__ import annotations

import curses
from typing import List

from vfd.vfd_colors import meter_zone_attr_ratio

DECAY_RATE = 3.0
PEAK_HOLD_FRAMES = 45


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
        self._levels: List[float] = []
        self._peaks: List[float] = []
        self._peak_timers: List[int] = []

    def render(self, win, bands_db: List[float], palette) -> None:
        rows, cols = win.getmaxyx()
        n = len(bands_db)
        if n == 0 or rows <= 1 or cols <= 1:
            return

        if len(self._levels) != n:
            self._levels = list(bands_db)
            self._peaks = list(bands_db)
            self._peak_timers = [0] * n

        label_rows = 1 if self._freq_labels else 0
        scale_cols = 5 if self._db_labels else 0
        bar_rows = max(rows - label_rows - 1, 1)
        bar_cols = max(cols - scale_cols, 1)
        bar_width = max(bar_cols // n, 1)
        db_min, db_max = -80.0, 0.0

        for i, target in enumerate(bands_db):
            if self._decay:
                self._levels[i] = max(target, self._levels[i] - DECAY_RATE)
            else:
                self._levels[i] = target

            if self._peak_hold:
                if target >= self._peaks[i]:
                    self._peaks[i] = target
                    self._peak_timers[i] = PEAK_HOLD_FRAMES
                elif self._peak_timers[i] > 0:
                    self._peak_timers[i] -= 1
                else:
                    self._peaks[i] = max(self._peaks[i] - DECAY_RATE, target)

            filled = int((self._levels[i] - db_min) / (db_max - db_min) * bar_rows)
            filled = max(0, min(filled, bar_rows))
            x = scale_cols + i * bar_width

            for row_idx in range(bar_rows):
                y = bar_rows - row_idx
                if y >= rows - label_rows:
                    continue
                if row_idx < filled:
                    zone_ratio = row_idx / max(bar_rows - 1, 1)
                    attr = meter_zone_attr_ratio(zone_ratio, palette)
                    if self._glow and row_idx >= filled - 2 and attr not in (palette.warn, palette.clip):
                        attr = palette.bright
                    char = "#"
                else:
                    attr = palette.bg
                    char = "."
                try:
                    win.addstr(y, x, char * min(bar_width, max(cols - x, 0)), attr)
                except curses.error:
                    pass

            if self._peak_hold and self._peak_timers[i] > 0:
                peak_row = bar_rows - int((self._peaks[i] - db_min) / (db_max - db_min) * bar_rows)
                peak_row = max(1, min(peak_row, bar_rows))
                try:
                    win.addstr(peak_row, x, "-" * min(bar_width, max(cols - x, 0)), palette.peak)
                except curses.error:
                    pass
