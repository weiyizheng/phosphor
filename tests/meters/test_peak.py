from unittest.mock import MagicMock

from vfd.meters.peak import PeakMeter


def test_render_vertical_does_not_crash():
    meter = PeakMeter(style="vertical", peak_hold=True)
    win = MagicMock()
    win.getmaxyx.return_value = (20, 20)
    meter.render(win, peak_db=-3.0, palette=MagicMock())
