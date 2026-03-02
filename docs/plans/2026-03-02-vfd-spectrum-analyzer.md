# VFD Audio Spectrum Analyzer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a macOS CLI app (`vfd`) that captures system audio via BlackHole and renders a real-time VFD-style spectrum analyzer and audio meters in the terminal.

**Architecture:** Three-layer pipeline — AudioCapture (sounddevice + ring buffer) → SpectrumAnalyzer (numpy FFT + meter math) → VFDRenderer (curses per-cell rendering). Layers are decoupled so each can be tested independently. Config merges CLI flags over TOML file over hardcoded defaults.

**Tech Stack:** Python 3.11+, sounddevice, numpy, scipy, curses (stdlib), click (CLI), toml (stdlib 3.11+), pipx (distribution)

**Design doc:** `docs/plans/2026-03-02-vfd-spectrum-analyzer-design.md`

---

## Project Structure

```
vfd/
├── pyproject.toml
├── README.md
├── src/
│   └── vfd/
│       ├── __init__.py
│       ├── __main__.py          # entry point
│       ├── cli.py               # click CLI + config merge
│       ├── config.py            # config dataclass + TOML load/save
│       ├── capture.py           # AudioCapture + ring buffer
│       ├── analyzer.py          # SpectrumAnalyzer (FFT, RMS, peak, LUFS)
│       ├── renderer.py          # VFDRenderer (curses orchestrator)
│       ├── layouts.py           # layout/pane system
│       └── meters/
│           ├── __init__.py
│           ├── spectrum.py      # spectrum bars
│           ├── vu.py            # VU meter styles
│           ├── peak.py          # Peak meter styles
│           ├── rms.py           # RMS meter styles
│           └── lufs.py          # LUFS meter styles
└── tests/
    ├── test_config.py
    ├── test_analyzer.py
    ├── test_capture.py
    ├── test_layouts.py
    └── meters/
        ├── test_spectrum.py
        ├── test_vu.py
        ├── test_peak.py
        ├── test_rms.py
        └── test_lufs.py
```

---

### Task 1: Project scaffold

**Files:**
- Create: `vfd/pyproject.toml`
- Create: `vfd/src/vfd/__init__.py`
- Create: `vfd/src/vfd/__main__.py`

**Step 1: Create project directory and pyproject.toml**

```bash
mkdir -p vfd/src/vfd/meters vfd/tests/meters
```

`vfd/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "vfd"
version = "0.1.0"
description = "VFD Audio Spectrum Analyzer for macOS"
requires-python = ">=3.11"
dependencies = [
    "sounddevice>=0.4.6",
    "numpy>=1.26",
    "scipy>=1.12",
    "click>=8.1",
]

[project.scripts]
vfd = "vfd.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/vfd"]
```

**Step 2: Create entry point**

`vfd/src/vfd/__main__.py`:
```python
from vfd.cli import main

if __name__ == "__main__":
    main()
```

`vfd/src/vfd/__init__.py`:
```python
__version__ = "0.1.0"
```

**Step 3: Install in dev mode**

```bash
cd vfd && pip install -e ".[dev]" 2>/dev/null || pip install -e .
```

**Step 4: Verify entry point exists**

```bash
python -m vfd --help
```
Expected: No error (even if empty for now)

**Step 5: Commit**

```bash
git init && git add . && git commit -m "chore: scaffold vfd project"
```

---

### Task 2: Config system

**Files:**
- Create: `vfd/src/vfd/config.py`
- Create: `vfd/tests/test_config.py`

**Step 1: Write failing tests**

`vfd/tests/test_config.py`:
```python
import pytest
from pathlib import Path
from vfd.config import Config, load_config, DEFAULT_CONFIG_PATH

def test_default_config_values():
    config = Config()
    assert config.color == "green"
    assert config.bands == 64
    assert config.fps == 60
    assert config.stereo is True
    assert config.layout == "classic"
    assert config.vu_style == "segmented"
    assert config.peak_style == "vertical"
    assert config.rms_style == "dual"
    assert config.lufs_style == "graph"
    assert config.peak_hold is True
    assert config.decay is True
    assert config.glow is True
    assert config.db_labels is True
    assert config.freq_labels is True
    assert config.device == "BlackHole 2ch"

def test_load_config_from_toml(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text('[display]\ncolor = "amber"\nbands = 32\n')
    config = load_config(toml_file)
    assert config.color == "amber"
    assert config.bands == 32
    # unset values fall back to defaults
    assert config.fps == 60

def test_load_config_missing_file(tmp_path):
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.color == "green"  # returns defaults

def test_config_merge_flags():
    config = Config(color="blue", bands=128)
    assert config.color == "blue"
    assert config.bands == 128
    assert config.fps == 60  # default preserved
```

**Step 2: Run tests to verify they fail**

```bash
cd vfd && python -m pytest tests/test_config.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'vfd.config'`

**Step 3: Implement config.py**

`vfd/src/vfd/config.py`:
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import tomllib

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "vfd" / "config.toml"

VALID_COLORS = ("green", "amber", "blue", "white")
VALID_BANDS = (32, 64, 128, "auto")
VALID_LAYOUTS = ("classic", "dashboard")
VALID_SPLITS = ("vertical", "horizontal", "quad", "main", "tiled")
VALID_VU_STYLES = ("segmented", "bar", "needle")
VALID_PEAK_STYLES = ("vertical", "horizontal", "ppm")
VALID_RMS_STYLES = ("dual", "bar", "segmented")
VALID_LUFS_STYLES = ("graph", "target", "numeric")


