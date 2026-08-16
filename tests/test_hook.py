"""Tests for hook.py's install/uninstall round-trip: idempotency, and that
uninstall restores rc files to exactly their pre-install state.
"""

from terminal_pet import hook


def _patch_paths(monkeypatch, tmp_path):
    hook_dir = tmp_path / ".terminal_pet"
    zshrc = tmp_path / ".zshrc"
    bashrc = tmp_path / ".bashrc"
    monkeypatch.setattr(hook, "HOOK_DIR", str(hook_dir))
    monkeypatch.setattr(hook, "ZSH_HOOK_PATH", str(hook_dir / "hook.zsh"))
    monkeypatch.setattr(hook, "BASH_HOOK_PATH", str(hook_dir / "hook.bash"))
    monkeypatch.setattr(hook, "ZSHRC", str(zshrc))
    monkeypatch.setattr(hook, "BASHRC", str(bashrc))
    return zshrc, bashrc


def test_install_writes_hook_scripts_and_sources_them(tmp_path, monkeypatch):
    zshrc, bashrc = _patch_paths(monkeypatch, tmp_path)

    hook.run()

    assert (tmp_path / ".terminal_pet" / "hook.zsh").exists()
    assert (tmp_path / ".terminal_pet" / "hook.bash").exists()
    assert hook.ZSH_HOOK_PATH in zshrc.read_text()
    assert hook.BASH_HOOK_PATH in bashrc.read_text()


def test_install_is_idempotent(tmp_path, monkeypatch):
    zshrc, bashrc = _patch_paths(monkeypatch, tmp_path)

    hook.run()
    zshrc_once = zshrc.read_text()
    bashrc_once = bashrc.read_text()

    hook.run()  # second install shouldn't duplicate the source lines
    assert zshrc.read_text() == zshrc_once
    assert bashrc.read_text() == bashrc_once


def test_install_preserves_existing_rc_content(tmp_path, monkeypatch):
    zshrc, bashrc = _patch_paths(monkeypatch, tmp_path)
    zshrc.write_text("export FOO=bar\n")
    bashrc.write_text("export BAZ=qux\n")

    hook.run()

    assert "export FOO=bar" in zshrc.read_text()
    assert "export BAZ=qux" in bashrc.read_text()


def test_uninstall_restores_original_rc_content(tmp_path, monkeypatch):
    zshrc, bashrc = _patch_paths(monkeypatch, tmp_path)
    original_zshrc = "export FOO=bar\n"
    original_bashrc = "export BAZ=qux\n"
    zshrc.write_text(original_zshrc)
    bashrc.write_text(original_bashrc)

    hook.run()
    hook.uninstall()

    assert zshrc.read_text() == original_zshrc
    assert bashrc.read_text() == original_bashrc
    assert not (tmp_path / ".terminal_pet").exists()


def test_uninstall_without_prior_install_is_a_noop(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    hook.uninstall()  # should not raise even though nothing was installed
