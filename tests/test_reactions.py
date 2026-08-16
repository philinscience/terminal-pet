"""Tests for the pure command-matching logic: which reaction a typed command
triggers, and what typo suggestion (if any) gets offered on a bad exit code.
"""

from terminal_pet import pet


def _first_match_options(cmd):
    for pattern, options in pet.COMMAND_REACTIONS:
        if pattern.search(cmd):
            return options
    return None


def test_git_commit_matches_before_generic_git():
    # git commit has its own reaction and must win over the generic "git" catch-all.
    options = _first_match_options("git commit -m 'fix bug'")
    assert options == pet.COMMAND_REACTIONS[0][1]
    assert options != _first_match_options("git remote -v")


def test_generic_git_catches_unmatched_git_subcommands():
    options = _first_match_options("git remote -v")
    assert options is not None
    assert "git stuff! neat" in options


def test_ls_family_matches():
    for cmd in ("ls -la", "ll", "la", "tree"):
        assert _first_match_options(cmd) is not None, cmd


def test_unrelated_command_has_no_reaction():
    assert _first_match_options("banana --peel") is None


def test_reaction_matches_only_at_start_of_command():
    # "cd" shouldn't fire on something like "recd" or a command that merely
    # contains "cd" mid-string.
    assert _first_match_options("recd something") is None


def test_suggest_command_fixes_common_typo():
    assert pet._suggest_command("gti") == "git"
    assert pet._suggest_command("pyhton") == "python"


def test_suggest_command_returns_none_for_gibberish():
    assert pet._suggest_command("xzqvbnmqq") is None
