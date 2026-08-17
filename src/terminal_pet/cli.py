"""CLI entrypoints for terminal-pet."""

import argparse
import locale
import os
import random
import sys

from . import __version__, hook, pet
from .config import CONFIG_DIR, CONFIG_PATH, DEFAULT_CONFIG, load_config, save_config

BOOL_KEYS = (
    "enable_encouragements",
    "enable_roasts",
    "enable_typo_help",
    "enable_seasonal",
    "enable_sparkles",
)


def build_parser():
    parser = argparse.ArgumentParser(description="A little pet that wanders around your terminal.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="launch the pet")
    _add_run_arguments(run_parser)

    setup_parser = subparsers.add_parser("setup", help="guided first-run setup")
    setup_parser.add_argument("--pet", choices=[*pet.PETS.keys(), "random"])
    setup_parser.add_argument("--speed", type=float)
    setup_parser.add_argument("--dock", dest="dock", action="store_true", default=None, help="make docking the default when supported")
    setup_parser.add_argument("--no-dock", dest="dock", action="store_false", help="avoid docking by default")
    setup_parser.add_argument("--chattiness", choices=["quiet", "normal", "chaos"])
    setup_parser.add_argument("--yes", action="store_true", help="accept prompts using defaults or flags")
    for key in BOOL_KEYS:
        label = key.replace("enable_", "").replace("_", "-")
        setup_parser.add_argument(f"--{label}", dest=key, action="store_true")
        setup_parser.add_argument(f"--no-{label}", dest=key, action="store_false")
        setup_parser.set_defaults(**{key: None})

    check_parser = subparsers.add_parser("check", help="show install and environment diagnostics")
    check_parser.add_argument("--verbose", action="store_true", help="show paths and config details")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    _add_run_arguments(parser)
    return parser


def _add_run_arguments(parser):
    parser.add_argument("--pet", dest="pet_name", choices=[*pet.PETS.keys(), "random"], default=None)
    parser.add_argument("--speed", type=float, default=None, help="higher = faster")
    parser.add_argument(
        "--dock",
        action="store_true",
        default=None,
        help="launch docked in a small pane/window instead of taking over this one",
    )
    parser.add_argument(
        "--no-dock",
        dest="dock",
        action="store_false",
        help="run in the current terminal even if docking is enabled in saved defaults",
    )
    parser.add_argument(
        "--dock-height",
        type=float,
        default=15.0,
        metavar="PERCENT",
        help="iTerm2 only: dock pane height as %% of window height (default 15)",
    )
    parser.add_argument("--chattiness", choices=["quiet", "normal", "chaos"], default=None)
    for key in BOOL_KEYS:
        label = key.replace("enable_", "").replace("_", "-")
        parser.add_argument(f"--{label}", dest=key, action="store_true", default=None)
        parser.add_argument(f"--no-{label}", dest=key, action="store_false")


def parse_args(argv=None):
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"-h", "--help"}:
        return parser.parse_args(argv)
    if argv and argv[0] in {"run", "setup", "check"}:
        return parser.parse_args(argv)
    return parser.parse_args(["run", *argv])


def _merge_runtime_config(args):
    config = load_config()
    runtime = dict(config)
    if getattr(args, "pet_name", None) is not None:
        runtime["default_pet"] = args.pet_name
    if getattr(args, "speed", None) is not None:
        runtime["default_speed"] = args.speed
    if getattr(args, "dock", None) is not None:
        runtime["default_dock"] = args.dock
    if getattr(args, "chattiness", None) is not None:
        runtime["chattiness"] = args.chattiness
    for key in BOOL_KEYS:
        value = getattr(args, key, None)
        if value is not None:
            runtime[key] = value
    return runtime


def _shell_rc_path(shell_name):
    return os.path.expanduser(f"~/.{shell_name}rc")


def _terminal_support():
    term_program = os.environ.get("TERM_PROGRAM", "")
    if sys.platform == "darwin":
        if term_program in {"iTerm.app", "Apple_Terminal"}:
            return "supported", f"Docking supported in {term_program}."
        if term_program:
            return "partial", f"{term_program} detected. Pet runs fine, but docking falls back to inline mode."
        return "partial", "Unknown macOS terminal. Pet runs, but docking may fall back to inline mode."
    if sys.platform.startswith("linux"):
        return "partial", "Linux detected. Pet runs, but --dock falls back to inline mode."
    if sys.platform.startswith("win"):
        return "unsupported", "Windows is not supported yet because curses is unavailable by default."
    return "partial", f"{sys.platform} detected. Basic terminal mode may work, but docking is not supported."


