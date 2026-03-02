from unittest.mock import MagicMock

import pytest

from phosphor.config import Config
from phosphor.renderer import VFDRenderer


class DummyResult:
    spectrum_db = [-10.0] * 8
    spectrum_db_l = [-10.0] * 8
    spectrum_db_r = [-11.0] * 8
    rms_db = -12.0
    rms_db_l = -12.5
    rms_db_r = -11.5
    peak_db = -3.0
    peak_db_l = -3.5
    peak_db_r = -2.5
    lufs_momentary = -14.0
    lufs_shortterm = -15.0
    lufs_integrated = -16.0
    lufs_history = [-15.0] * 10


def test_auto_bands_resolve_from_terminal_width():
    renderer = VFDRenderer(Config(bands="auto"), None)
    assert renderer._resolve_band_count(120) == 112


def test_mode_renders_only_selected_meter():
    renderer = VFDRenderer(Config(), "vu")
    win = MagicMock()
    palette = MagicMock()

    spectrum_meter = MagicMock()
    vu_meter = MagicMock()
    peak_meter = MagicMock()
    rms_meter = MagicMock()
    lufs_meter = MagicMock()

    renderer._render_single_mode(
        win,
        "vu",
        DummyResult(),
        spectrum_meter,
        vu_meter,
        peak_meter,
        rms_meter,
        lufs_meter,
        palette,
    )

    vu_meter.render.assert_called_once()
    spectrum_meter.render.assert_not_called()
    peak_meter.render.assert_not_called()
    rms_meter.render.assert_not_called()
    lufs_meter.render.assert_not_called()


@pytest.mark.parametrize(
    "mode,called",
    [
        ("spectrum", "spectrum"),
        ("vu", "vu"),
        ("peak", "peak"),
        ("rms", "rms"),
        ("lufs", "lufs"),
    ],
)
def test_mode_dispatch_all_branches(mode, called):
    renderer = VFDRenderer(Config(), mode)
    win = MagicMock()
    palette = MagicMock()

    spectrum_meter = MagicMock()
    vu_meter = MagicMock()
    peak_meter = MagicMock()
    rms_meter = MagicMock()
    lufs_meter = MagicMock()

    renderer._render_single_mode(
        win,
        mode,
        DummyResult(),
        spectrum_meter,
        vu_meter,
        peak_meter,
        rms_meter,
        lufs_meter,
        palette,
    )

    calls = {
        "spectrum": spectrum_meter.render.call_count,
        "vu": vu_meter.render.call_count,
        "peak": peak_meter.render.call_count,
        "rms": rms_meter.render.call_count,
        "lufs": lufs_meter.render.call_count,
    }
    assert calls[called] == 1
    for key, value in calls.items():
        if key != called:
            assert value == 0


def test_mode_dispatch_invalid_raises():
    renderer = VFDRenderer(Config(), "invalid")
    with pytest.raises(ValueError, match="Unsupported mode"):
        renderer._render_single_mode(
            MagicMock(),
            "invalid",
            DummyResult(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