@dataclass
class Config:
    # Display
    color: str = "green"
    bands: int = 64
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


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Load config from TOML file, returning defaults if file missing."""
    if not path.exists():
        return Config()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    kwargs = {}
    display = data.get("display", {})
    kwargs.update({k: v for k, v in display.items() if hasattr(Config, k)})

    meters = data.get("meters", {})
    kwargs.update({k: v for k, v in meters.items() if hasattr(Config, k)})

    effects = data.get("effects", {})
    kwargs.update({k: v for k, v in effects.items() if hasattr(Config, k)})

    device_section = data.get("device", {})
    kwargs.update({k: v for k, v in device_section.items() if hasattr(Config, k)})

    layout_section = data.get("layout", {})
    kwargs.update({k: v for k, v in layout_section.items() if hasattr(Config, k)})

    return Config(**kwargs)
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_config.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/config.py tests/test_config.py
git commit -m "feat: add config system with TOML load and defaults"
```

---

### Task 3: Config file generator (commented TOML)

**Files:**
- Modify: `vfd/src/vfd/config.py`
- Create: `vfd/tests/test_config_generate.py`

**Step 1: Write failing test**

`vfd/tests/test_config_generate.py`:
```python
from vfd.config import generate_default_config

def test_generate_config_contains_comments():
    content = generate_default_config()
    assert "# Controls the phosphor color" in content
    assert "color = " in content
    assert "bands = " in content
    assert "fps = " in content

def test_generate_config_is_valid_toml(tmp_path):
    import tomllib
    content = generate_default_config()
    path = tmp_path / "config.toml"
    path.write_text(content)
    with open(path, "rb") as f:
        data = tomllib.load(f)
    assert data["display"]["color"] == "green"
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_config_generate.py -v
```
Expected: FAIL

**Step 3: Implement generate_default_config**

Add to `vfd/src/vfd/config.py`:
```python
def generate_default_config() -> str:
    """Generate a fully-commented default config file as a string."""
    return """\
# vfd — VFD Audio Spectrum Analyzer Configuration
# All values shown are defaults. Uncomment and modify to customize.
# CLI flags always override config file values.
# Run `vfd --help` for available flags.

[display]

# Controls the phosphor color of the VFD display.
# Simulates different eras of vacuum fluorescent hardware:
#   green  — classic Futaba/Noritake VFD phosphor (default)
#   amber  — warm vintage hi-fi receiver aesthetic
#   blue   — modern Sony/Pioneer equipment style
#   white  — high-brightness neutral display
# Override at runtime: vfd --color amber
color = "green"

# Number of frequency bands in the spectrum analyzer.
# More bands = more detail but requires a wider terminal.
#   32   — coarse, classic "bar graph EQ" look
#   64   — good balance of detail and readability (default)
#   128  — dense, cinematic; requires ~130 column terminal
#   auto — fills available terminal width
# Override at runtime: vfd --bands 128
bands = 64

# Render framerate cap in frames per second.
# Lower values reduce CPU usage. 60fps is smooth at typical terminal sizes.
# Override at runtime: vfd --fps 30
fps = 60

# Show stereo L/R channels separately (true) or sum to mono (false).
# Override at runtime: vfd --mono  (sets stereo = false)
stereo = true

[layout]

# Layout preset controlling how meters are arranged on screen.
#   classic    — spectrum top (~70%), meters row along the bottom (default)
#   dashboard  — spectrum left, meters stacked on the right
# Override at runtime: vfd --layout dashboard
layout = "classic"

# Custom panel split type. Only used when layout = "custom".
# Overrides the preset layout entirely. Assign meters to panes below.
#   vertical    — left | right (2 panes)
#   horizontal  — top / bottom (2 panes)
#   quad        — 2×2 grid (4 panes)
#   main        — one large pane + smaller surrounding panes
#   tiled       — all panes equal size in a grid
# split = "horizontal"

# Assign meters to panes when using a custom split.
# Available meters: spectrum, vu, peak, rms, lufs
# [layout.panes]
# top = "spectrum"
# bottom = ["vu", "peak", "rms", "lufs"]

[meters]

# VU meter display style.
# VU shows average loudness with ballistic (bouncy) decay animation.
#   segmented — discrete lit/unlit block segments, classic hi-fi VFD look (default)
#   bar       — continuous horizontal fill bar with ballistic decay
#   needle    — ASCII arc sweep simulating a physical analog VU needle
vu_style = "segmented"

# Peak meter display style.
# Peak shows instantaneous highest sample — useful for detecting clipping.
#   vertical    — two vertical bars (L/R) with peak hold line at top (default)
#   horizontal  — horizontal stereo bars, snaps immediately to peak value
#   ppm         — segmented ladder, BBC/EBU PPM broadcast scale
peak_style = "vertical"

# RMS meter display style.
# RMS (root mean square) shows perceived loudness averaged over ~300ms.
#   dual      — horizontal bar: RMS fill + instantaneous peak marker overlay (default)
#   bar       — continuous bar, slower/smoother movement than VU
#   segmented — discrete block segments
rms_style = "dual"

# LUFS meter display style.
# LUFS is the broadcast/streaming loudness standard (Spotify: -14, broadcast: -23).
# Tracks momentary (M, 400ms window), short-term (ST, 3s), and integrated (I, full session).
#   graph    — scrolling loudness history graph + live M/ST/I numeric readout (default)
#   target   — horizontal bar showing position relative to platform targets
#   numeric  — minimal three-number readout only (M / ST / I)
lufs_style = "graph"

[effects]

# Show peak hold indicators on bar-style meters.
# A dot/dash marker hangs at the recent peak then slowly falls back down.
# Applies to: spectrum bars, VU bar, peak meters, RMS bar.
peak_hold = true

# Enable smooth decay animation on bars.
# Bars fall gradually rather than snapping to the current level each frame.
decay = true

# Enable phosphor glow effect on bar tops.
# Uses brighter/bolder characters at the top of each bar to simulate
# the bloom of a real VFD phosphor element.
glow = true

# Show dB scale labels on the Y-axis of the spectrum analyzer.
db_labels = true

