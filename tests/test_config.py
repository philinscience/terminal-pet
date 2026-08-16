from terminal_pet import config


def test_normalize_config_merges_defaults():
    normalized = config.normalize_config({"chattiness": "chaos", "enable_roasts": False})
    assert normalized["chattiness"] == "chaos"
    assert normalized["enable_roasts"] is False
    assert normalized["enable_typo_help"] is True


def test_load_config_falls_back_on_invalid_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    loaded = config.load_config(str(path))
    assert loaded == config.DEFAULT_CONFIG


def test_save_config_round_trip(tmp_path):
    path = tmp_path / "config.json"
    saved = config.save_config({"default_pet": "duck", "default_speed": 1.5}, str(path))
    loaded = config.load_config(str(path))
    assert saved == loaded
    assert loaded["default_pet"] == "duck"
    assert loaded["default_speed"] == 1.5
