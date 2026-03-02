# phosphor

VFD Audio Spectrum Analyzer for macOS terminals.

## Install

```bash
cd phosphor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Setup

Run the built-in guide:

```bash
phosphor --setup
```

Use `phosphor --list-devices` to confirm the capture device name.

## Usage

```bash
phosphor
phosphor --color amber --bands 32 --layout dashboard
phosphor --device "BlackHole 2ch"
```

Press `q` to quit.

## Config

Default config path:

```text
~/.config/phosphor/config.toml
```

It is auto-created on first run.

## CLI Flags

- `--color [green|amber|blue|white]`
- `--color [green|amber|blue|white|btop|hifi]`
- `--bands [32|64|128|auto]`
- `--fps INT`
- `--mono`
- `--layout [classic|dashboard]`
- `--mode [spectrum|vu|peak|rms|lufs]`
- `--device TEXT`
- `--list-devices`
- `--setup`
- `--config PATH`
