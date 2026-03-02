from __future__ import annotations

import curses

from vfd.vfd_colors import meter_zone_attr

PEAK_HOLD_FRAMES = 60
DECAY_RATE = 1.5


class PeakMeter:
    def __init__(self, style: str = "vertical", peak_hold: bool = True):
        self._style = style
        self._peak_hold = peak_hold
        self._held_peak = -90.0
        self._hold_timer = 0

    def render(self, win, peak_db: float, palette) -> None:
        if self._peak_hold:
            if peak_db >= self._held_peak:
                self._held_peak = peak_db
                self._hold_timer = PEAK_HOLD_FRAMES
            elif self._hold_timer > 0:
                self._hold_timer -= 1
            else:
                self._held_peak = max(self._held_peak - DECAY_RATE, peak_db)

        {
            "vertical": self._render_vertical,
            "horizontal": self._render_horizontal,
            "ppm": self._render_ppm,
        }.get(self._style, self._render_vertical)(win, peak_db, palette)

    def _norm(self, db: float, length: int) -> int:
        return max(0, min(int((db + 60) / 60 * length), length))

    def _render_vertical(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        h = max(rows - 2, 1)
        filled = self._norm(db, h)
        hold = self._norm(self._held_peak, h)
        x = max(0, cols // 2)
        try:
            win.addstr(0, 0, "PEAK", palette.dim)
            for i in range(h):
                y = rows - 2 - i
                lit = i < filled
                win.addstr(y, x, "|", meter_zone_attr(i, h, palette) if lit else palette.bg)
                if self._peak_hold and i == hold:
                    win.addstr(y, x, "-", palette.peak)
        except curses.error:
            pass

    def _render_horizontal(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 7, 1)
        filled = self._norm(db, w)
        hold = self._norm(self._held_peak, w)
        y = max(0, rows // 2)
        try:
            win.addstr(y, 0, "PK [", palette.dim)
            for i in range(w):
                lit = i < filled
                win.addstr(y, 4 + i, "=" if lit else ".", meter_zone_attr(i, w, palette) if lit else palette.bg)
            if self._peak_hold:
                win.addstr(y, 4 + min(max(hold - 1, 0), w - 1), "|", palette.peak)
            win.addstr(y, 4 + w, "]", palette.dim)
        except curses.error:
            pass

    def _render_ppm(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        segments = 7
        seg_w = max((cols - 3) // segments, 1)
        thresholds = [-36, -26, -18, -12, -6, 0, 6]
        y = max(0, rows // 2)
        try:
            win.addstr(0, 0, "PPM", palette.dim)
            for i, th in enumerate(thresholds):
                x = 2 + i * seg_w
                lit = db >= th
                attr = meter_zone_attr(i, len(thresholds), palette) if lit else palette.bg
                win.addstr(y, x, "#" * seg_w, attr)
        except curses.error:
            pass
