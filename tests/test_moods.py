"""Tests for time-aware moods (sleepy at night, festive on special dates)
and the rare easter eggs (golden pet, shooting star).
"""

import random
import time

import pytest

from terminal_pet import pet


@pytest.fixture(autouse=True)
def _seeded_random():
    random.seed(0)


@pytest.fixture(autouse=True)
def _isolated_state_files(tmp_path, monkeypatch):
    monkeypatch.setattr(pet, "CMD_FILE", str(tmp_path / "lastcmd"))
    monkeypatch.setattr(pet, "EXIT_FILE", str(tmp_path / "lastexit"))


def _struct_time(hour=12, month=6, day=15):
    return time.struct_time((2026, month, day, hour, 0, 0, 0, 0, -1))


def test_is_night_true_during_night_hours(monkeypatch):
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    for hour in (23, 0, 3, 5):
        monkeypatch.setattr(pet.time, "localtime", lambda h=hour: _struct_time(hour=h))
        assert p._is_night() is True, hour


def test_is_night_false_during_day_hours(monkeypatch):
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    for hour in (6, 9, 12, 18, 22):
        monkeypatch.setattr(pet.time, "localtime", lambda h=hour: _struct_time(hour=h))
        assert p._is_night() is False, hour


def test_special_date_detected(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(month=10, day=31))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    assert p.festive is True
    assert p.special_info is pet.SPECIAL_DATES[(10, 31)]


def test_no_special_date_on_an_ordinary_day(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(month=6, day=15))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    assert p.festive is False
    assert p.special_info is None


def test_chatter_pool_uses_sleepy_sayings_at_night(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=2, month=6, day=15))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    pool = p._chatter_pool()
    assert set(pet.SLEEPY_SAYINGS) <= set(pool)
    assert not set(pet.ENCOURAGEMENTS) & set(pool)


def test_chatter_pool_uses_encouragements_during_the_day(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    pool = p._chatter_pool()
    assert set(pet.ENCOURAGEMENTS) <= set(pool)
    assert not set(pet.SLEEPY_SAYINGS) & set(pool)


def test_chatter_pool_prefers_festive_over_sleepy(monkeypatch):
    # 2am on Halloween: festive should win, not sleepy.
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=2, month=10, day=31))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    pool = p._chatter_pool()
    assert set(pet.SPECIAL_DATES[(10, 31)]["sayings"]) <= set(pool)
    assert not set(pet.SLEEPY_SAYINGS) & set(pool)


def test_large_pet_wiggles_slower_at_night(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    day_pet = pet.Pet("bunny", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    day_pet.tick = 15
    day_offset = day_pet.y_offset()

    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=2, month=6, day=15))
    night_pet = pet.Pet("bunny", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    night_pet.tick = 15
    night_offset = night_pet.y_offset()

    # At tick 15, the day cadence (10) has already flipped past its first
    # bob (back to 0) while the slower night cadence (20) is still mid-bob
    # (-1) — proving night wiggles slower, not just differently.
    assert day_offset == 0
    assert night_offset == -1


def test_idle_pet_becomes_sleepy_during_day(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    p.idle_ticks = pet.IDLE_SLEEP_TICKS
    assert p._is_sleepy() is True
    pool = p._chatter_pool()
    assert set(pet.SLEEPY_SAYINGS) <= set(pool)


def test_activity_wakes_sleepy_pet(tmp_path, monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    cmd_file = tmp_path / "lastcmd"
    monkeypatch.setattr(pet, "CMD_FILE", str(cmd_file))

    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    p.idle_ticks = pet.VERY_SLEEPY_TICKS
    cmd_file.write_text("git status")
    p.check_command()

    assert p.idle_ticks == 0
    assert p._is_sleepy() is False


def test_large_pet_wiggles_slower_when_very_sleepy_during_day(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    lively_pet = pet.Pet("bunny", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    lively_pet.tick = 15
    lively_offset = lively_pet.y_offset()

    sleepy_pet = pet.Pet("bunny", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    sleepy_pet.idle_ticks = pet.VERY_SLEEPY_TICKS
    sleepy_pet.tick = 15
    sleepy_offset = sleepy_pet.y_offset()

    assert lively_offset == 0
    assert sleepy_offset == -1


def test_golden_pet_always_spawns_when_forced(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.0)  # below GOLDEN_CHANCE
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    assert p.golden is True
    assert p.bubble == pet.GOLDEN_SAYING


def test_golden_pet_never_spawns_when_chance_not_met(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.99)  # above GOLDEN_CHANCE
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[])
    assert p.golden is False


def test_star_spawns_and_crosses_and_despawns(monkeypatch):
    # Force the spawn roll to succeed on the very first check.
    monkeypatch.setattr(random, "random", lambda: 0.0)
    p = pet.Pet("duck", max_x=50, max_y=50, speed=1.0, bubble_pairs=[])
    assert p.star_x is None

    p._update_star()
    assert p.star_x == 0.0
    assert p.star_y is not None

    # Once active, force the roll high so it doesn't matter (spawn check is
    # skipped while a star is already active) and just advance it to the edge.
    monkeypatch.setattr(random, "random", lambda: 0.99)
    for _ in range(50):
        p._update_star()
    assert p.star_x is None  # despawned after crossing max_x
    assert p.star_y is None


def test_special_dates_can_be_disabled(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(month=10, day=31))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[], settings={"enable_seasonal": False})
    assert p.festive is False


def test_encouragements_can_be_disabled(monkeypatch):
    monkeypatch.setattr(pet.time, "localtime", lambda: _struct_time(hour=14, month=6, day=15))
    p = pet.Pet("duck", max_x=100, max_y=50, speed=1.0, bubble_pairs=[], settings={"enable_encouragements": False})
    pool = p._chatter_pool()
    assert not set(pet.ENCOURAGEMENTS) & set(pool)
