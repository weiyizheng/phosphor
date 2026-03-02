import tomllib

from vfd.config import generate_default_config


def test_generate_config_contains_comments():
    content = generate_default_config()
    assert "# Controls the phosphor color" in content
    assert "color = " in content
    assert "bands = " in content
    assert "fps = " in content


def test_generate_config_is_valid_toml(tmp_path):
    content = generate_default_config()
    path = tmp_path / "config.toml"
    path.write_text(content, encoding="utf-8")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    assert data["display"]["color"] == "green"
