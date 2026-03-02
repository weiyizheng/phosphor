from unittest.mock import MagicMock

from phosphor.meters.spectrum import SpectrumMeter


def make_mock_window(rows=30, cols=80):
    win = MagicMock()
    win.getmaxyx.return_value = (rows, cols)
    return win


def test_render_does_not_crash():
    meter = SpectrumMeter(peak_hold=True, decay=True, glow=True, db_labels=True, freq_labels=True, color="green")
    win = make_mock_window()
    bands_db = [-60.0 + i for i in range(64)]
    meter.render(win, bands_db, palette=MagicMock())


def test_decay_smooths_values():
    meter = SpectrumMeter(peak_hold=True, decay=True, glow=True, db_labels=False, freq_labels=False, color="green")
    win = make_mock_window()
    palette = MagicMock()
    bands_high = [0.0] * 64
    bands_low = [-60.0] * 64
    meter.render(win, bands_high, palette=palette)
    meter.render(win, bands_low, palette=palette)
    assert all(-60.0 < v < 0.0 for v in meter._levels_l)