# Show frequency labels on the X-axis of the spectrum analyzer.
# Labels shown at key frequencies: 20Hz, 100Hz, 500Hz, 1kHz, 5kHz, 10kHz, 20kHz.
freq_labels = true

[device]

# Audio input device to capture from.
# This should be BlackHole 2ch, or an Aggregate Device that includes BlackHole.
# Run `vfd --list-devices` to see all available audio input devices.
# For normal audio playback while capturing, set up an Aggregate Device in
# macOS Audio MIDI Setup combining BlackHole + your speakers/headphones,
# then set that Aggregate Device as your system output.
# Run `vfd --setup` for a step-by-step setup guide.
device = "BlackHole 2ch"
"""
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_config_generate.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/config.py tests/test_config_generate.py
git commit -m "feat: add commented default config file generator"
```

---

### Task 4: CLI entry point

**Files:**
- Create: `vfd/src/vfd/cli.py`

**Step 1: Implement CLI**

`vfd/src/vfd/cli.py`:
```python
import sys
import click
from pathlib import Path
from vfd.config import Config, load_config, DEFAULT_CONFIG_PATH, generate_default_config

@click.command()
@click.option("--color", type=click.Choice(["green", "amber", "blue", "white"]), help="Phosphor color preset")
@click.option("--bands", type=click.Choice(["32", "64", "128", "auto"]), help="Number of frequency bands")
@click.option("--fps", type=int, default=None, help="Render framerate cap")
@click.option("--mono", is_flag=True, default=False, help="Sum stereo to mono")
@click.option("--layout", type=click.Choice(["classic", "dashboard"]), help="Layout preset")
@click.option("--mode", type=click.Choice(["spectrum", "vu", "peak", "rms", "lufs"]), help="Fullscreen single meter")
@click.option("--device", type=str, default=None, help="Audio input device name")
@click.option("--list-devices", is_flag=True, default=False, help="List available audio input devices")
@click.option("--setup", is_flag=True, default=False, help="Run first-run setup guide")
@click.option("--config", type=click.Path(), default=None, help=f"Config file path (default: {DEFAULT_CONFIG_PATH})")
def main(color, bands, fps, mono, layout, mode, device, list_devices, setup, config):
    """VFD Audio Spectrum Analyzer — real-time terminal audio visualization."""

    if list_devices:
        _list_devices()
        return

    if setup:
        _print_setup_guide()
        return

    config_path = Path(config) if config else DEFAULT_CONFIG_PATH
    cfg = load_config(config_path)

    # CLI flags override config
    if color:
        cfg.color = color
    if bands:
        cfg.bands = int(bands) if bands != "auto" else "auto"
    if fps:
        cfg.fps = fps
    if mono:
        cfg.stereo = False
    if layout:
        cfg.layout = layout
    if device:
        cfg.device = device

    _ensure_config_file(config_path)
    _run(cfg, mode)


def _list_devices():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        click.echo("Available audio input devices:\n")
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                click.echo(f"  [{i}] {d['name']}")
    except Exception as e:
        click.echo(f"Error querying devices: {e}", err=True)
        sys.exit(1)


def _print_setup_guide():
    click.echo("""
VFD Setup Guide
===============

Step 1: Install BlackHole
  brew install blackhole-2ch

Step 2: Create an Aggregate Device (so audio plays AND gets captured)
  1. Open Audio MIDI Setup (Applications > Utilities > Audio MIDI Setup)
  2. Click the + button at the bottom left → "Create Aggregate Device"
  3. Check both "BlackHole 2ch" and your speakers/headphones
  4. Name it something like "VFD Capture"

Step 3: Set system output
  1. Open System Settings > Sound > Output
  2. Select your new Aggregate Device

Step 4: Configure vfd
  Set device = "BlackHole 2ch" in ~/.config/vfd/config.toml
  (or use: vfd --device "BlackHole 2ch")

Step 5: Run vfd
  vfd
""")


def _ensure_config_file(path: Path):
    """Write default commented config if it doesn't exist yet."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generate_default_config())
        click.echo(f"Created default config at {path}")


def _run(cfg: Config, mode):
    from vfd.renderer import VFDRenderer
    renderer = VFDRenderer(cfg, mode)
    renderer.run()
```

**Step 2: Verify CLI help works**

```bash
python -m vfd --help
```
Expected: Clean help output listing all flags

**Step 3: Verify list-devices works**

```bash
python -m vfd --list-devices
```
Expected: List of audio devices (or error if sounddevice not installed yet)

**Step 4: Commit**

```bash
git add src/vfd/cli.py
git commit -m "feat: add CLI with all flags, setup guide, device listing"
```

---

### Task 5: Ring buffer

**Files:**
- Create: `vfd/src/vfd/ring_buffer.py`
- Create: `vfd/tests/test_ring_buffer.py`

**Step 1: Write failing tests**

`vfd/tests/test_ring_buffer.py`:
```python
import numpy as np
from vfd.ring_buffer import RingBuffer

def test_write_and_read():
    buf = RingBuffer(capacity=1024, channels=2)
    data = np.ones((512, 2), dtype=np.float32)
    buf.write(data)
    out = buf.read(512)
    assert out.shape == (512, 2)
    np.testing.assert_array_equal(out, data)

def test_read_returns_zeros_when_empty():
    buf = RingBuffer(capacity=1024, channels=2)
    out = buf.read(256)
    assert out.shape == (256, 2)
    np.testing.assert_array_equal(out, 0)

def test_overwrites_oldest_on_overflow():
    buf = RingBuffer(capacity=4, channels=1)
    buf.write(np.array([[1.0], [2.0], [3.0], [4.0]], dtype=np.float32))
    buf.write(np.array([[5.0]], dtype=np.float32))  # overflow by 1
    out = buf.read(4)
    # oldest sample (1.0) should be gone
    assert 1.0 not in out[:, 0]
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_ring_buffer.py -v
```
Expected: FAIL

**Step 3: Implement RingBuffer**

`vfd/src/vfd/ring_buffer.py`:
```python
import numpy as np
import threading


