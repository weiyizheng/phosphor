from __future__ import annotations

import curses

from phosphor.vfd_colors import hotter_attr, meter_level_attr, meter_zone_attr

DECAY_RATE = 1.0
PARTICLE_DIM = "⣀"
PARTICLE_MID = "⣶"
PARTICLE_HOT = "⣿"


class RMSMeter:
    def __init__(self, style: str = "dual"):
        self._style = style
        self._level_l = -60.0
        self._level_r = -60.0

    def _ballistic(self, current: float, target: float) -> float:
        if target > current:
            return target
        return max(target, current - DECAY_RATE)

    def render(
        self,
        win,
        rms_db: float,
        peak_db: float,
        palette,
        rms_db_l: float | None = None,
        rms_db_r: float | None = None,
        peak_db_l: float | None = None,
        peak_db_r: float | None = None,
    ) -> None:
        left_rms = rms_db if rms_db_l is None else rms_db_l
        right_rms = rms_db if rms_db_r is None else rms_db_r
        left_peak = peak_db if peak_db_l is None else peak_db_l
        right_peak = peak_db if peak_db_r is None else peak_db_r
        self._level_l = self._ballistic(self._level_l, left_rms)
        self._level_r = self._ballistic(self._level_r, right_rms)

        {
            "dual": self._render_dual,
            "bar": self._render_bar,
            "segmented": self._render_segmented,
        }.get(self._style, self._render_dual)(win, self._level_l, self._level_r, left_peak, right_peak, palette)

    def _norm(self, db: float, length: int) -> int:
        return max(0, min(int((db + 60) / 60 * length), length))

    def _render_dual(self, win, rms_l: float, rms_r: float, peak_l: float, peak_r: float, palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 6, 1)
        rms_fill_l = self._norm(rms_l, w)
        rms_fill_r = self._norm(rms_r, w)
        pk_l = self._norm(peak_l, w)
        pk_r = self._norm(peak_r, w)
        y_l = max(0, rows // 2 - 1)
        y_r = min(rows - 1, y_l + 1)
        try:
            win.addstr(0, 0, "RMS", palette.dim)
            win.addstr(y_l, 0, "L ", palette.dim)
            level_attr_l = meter_level_attr(rms_l, palette)
            for i in range(w):
                lit_l = i < rms_fill_l
                attr_l = hotter_attr(meter_zone_attr(i, w, palette), level_attr_l, palette) if lit_l else palette.bg
                glyph_l = PARTICLE_HOT if attr_l in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_l == palette.mid else PARTICLE_DIM
                win.addstr(y_l, 2 + i, glyph_l if lit_l else " ", attr_l)
            win.addstr(y_r, 0, "R ", palette.dim)
            level_attr_r = meter_level_attr(rms_r, palette)
            for i in range(w):
                lit_r = i < rms_fill_r
                attr_r = hotter_attr(meter_zone_attr(i, w, palette), level_attr_r, palette) if lit_r else palette.bg
                glyph_r = PARTICLE_HOT if attr_r in (palette.warn, palette.clip, palette.bright) else PARTICLE_MID if attr_r == palette.mid else PARTICLE_DIM
                win.addstr(y_r, 2 + i, glyph_r if lit_r else " ", attr_r)
            if w > 0:
                marker_l = int(min(2 + max(pk_l - 1, 0), w + 1))
                marker_r = int(min(2 + max(pk_r - 1, 0), w + 1))
                win.addstr(y_l, marker_l, "▏", palette.peak)
                win.addstr(y_r, marker_r, "▏", palette.peak)
        except curses.error:
            pass

    def _render_bar(self, win, rms_l: float, rms_r: float, peak_l: float, peak_r: float, palette) -> None:
        self._render_dual(win, rms_l, rms_r, peak_l, peak_r, palette)

    def _render_segmented(self, win, rms_l: float, rms_r: float, peak_l: float, peak_r: float, palette) -> None:
        self._render_dual(win, rms_l, rms_r, peak_l, peak_r, palette)
