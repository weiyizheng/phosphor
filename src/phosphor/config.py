from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import tomllib
import warnings

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "phosphor" / "config.toml"

VALID_COLORS = ("green", "amber", "blue", "white", "btop", "hifi")
VALID_BANDS = (32, 64, 128, "auto")
VALID_LAYOUTS = ("classic", "dashboard")
VALID_VU_STYLES = ("segmented", "bar", "needle")
VALID_PEAK_STYLES = ("vertical", "horizontal", "ppm")
VALID_RMS_STYLES = ("dual", "bar", "segmented")
VALID_LUFS_STYLES = ("graph", "target", "numeric")
MAX_FPS = 240


class ConfigValidationError(ValueError):
    """Raised when config values are invalid."""


@dataclass
class Config:
    # Display
    color: str = "hifi"
    bands: Union[int, str] = 64
    fps: int = 60
    stereo: bool = True
    # Layout
    layout: str = "classic"
    split: Optional[str] = None
    # Meter styles
    vu_style: str = "segmented"
    peak_style: str = "vertical"
    rms_style: str = "dual"
    lufs_style: str = "graph"
    # Effects
    peak_hold: bool = True
    decay: bool = True
    glow: bool = True
    db_labels: bool = True
    freq_labels: bool = True
    # Device
    device: str = "BlackHole 2ch"


def validate_config(cfg: Config) -> Config:
    if cfg.color not in VALID_COLORS:
        raise ConfigValidationError(f"Invalid color '{cfg.color}'. Expected one of: {VALID_COLORS}.")

    if cfg.bands not in VALID_BANDS:
        raise ConfigValidationError(f"Invalid bands '{cfg.bands}'. Expected one of: {VALID_BANDS}.")

    if not isinstance(cfg.fps, int) or cfg.fps <= 0 or cfg.fps > MAX_FPS:
        raise ConfigValidationError(f"Invalid fps '{cfg.fps}'. Expected an integer in range 1..{MAX_FPS}.")

    if cfg.layout not in VALID_LAYOUTS:
        raise ConfigValidationError(f"Invalid layout '{cfg.layout}'. Expected one of: {VALID_LAYOUTS}.")

    if cfg.vu_style not in VALID_VU_STYLES:
        raise ConfigValidationError(
            f"Invalid vu_style '{cfg.vu_style}'. Expected one of: {VALID_VU_STYLES}."
        )

    if cfg.peak_style not in VALID_PEAK_STYLES:
        raise ConfigValidationError(
            f"Invalid peak_style '{cfg.peak_style}'. Expected one of: {VALID_PEAK_STYLES}."
        )

    if cfg.rms_style not in VALID_RMS_STYLES:
        raise ConfigValidationError(
            f"Invalid rms_style '{cfg.rms_style}'. Expected one of: {VALID_RMS_STYLES}."
        )

    if cfg.lufs_style not in VALID_LUFS_STYLES:
        raise ConfigValidationError(
            f"Invalid lufs_style '{cfg.lufs_style}'. Expected one of: {VALID_LUFS_STYLES}."
        )

    if not isinstance(cfg.stereo, bool):
        raise ConfigValidationError("Invalid stereo value. Expected true/false.")
    if not isinstance(cfg.peak_hold, bool):
        raise ConfigValidationError("Invalid peak_hold value. Expected true/false.")
    if not isinstance(cfg.decay, bool):
        raise ConfigValidationError("Invalid decay value. Expected true/false.")
    if not isinstance(cfg.glow, bool):
        raise ConfigValidationError("Invalid glow value. Expected true/false.")
    if not isinstance(cfg.db_labels, bool):
        raise ConfigValidationError("Invalid db_labels value. Expected true/false.")
    if not isinstance(cfg.freq_labels, bool):
        raise ConfigValidationError("Invalid freq_labels value. Expected true/false.")
    if not isinstance(cfg.device, str) or not cfg.device.strip():
        raise ConfigValidationError("Invalid device value. Expected a non-empty string.")

    return cfg


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Load config from TOML file, returning defaults if file is missing/invalid."""
    if not path.exists():
        return Config()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except OSError:
        return Config()
    except tomllib.TOMLDecodeError:
        warnings.warn(f"Config file is invalid TOML: {path}. Falling back to defaults.", RuntimeWarning)
        return Config()

    kwargs: dict[str, object] = {}
    for section in ("display", "meters", "effects", "device", "layout"):
        section_values = data.get(section, {})
        if isinstance(section_values, dict):
            kwargs.update({k: v for k, v in section_values.items() if hasattr(Config, k)})

    return validate_config(Config(**kwargs))


def generate_default_config() -> str:
    """Generate a fully-commented default configuration file."""
    return """\
# phosphor — VFD Audio Spectrum Analyzer Configuration
# All values shown are defaults. Uncomment and modify to customize.
# CLI flags always override config file values.
# Run `phosphor --help` for available flags.

[display]

# Controls the phosphor color of the VFD display.
# green, amber, blue, white, btop, hifi
color = "hifi"

# Number of frequency bands in the spectrum analyzer.
# 32, 64, 128, or "auto"
bands = 64

# Render framerate cap in frames per second.
fps = 60

# Show stereo channels separately (true) or sum to mono (false).
stereo = true

[layout]

# Layout preset: classic or dashboard
layout = "classic"

[meters]

# VU: segmented, bar, needle
vu_style = "segmented"

# Peak: vertical, horizontal, ppm
peak_style = "vertical"

# RMS: dual, bar, segmented
rms_style = "dual"

# LUFS: graph, target, numeric
lufs_style = "graph"

[effects]

# Peak hold marker on bars
peak_hold = true

# Smooth decay animation
# (false = immediate update)
decay = true

# Brighter bar top for phosphor glow
glow = true

# Show dB scale labels on spectrum
db_labels = true

# Show frequency labels on spectrum
freq_labels = true

[device]

# Audio device name to capture
device = "BlackHole 2ch"
"""
