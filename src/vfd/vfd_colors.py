from __future__ import annotations

import curses
from dataclasses import dataclass
from enum import IntEnum


class GlowLevel(IntEnum):
    BRIGHT = 3
    MID = 2
    DIM = 1


@dataclass
class VFDPalette:
    name: str
    bright: int
    mid: int
    dim: int
    peak: int
    bg: int
    warn: int
    clip: int


def meter_zone_attr(index: int, total: int, palette) -> int:
    ratio = (index + 1) / max(total, 1)
    return meter_zone_attr_ratio(ratio, palette)


def meter_zone_attr_ratio(ratio: float, palette) -> int:
    if ratio >= 0.9:
        return palette.clip
    if ratio >= 0.75:
        return palette.warn
    if ratio >= 0.45:
        return palette.mid
    return palette.dim


_PALETTE_OFFSET = {"green": 10, "amber": 20, "blue": 30, "white": 40}
_PALETTE_RGB = {
    "green": {
        "bright": (200, 1000, 200),
        "mid": (100, 700, 100),
        "dim": (50, 350, 50),
        "peak": (255, 1000, 255),
        "bg": (20, 80, 20),
        "warn": (1000, 680, 120),
        "clip": (1000, 180, 180),
    },
    "amber": {
        "bright": (1000, 700, 100),
        "mid": (800, 500, 60),
        "dim": (500, 300, 30),
        "peak": (1000, 800, 200),
        "bg": (80, 50, 10),
        "warn": (1000, 780, 220),
        "clip": (1000, 240, 160),
    },
    "blue": {
        "bright": (400, 700, 1000),
        "mid": (200, 450, 800),
        "dim": (100, 200, 500),
        "peak": (600, 900, 1000),
        "bg": (20, 40, 80),
        "warn": (1000, 720, 120),
        "clip": (1000, 160, 160),
    },
    "white": {
        "bright": (1000, 1000, 1000),
        "mid": (700, 700, 700),
        "dim": (400, 400, 400),
        "peak": (1000, 1000, 1000),
        "bg": (60, 60, 60),
        "warn": (1000, 720, 120),
        "clip": (1000, 160, 160),
    },
}

_initialized = False
_palettes: dict[str, VFDPalette] = {}


def init_colors() -> None:
    global _initialized
    if _initialized:
        return

    curses.start_color()
    curses.use_default_colors()

    if not curses.can_change_color():
        # Fallback pairs for terminals without custom color support.
        _palettes.update(
            {
                "green": VFDPalette("green", curses.A_BOLD, curses.A_NORMAL, curses.A_DIM, curses.A_BOLD, curses.A_DIM, curses.A_BOLD, curses.A_BOLD),
                "amber": VFDPalette("amber", curses.A_BOLD, curses.A_NORMAL, curses.A_DIM, curses.A_BOLD, curses.A_DIM, curses.A_BOLD, curses.A_BOLD),
                "blue": VFDPalette("blue", curses.A_BOLD, curses.A_NORMAL, curses.A_DIM, curses.A_BOLD, curses.A_DIM, curses.A_BOLD, curses.A_BOLD),
                "white": VFDPalette("white", curses.A_BOLD, curses.A_NORMAL, curses.A_DIM, curses.A_BOLD, curses.A_DIM, curses.A_BOLD, curses.A_BOLD),
            }
        )
        _initialized = True
        return

    bg_color = -1
    color_index = 100
    for name, levels in _PALETTE_RGB.items():
        offset = _PALETTE_OFFSET[name]
        pair_indices: dict[str, int] = {}
        for i, level in enumerate(("bright", "mid", "dim", "peak", "bg", "warn", "clip")):
            r, g, b = levels[level]
            curses.init_color(color_index, r, g, b)
            pair_num = offset + i
            curses.init_pair(pair_num, color_index, bg_color)
            pair_indices[level] = curses.color_pair(pair_num)
            color_index += 1

        _palettes[name] = VFDPalette(
            name=name,
            bright=pair_indices["bright"] | curses.A_BOLD,
            mid=pair_indices["mid"],
            dim=pair_indices["dim"],
            peak=pair_indices["peak"] | curses.A_BOLD,
            bg=pair_indices["bg"],
            warn=pair_indices["warn"] | curses.A_BOLD,
            clip=pair_indices["clip"] | curses.A_BOLD,
        )

    _initialized = True


def get_palette(name: str) -> VFDPalette:
    if not _initialized:
        return VFDPalette(name=name, bright=1, mid=2, dim=3, peak=4, bg=5, warn=6, clip=7)
    return _palettes.get(name, _palettes.get("green", VFDPalette("green", 1, 2, 3, 4, 5, 6, 7)))