class RingBuffer:
    """Thread-safe ring buffer for audio PCM data."""

    def __init__(self, capacity: int, channels: int):
        self._buf = np.zeros((capacity, channels), dtype=np.float32)
        self._capacity = capacity
        self._channels = channels
        self._write_pos = 0
        self._available = 0
        self._lock = threading.Lock()

    def write(self, data: np.ndarray):
        with self._lock:
            n = len(data)
            for i in range(n):
                self._buf[self._write_pos % self._capacity] = data[i]
                self._write_pos += 1
            self._available = min(self._available + n, self._capacity)

    def read(self, n: int) -> np.ndarray:
        with self._lock:
            if self._available == 0:
                return np.zeros((n, self._channels), dtype=np.float32)
            start = (self._write_pos - self._available) % self._capacity
            out = np.zeros((n, self._channels), dtype=np.float32)
            available = min(n, self._available)
            for i in range(available):
                out[i] = self._buf[(start + i) % self._capacity]
            return out
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_ring_buffer.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/ring_buffer.py tests/test_ring_buffer.py
git commit -m "feat: add thread-safe ring buffer for audio capture"
```

---

### Task 6: Audio capture

**Files:**
- Create: `vfd/src/vfd/capture.py`
- Create: `vfd/tests/test_capture.py`

**Step 1: Write failing tests**

`vfd/tests/test_capture.py`:
```python
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from vfd.capture import AudioCapture, DeviceNotFoundError

def test_raises_if_device_not_found():
    with patch("sounddevice.query_devices", return_value=[
        {"name": "Built-in Microphone", "max_input_channels": 1},
    ]):
        with pytest.raises(DeviceNotFoundError):
            AudioCapture(device_name="BlackHole 2ch", sample_rate=44100, channels=2)

