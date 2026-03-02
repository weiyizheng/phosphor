from __future__ import annotations

import curses

from vfd.vfd_colors import meter_zone_attr

DECAY_RATE = 1.0


class RMSMeter:
    def __init__(self, style: str = "dual"):
        self._style = style
        self._level = -60.0

    def render(self, win, rms_db: float, peak_db: float, palette) -> None:
        if rms_db > self._level:
            self._level = rms_db
        else:
            self._level = max(rms_db, self._level - DECAY_RATE)

        {
            "dual": self._render_dual,
            "bar": self._render_bar,
            "segmented": self._render_segmented,
        }.get(self._style, self._render_dual)(win, self._level, peak_db, palette)

    def _norm(self, db: float, length: int) -> int:
        return max(0, min(int((db + 60) / 60 * length), length))

    def _render_dual(self, win, rms_db: float, peak_db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 8, 1)
        rms = self._norm(rms_db, w)
        pk = self._norm(peak_db, w)
        y = max(0, rows // 2)
        try:
            win.addstr(0, 0, "RMS", palette.dim)
            win.addstr(y, 0, "[", palette.dim)
            for i in range(w):
                lit = i < rms
                win.addstr(y, 1 + i, "=" if lit else ".", meter_zone_attr(i, w, palette) if lit else palette.bg)
            if w > 0:
                win.addstr(y, min(1 + max(pk - 1, 0), w), "|", palette.peak)
            win.addstr(y, 1 + w, "]", palette.dim)
        except curses.error:
            pass

    def _render_bar(self, win, rms_db: float, peak_db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 7, 1)
        rms = self._norm(rms_db, w)
        y = max(0, rows // 2)
        try:
            win.addstr(y, 0, "R [", palette.dim)
            for i in range(w):
                lit = i < rms
                win.addstr(y, 4 + i, "=" if lit else ".", meter_zone_attr(i, w, palette) if lit else palette.bg)
            win.addstr(y, 4 + w, "]", palette.dim)
        except curses.error:
            pass

    def _render_segmented(self, win, rms_db: float, peak_db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        segs = max(cols - 5, 1)
        filled = self._norm(rms_db, segs)
        y = max(0, rows // 2)
        try:
            win.addstr(y, 0, "RMS ", palette.dim)
            for i in range(segs):
                lit = i < filled
                win.addstr(y, 4 + i, "#" if lit else "-", meter_zone_attr(i, segs, palette) if lit else palette.bg)
        except curses.error:
            pass
