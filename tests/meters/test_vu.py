from unittest.mock import MagicMock

from phosphor.meters.vu import VUMeter


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
