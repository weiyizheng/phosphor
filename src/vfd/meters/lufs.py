from __future__ import annotations

import curses
from typing import List

SPARKLINE = " .:-=+*#%@"
TARGETS = {"Spotify": -14, "YouTube": -14, "Apple": -16, "Broadcast": -23}


class LUFSMeter:
    def __init__(self, style: str = "graph"):
        self._style = style

    def render(
        self,
        win,
        momentary: float,
        shortterm: float,
        integrated: float,
        history: List[float],
        palette,
    ) -> None:
        {
            "graph": self._render_graph,
            "target": self._render_target,
            "numeric": self._render_numeric,
        }.get(self._style, self._render_graph)(
            win, momentary, shortterm, integrated, history, palette
        )

    def _render_graph(self, win, m: float, st: float, i: float, history: List[float], palette) -> None:
        rows, cols = win.getmaxyx()
        try:
            win.addstr(0, 0, "LUFS~", palette.dim)
            win.addstr(1, 0, f"M  {m:>+6.1f}", palette.bright)
            win.addstr(2, 0, f"ST {st:>+6.1f}", palette.mid)
            win.addstr(3, 0, f"I  {i:>+6.1f}", palette.dim)

            if rows > 5 and history:
                graph_cols = max(min(cols - 1, len(history)), 1)
                recent = history[-graph_cols:]
                line = ""
                for val in recent:
                    idx = int((val + 36.0) / 36.0 * (len(SPARKLINE) - 1))
                    idx = max(0, min(idx, len(SPARKLINE) - 1))
                    line += SPARKLINE[idx]
                win.addstr(5, 0, line[: cols - 1], palette.mid)
        except curses.error:
            pass

    def _render_target(self, win, m: float, st: float, i: float, history: List[float], palette) -> None:
        rows, cols = win.getmaxyx()
        w = max(cols - 2, 1)
        fill = max(0, min(int((i + 36) / 36 * w), w))
        y = max(1, rows // 2)
        try:
            win.addstr(0, 0, "LUFS~ TARGET", palette.dim)
            for x in range(w):
                win.addstr(y, x, "=" if x < fill else ".", palette.mid if x < fill else palette.bg)
            r = min(y + 1, rows - 1)
            text = " ".join([f"{k}:{v}" for k, v in TARGETS.items()])
            win.addstr(r, 0, text[: cols - 1], palette.dim)
        except curses.error:
            pass

    def _render_numeric(self, win, m: float, st: float, i: float, history: List[float], palette) -> None:
        rows, cols = win.getmaxyx()
        mid = max(0, rows // 2 - 1)
        try:
            win.addstr(0, 0, "LUFS~", palette.dim)
            win.addstr(mid, 0, f"M  {m:>+6.1f}", palette.bright)
            if mid + 1 < rows:
                win.addstr(mid + 1, 0, f"ST {st:>+6.1f}", palette.mid)
            if mid + 2 < rows:
                win.addstr(mid + 2, 0, f"I  {i:>+6.1f}", palette.dim)
        except curses.error:
            pass
