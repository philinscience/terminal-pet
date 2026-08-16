"""Launches the pet docked in a small pane/window, detecting the terminal app in use.

Small pets (duck, mouse) get a compact pane/window:
  - iTerm2: docks it in a split pane sized as a precise percentage of the
    current window's height (default 15%) below your current session, using
    iTerm2's Python API. Falls back to a plain 50/50 AppleScript split if the
    Python API isn't available (AppleScript alone can't set a custom ratio).
  - Terminal.app: opens a small separate window in the bottom-right corner of the
    screen (Terminal.app has no split-pane support).
  - tmux (any platform, e.g. SSH'd into a Linux box from a Mac): the
    AppleScript/iTerm2-API paths above only work because they control the
    terminal *application* itself, which has to run on the same machine as
    your eyeballs. Over SSH the pet process is on the remote box and has no
    way to reach back and drive your local terminal app. tmux sidesteps this
    entirely — a split pane is just terminal output multiplexed over the
    same SSH stream, so it renders inside whatever window you're already
    looking at. Used whenever $TMUX is set (i.e. --dock is run from inside a
    tmux session) and the mac-native paths above don't apply.

Large pets (bunny, and any future pet marked "size": "large" in pet.PETS)
always get their own separate square window instead, on iTerm2 and
Terminal.app; under tmux they get their own tmux window (not sized/square,
since tmux windows fill the terminal).

Anything else: runs it directly in the current window.
"""

import os
import shlex
import shutil
import subprocess
import sys

ITERM_APPLESCRIPT_FALLBACK = """
tell application "iTerm2"
    tell current window
        tell current session
            set newSession to (split horizontally with same profile)
            tell newSession
                write text "{cmd}; exit"
            end tell
        end tell
    end tell
end tell
"""

TERMINAL_SMALL_SCRIPT = """
tell application "Terminal"
    activate
    do script "{cmd}; exit"
    delay 0.3
    set targetWindow to front window
    tell application "Finder" to set screenBounds to bounds of window of desktop
    set scrW to item 3 of screenBounds
    set scrH to item 4 of screenBounds
    set winW to {win_w}
    set winH to {win_h}
    set x2 to scrW - 20
    set y2 to scrH - 60
    set x1 to x2 - winW
    set y1 to y2 - winH
    set bounds of targetWindow to {{x1, y1, x2, y2}}
end tell
"""

# Large pets: resize the window WHILE IT'S STILL AN IDLE SHELL, then launch
# the pet — not the other way round. Launching first and resizing after (like
# the small-pet script above) means curses starts at the terminal's default
# size and then gets hit with a resize mid-run, which reads as jittery/erratic
# since the pet's centered position keeps recomputing while the window is
# still settling.
TERMINAL_SCRIPT = """
tell application "Terminal"
    activate
    do script ""
    delay 0.3
    set targetWindow to front window
    tell application "Finder" to set screenBounds to bounds of window of desktop
    set scrW to item 3 of screenBounds
    set scrH to item 4 of screenBounds
    set winW to {win_w}
    set winH to {win_h}
    set x2 to scrW - 20
    set y2 to scrH - 60
    set x1 to x2 - winW
    set y1 to y2 - winH
    set bounds of targetWindow to {{x1, y1, x2, y2}}
    delay 0.2
    do script "{cmd}; exit" in targetWindow
end tell
"""

ITERM_NEW_WINDOW_SCRIPT = """
tell application "iTerm2"
    activate
    set beforeIDs to id of windows
    create window with default profile
    delay 0.3
    set newWindow to missing value
    repeat with w in windows
        if beforeIDs does not contain (id of w) then
            set newWindow to w
            exit repeat
        end if
    end repeat
    if newWindow is not missing value then
        tell application "Finder" to set screenBounds to bounds of window of desktop
        set scrW to item 3 of screenBounds
        set scrH to item 4 of screenBounds
        set winW to {win_w}
        set winH to {win_h}
        set x2 to scrW - 20
        set y2 to scrH - 60
        set x1 to x2 - winW
        set y1 to y2 - winH
        set bounds of newWindow to {{x1, y1, x2, y2}}
        delay 0.2
        tell current session of current tab of newWindow
            write text "{cmd}; exit"
        end tell
    end if
end tell
"""

# Rough monospace cell size (px) used to size the square window around a
# large pet's art, plus flat padding for the title bar, speech bubble line,
# footer, and a little wiggle room.
CHAR_W_PX = 9
CHAR_H_PX = 18
WINDOW_PADDING_PX = 160
MIN_LARGE_WINDOW_SIZE = 400


def _large_window_size(pet):
    from . import pet as pet_module

    art = pet_module.PETS[pet]["art"]
    width_chars = max(len(line) for line in art)
    height_chars = len(art)
    needed_w = width_chars * CHAR_W_PX + WINDOW_PADDING_PX
    needed_h = height_chars * CHAR_H_PX + WINDOW_PADDING_PX
    return max(MIN_LARGE_WINDOW_SIZE, needed_w, needed_h)


def _pet_command(pet_argv):
    exe = shutil.which("terminal-pet")
    parts = [exe] if exe else [sys.executable, "-m", "terminal_pet.pet"]
    parts += pet_argv
    return " ".join(shlex.quote(p) for p in parts)


