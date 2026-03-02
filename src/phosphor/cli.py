from __future__ import annotations

import sys
from pathlib import Path

import click

from phosphor.config import (
    Config,
    ConfigValidationError,
    DEFAULT_CONFIG_PATH,
    generate_default_config,
    load_config,
    validate_config,
)


@click.command()
@click.option("--color", type=click.Choice(["green", "amber", "blue", "white", "btop", "hifi"]))
@click.option("--bands", type=click.Choice(["32", "64", "128", "auto"]))
@click.option("--fps", type=int, default=None)
@click.option("--mono", is_flag=True, default=False)
@click.option("--layout", type=click.Choice(["classic", "dashboard"]))
@click.option("--mode", type=click.Choice(["spectrum", "vu", "peak", "rms", "lufs"]))
@click.option("--device", type=str, default=None)
@click.option("--list-devices", is_flag=True, default=False)
@click.option("--setup", is_flag=True, default=False)
@click.option("--config", type=click.Path(path_type=Path), default=None)
def main(
    color: str | None,
    bands: str | None,
    fps: int | None,
    mono: bool,
    layout: str | None,
    mode: str | None,
    device: str | None,
    list_devices: bool,
    setup: bool,
    config: Path | None,
) -> None:
    """VFD Audio Spectrum Analyzer - real-time terminal audio visualization."""
    if list_devices:
        _list_devices()
        return

    if setup:
        _print_setup_guide()
        return

    config_path = config or DEFAULT_CONFIG_PATH
    try:
        cfg = load_config(config_path)
    except ConfigValidationError as exc:
        click.echo(f"Invalid config file '{config_path}': {exc}", err=True)
        sys.exit(2)

    if color:
        cfg.color = color
    if bands:
        cfg.bands = int(bands) if bands != "auto" else "auto"
    if fps is not None:
        cfg.fps = fps
    if mono:
        cfg.stereo = False
    if layout:
        cfg.layout = layout
    if device:
        cfg.device = device

    try:
        validate_config(cfg)
    except ConfigValidationError as exc:
        click.echo(f"Invalid runtime configuration: {exc}", err=True)
        sys.exit(2)

    _ensure_config_file(config_path)
    _run(cfg, mode)


def _list_devices() -> None:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        click.echo("Available audio input devices:\n")
        for i, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                click.echo(f"  [{i}] {d['name']}")
    except Exception as exc:  # pragma: no cover - hardware dependent
        click.echo(f"Error querying devices: {exc}", err=True)
        sys.exit(1)


def _print_setup_guide() -> None:
    click.echo(
        """
VFD Setup Guide
===============

Step 1: Install BlackHole
  brew install blackhole-2ch

Step 2: Create an Aggregate Device
  1. Open Audio MIDI Setup
  2. Click + -> Create Aggregate Device
  3. Select BlackHole 2ch and your output device

Step 3: Set system output to that Aggregate Device.

Step 4: Configure phosphor
  device = "BlackHole 2ch" in ~/.config/phosphor/config.toml

Step 5: Run
  phosphor
""".strip()
    )


def _ensure_config_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_default_config(), encoding="utf-8")
    click.echo(f"Created default config at {path}")


def _run(cfg: Config, mode: str | None) -> None:
    from phosphor.renderer import VFDRenderer

    renderer = VFDRenderer(cfg, mode)
    renderer.run()