def get_doctor_report():
    config = load_config()
    hook_status = hook.is_installed()
    active_shell = os.path.basename(os.environ.get("SHELL", "")) or "unknown"
    term_status, term_message = _terminal_support()
    state_dir_ok = os.path.isdir(CONFIG_DIR) or not os.path.exists(CONFIG_DIR)
    write_test_ok = False
    write_error = None
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        probe = os.path.join(CONFIG_DIR, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        write_test_ok = True
    except OSError as exc:
        write_error = str(exc)

    return {
        "shell": active_shell,
        "shell_rc": _shell_rc_path(active_shell) if active_shell in {"zsh", "bash"} else None,
        "hook_status": hook_status,
        "term_status": term_status,
        "term_message": term_message,
        "curses_available": pet.curses is not None,
        "config_path": CONFIG_PATH,
        "config": config,
        "state_dir_ok": state_dir_ok,
        "write_test_ok": write_test_ok,
        "write_error": write_error,
    }


def _print_check_line(label, ok, details):
    status = "OK" if ok else "WARN"
    print(f"[{status}] {label}: {details}")


def command_check(args):
    report = get_doctor_report()

    shell = report["shell"]
    print("terminal-pet check")
    print(f"Shell: {shell}")
    print(f"Config: {report['config_path']}")
    print("")

    active_hook = report["hook_status"].get(shell)
    if active_hook:
        hook_ok = active_hook["hook_exists"] and active_hook["rc_has_source"]
        hook_details = "hook script and rc source line found" if hook_ok else "run `terminal-pet setup` to install the hook"
    else:
        hook_ok = False
        hook_details = "shell not recognized for auto-hook install"
    _print_check_line("Hook", hook_ok, hook_details)

    _print_check_line("Terminal", report["term_status"] != "unsupported", report["term_message"])
    _print_check_line("State dir", report["write_test_ok"], "read/write access looks good" if report["write_test_ok"] else report["write_error"])
    _print_check_line("Curses", report["curses_available"], "available" if report["curses_available"] else "missing; the pet UI will not launch here")

    if args.verbose:
        print("")
        print("Current defaults:")
        for key in sorted(report["config"]):
            print(f"  {key}: {report['config'][key]}")
        print("")
        print("Hook details:")
        for shell_name, status in sorted(report["hook_status"].items()):
            print(
                f"  {shell_name}: hook_exists={status['hook_exists']} rc_has_source={status['rc_has_source']} "
                f"hook_path={status['hook_path']} rc_path={status['rc_path']}"
            )
    return 0


def _prompt_choice(prompt, options, default, enabled):
    if not enabled:
        return default
    suffix = "/".join(options)
    raw = input(f"{prompt} [{suffix}] (default: {default}): ").strip().lower()
    return raw if raw in options else default


def _prompt_bool(prompt, default, enabled):
    if not enabled:
        return default
    default_label = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{default_label}]: ").strip().lower()
    if raw in {"y", "yes"}:
        return True
    if raw in {"n", "no"}:
        return False
    return default


def command_setup(args):
    config = load_config()
    interactive = not args.yes

    chosen_pet = args.pet or _prompt_choice("Pick a default pet", [*pet.PETS.keys(), "random"], config["default_pet"], interactive)
    speed = args.speed
    if speed is None and interactive:
        raw_speed = input(f"Default speed (current {config['default_speed']}): ").strip()
        if raw_speed:
            try:
                speed = float(raw_speed)
            except ValueError:
                speed = config["default_speed"]
    if speed is None:
        speed = config["default_speed"]

    chattiness = args.chattiness or _prompt_choice("How chatty should your pet be?", ["quiet", "normal", "chaos"], config["chattiness"], interactive)
    default_dock = args.dock if args.dock is not None else _prompt_bool("Dock by default when supported?", config["default_dock"], interactive)

    new_config = dict(config)
    new_config.update(
        {
            "default_pet": chosen_pet,
            "default_speed": speed,
            "default_dock": default_dock,
            "chattiness": chattiness,
        }
    )

    for key in BOOL_KEYS:
        value = getattr(args, key, None)
        if value is None:
            label = key.replace("enable_", "").replace("_", " ")
            value = _prompt_bool(f"Enable {label}?", config[key], interactive)
        new_config[key] = value

    save_config(new_config)
    hook.install()
    print(f"Saved config to {CONFIG_PATH}")
    print("Setup complete.")
    print("Next steps:")
    print("  1. Open a new terminal tab, or source your shell rc file.")
    print("  2. Run `terminal-pet` to launch using your saved defaults.")
    print("  3. Run `terminal-pet check` anytime to verify your setup.")
    return 0


def command_run(args):
    runtime = _merge_runtime_config(args)
    kind = runtime["default_pet"]
    if kind == "random":
        kind = random.choice(list(pet.PETS.keys()))

    if runtime["default_dock"]:
        from . import dock

        dock.launch(kind, runtime["default_speed"], args.dock_height)
        return 0

    if pet.curses is None:
        print("terminal-pet needs Python's `curses` module, which isn't available here.")
        print("On Windows, install it with: pip install windows-curses")
        return 1

    locale.setlocale(locale.LC_ALL, "")
    try:
        pet.run_curses(kind, runtime["default_speed"], runtime)
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None):
    args = parse_args(argv)
    if args.command == "setup":
        return command_setup(args)
    if args.command == "check":
        return command_check(args)
    return command_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
