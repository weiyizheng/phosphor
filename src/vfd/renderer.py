from __future__ import annotations

import curses
import shutil
import sys
import time

from vfd.analyzer import SpectrumAnalyzer
from vfd.capture import AudioCapture, DeviceNotFoundError
from vfd.config import Config
from vfd.layouts import build_layout, split_meter_pane
from vfd.meters.lufs import LUFSMeter
from vfd.meters.peak import PeakMeter
from vfd.meters.rms import RMSMeter
from vfd.meters.spectrum import SpectrumMeter
from vfd.meters.vu import VUMeter
from vfd.vfd_colors import get_palette, init_colors

SAMPLE_RATE = 44100
CHUNK_SIZE = 1024


class VFDRenderer:
    def __init__(self, cfg: Config, mode: str | None = None):
        self._cfg = cfg
        self._mode = mode

    def run(self) -> None:
        channels = 2 if self._cfg.stereo else 1
        try:
            capture = AudioCapture(
                device_name=self._cfg.device,
                sample_rate=SAMPLE_RATE,
                channels=channels,
            )
        except DeviceNotFoundError as exc:
            print(str(exc))
            sys.exit(1)

        initial_cols = shutil.get_terminal_size(fallback=(120, 30)).columns
        bands = self._resolve_band_count(initial_cols)
        analyzer = SpectrumAnalyzer(sample_rate=SAMPLE_RATE, bands=bands, channels=channels)

        capture.start()
        try:
            try:
                curses.wrapper(self._curses_main, capture, analyzer)
            except Exception as exc:
                print(f"Renderer crashed: {exc}", file=sys.stderr)
                sys.exit(1)
        finally:
            capture.stop()

    def _curses_main(self, screen, capture: AudioCapture, analyzer: SpectrumAnalyzer) -> None:
        curses.curs_set(0)
        screen.nodelay(True)

        init_colors()
        palette = get_palette(self._cfg.color)

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

        frame_duration = 1.0 / max(self._cfg.fps, 1)
        layout = None
        meter_wins = None
        if self._mode is None:
            layout = build_layout(self._cfg.layout, screen)
            meter_wins = split_meter_pane(layout.panes["meters"], ["vu", "peak", "rms", "lufs"])
        last_size = screen.getmaxyx()

        while True:
            key = screen.getch()
            if key == ord("q"):
                break

            current_size = screen.getmaxyx()
            if current_size != last_size:
                screen.clear()
                if self._mode is None:
                    layout = build_layout(self._cfg.layout, screen)
                    meter_wins = split_meter_pane(layout.panes["meters"], ["vu", "peak", "rms", "lufs"])
                if self._cfg.bands == "auto":
                    analyzer.set_bands(self._resolve_band_count(current_size[1]))
                last_size = current_size

            pcm = capture.read(CHUNK_SIZE)
            result = analyzer.process(pcm)

            if self._mode is not None:
                screen.erase()
                self._render_single_mode(
                    screen,
                    self._mode,
                    result,
                    spectrum_meter,
                    vu_meter,
                    peak_meter,
                    rms_meter,
                    lufs_meter,
                    palette,
                )
                screen.noutrefresh()
            else:
                spectrum_win = layout.panes["spectrum"]["window"]
                spectrum_win.erase()
                spectrum_meter.render(spectrum_win, result.spectrum_db, palette)
                spectrum_win.noutrefresh()

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
                    result.lufs_momentary,
                    result.lufs_shortterm,
                    result.lufs_integrated,
                    result.lufs_history,
                    palette,
                )
                meter_wins["lufs"]["window"].noutrefresh()

            curses.doupdate()
            time.sleep(frame_duration)

    def _resolve_band_count(self, cols: int) -> int:
        if isinstance(self._cfg.bands, int):
            return self._cfg.bands
        return max(16, cols - 8)

    def _render_single_mode(
        self,
        win,
        mode: str,
        result,
        spectrum_meter: SpectrumMeter,
        vu_meter: VUMeter,
        peak_meter: PeakMeter,
        rms_meter: RMSMeter,
        lufs_meter: LUFSMeter,
        palette,
    ) -> None:
        if mode == "spectrum":
            spectrum_meter.render(win, result.spectrum_db, palette)
        elif mode == "vu":
            vu_meter.render(win, result.rms_db, palette)
        elif mode == "peak":
            peak_meter.render(win, result.peak_db, palette)
        elif mode == "rms":
            rms_meter.render(win, result.rms_db, result.peak_db, palette)
        elif mode == "lufs":
            lufs_meter.render(
                win,
                result.lufs_momentary,
                result.lufs_shortterm,
                result.lufs_integrated,
                result.lufs_history,
                palette,
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")
