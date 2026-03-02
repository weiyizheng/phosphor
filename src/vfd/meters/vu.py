from __future__ import annotations

import curses

from vfd.vfd_colors import meter_zone_attr

DECAY_RATE = 2.0


class VUMeter:
    """VU meter with ballistic decay."""

    def __init__(self, style: str = "segmented"):
        self._style = style
        self._level = -60.0

    def render(self, win, rms_db: float, palette) -> None:
        if rms_db > self._level:
            self._level = rms_db
        else:
            self._level = max(rms_db, self._level - DECAY_RATE)

        {
            "segmented": self._render_segmented,
            "bar": self._render_bar,
            "needle": self._render_needle,
        }.get(self._style, self._render_segmented)(win, self._level, palette)

    def _filled(self, db: float, width: int) -> int:
        return max(0, min(int(max(0.0, (db + 60) / 63) * width), width))

    def _render_segmented(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        segs = max(cols - 4, 1)
        filled = self._filled(db, segs)
        y = max(0, rows // 2)
        try:
            win.addstr(y, 0, "VU ", palette.dim)
            for i in range(segs):
                lit = i < filled
                attr = meter_zone_attr(i, segs, palette) if lit else palette.bg
                win.addstr(y, 3 + i, "#" if lit else "-", attr)
            if rows > 1:
                win.addstr(rows - 1, 0, f"{db:>+6.1f}dB", palette.mid)
        except curses.error:
            pass

    def _render_bar(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        width = max(cols - 7, 1)
        filled = self._filled(db, width)
        y = max(0, rows // 2)
        try:
            win.addstr(y, 0, "VU [", palette.dim)
            for i in range(width):
                lit = i < filled
                attr = meter_zone_attr(i, width, palette) if lit else palette.bg
                win.addstr(y, 4 + i, "=" if lit else ".", attr)
            win.addstr(y, 4 + width, "]", palette.dim)
        except curses.error:
            pass

    def _render_needle(self, win, db: float, palette) -> None:
        rows, cols = win.getmaxyx()
        width = max(cols - 2, 1)
        pos = max(0, min(int((db + 20) / 23 * width), width - 1))
        try:
            win.addstr(0, 0, "VU NEEDLE", palette.dim)
            y = max(1, rows // 2)
            win.addstr(y, 0, "-" * min(width, cols - 1), palette.dim)
            win.addstr(y, pos, "^", palette.bright)
        except curses.error:
            pass
