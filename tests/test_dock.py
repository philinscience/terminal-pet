"""Tests for dock.py's pure logic: command quoting and the per-pet square
window size calculation. Doesn't touch AppleScript/osascript at all.
"""

from terminal_pet import dock, pet


def test_pet_command_quotes_paths_with_spaces(monkeypatch):
    monkeypatch.setattr(dock.shutil, "which", lambda name: "/opt/my apps/terminal-pet")
    cmd = dock._pet_command(["--pet", "duck", "--speed", "1.0"])
    assert cmd == "'/opt/my apps/terminal-pet' --pet duck --speed 1.0"


def test_pet_command_falls_back_to_module_invocation(monkeypatch):
    monkeypatch.setattr(dock.shutil, "which", lambda name: None)
    cmd = dock._pet_command(["--pet", "bunny"])
    assert "terminal_pet.cli" in cmd
    assert "--pet bunny" in cmd


def test_large_window_size_scales_with_art_dimensions():
    bunny_size = dock._large_window_size("bunny")
    raccoon_size = dock._large_window_size("raccoon")

    # Raccoon's art is bigger in both dimensions than bunny's, so it should
    # get a bigger (or equal) square window.
    assert raccoon_size >= bunny_size
    assert raccoon_size >= dock.MIN_LARGE_WINDOW_SIZE
    assert bunny_size >= dock.MIN_LARGE_WINDOW_SIZE


def test_large_window_size_fits_the_art():
    for name in ("bunny", "raccoon"):
        art = pet.PETS[name]["art"]
        width_chars = max(len(line) for line in art)
        height_chars = len(art)
        size = dock._large_window_size(name)
        assert size >= width_chars * dock.CHAR_W_PX
        assert size >= height_chars * dock.CHAR_H_PX


def test_in_tmux_requires_both_env_and_binary(monkeypatch):
    monkeypatch.setattr(dock.shutil, "which", lambda name: "/usr/bin/tmux")
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1234,0")
    assert dock._in_tmux() is True

    monkeypatch.delenv("TMUX", raising=False)
    assert dock._in_tmux() is False

    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1234,0")
    monkeypatch.setattr(dock.shutil, "which", lambda name: None)
    assert dock._in_tmux() is False


def test_launch_tmux_pane_splits_with_percent_height(monkeypatch):
    calls = []
    monkeypatch.setattr(dock.subprocess, "run", lambda args, **kw: calls.append(args))
    monkeypatch.setattr(dock, "_pet_command", lambda argv: "terminal-pet --pet duck")

    dock._launch_tmux_pane(["--pet", "duck"], 20.0)

    assert calls == [["tmux", "split-window", "-d", "-v", "-l", "20%", "terminal-pet --pet duck"]]


def test_launch_tmux_window_names_pane(monkeypatch):
    calls = []
    monkeypatch.setattr(dock.subprocess, "run", lambda args, **kw: calls.append(args))
    monkeypatch.setattr(dock, "_pet_command", lambda argv: "terminal-pet --pet bunny")

    dock._launch_tmux_window(["--pet", "bunny"])

    assert calls == [["tmux", "new-window", "-d", "-n", "pet", "terminal-pet --pet bunny"]]
