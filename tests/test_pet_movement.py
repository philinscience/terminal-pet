"""Tests for Pet movement/state logic and the command/exit-reaction file
watching — all pure, no curses required.
"""

import random

import pytest

from terminal_pet import pet


@pytest.fixture(autouse=True)
def _seeded_random():
    random.seed(0)


@pytest.fixture(autouse=True)
def _isolated_state_files(tmp_path, monkeypatch):
    # Every test gets its own empty CMD_FILE/EXIT_FILE by default, so none of
    # them accidentally read the real ~/.terminal_pet/lastcmd on the machine
    # running the tests (which is live and reacts to whatever command was
    # actually run last). Tests that specifically exercise check_command()/
    # check_exit() override these further with their own tmp files.
    monkeypatch.setattr(pet, "CMD_FILE", str(tmp_path / "lastcmd"))
    monkeypatch.setattr(pet, "EXIT_FILE", str(tmp_path / "lastexit"))


def test_small_pet_walks_left_and_right(monkeypatch):
    # Pin random.random() above the sit/chatter/star thresholds so this test
    # exercises only the deterministic walk/bounce logic, regardless of how
    # many random() calls anything else in update() happens to make per tick.
    monkeypatch.setattr(random, "random", lambda: 0.99)

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    xs = set()
    for _ in range(300):
        p.update()
        xs.add(round(p.x, 1))
    assert min(xs) <= 5
    assert max(xs) >= 80


def test_large_pet_stays_centered_and_only_wiggles_vertically():
    p = pet.Pet("bunny", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    start_x = p.x
    expected_x = (100 - p.width) // 2
    expected_y = (50 - p.height) // 2
    assert p.x == expected_x
    assert p.y == expected_y

    offsets = set()
    for _ in range(200):
        p.update()
        offsets.add(p.y_offset())
    assert p.x == start_x  # never moves horizontally
    assert offsets <= {-1, 0}  # only ever bobs by one row


def test_large_pet_recenters_on_resize():
    p = pet.Pet("raccoon", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    p.resize(200, 80)
    assert p.x == (200 - p.width) // 2
    assert p.y == (80 - p.height) // 2


def test_small_pet_bounces_off_edges(monkeypatch):
    # Pin random.random() above the sit/chatter thresholds so this test
    # exercises only the deterministic edge-bounce logic.
    monkeypatch.setattr(random, "random", lambda: 0.99)

    p = pet.Pet("mouse", max_x=100, max_y=20, speed=5.0, bubble_pairs=[])
    p.x = 0.0
    p.direction = -1
    p.state = "walk"
    p.update()
    assert p.x == 0
    assert p.direction == 1

    max_x_pos = max(0, p.max_x - p.width - 1)
    p.x = float(max_x_pos)
    p.direction = 1
    p.update()
    assert p.x == max_x_pos
    assert p.direction == -1


def test_feed_sets_bubble_and_sparkle():
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[2, 3])
    p.feed()
    assert p.bubble in pet.DUCK_FED
    assert p.sparkle is True
    assert p.state == "sit"


def test_check_command_sets_bubble_on_reaction(tmp_path, monkeypatch):
    cmd_file = tmp_path / "lastcmd"
    monkeypatch.setattr(pet, "CMD_FILE", str(cmd_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    cmd_file.write_text("git commit -m hi")
    p.check_command()

    assert p.last_cmd == "git commit -m hi"
    assert p.bubble in pet.COMMAND_REACTIONS[0][1]
    assert p.state == "sit"


def test_check_command_ignores_unchanged_mtime(tmp_path, monkeypatch):
    cmd_file = tmp_path / "lastcmd"
    monkeypatch.setattr(pet, "CMD_FILE", str(cmd_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    cmd_file.write_text("ls")
    p.check_command()
    p.bubble = None  # simulate the bubble having already expired
    p.check_command()  # file untouched: mtime unchanged, should be a no-op

    assert p.bubble is None


def test_check_exit_zero_is_silent(tmp_path, monkeypatch):
    exit_file = tmp_path / "lastexit"
    monkeypatch.setattr(pet, "EXIT_FILE", str(exit_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    exit_file.write_text("0")
    p.check_exit()

    assert p.bubble is None


def test_check_exit_nonzero_shows_roast(tmp_path, monkeypatch):
    exit_file = tmp_path / "lastexit"
    monkeypatch.setattr(pet, "EXIT_FILE", str(exit_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    p.last_cmd = "somecommand --flag"
    exit_file.write_text("1")
    p.check_exit()

    assert p.bubble in pet.ROAST_LINES


def test_check_exit_127_suggests_fix(tmp_path, monkeypatch):
    exit_file = tmp_path / "lastexit"
    monkeypatch.setattr(pet, "EXIT_FILE", str(exit_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    p.last_cmd = "gti status"
    exit_file.write_text("127")
    p.check_exit()

    assert "git" in p.bubble
