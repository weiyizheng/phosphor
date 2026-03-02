from __future__ import annotations

import curses

from phosphor.vfd_colors import hotter_attr, meter_level_attr, meter_zone_attr

DECAY_RATE = 2.0
PARTICLE_DIM = "⣀"
PARTICLE_MID = "⣶"
PARTICLE_HOT = "⣿"


class VUMeter:
    """VU meter with ballistic decay."""

    def __init__(self, style: str = "segmented"):
        self._style = style
        self._level_l = -60.0
        self._level_r = -60.0

    def _ballistic(self, current: float, target: float) -> float:
        if target > current:
            return target
        return max(target, current - DECAY_RATE)

    def render(self, win, rms_db: float, palette, rms_db_l: float | None = None, rms_db_r: float | None = None) -> None:
        left = rms_db if rms_db_l is None else rms_db_l
        right = rms_db if rms_db_r is None else rms_db_r
        self._level_l = self._ballistic(self._level_l, left)
        self._level_r = self._ballistic(self._level_r, right)

        {
            "segmented": self._render_segmented,
            "bar": self._render_bar,
            "needle": self._render_needle,
        }.get(self._style, self._render_segmented)(win, self._level_l, self._level_r, palette)

    def _filled(self, db: float, width: int) -> int:
        return max(0, min(int(max(0.0, (db + 60) / 63) * width), width))

    def _render_segmented(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        segs = max(cols - 6, 1)
        filled_l = self._filled(db_l, segs)
        filled_r = self._filled(db_r, segs)
        y_l = max(0, rows // 2 - 1)
        y_r = min(rows - 1, y_l + 1)
        try:
            win.addstr(y_l, 0, "L ", palette.dim)
            level_attr_l = meter_level_attr(db_l, palette)
            for i in range(segs):
                lit = i < filled_l
                attr = hotter_attr(meter_zone_attr(i, segs, palette), level_attr_l, palette) if lit else palette.bg
                glyph = PARTICLE_HOT if attr in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr == palette.mid else PARTICLE_DIM
                win.addstr(y_l, 2 + i, glyph if lit else " ", attr)
            win.addstr(y_r, 0, "R ", palette.dim)
            level_attr_r = meter_level_attr(db_r, palette)
            for i in range(segs):
                lit = i < filled_r
                attr = hotter_attr(meter_zone_attr(i, segs, palette), level_attr_r, palette) if lit else palette.bg
                glyph = PARTICLE_HOT if attr in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr == palette.mid else PARTICLE_DIM
                win.addstr(y_r, 2 + i, glyph if lit else " ", attr)
        except curses.error:
            pass

    def _render_bar(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        width = max(cols - 6, 1)
        filled_l = self._filled(db_l, width)
        filled_r = self._filled(db_r, width)
        y_l = max(0, rows // 2 - 1)
        y_r = min(rows - 1, y_l + 1)
        try:
            win.addstr(y_l, 0, "L ", palette.dim)
            level_attr_l = meter_level_attr(db_l, palette)
            for i in range(width):
                lit = i < filled_l
                attr = hotter_attr(meter_zone_attr(i, width, palette), level_attr_l, palette) if lit else palette.bg
                glyph = PARTICLE_HOT if attr in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr == palette.mid else PARTICLE_DIM
                win.addstr(y_l, 2 + i, glyph if lit else " ", attr)
            win.addstr(y_r, 0, "R ", palette.dim)
            level_attr_r = meter_level_attr(db_r, palette)
            for i in range(width):
                lit = i < filled_r
                attr = hotter_attr(meter_zone_attr(i, width, palette), level_attr_r, palette) if lit else palette.bg
                glyph = PARTICLE_HOT if attr in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr == palette.mid else PARTICLE_DIM
                win.addstr(y_r, 2 + i, glyph if lit else " ", attr)
        except curses.error:
            pass

    def _render_needle(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        width = max(cols - 2, 1)
        pos_l = max(0, min(int((db_l + 20) / 23 * width), width - 1))
        pos_r = max(0, min(int((db_r + 20) / 23 * width), width - 1))
        try:
            win.addstr(0, 0, "VU NEEDLE", palette.dim)
            y_l = max(1, rows // 2 - 1)
            y_r = min(rows - 1, y_l + 1)
            win.addstr(y_l, 0, "-" * min(width, cols - 1), palette.dim)
            win.addstr(y_r, 0, "-" * min(width, cols - 1), palette.dim)
            win.addstr(y_l, pos_l, "^", palette.bright)
            win.addstr(y_r, pos_r, "^", palette.mid)
        except curses.error:
            pass