def test_find_device_index():
    devices = [
        {"name": "Built-in Microphone", "max_input_channels": 1},
        {"name": "BlackHole 2ch", "max_input_channels": 2},
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        capture = AudioCapture.__new__(AudioCapture)
        idx = capture._find_device(devices, "BlackHole 2ch")
        assert idx == 1

def test_read_returns_numpy_array():
    with patch("sounddevice.query_devices", return_value=[
        {"name": "BlackHole 2ch", "max_input_channels": 2},
    ]), patch("sounddevice.InputStream"):
        capture = AudioCapture(device_name="BlackHole 2ch", sample_rate=44100, channels=2)
        data = capture.read(512)
        assert isinstance(data, np.ndarray)
        assert data.shape[1] == 2
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_capture.py -v
```
Expected: FAIL

**Step 3: Implement AudioCapture**

`vfd/src/vfd/capture.py`:
```python
import numpy as np
import sounddevice as sd
from vfd.ring_buffer import RingBuffer


class DeviceNotFoundError(Exception):
    pass


class AudioCapture:
    def __init__(self, device_name: str, sample_rate: int = 44100, channels: int = 2, buffer_size: int = 8192):
        self._sample_rate = sample_rate
        self._channels = channels
        self._ring = RingBuffer(capacity=buffer_size, channels=channels)

        devices = sd.query_devices()
        device_idx = self._find_device(devices, device_name)
        if device_idx is None:
            raise DeviceNotFoundError(
                f"Device '{device_name}' not found.\n"
                f"Run `vfd --list-devices` to see available devices.\n"
                f"Run `vfd --setup` for setup instructions."
            )

        self._stream = sd.InputStream(
            device=device_idx,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=self._callback,
        )

    def _find_device(self, devices, name: str):
        for i, d in enumerate(devices):
            if name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
        return None

    def _callback(self, indata, frames, time, status):
        self._ring.write(indata.copy())

    def start(self):
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()

    def read(self, n: int) -> np.ndarray:
        return self._ring.read(n)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_capture.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/capture.py tests/test_capture.py
git commit -m "feat: add AudioCapture with BlackHole device detection"
```

---

### Task 7: Spectrum analyzer (FFT + meter math)

**Files:**
- Create: `vfd/src/vfd/analyzer.py`
- Create: `vfd/tests/test_analyzer.py`

**Step 1: Write failing tests**

`vfd/tests/test_analyzer.py`:
```python
import numpy as np
import pytest
from vfd.analyzer import SpectrumAnalyzer, AnalysisResult

def make_sine(freq_hz, duration_s=0.1, sample_rate=44100):
    t = np.linspace(0, duration_s, int(sample_rate * duration_s))
    wave = np.sin(2 * np.pi * freq_hz * t).astype(np.float32)
    return np.column_stack([wave, wave])  # stereo

def test_spectrum_returns_correct_band_count():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=32, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    assert len(result.spectrum_db) == 32

def test_spectrum_peaks_near_sine_frequency():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    # 1kHz should produce a notable peak somewhere in the upper half of bands
    assert max(result.spectrum_db) > min(result.spectrum_db) + 20

def test_rms_of_silence_is_very_low():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    silence = np.zeros((4410, 2), dtype=np.float32)
    result = analyzer.process(silence)
    assert result.rms_db < -60

def test_peak_of_full_scale_sine():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    assert result.peak_db > -3  # near 0dBFS for full-scale sine

def test_result_has_all_fields():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(440)
    result = analyzer.process(pcm)
    assert hasattr(result, "spectrum_db")
    assert hasattr(result, "rms_db")
    assert hasattr(result, "peak_db")
    assert hasattr(result, "lufs_momentary")
    assert hasattr(result, "lufs_shortterm")
    assert hasattr(result, "lufs_integrated")
    assert hasattr(result, "lufs_history")
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_analyzer.py -v
```
Expected: FAIL

**Step 3: Implement SpectrumAnalyzer**

`vfd/src/vfd/analyzer.py`:
```python
import numpy as np
from dataclasses import dataclass, field
from collections import deque
from typing import List
from scipy.signal import windows


@dataclass
class AnalysisResult:
    spectrum_db: List[float]
    rms_db: float
    peak_db: float
    lufs_momentary: float
    lufs_shortterm: float
    lufs_integrated: float
    lufs_history: List[float]  # last N shortterm values for graph


class SpectrumAnalyzer:
    def __init__(self, sample_rate: int, bands: int, channels: int):
        self._sample_rate = sample_rate
        self._bands = bands
        self._channels = channels
        self._fft_size = 2048
        self._window = windows.hann(self._fft_size)
        self._freq_bins = np.fft.rfftfreq(self._fft_size, d=1.0 / sample_rate)
        self._band_edges = self._log_band_edges(bands, 20, 20000)
        # LUFS history buffers
        self._momentary_buf = deque(maxlen=int(sample_rate * 0.4))
        self._shortterm_buf = deque(maxlen=int(sample_rate * 3))
        self._integrated_squares: List[float] = []
        self._lufs_history: deque = deque(maxlen=200)

    def _log_band_edges(self, bands: int, f_low: float, f_high: float):
        return np.logspace(np.log10(f_low), np.log10(f_high), bands + 1)

    def process(self, pcm: np.ndarray) -> AnalysisResult:
        mono = pcm.mean(axis=1)

        # FFT spectrum
        chunk = mono[-self._fft_size:] if len(mono) >= self._fft_size else np.pad(mono, (self._fft_size - len(mono), 0))
        windowed = chunk * self._window
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum_db = self._bin_to_bands(spectrum)

        # RMS
        rms = np.sqrt(np.mean(mono ** 2))
        rms_db = 20 * np.log10(max(rms, 1e-9))

        # Peak
        peak = np.max(np.abs(mono))
        peak_db = 20 * np.log10(max(peak, 1e-9))

        # LUFS (simplified K-weighting approximation)
        self._momentary_buf.extend(mono ** 2)
        self._shortterm_buf.extend(mono ** 2)
        self._integrated_squares.extend(mono ** 2)

        lufs_m = self._lkfs(list(self._momentary_buf))
        lufs_st = self._lkfs(list(self._shortterm_buf))
        lufs_i = self._lkfs(self._integrated_squares)

        self._lufs_history.append(lufs_st)

        return AnalysisResult(
            spectrum_db=spectrum_db,
            rms_db=rms_db,
            peak_db=peak_db,
            lufs_momentary=lufs_m,
            lufs_shortterm=lufs_st,
            lufs_integrated=lufs_i,
            lufs_history=list(self._lufs_history),
        )

    def _bin_to_bands(self, spectrum: np.ndarray) -> List[float]:
        bands = []
        for i in range(self._bands):
            lo, hi = self._band_edges[i], self._band_edges[i + 1]
            mask = (self._freq_bins >= lo) & (self._freq_bins < hi)
            if mask.any():
                val = np.mean(spectrum[mask])
            else:
                val = 1e-9
            bands.append(20 * np.log10(max(val, 1e-9)))
        return bands

    def _lkfs(self, squares: List[float]) -> float:
        if not squares:
            return -70.0
        mean_sq = np.mean(squares)
        return -0.691 + 10 * np.log10(max(mean_sq, 1e-9))
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_analyzer.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/analyzer.py tests/test_analyzer.py
git commit -m "feat: add SpectrumAnalyzer with FFT, RMS, peak, LUFS"
```

---

### Task 8: VFD color system + glow effect

**Files:**
- Create: `vfd/src/vfd/vfd_colors.py`
- Create: `vfd/tests/test_vfd_colors.py`

**Step 1: Write failing tests**

`vfd/tests/test_vfd_colors.py`:
```python
from vfd.vfd_colors import VFDPalette, get_palette, GlowLevel

def test_get_palette_green():
    p = get_palette("green")
    assert p.name == "green"
    assert p.bright is not None
    assert p.dim is not None
    assert p.peak is not None

def test_all_presets_available():
    for name in ("green", "amber", "blue", "white"):
        p = get_palette(name)
        assert p.name == name

def test_glow_levels():
    assert GlowLevel.BRIGHT > GlowLevel.MID
    assert GlowLevel.MID > GlowLevel.DIM
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_vfd_colors.py -v
```

**Step 3: Implement color system**

`vfd/src/vfd/vfd_colors.py`:
```python
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
    bright: int   # curses color pair index — top of bar / peak indicator
    mid: int      # curses color pair index — middle of bar
    dim: int      # curses color pair index — lower portion of bar
    peak: int     # curses color pair index — peak hold indicator
    bg: int       # curses color pair index — empty/background segments


# Color pair indices reserved per palette (5 pairs each, starting at offset)
_PALETTE_OFFSET = {
    "green": 10,
    "amber": 20,
    "blue":  30,
    "white": 40,
}

# (fg_r, fg_g, fg_b) in 0-1000 curses scale for each level
_PALETTE_RGB = {
    "green": {
        "bright": (200, 1000, 200),
        "mid":    (100,  700, 100),
        "dim":    ( 50,  350,  50),
        "peak":   (255, 1000, 255),
        "bg":     ( 20,   80,  20),
    },
    "amber": {
        "bright": (1000, 700, 100),
        "mid":    ( 800, 500,  60),
        "dim":    ( 500, 300,  30),
        "peak":   (1000, 800, 200),
        "bg":     (  80,  50,  10),
    },
    "blue": {
        "bright": (400, 700, 1000),
        "mid":    (200, 450,  800),
        "dim":    (100, 200,  500),
        "peak":   (600, 900, 1000),
        "bg":     ( 20,  40,   80),
    },
    "white": {
        "bright": (1000, 1000, 1000),
        "mid":    ( 700,  700,  700),
        "dim":    ( 400,  400,  400),
        "peak":   (1000, 1000, 1000),
        "bg":     (  60,   60,   60),
    },
}

_initialized = False
_palettes: dict[str, VFDPalette] = {}


def init_colors():
    """Call once after curses.initscr(). Registers all color pairs."""
    global _initialized
    if _initialized:
        return
    curses.start_color()
    curses.use_default_colors()
    bg_color = -1  # transparent background

    color_index = 100  # start custom colors above system colors

    for name, levels in _PALETTE_RGB.items():
        offset = _PALETTE_OFFSET[name]
        pair_indices = {}
        for i, level in enumerate(("bright", "mid", "dim", "peak", "bg")):
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
        )

    _initialized = True


