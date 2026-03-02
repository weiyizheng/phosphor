# vfd

VFD Audio Spectrum Analyzer for macOS terminals.

## Install

```bash
cd vfd
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Setup

Run the built-in guide:

```bash
vfd --setup
```

Use `vfd --list-devices` to confirm the capture device name.

## Usage

```bash
vfd
vfd --color amber --bands 32 --layout dashboard
vfd --device "BlackHole 2ch"
```

Press `q` to quit.

## Config

Default config path:

```text
~/.config/vfd/config.toml
```

It is auto-created on first run.

## CLI Flags

- `--color [green|amber|blue|white]`
- `--bands [32|64|128|auto]`
- `--fps INT`
- `--mono`
- `--layout [classic|dashboard]`
- `--mode [spectrum|vu|peak|rms|lufs]`
- `--device TEXT`
- `--list-devices`
- `--setup`
- `--config PATH`
