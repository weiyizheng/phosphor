from unittest.mock import MagicMock

from vfd.meters.lufs import LUFSMeter


def test_render_graph_does_not_crash():
    meter = LUFSMeter(style="graph")
    win = MagicMock()
    win.getmaxyx.return_value = (10, 60)
    meter.render(win, momentary=-14.0, shortterm=-15.0, integrated=-16.0, history=[-15.0] * 50, palette=MagicMock())


def test_render_uses_approximate_label():
    meter = LUFSMeter(style="numeric")
    win = MagicMock()
    win.getmaxyx.return_value = (8, 40)
    meter.render(win, momentary=-14.0, shortterm=-15.0, integrated=-16.0, history=[], palette=MagicMock())
    calls = [args[0][2] for args in win.addstr.call_args_list if len(args[0]) >= 3]
    assert any("LUFS~" in text for text in calls)
