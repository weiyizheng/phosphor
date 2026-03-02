# VFD Audio Spectrum Analyzer — Design Document

**Date:** 2026-03-02
**Status:** Approved

---

## Overview

A macOS CLI app (`vfd`) that captures system audio output via BlackHole and renders a
real-time VFD (Vacuum Fluorescent Display) style audio analyzer in the terminal. Supports
spectrum analysis and VU, Peak, RMS, and LUFS metering with configurable layouts, visual
styles, and a fully commented config file.

---

## Platform

- macOS 12+ (Intel and Apple Silicon)
- Python, distributed via `pipx install vfd`
- Audio capture via BlackHole virtual audio device (`brew install blackhole-2ch`)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     vfd (CLI entry)                  │
│  parse flags → merge config file → launch app        │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────▼───────────┐
        │    AudioCapture       │  sounddevice stream
        │  (BlackHole device)   │  → callback → ring buffer
        └───────────┬───────────┘
                    │  raw PCM chunks
        ┌───────────▼───────────┐
        │    SpectrumAnalyzer   │  numpy FFT → log-scale
        │                       │  band binning → dB levels
        └───────────┬───────────┘
                    │  band dB array + meter values
        ┌───────────▼───────────┐
        │    VFDRenderer        │  curses, per-cell glow,
        │                       │  peak hold, decay
        └───────────────────────┘
```

Three clean layers — capture, analysis, render — each independent and testable.
The ring buffer decouples audio callback timing from render timing.

---

## Audio Capture

- Requires BlackHole 2ch (`brew install blackhole-2ch`)
- Recommended setup: macOS Aggregate Device (BlackHole + speakers/headphones) via
  Audio MIDI Setup, so audio plays normally while being captured simultaneously
- `sounddevice` streams from the selected device as an input source
- PCM data fed into a ring buffer, decoupled from the render loop
- Auto-detects BlackHole device on launch; prints setup guide if not found
- `vfd --setup` runs an interactive first-run wizard (BlackHole install + aggregate
  device creation instructions)
- If device disconnects mid-session, shows a clean error rather than crashing

---

## Analysis Layer

- `numpy` FFT on windowed PCM chunks (Hann window to reduce spectral leakage)
- Log-scale frequency binning into configurable bands (32 / 64 / 128 / auto)
- Each frame computes in parallel: spectrum bands, RMS, peak, LUFS
- LUFS tracks momentary (400ms), short-term (3s), and integrated (full session) values
- Stereo (L/R separate) or mono (summed), configurable

---

## Meters & Visual Styles

### Spectrum Analyzer
- Vertical bars, one per frequency band
- Glow effect: brighter characters at bar tops, dimmer fill toward bottom
- Peak hold indicator per band (dot/dash that hangs then slowly falls)
- Smooth decay animation
- X-axis: frequency labels (20Hz, 100Hz, 1kHz, 10kHz, etc.)
- Y-axis: dB scale labels

### VU Meter
| Style | Description |
|---|---|
| `segmented` (default) | Discrete lit/unlit block segments, classic hi-fi VFD look |
| `bar` | Continuous horizontal fill bar with ballistic needle decay |
| `needle` | ASCII arc sweep simulating physical analog needle |

Color shifts green → amber → red near 0dB on all styles.

### Peak Meter
| Style | Description |
|---|---|
| `vertical` (default) | Two vertical bars (L/R), peak hold line at top |
| `horizontal` | Horizontal stereo bars, snaps to peak immediately |
| `ppm` | Segmented ladder, BBC/EBU PPM scale |

### RMS Meter
| Style | Description |
|---|---|
| `dual` (default) | Horizontal bar showing RMS fill + instantaneous peak marker overlay |
| `bar` | Continuous bar, slower/smoother movement than VU |
| `segmented` | Discrete block segments |

### LUFS Meter
| Style | Description |
|---|---|
| `graph` (default) | Scrolling loudness history graph + live numeric readout (M/ST/I) |
| `target` | Horizontal bar showing position relative to platform targets (-14 Spotify, -23 broadcast) |
| `numeric` | Minimal three-number readout only |

---

## VFD Aesthetic

- Rendered with `curses` for precise per-cell character control
- Phosphor glow effect via character brightness graduation within each bar
- Peak hold indicators on all bar-style meters
- Smooth decay animation on all meters

### Color Presets
| Preset | Description |
|---|---|
| `green` (default) | Classic Futaba/Noritake VFD phosphor |
| `amber` | Warm vintage hi-fi receiver aesthetic |
| `blue` | Modern Sony/Pioneer equipment style |
| `white` | High-brightness neutral display |

---

## Layout System

### Presets
- `classic` (default) — horizontal split, spectrum top (~70%), meters row bottom (~30%)
- `dashboard` — vertical split, spectrum left, meters stacked right

### Classic Layout
```
┌─────────────────────────────────────────┐
│                                         │
│             SPECTRUM                    │
│                                         │
├──────────┬──────────┬──────────┬────────┤
│    VU    │   PEAK   │   RMS    │  LUFS  │
└──────────┴──────────┴──────────┴────────┘
```

### Dashboard Layout
```
┌─────────────────────┬──────────────────┐
│                     │       VU         │
│                     ├──────────────────┤
│      SPECTRUM       │      PEAK        │
│                     ├──────────────────┤
│                     │       RMS        │
│                     ├──────────────────┤
│                     │      LUFS        │
└─────────────────────┴──────────────────┘
```

### Custom Panel Splits
| Split | Description |
|---|---|
| `vertical` | Left \| Right (2 panes) |
| `horizontal` | Top / Bottom (2 panes) |
| `quad` | 2×2 grid (4 panes) |
| `main` | One large pane + smaller panes |
| `tiled` | All panes equal size in a grid |

User assigns meters to panes in config:
```toml
[layout]
split = "horizontal"

[layout.panes]
top = "spectrum"
bottom = ["vu", "peak", "rms", "lufs"]
```

---

## CLI Interface

```
vfd                            # launch with saved/default config
vfd --color amber              # override phosphor color
vfd --bands 128                # override frequency bands
vfd --layout dashboard         # override layout preset
vfd --mode spectrum            # fullscreen single meter
vfd --mode vu                  # fullscreen VU meter
vfd --fps 30                   # cap render framerate (default: 60)
vfd --mono                     # sum stereo to mono
vfd --list-devices             # show available audio input devices
vfd --device "BlackHole 2ch"   # specify capture device explicitly
vfd --setup                    # run first-run setup wizard
```

---

## Configuration File

Located at `~/.config/vfd/config.toml`. Generated on first run with full inline comments
explaining every option, valid values, visual effects, and defaults — functioning as an
in-place reference manual.

Config precedence: **CLI flags > config file > defaults**

---

## Additional Behaviors

- **`--fps`** — cap render framerate, default 60fps; lower values reduce CPU usage
- **Stereo/mono** — all meters show L/R channels separately by default; `--mono` sums to mono
- **First-run detection** — if BlackHole not found, prints step-by-step setup guide
- **Graceful degradation** — clean error message if capture device disconnects mid-session
- **`--list-devices`** — enumerates all available audio input devices to help identify
  the correct BlackHole or aggregate device name
