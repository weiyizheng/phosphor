# phosphor

A real-time VFD (Vacuum Fluorescent Display) audio analyzer for your terminal. Captures your Mac's system audio and renders a glowing spectrum analyzer alongside VU, Peak, RMS, and LUFS meters — all in the style of vintage hi-fi equipment displays.

```
┌─────────────────────────────────────────────────────────────────┐
│  ▁▁▂▃▄▅▆▇█▇▆▅▄▅▆▇███▇▆▅▄▃▄▅▆▇▆▅▄▃▂▃▄▅▄▃▂▁▂▃▂▁▁▁▂▃▂▁▁▁▁▁▁▁▁▁▁  │
│  ████████████████████████████████████████████████████████████  │
│  ░░░▁▂▄▆███████████████████████▆▄▂▁░░░░░░░░░░░░░░░░░░░░░░░░░  │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  VU          │  PEAK        │  RMS         │  LUFS              │
│  ■■■■■□□□□□  │  L ████░░░  │  ████|░░░░░  │  M: -14.2          │
│  ■■■■■■□□□□  │  R ██░░░░░  │  ██░░|░░░░░  │  ST: -15.8         │
│              │              │              │  I: -16.1          │
│              │              │              │  ▁▂▃▄▃▂▁▂▃▄▅▄▃▂▁  │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

## Requirements

- macOS 12+, Intel or Apple Silicon
- Python 3.11+
- [BlackHole 2ch](https://existential.audio/blackhole/) (free virtual audio driver)

## Install

```bash
pipx install phosphor
```

Or for development:

```bash
git clone https://github.com/weiyizheng/phosphor
cd phosphor
pip install -e .
```

## Setup

phosphor captures audio by reading from BlackHole, a virtual audio device that mirrors your system output.

**Step 1: Install BlackHole**

```bash
brew install blackhole-2ch
```

**Step 2: Create an Aggregate Device**

So audio plays through your speakers AND gets captured simultaneously:

1. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)
2. Click **+** at the bottom left → **Create Aggregate Device**
3. Check both **BlackHole 2ch** and your **speakers/headphones**
4. Name it something like `VFD Capture`

**Step 3: Set system output**

System Settings → Sound → Output → select your new Aggregate Device

**Step 4: Run the guided setup wizard**

```bash
phosphor --setup
```

## Usage

```bash
# Launch with defaults
phosphor

# Change phosphor color
phosphor --color amber       # amber | green | blue | white

# Change frequency band count
phosphor --bands 128         # 32 | 64 | 128 | auto

# Change layout
phosphor --layout dashboard  # classic | dashboard

# View a single meter fullscreen
phosphor --mode spectrum
phosphor --mode vu
phosphor --mode lufs

# Limit framerate (saves CPU)
phosphor --fps 30

# Sum stereo to mono
phosphor --mono

# Use a specific capture device
phosphor --device "BlackHole 2ch"

# List available audio input devices
phosphor --list-devices

# First-run setup guide
phosphor --setup
```

Press `q` to quit.

## Layouts

**Classic** (default) — spectrum on top, meters along the bottom:

```
┌─────────────────────────────────────────┐
│                                         │
│             SPECTRUM                    │
│                                         │
├──────────┬──────────┬──────────┬────────┤
│    VU    │   PEAK   │   RMS    │  LUFS  │
└──────────┴──────────┴──────────┴────────┘
```

**Dashboard** — spectrum left, meters stacked right:

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

## Phosphor Colors

| Preset  | Look                                      |
|---------|-------------------------------------------|
| `green` | Classic Futaba/Noritake VFD phosphor (default) |
| `amber` | Warm vintage hi-fi receiver               |
| `blue`  | Modern Sony/Pioneer equipment             |
| `white` | High-brightness neutral                   |

## Meters

| Meter    | What it shows | Default style |
|----------|---------------|---------------|
| Spectrum | Frequency content of the audio, log scale | Bars + glow + peak hold |
| VU       | Average loudness with ballistic decay | Segmented bar |
| Peak     | Instantaneous highest sample (clipping risk) | Vertical bar pair |
| RMS      | Perceived loudness (~300ms average) | Dual bar with peak overlay |
| LUFS     | Broadcast/streaming loudness standard | Numeric + scrolling history graph |

Each meter style is configurable. See `~/.config/phosphor/config.toml` for options.

## Configuration

On first run, phosphor creates a fully-commented config file at:

```
~/.config/phosphor/config.toml
```

Every option is documented inline with valid values and visual effect descriptions. CLI flags always override the config file.

Example config:

```toml
[display]
color = "amber"
bands = 64
fps = 60
stereo = true

[layout]
layout = "classic"

[meters]
vu_style = "segmented"    # segmented | bar | needle
peak_style = "vertical"   # vertical | horizontal | ppm
rms_style = "dual"        # dual | bar | segmented
lufs_style = "graph"      # graph | target | numeric

[effects]
peak_hold = true
decay = true
glow = true
db_labels = true
freq_labels = true

[device]
device = "BlackHole 2ch"
```

## How It Works

```
BlackHole (system audio) → sounddevice → ring buffer
                                              ↓
                                       numpy FFT + RMS/Peak/LUFS math
                                              ↓
                                       curses per-cell VFD rendering
```

Audio is captured via BlackHole, processed with a Hann-windowed FFT for the spectrum and running averages for the meters, then rendered character-by-character in the terminal using curses with per-cell color control to simulate phosphor glow.

## License

MIT
