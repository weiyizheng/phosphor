from unittest.mock import MagicMock

from vfd.layouts import build_layout


def test_classic_layout_returns_two_panes():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("classic", screen)
    assert "spectrum" in layout.panes
    assert len(layout.panes) == 2


def test_dashboard_layout_returns_two_panes():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("dashboard", screen)
    assert "spectrum" in layout.panes
    assert len(layout.panes) == 2


def test_pane_dimensions_fill_screen():
    screen = MagicMock()
    screen.getmaxyx.return_value = (40, 120)
    layout = build_layout("classic", screen)
    total_rows = sum(p["rows"] for p in layout.panes.values())
    assert total_rows == 40
