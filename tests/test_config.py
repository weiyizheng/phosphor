from pathlib import Path

import pytest

from phosphor.config import Config, ConfigValidationError, load_config, validate_config


def test_default_config_values():
    config = Config()
    assert config.color == "hifi"
    assert config.bands == 64
    assert config.fps == 60
    assert config.stereo is True
    assert config.layout == "classic"
    assert config.vu_style == "segmented"
    assert config.peak_style == "vertical"
    assert config.rms_style == "dual"
    assert config.lufs_style == "graph"
    assert config.peak_hold is True
    assert config.decay is True
    assert config.glow is True
    assert config.db_labels is True
    assert config.freq_labels is True
    assert config.device == "BlackHole 2ch"


def test_load_config_from_toml(tmp_path: Path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text('[display]\ncolor = "amber"\nbands = 32\n', encoding="utf-8")
    config = load_config(toml_file)
    assert config.color == "amber"
    assert config.bands == 32
    assert config.fps == 60


def test_load_config_missing_file(tmp_path: Path):
    config = load_config(tmp_path / "missing.toml")
    assert config.color == "hifi"


def test_config_merge_flags():
    config = Config(color="blue", bands=128)
    assert config.color == "blue"
    assert config.bands == 128
    assert config.fps == 60


def test_invalid_color_raises(tmp_path: Path):
    toml_file = tmp_path / "bad.toml"
    toml_file.write_text('[display]\ncolor = "invalid"\n', encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_config(toml_file)


def test_invalid_fps_high_raises():
    with pytest.raises(ConfigValidationError):
        validate_config(Config(fps=10000))


@pytest.mark.parametrize(
    "field,value",
    [
        ("bands", 999),
        ("layout", "invalid"),
        ("vu_style", "bad"),
        ("peak_style", "bad"),
        ("rms_style", "bad"),
        ("lufs_style", "bad"),
        ("stereo", "yes"),
        ("device", ""),
    ],
)
def test_validate_config_rejects_invalid_values(field, value):
    cfg = Config()
    setattr(cfg, field, value)
    with pytest.raises(ConfigValidationError):
        validate_config(cfg)


def test_corrupt_toml_warns_and_falls_back(tmp_path: Path):
    toml_file = tmp_path / "broken.toml"
    toml_file.write_text("[display\ncolor = 'green'\n", encoding="utf-8")
    with pytest.warns(RuntimeWarning, match="invalid TOML"):
        cfg = load_config(toml_file)
    assert cfg.color == "hifi"
