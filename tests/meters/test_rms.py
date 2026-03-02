from unittest.mock import MagicMock

from vfd.meters.rms import RMSMeter


def test_render_dual_does_not_crash():
    meter = RMSMeter(style="dual")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, rms_db=-14.0, peak_db=-8.0, palette=MagicMock())
