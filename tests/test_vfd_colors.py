from phosphor.vfd_colors import GlowLevel, get_palette


def test_get_palette_green():
    p = get_palette("green")
    assert p.name == "green"
    assert p.bright is not None
    assert p.dim is not None
    assert p.peak is not None


def test_all_presets_available():
    for name in ("green", "amber", "blue", "white"):
        p = get_palette(name)
        assert p.name == name


def test_glow_levels():
    assert GlowLevel.BRIGHT > GlowLevel.MID
    assert GlowLevel.MID > GlowLevel.DIM
