import pytest

from terminal_pet import cli


def test_parse_args_treats_plain_invocation_as_run():
    args = cli.parse_args(["--pet", "duck", "--speed", "2"])
    assert args.command == "run"
    assert args.pet_name == "duck"
    assert args.speed == 2.0


def test_parse_args_keeps_top_level_help_top_level():
    with pytest.raises(SystemExit) as excinfo:
        cli.parse_args(["--help"])
    assert excinfo.value.code == 0


def test_merge_runtime_config_overrides_file_values(monkeypatch):
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "default_pet": "mouse",
            "default_speed": 1.0,
            "default_dock": False,
            "chattiness": "normal",
            "enable_encouragements": True,
            "enable_roasts": True,
            "enable_typo_help": True,
            "enable_seasonal": True,
            "enable_sparkles": True,
        },
    )
    args = cli.parse_args(["--pet", "duck", "--dock", "--chattiness", "quiet", "--no-roasts"])
    runtime = cli._merge_runtime_config(args)
    assert runtime["default_pet"] == "duck"
    assert runtime["default_dock"] is True
    assert runtime["chattiness"] == "quiet"
    assert runtime["enable_roasts"] is False


def test_get_doctor_report_includes_hook_and_terminal(monkeypatch):
    monkeypatch.setattr(
        cli.hook,
        "is_installed",
        lambda: {
            "zsh": {"hook_exists": True, "rc_exists": True, "rc_has_source": True, "hook_path": "/tmp/hook.zsh", "rc_path": "/tmp/.zshrc"},
            "bash": {"hook_exists": False, "rc_exists": False, "rc_has_source": False, "hook_path": "/tmp/hook.bash", "rc_path": "/tmp/.bashrc"},
        },
    )
    monkeypatch.setattr(cli, "load_config", lambda: dict(cli.DEFAULT_CONFIG))
    report = cli.get_doctor_report()
    assert "hook_status" in report
    assert "term_message" in report