def get_palette(name: str) -> VFDPalette:
    if not _initialized:
        # Return a stub for testing outside curses
        return VFDPalette(name=name, bright=1, mid=2, dim=3, peak=4, bg=5)
    return _palettes.get(name, _palettes["green"])
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_vfd_colors.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/vfd_colors.py tests/test_vfd_colors.py
git commit -m "feat: add VFD color palette system with glow levels"
```

---

### Task 9: Spectrum meter renderer

**Files:**
- Create: `vfd/src/vfd/meters/spectrum.py`
- Create: `vfd/tests/meters/test_spectrum.py`

**Step 1: Write failing tests**

`vfd/tests/meters/test_spectrum.py`:
```python
import pytest
from unittest.mock import MagicMock
from vfd.meters.spectrum import SpectrumMeter

def make_mock_window(rows=30, cols=80):
    win = MagicMock()
    win.getmaxyx.return_value = (rows, cols)
    return win

def test_render_does_not_crash():
    meter = SpectrumMeter(peak_hold=True, decay=True, glow=True,
                          db_labels=True, freq_labels=True, color="green")
    win = make_mock_window()
    bands_db = [-60.0 + i for i in range(64)]
    meter.render(win, bands_db, palette=MagicMock())

def test_decay_smooths_values():
    meter = SpectrumMeter(peak_hold=True, decay=True, glow=True,
                          db_labels=False, freq_labels=False, color="green")
    win = make_mock_window()
    palette = MagicMock()
    bands_high = [0.0] * 64
    bands_low = [-60.0] * 64
    meter.render(win, bands_high, palette=palette)
    meter.render(win, bands_low, palette=palette)
    # after one frame of decay, internal levels should be between high and low
    assert all(-60.0 < v < 0.0 for v in meter._levels)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/meters/test_spectrum.py -v
```

**Step 3: Implement SpectrumMeter**

`vfd/src/vfd/meters/spectrum.py`:
```python
import curses
from typing import List

DECAY_RATE = 3.0   # dB per frame to decay
PEAK_HOLD_FRAMES = 45
BAR_CHARS = " ▁▂▃▄▅▆▇█"


class SpectrumMeter:
    def __init__(self, peak_hold: bool, decay: bool, glow: bool,
                 db_labels: bool, freq_labels: bool, color: str):
        self._peak_hold = peak_hold
        self._decay = decay
        self._glow = glow
        self._db_labels = db_labels
        self._freq_labels = freq_labels
        self._color = color
        self._levels: List[float] = []
        self._peaks: List[float] = []
        self._peak_timers: List[int] = []

    def render(self, win, bands_db: List[float], palette):
        rows, cols = win.getmaxyx()
        n = len(bands_db)

        if not self._levels:
            self._levels = list(bands_db)
            self._peaks = list(bands_db)
            self._peak_timers = [0] * n

        label_rows = 1 if self._freq_labels else 0
        scale_cols = 5 if self._db_labels else 0
        bar_rows = rows - label_rows - 1
        bar_cols = cols - scale_cols
        bar_width = max(1, bar_cols // n)

        db_min, db_max = -80.0, 0.0

        for i in range(n):
            target = bands_db[i]
            if self._decay:
                self._levels[i] = max(target, self._levels[i] - DECAY_RATE)
            else:
                self._levels[i] = target

            if self._peak_hold:
                if target >= self._peaks[i]:
                    self._peaks[i] = target
                    self._peak_timers[i] = PEAK_HOLD_FRAMES
                else:
                    if self._peak_timers[i] > 0:
                        self._peak_timers[i] -= 1
                    else:
                        self._peaks[i] = max(self._peaks[i] - DECAY_RATE, target)

            level = self._levels[i]
            filled = int((level - db_min) / (db_max - db_min) * bar_rows)
            filled = max(0, min(filled, bar_rows))
            x = scale_cols + i * bar_width

            for row_idx in range(bar_rows):
                y = bar_rows - row_idx  # bottom = row bar_rows, top = row 1
                if y >= rows - label_rows:
                    continue
                if row_idx < filled:
                    # choose glow level
                    if self._glow and row_idx >= filled - 2:
                        attr = palette.bright
                    elif row_idx >= filled // 2:
                        attr = palette.mid
                    else:
                        attr = palette.dim
                    char = "█"
                else:
                    attr = palette.bg
                    char = "░"
                try:
                    win.addstr(y, x, char * bar_width, attr)
                except curses.error:
                    pass

            # peak hold indicator
            if self._peak_hold and self._peak_timers[i] > 0:
                peak_row = bar_rows - int((self._peaks[i] - db_min) / (db_max - db_min) * bar_rows)
                peak_row = max(1, min(peak_row, bar_rows))
                try:
                    win.addstr(peak_row, x, "▀" * bar_width, palette.peak)
                except curses.error:
                    pass
```

**Step 4: Run tests**

```bash
python -m pytest tests/meters/test_spectrum.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/meters/spectrum.py tests/meters/test_spectrum.py src/vfd/meters/__init__.py
git commit -m "feat: add spectrum meter renderer with glow and peak hold"
```

---

### Task 10: VU, Peak, RMS, LUFS meter renderers

**Files:**
- Create: `vfd/src/vfd/meters/vu.py`
- Create: `vfd/src/vfd/meters/peak.py`
- Create: `vfd/src/vfd/meters/rms.py`
- Create: `vfd/src/vfd/meters/lufs.py`
- Create: `vfd/tests/meters/test_vu.py`
- Create: `vfd/tests/meters/test_peak.py`
- Create: `vfd/tests/meters/test_rms.py`
- Create: `vfd/tests/meters/test_lufs.py`

**Step 1: Write failing tests for all four**

`vfd/tests/meters/test_vu.py`:
```python
from unittest.mock import MagicMock
from vfd.meters.vu import VUMeter

def test_render_segmented_does_not_crash():
    meter = VUMeter(style="segmented")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, rms_db=-12.0, palette=MagicMock())

