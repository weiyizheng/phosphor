from __future__ import annotations

import curses

from phosphor.vfd_colors import hotter_attr, meter_level_attr, meter_zone_attr

PEAK_HOLD_FRAMES = 60
DECAY_RATE = 1.5
PARTICLE_DIM = "⣀"
PARTICLE_MID = "⣶"
PARTICLE_HOT = "⣿"


class PeakMeter:
    def __init__(self, style: str = "vertical", peak_hold: bool = True):
        self._style = style
        self._peak_hold = peak_hold
        self._held_peak = -90.0
        self._hold_timer = 0

    def render(self, win, peak_db: float, palette, peak_db_l: float | None = None, peak_db_r: float | None = None) -> None:
        left = peak_db if peak_db_l is None else peak_db_l
        right = peak_db if peak_db_r is None else peak_db_r
        peak_max = max(left, right)
        if self._peak_hold:
            if peak_max >= self._held_peak:
                self._held_peak = peak_max
                self._hold_timer = PEAK_HOLD_FRAMES
            elif self._hold_timer > 0:
                self._hold_timer -= 1
            else:
                self._held_peak = max(self._held_peak - DECAY_RATE, peak_max)

        {
            "vertical": self._render_vertical,
            "horizontal": self._render_horizontal,
            "ppm": self._render_ppm,
        }.get(self._style, self._render_vertical)(win, left, right, palette)

    def _norm(self, db: float, length: int) -> int:
        return max(0, min(int((db + 60) / 60 * length), length))

    def _render_vertical(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        h = max(rows - 2, 1)
        filled_l = self._norm(db_l, h)
        filled_r = self._norm(db_r, h)
        hold = int(round(self._norm(self._held_peak, h)))
        x_l = max(0, cols // 3)
        x_r = min(cols - 1, max(x_l + 2, 2 * cols // 3))
        try:
            win.addstr(0, 0, "PEAK", palette.dim)
            level_attr_l = meter_level_attr(db_l, palette)
            level_attr_r = meter_level_attr(db_r, palette)
            for i in range(h):
                y = rows - 2 - i
                lit_l = i < filled_l
                lit_r = i < filled_r
                attr_l = hotter_attr(meter_zone_attr(i, h, palette), level_attr_l, palette) if lit_l else palette.bg
                attr_r = hotter_attr(meter_zone_attr(i, h, palette), level_attr_r, palette) if lit_r else palette.bg
                glyph_l = PARTICLE_HOT if attr_l in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_l == palette.mid else PARTICLE_DIM
                glyph_r = PARTICLE_HOT if attr_r in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_r == palette.mid else PARTICLE_DIM
                win.addstr(y, x_l, glyph_l if lit_l else " ", attr_l)
                win.addstr(y, x_r, glyph_r if lit_r else " ", attr_r)
                if self._peak_hold and i == hold:
                    win.addstr(y, x_l, "▔", palette.peak)
                    win.addstr(y, x_r, "▔", palette.peak)
        except curses.error:
            pass

    def _render_horizontal(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 6, 1)
        filled_l = self._norm(db_l, w)
        filled_r = self._norm(db_r, w)
        hold = int(round(self._norm(self._held_peak, w)))
        y_l = max(0, rows // 2 - 1)
        y_r = min(rows - 1, y_l + 1)
        try:
            win.addstr(y_l, 0, "L ", palette.dim)
            level_attr_l = meter_level_attr(db_l, palette)
            for i in range(w):
                lit_l = i < filled_l
                attr_l = hotter_attr(meter_zone_attr(i, w, palette), level_attr_l, palette) if lit_l else palette.bg
                glyph_l = PARTICLE_HOT if attr_l in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_l == palette.mid else PARTICLE_DIM
                win.addstr(y_l, 2 + i, glyph_l if lit_l else " ", attr_l)
            win.addstr(y_r, 0, "R ", palette.dim)
            level_attr_r = meter_level_attr(db_r, palette)
            for i in range(w):
                lit_r = i < filled_r
                attr_r = hotter_attr(meter_zone_attr(i, w, palette), level_attr_r, palette) if lit_r else palette.bg
                glyph_r = PARTICLE_HOT if attr_r in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_r == palette.mid else PARTICLE_DIM
                win.addstr(y_r, 2 + i, glyph_r if lit_r else " ", attr_r)
            if self._peak_hold:
                hold_x = int(2 + min(max(hold - 1, 0), w - 1))
                win.addstr(y_l, hold_x, "▏", palette.peak)
                win.addstr(y_r, hold_x, "▏", palette.peak)
        except curses.error:
            pass

    def _render_ppm(self, win, db_l: float, db_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        segments = 7
        seg_w = max((cols - 2) // segments, 1)
        thresholds = [-36, -26, -18, -12, -6, 0, 6]
        y_l = max(0, rows // 2 - 1)
        y_r = min(rows - 1, y_l + 1)
        try:
            win.addstr(0, 0, "PPM", palette.dim)
            level_attr_l = meter_level_attr(db_l, palette, floor_db=-36.0, ceil_db=6.0)
            level_attr_r = meter_level_attr(db_r, palette, floor_db=-36.0, ceil_db=6.0)
            for i, th in enumerate(thresholds):
                x = 1 + i * seg_w
                lit_l = db_l >= th
                lit_r = db_r >= th
                attr_l = hotter_attr(meter_zone_attr(i, len(thresholds), palette), level_attr_l, palette) if lit_l else palette.bg
                attr_r = hotter_attr(meter_zone_attr(i, len(thresholds), palette), level_attr_r, palette) if lit_r else palette.bg
                glyph_l = "█" if lit_l else " "
                glyph_r = "█" if lit_r else " "
                win.addstr(y_l, x, glyph_l * seg_w, attr_l)
                win.addstr(y_r, x, glyph_r * seg_w, attr_r)
        except curses.error:
            pass