def _launch_iterm_applescript(cmd):
    script = ITERM_APPLESCRIPT_FALLBACK.format(cmd=cmd)
    subprocess.run(["osascript", "-e", script], check=True)
    print("Pet pane launched below your current session (50/50 split).")
    print(
        "For a precise --dock-height, enable iTerm2's Python API: "
        "iTerm2 > Settings > General > Magic > \"Enable Python API\", "
        "and `pip install iterm2`."
    )


def _launch_iterm(pet_argv, dock_height_percent):
    cmd = _pet_command(pet_argv)

    try:
        import iterm2
    except ImportError:
        print("Precise sizing needs the 'iterm2' package: pip install iterm2")
        _launch_iterm_applescript(cmd)
        return

    outcome = {"ok": False}

    async def main(connection):
        app = await iterm2.async_get_app(connection)
        window = app.current_terminal_window
        if window is None:
            return
        tab = window.current_tab
        session = tab.current_session

        total_rows = session.grid_size.height
        total_cols = session.grid_size.width
        target_rows = max(5, round(total_rows * dock_height_percent / 100.0))

        new_session = await session.async_split_pane(vertical=False)
        new_session.preferred_size = iterm2.util.Size(total_cols, target_rows)
        await tab.async_update_layout()
        await new_session.async_send_text(f"{cmd}; exit\n")
        outcome["ok"] = True

    try:
        iterm2.run_until_complete(main)
    except Exception:
        pass

    if outcome["ok"]:
        print(f"Pet pane launched below your current session (~{dock_height_percent:.0f}% of window height).")
        print("(Pass --dock-height PERCENT to change it.)")
    else:
        print("Couldn't connect to iTerm2's Python API.")
        print("Enable it: iTerm2 > Settings > General > Magic > \"Enable Python API\", then try again.")
        _launch_iterm_applescript(cmd)


def _in_tmux():
    return bool(os.environ.get("TMUX")) and shutil.which("tmux") is not None


def _launch_tmux_pane(pet_argv, dock_height_percent):
    cmd = _pet_command(pet_argv)
    # -d keeps focus on your current pane ("keep working normally"); -l NN%
    # sizes the new pane as a percentage of the window (tmux >= 2.9; older
    # tmux only understands the now-deprecated -p NN, not handled here).
    subprocess.run(
        ["tmux", "split-window", "-d", "-v", "-l", f"{dock_height_percent:.0f}%", cmd],
        check=True,
    )
    print(f"Pet pane launched below your current pane (~{dock_height_percent:.0f}% of window height, tmux).")
    print("(Pass --dock-height PERCENT to change it.)")


def _launch_tmux_window(pet_argv):
    cmd = _pet_command(pet_argv)
    subprocess.run(["tmux", "new-window", "-d", "-n", "pet", cmd], check=True)
    print("Pet launched in a new tmux window named 'pet'.")
    print("Switch to it with `tmux select-window -t pet` (or prefix + w).")


def _run_inline(pet_argv):
    if sys.platform == "darwin":
        print(f"Unrecognized terminal (TERM_PROGRAM={os.environ.get('TERM_PROGRAM', '')!r}).")
    elif shutil.which("tmux") is None:
        print("Docking on Linux needs tmux — install it and run --dock from inside a tmux session.")
    else:
        print("Not inside a tmux session — start one with `tmux` and rerun --dock for a docked pane.")
    print("Running the pet directly in this window instead.")
    sys.argv = ["terminal-pet", *pet_argv]
    from . import pet as pet_module

    pet_module.run()


def _launch_large_window(pet, pet_argv):
    term_program = os.environ.get("TERM_PROGRAM", "")
    cmd = _pet_command(pet_argv)
    size = _large_window_size(pet)

    if term_program == "iTerm.app":
        script = ITERM_NEW_WINDOW_SCRIPT.format(cmd=cmd, win_w=size, win_h=size)
        subprocess.run(["osascript", "-e", script], check=True)
    elif term_program == "Apple_Terminal":
        script = TERMINAL_SCRIPT.format(cmd=cmd, win_w=size, win_h=size)
        subprocess.run(["osascript", "-e", script], check=True)
    elif _in_tmux():
        _launch_tmux_window(pet_argv)
        return
    else:
        _run_inline(pet_argv)
        return

    print("Pet launched, enjoy <3")


def launch(pet, speed, dock_height_percent=15.0):
    pet_argv = ["--pet", pet, "--speed", str(speed)]

    from . import pet as pet_module

    if pet_module.PETS[pet].get("size") == "large":
        _launch_large_window(pet, pet_argv)
        return

    term_program = os.environ.get("TERM_PROGRAM", "")

    if term_program == "iTerm.app":
        _launch_iterm(pet_argv, dock_height_percent)

    elif term_program == "Apple_Terminal":
        cmd = _pet_command(pet_argv)
        script = TERMINAL_SMALL_SCRIPT.format(cmd=cmd, win_w=380, win_h=260)
        subprocess.run(["osascript", "-e", script], check=True)
        print("Pet launched, enjoy <3")

    elif _in_tmux():
        _launch_tmux_pane(pet_argv, dock_height_percent)

    else:
        _run_inline(pet_argv)
