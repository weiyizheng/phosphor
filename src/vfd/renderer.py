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
                panel = self._draw_panel(
                    screen,
                    self._panel_title(self._mode),
                    self._mode_legend(self._mode, result),
                )
                self._render_single_mode(
                    panel,
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
                spectrum_panel = self._draw_panel(
                    spectrum_win,
                    "Spectrum",
                    self._stereo_legend(result.peak_db_l, result.peak_db_r, "PK"),
                )
                spectrum_meter.render(
                    spectrum_panel,
                    result.spectrum_db_l,
                    palette,
                    bands_db_r=result.spectrum_db_r,
                )
                spectrum_win.noutrefresh()

                meter_wins["vu"]["window"].erase()
                vu_panel = self._draw_panel(
                    meter_wins["vu"]["window"],
                    "VU",
                    self._stereo_legend(result.rms_db_l, result.rms_db_r, "RMS"),
                )
                vu_meter.render(vu_panel, result.rms_db, palette, rms_db_l=result.rms_db_l, rms_db_r=result.rms_db_r)
                meter_wins["vu"]["window"].noutrefresh()

                meter_wins["peak"]["window"].erase()
                peak_panel = self._draw_panel(
                    meter_wins["peak"]["window"],
                    "Peak",
                    self._stereo_legend(result.peak_db_l, result.peak_db_r, "PK"),
                )
                peak_meter.render(
                    peak_panel,
                    result.peak_db,
                    palette,
                    peak_db_l=result.peak_db_l,
                    peak_db_r=result.peak_db_r,
                )
                meter_wins["peak"]["window"].noutrefresh()

                meter_wins["rms"]["window"].erase()
                rms_panel = self._draw_panel(
                    meter_wins["rms"]["window"],
                    "RMS",
                    self._stereo_legend(result.rms_db_l, result.rms_db_r, "RMS"),
                )
                rms_meter.render(
                    rms_panel,
                    result.rms_db,
                    result.peak_db,
                    palette,
                    rms_db_l=result.rms_db_l,
                    rms_db_r=result.rms_db_r,
                    peak_db_l=result.peak_db_l,
                    peak_db_r=result.peak_db_r,
                )
                meter_wins["rms"]["window"].noutrefresh()

                meter_wins["lufs"]["window"].erase()
                lufs_panel = self._draw_panel(
                    meter_wins["lufs"]["window"],
                    "LUFS~",
                    "M/ST/I approximate",
                )
                lufs_meter.render(
                    lufs_panel,
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
            spectrum_meter.render(
                win,
                result.spectrum_db_l,
                palette,
                bands_db_r=result.spectrum_db_r,
            )
        elif mode == "vu":
            vu_meter.render(win, result.rms_db, palette, rms_db_l=result.rms_db_l, rms_db_r=result.rms_db_r)
        elif mode == "peak":
            peak_meter.render(
                win,
                result.peak_db,
                palette,
                peak_db_l=result.peak_db_l,
                peak_db_r=result.peak_db_r,
            )
        elif mode == "rms":
            rms_meter.render(
                win,
                result.rms_db,
                result.peak_db,
                palette,
                rms_db_l=result.rms_db_l,
                rms_db_r=result.rms_db_r,
                peak_db_l=result.peak_db_l,
                peak_db_r=result.peak_db_r,
            )
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

    def _draw_panel(self, win, title: str, legend: str):
        rows, cols = win.getmaxyx()
        if rows < 3 or cols < 4:
            return win

        try:
            win.box()
            title_text = f" {title} "
            legend_text = f" {legend} "
            if len(title_text) < cols - 2:
                win.addstr(0, 2, title_text)
            if len(legend_text) < cols - 2:
                start = max(2, cols - len(legend_text) - 2)
                win.addstr(0, start, legend_text)
        except curses.error:
            pass

        inner_rows = max(rows - 2, 1)
        inner_cols = max(cols - 2, 1)
        return win.derwin(inner_rows, inner_cols, 1, 1)

    def _panel_title(self, mode: str) -> str:
        return {
            "spectrum": "Spectrum",
            "vu": "VU",
            "peak": "Peak",
            "rms": "RMS",
            "lufs": "LUFS~",
        }.get(mode, mode.upper())

    def _panel_legend(self, mode: str) -> str:
        return {
            "spectrum": "q quit | bars dBFS with peak hold",
            "vu": "stereo ballistic average",
            "peak": "stereo instantaneous peak",
            "rms": "stereo energy + peak marker",
            "lufs": "M/ST/I approximate",
        }.get(mode, "")

    def _mode_legend(self, mode: str, result) -> str:
        if mode == "vu":
            return self._stereo_legend(result.rms_db_l, result.rms_db_r, "RMS")
        if mode == "peak":
            return self._stereo_legend(result.peak_db_l, result.peak_db_r, "PK")
        if mode == "rms":
            return self._stereo_legend(result.rms_db_l, result.rms_db_r, "RMS")
        return self._panel_legend(mode)

    def _stereo_legend(self, left_db: float, right_db: float, tag: str) -> str:
        return f"{tag} L {left_db:+5.1f}dB R {right_db:+5.1f}dB"
