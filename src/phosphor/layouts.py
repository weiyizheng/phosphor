from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Layout:
    panes: Dict[str, Dict[str, Any]]


def build_layout(preset: str, screen) -> Layout:
    rows, cols = screen.getmaxyx()

    if preset == "classic":
        spectrum_rows = int(rows * 0.7)
        meter_rows = rows - spectrum_rows
        spectrum_win = screen.derwin(spectrum_rows, cols, 0, 0)
        meter_win = screen.derwin(meter_rows, cols, spectrum_rows, 0)
        return Layout(
            panes={
                "spectrum": {"rows": spectrum_rows, "cols": cols, "y": 0, "x": 0, "window": spectrum_win},
                "meters": {"rows": meter_rows, "cols": cols, "y": spectrum_rows, "x": 0, "window": meter_win},
            }
        )

    if preset == "dashboard":
        spectrum_cols = cols // 2
        meter_cols = cols - spectrum_cols
        spectrum_win = screen.derwin(rows, spectrum_cols, 0, 0)
        meter_win = screen.derwin(rows, meter_cols, 0, spectrum_cols)
        return Layout(
            panes={
                "spectrum": {"rows": rows, "cols": spectrum_cols, "y": 0, "x": 0, "window": spectrum_win},
                "meters": {"rows": rows, "cols": meter_cols, "y": 0, "x": spectrum_cols, "window": meter_win},
            }
        )

    return build_layout("classic", screen)


def split_meter_pane(pane: Dict[str, Any], meter_names: list[str]) -> Dict[str, Dict[str, Any]]:
    rows, cols = pane["rows"], pane["cols"]
    y0, x0 = pane["y"], pane["x"]
    parent = pane["window"]
    n = max(len(meter_names), 1)
    meter_cols = max(cols // n, 1)
    out: Dict[str, Dict[str, Any]] = {}

    for i, name in enumerate(meter_names):
        x = x0 + i * meter_cols
        w = cols - (i * meter_cols) if i == n - 1 else meter_cols
        win = parent.derwin(rows, w, 0, i * meter_cols)
        out[name] = {"rows": rows, "cols": w, "y": y0, "x": x, "window": win}

    return out