def test_render_bar_does_not_crash():
    meter = VUMeter(style="bar")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, rms_db=-6.0, palette=MagicMock())

def test_render_needle_does_not_crash():
    meter = VUMeter(style="needle")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, rms_db=-3.0, palette=MagicMock())
```

`vfd/tests/meters/test_peak.py`:
```python
from unittest.mock import MagicMock
from vfd.meters.peak import PeakMeter

def test_render_vertical_does_not_crash():
    meter = PeakMeter(style="vertical", peak_hold=True)
    win = MagicMock()
    win.getmaxyx.return_value = (20, 20)
    meter.render(win, peak_db=-3.0, palette=MagicMock())
```

`vfd/tests/meters/test_rms.py`:
```python
from unittest.mock import MagicMock
from vfd.meters.rms import RMSMeter

def test_render_dual_does_not_crash():
    meter = RMSMeter(style="dual")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, rms_db=-14.0, peak_db=-8.0, palette=MagicMock())
```

`vfd/tests/meters/test_lufs.py`:
```python
from unittest.mock import MagicMock
from vfd.meters.lufs import LUFSMeter

def test_render_graph_does_not_crash():
    meter = LUFSMeter(style="graph")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, momentary=-14.0, shortterm=-15.0, integrated=-16.0,
                 history=[-15.0] * 50, palette=MagicMock())
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/meters/ -v
```

**Step 3: Implement all four meters**

Each meter follows the same pattern — dispatch to a `_render_<style>` method.
See design doc for visual descriptions. Implement minimal versions that render
correct characters without crashing; visual polish is iterative.

`vfd/src/vfd/meters/vu.py` — implement `VUMeter` with `segmented`, `bar`, `needle` styles
`vfd/src/vfd/meters/peak.py` — implement `PeakMeter` with `vertical`, `horizontal`, `ppm` styles
`vfd/src/vfd/meters/rms.py` — implement `RMSMeter` with `dual`, `bar`, `segmented` styles
`vfd/src/vfd/meters/lufs.py` — implement `LUFSMeter` with `graph`, `target`, `numeric` styles

Key implementation notes:
- VU needle: compute position as `int((db + 20) / 23 * cols)` for -20dB to +3dB range
- LUFS graph: scroll `history` left by one each frame, plot as sparkline using `▁▂▃▄▅▆▇█`
- PPM scale: map -36dB to +6dB across 7 segments, light up filled ones
- All meters: wrap `win.addstr` calls in `try/except curses.error` to handle resize events

**Step 4: Run tests**

```bash
python -m pytest tests/meters/ -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/meters/ tests/meters/
git commit -m "feat: add VU, Peak, RMS, LUFS meter renderers"
```

---

### Task 11: Layout system

**Files:**
- Create: `vfd/src/vfd/layouts.py`
- Create: `vfd/tests/test_layouts.py`

**Step 1: Write failing tests**

`vfd/tests/test_layouts.py`:
```python
from unittest.mock import MagicMock
from vfd.layouts import Layout, build_layout

def test_classic_layout_returns_two_panes():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("classic", screen)
    assert "spectrum" in layout.panes
    assert len(layout.panes) == 2  # spectrum + meters

def test_dashboard_layout_returns_two_panes():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("dashboard", screen)
    assert "spectrum" in layout.panes
    assert len(layout.panes) == 2

def test_pane_dimensions_fill_screen():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("classic", screen)
    total_rows = sum(p["rows"] for p in layout.panes.values())
    assert total_rows == 40
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_layouts.py -v
```

**Step 3: Implement layouts**

`vfd/src/vfd/layouts.py`:
```python
from dataclasses import dataclass, field
from typing import Dict, Any
import curses


@dataclass
class Layout:
    panes: Dict[str, Dict[str, Any]]  # name -> {rows, cols, y, x, window}


def build_layout(preset: str, screen) -> Layout:
    rows, cols = screen.getmaxyx()

    if preset == "classic":
        spectrum_rows = int(rows * 0.7)
        meter_rows = rows - spectrum_rows
        spectrum_win = screen.derwin(spectrum_rows, cols, 0, 0)
        meter_win = screen.derwin(meter_rows, cols, spectrum_rows, 0)
        return Layout(panes={
            "spectrum": {"rows": spectrum_rows, "cols": cols, "y": 0, "x": 0, "window": spectrum_win},
            "meters":   {"rows": meter_rows,   "cols": cols, "y": spectrum_rows, "x": 0, "window": meter_win},
        })

    elif preset == "dashboard":
        spectrum_cols = cols // 2
        meter_cols = cols - spectrum_cols
        spectrum_win = screen.derwin(rows, spectrum_cols, 0, 0)
        meter_win = screen.derwin(rows, meter_cols, 0, spectrum_cols)
        return Layout(panes={
            "spectrum": {"rows": rows, "cols": spectrum_cols, "y": 0, "x": 0, "window": spectrum_win},
            "meters":   {"rows": rows, "cols": meter_cols,   "y": 0, "x": spectrum_cols, "window": meter_win},
        })

    return build_layout("classic", screen)  # fallback


