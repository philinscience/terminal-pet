"""Shared config helpers for terminal-pet."""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.terminal_pet")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "default_pet": "random",
    "default_speed": 1.0,
    "default_dock": False,
    "chattiness": "normal",
    "enable_encouragements": True,
    "enable_roasts": True,
    "enable_typo_help": True,
    "enable_seasonal": True,
    "enable_sparkles": True,
}


def normalize_config(raw):
    config = dict(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return config

    default_pet = raw.get("default_pet", config["default_pet"])
    if isinstance(default_pet, str):
        config["default_pet"] = default_pet

    try:
        config["default_speed"] = float(raw.get("default_speed", config["default_speed"]))
    except (TypeError, ValueError):
        pass

    if raw.get("chattiness") in {"quiet", "normal", "chaos"}:
        config["chattiness"] = raw["chattiness"]

    for key in (
        "default_dock",
        "enable_encouragements",
        "enable_roasts",
        "enable_typo_help",
        "enable_seasonal",
        "enable_sparkles",
    ):
        if key in raw:
            config[key] = bool(raw[key])

    return config


def load_config(path=CONFIG_PATH):
    try:
        with open(path) as f:
            return normalize_config(json.load(f))
    except (OSError, ValueError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def save_config(config, path=CONFIG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    normalized = normalize_config(config)
    with open(path, "w") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)
        f.write("\n")
    return normalized