def split_meter_pane(pane: Dict[str, Any], meter_names: list) -> Dict[str, Dict[str, Any]]:
    """Divide a pane equally among the given meters (horizontal sub-split)."""
    rows, cols = pane["rows"], pane["cols"]
    y0, x0 = pane["y"], pane["x"]
    parent = pane["window"]
    n = len(meter_names)
    meter_cols = cols // n
    result = {}
    for i, name in enumerate(meter_names):
        x = x0 + i * meter_cols
        w = cols - i * meter_cols if i == n - 1 else meter_cols
        win = parent.derwin(rows, w, 0, i * meter_cols)
        result[name] = {"rows": rows, "cols": w, "y": y0, "x": x, "window": win}
    return result
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_layouts.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/vfd/layouts.py tests/test_layouts.py
git commit -m "feat: add layout system with classic and dashboard presets"
```

---

### Task 12: VFDRenderer (main render loop)

**Files:**
- Create: `vfd/src/vfd/renderer.py`

**Step 1: Implement renderer**

`vfd/src/vfd/renderer.py`:
```python
import curses
import time
import sys
from vfd.config import Config
from vfd.capture import AudioCapture, DeviceNotFoundError
from vfd.analyzer import SpectrumAnalyzer
from vfd.layouts import build_layout, split_meter_pane
from vfd.vfd_colors import init_colors, get_palette
from vfd.meters.spectrum import SpectrumMeter
from vfd.meters.vu import VUMeter
from vfd.meters.peak import PeakMeter
from vfd.meters.rms import RMSMeter
from vfd.meters.lufs import LUFSMeter

SAMPLE_RATE = 44100
CHUNK_SIZE = 1024


class VFDRenderer:
    def __init__(self, cfg: Config, mode: str = None):
        self._cfg = cfg
        self._mode = mode

    def run(self):
        try:
            capture = AudioCapture(
                device_name=self._cfg.device,
                sample_rate=SAMPLE_RATE,
                channels=2 if self._cfg.stereo else 1,
            )
        except DeviceNotFoundError as e:
            print(str(e))
            sys.exit(1)

        bands = self._cfg.bands if isinstance(self._cfg.bands, int) else 64
        analyzer = SpectrumAnalyzer(sample_rate=SAMPLE_RATE, bands=bands, channels=2)

        capture.start()
        try:
            curses.wrapper(self._curses_main, capture, analyzer)
        finally:
            capture.stop()

    def _curses_main(self, screen, capture, analyzer):
        curses.curs_set(0)
        screen.nodelay(True)
        init_colors()
        palette = get_palette(self._cfg.color)

        # Build meters
        spectrum_meter = SpectrumMeter(
            peak_hold=self._cfg.peak_hold,
            decay=self._cfg.decay,
            glow=self._cfg.glow,
            db_labels=self._cfg.db_labels,
            freq_labels=self._cfg.freq_labels,
            color=self._cfg.color,
        )
        vu_meter = VUMeter(style=self._cfg.vu_style)
        peak_meter = PeakMeter(style=self._cfg.peak_style, peak_hold=self._cfg.peak_hold)
        rms_meter = RMSMeter(style=self._cfg.rms_style)
        lufs_meter = LUFSMeter(style=self._cfg.lufs_style)

        frame_duration = 1.0 / self._cfg.fps

        while True:
            key = screen.getch()
            if key == ord("q"):
                break

            pcm = capture.read(CHUNK_SIZE)
            result = analyzer.process(pcm)

            layout = build_layout(self._cfg.layout, screen)
            spectrum_win = layout.panes["spectrum"]["window"]
            meter_pane = layout.panes["meters"]

            # Draw spectrum
            spectrum_win.erase()
            spectrum_meter.render(spectrum_win, result.spectrum_db, palette)
            spectrum_win.noutrefresh()

            # Split meter pane into 4
            meter_wins = split_meter_pane(meter_pane, ["vu", "peak", "rms", "lufs"])

            meter_wins["vu"]["window"].erase()
            vu_meter.render(meter_wins["vu"]["window"], result.rms_db, palette)
            meter_wins["vu"]["window"].noutrefresh()

            meter_wins["peak"]["window"].erase()
            peak_meter.render(meter_wins["peak"]["window"], result.peak_db, palette)
            meter_wins["peak"]["window"].noutrefresh()

            meter_wins["rms"]["window"].erase()
            rms_meter.render(meter_wins["rms"]["window"], result.rms_db, result.peak_db, palette)
            meter_wins["rms"]["window"].noutrefresh()

            meter_wins["lufs"]["window"].erase()
            lufs_meter.render(
                meter_wins["lufs"]["window"],
                result.lufs_momentary, result.lufs_shortterm,
                result.lufs_integrated, result.lufs_history,
                palette,
            )
            meter_wins["lufs"]["window"].noutrefresh()

            curses.doupdate()
            time.sleep(frame_duration)
```

**Step 2: Smoke test — run the app**

```bash
python -m vfd --list-devices
python -m vfd --setup
```
Expected: Both print output cleanly without errors.

**Step 3: Commit**

```bash
git add src/vfd/renderer.py
git commit -m "feat: add VFDRenderer main curses render loop"
```

---

### Task 13: Full integration smoke test + README

**Files:**
- Create: `vfd/README.md`

**Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 2: Test live (requires BlackHole installed)**

```bash
python -m vfd
# Press q to quit
python -m vfd --color amber --bands 32 --layout dashboard
```

**Step 3: Write README**

`vfd/README.md` — cover: install, BlackHole setup (link to `vfd --setup`), usage examples,
all CLI flags, config file location, layout screenshots (ASCII).

**Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: add README with install and usage instructions"
```

---

## Running All Tests

```bash
cd vfd && python -m pytest tests/ -v --tb=short
```

## Installing Locally

```bash
pip install -e .
vfd --help
```

## Distribution (after release)

```bash
pipx install vfd
```
