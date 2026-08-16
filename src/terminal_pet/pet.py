#!/usr/bin/env python3
"""A little pet that wanders around your terminal. Run it, press q to quit."""

import argparse
import difflib
import locale
import os
import random
import re
import sys
import time

try:
    import curses
except ImportError:
    # Stock Windows Python has no `curses` (it's POSIX-only in the stdlib).
    # Keep the module importable anyway — PETS/art/etc. are still useful
    # metadata for other code (e.g. dock.py) — and fail with a clear message
    # only once someone actually tries to launch the curses UI, in run().
    curses = None

CMD_FILE = os.path.expanduser("~/.terminal_pet/lastcmd")
EXIT_FILE = os.path.expanduser("~/.terminal_pet/lastexit")

# Basic 8-color codes (the standard curses.COLOR_* values — stable across
# platforms). Defined as plain ints, not curses.COLOR_*, so this module's
# color tables don't require curses to be importable just to be defined.
COLOR_YELLOW, COLOR_MAGENTA, COLOR_CYAN = 3, 5, 6
COLOR_GREEN, COLOR_RED = 2, 1

# (pattern, [possible reactions]) — first match wins, most specific first.
COMMAND_REACTIONS = [
    (re.compile(r"^git commit\b"), ["hell yeah, let's ship it!", "nice commit!", "*happy little wiggle*"]),
    (re.compile(r"^git push\b"), ["sending it off, good luck out there!", "off it goes...", "go go go!"]),
    (re.compile(r"^git pull\b"), ["bringing it all home!", "fetching the goods..."]),
    (re.compile(r"^git (status|diff|log)\b"), ["checking the vibes?", "let's see what changed..."]),
    (re.compile(r"^git\b"), ["git stuff! neat"]),
    (re.compile(r"^(ls|ll|la|tree)\b"), ["what's in here?", "ooh, let's look around"]),
    (re.compile(r"^(cat|less|more|bat)\b"), ["let me read that...", "ooh, what's this say?"]),
    (re.compile(r"^cd\b"), ["on the move!", "off we go"]),
    (re.compile(r"^rm\b"), ["uh oh... hope that was on purpose", "...gone. forever."]),
    (re.compile(r"^(npm|pip|pip3|yarn|brew|cargo|bundle) (i|install|add)\b"), ["ooh, snacks incoming (dependencies)", "gathering ingredients..."]),
    (re.compile(r"^(python|python3|node|ruby|go run)\b"), ["let's see if this works...", "fingers crossed"]),
    (re.compile(r"^(pytest|npm test|npm run test|go test|jest)\b"), ["testing time, fingers crossed", "moment of truth..."]),
    (re.compile(r"^ssh\b"), ["off to another machine!", "connecting..."]),
    (re.compile(r"^docker\b"), ["containers!", "boxed up nice and tidy..."]),
    (re.compile(r"^sudo\b"), ["ooh, big permissions energy", "with great power..."]),
    (re.compile(r"^curl\b"), ["fetching stuff from the internet!", "reaching into the ether..."]),
    (re.compile(r"^mkdir\b"), ["building something new?", "*digs a new burrow*"]),
    (re.compile(r"^touch\b"), ["a blank canvas!", "fresh file, fresh start"]),
    (re.compile(r"^(cp|mv)\b"), ["shuffling things around", "moving house?"]),
    (re.compile(r"^chmod\b"), ["adjusting permissions, very official", "ooh, access control"]),
    (re.compile(r"^(kill|killall|pkill)\b"), ["yikes, taking it down", "*gulp*"]),
    (re.compile(r"^(ps|top|htop)\b"), ["checking who's running the show", "peeking at the processes"]),
    (re.compile(r"^(vim|nvim|nano|code|emacs)\b"), ["editor time!", "let's write some magic"]),
    (re.compile(r"^man\b"), ["reading the manual, very responsible", "RTFM mode engaged"]),
    (re.compile(r"^history\b"), ["a trip down memory lane", "what have we been up to..."]),
    (re.compile(r"^clear\b"), ["fresh start!", "*wipes the board clean*"]),
    (re.compile(r"^pwd\b"), ["just checking where we are", "you are here"]),
    (re.compile(r"^(export|env)\b"), ["setting the scene", "configuring things"]),
    (re.compile(r"^(tar|zip|unzip)\b"), ["packing it up", "squishing files together"]),
    (re.compile(r"^wget\b"), ["grabbing that from the web", "incoming download"]),
    (re.compile(r"^make\b"), ["building it!", "*hammers away*"]),
    (re.compile(r"^kubectl\b"), ["into the cluster we go", "*pokes at pods*"]),
    (re.compile(r"^terraform\b"), ["shaping infrastructure", "*plans carefully*"]),
    (re.compile(r"^which\b"), ["let's find out", "tracking it down"]),
]

ENCOURAGEMENTS = [
    "you've got this!",
    "looking good today!",
    "keep it up!",
    "great focus!",
    "one step at a time",
    "you're on a roll!",
    "nice work!",
    "believe in yourself!",
    "small steps count too",
    "proud of you",
]

ROAST_LINES = [
    "well, that didn't go as planned",
    "bold strategy. did it work? (no)",
    "task failed successfully, I guess",
    "we don't talk about that one",
    "ambitious. wrong, but ambitious.",
    "that's a paddlin'",
    "the computer said no",
    "10/10 attempt, 0/10 result",
    "it happens to the best of us... and you",
]

TYPO_FALLBACKS = [
    "hmm, never heard of that one",
    "not a command I recognize, chief",
    "typo? or just making stuff up now",
]

SUGGESTION_TEMPLATES = [
    "did you mean '{}'?",
    "pretty sure you meant '{}'",
    "typo alert: probably '{}'?",
    "close... did you mean '{}'?",
]

KNOWN_COMMANDS = [
    "git", "ls", "cd", "cat", "cp", "mv", "rm", "mkdir", "rmdir", "touch", "chmod", "chown",
    "grep", "find", "sed", "awk", "curl", "wget", "ssh", "scp", "docker", "kubectl", "npm",
    "npx", "yarn", "pnpm", "pip", "pip3", "python", "python3", "node", "ruby", "go", "cargo",
    "rustc", "make", "brew", "sudo", "ps", "kill", "killall", "top", "htop", "less", "more",
    "head", "tail", "echo", "export", "source", "vim", "nvim", "nano", "code", "open", "clear",
    "history", "man", "which", "whoami", "pwd", "df", "du", "tar", "zip", "unzip", "ping",
    "ifconfig", "netstat", "systemctl", "journalctl", "apt", "apt-get", "yum", "gem", "bundle",
    "rails", "terraform", "aws", "gcloud", "az", "psql", "mysql", "redis-cli", "mongo", "jq",
    "tmux", "screen", "diff", "wc", "sort", "uniq", "xargs", "tree",
]


def _suggest_command(word):
    matches = difflib.get_close_matches(word, KNOWN_COMMANDS, n=1, cutoff=0.6)
    return matches[0] if matches else None

DUCK_ART = [
    "    __",
    "___( o)>",
    "\\ <_. )",
    " `---'",
]
DUCK_SAYINGS = ["quack!", "*waddles around*", "quack quack", "*preens feathers*"]
DUCK_FED = ["quack! yummy", "*happy waddle*", "quack <3"]

MOUSE_ART = [
    "       (`-()_.-=-.",
    "       /66  ,  ,  \\",
    "     =(o_/=//_(   /======`",
    "        ~\"` ~\"~~`",
]
MOUSE_SAYINGS = ["squeak!", "*twitches whiskers*", "*scurries about*", "squeak squeak"]
MOUSE_FED = ["squeak! yummy", "*happy nibble*", "squeak <3"]

BUNNY_ART = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⣠⣤⣦⣤⣄⡀⠀⠀⠀⠀⢀⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⣰⠟⠙⠀⠀⠀⠈⢻⡆⠀⣴⠞⠋⠉⠉⠙⠳⣦⡀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⢸⡛⠂⠀⠀⠀⠀⠀⠈⣿⣾⠋⠀⠀⠀⠀⠀⠀⠈⣿⡄⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⣽⠁⠀⠀⠀⠀⠀⠀⠀⣽⢇⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⢰⣿⠄⠀⠀⠀⠀⠀⠀⠐⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⢺⡇⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⢨⡟⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠇⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠈⣿⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⢠⡿⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⣿⡆⠀⠀⢀⣀⣀⡀⢸⣇⠀⠀⠀⠀⠀⠀⠀⢀⣾⠃⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⣘⡟⠰⠛⠛⠉⠙⠉⠈⠃⠀⠀⠀⠀⠀⠀⢰⣾⡟⠚⢶⣄⠀⠀⠀⠀⠀",
    "⠀⠀⠀⣤⡾⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡁⠀⢀⡬⢹⡇⠀⠀⠀⠀",
    "⠀⠀⣴⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣷⠀⠚⢷⣼⡷⠀⠀⠀⠀",
    "⠀⣼⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢙⣷⠀⠀⠘⢿⣷⠀⠀⠀",
    "⢸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣇⠀⠀⠀⢹⣧⠀⠀",
    "⣿⢣⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡏⣡⠀⠀⠀⠻⣧⠀",
    "⣿⡾⡿⠖⠀⠀⠀⠀⠀⠀⠀⠀⢀⣶⣿⣤⠀⠀⠀⠀⠀⠀⠀⣼⡇⠃⠀⠀⠀⠀⢹⣇",
    "⠹⣧⡀⠀⠀⠰⣦⣸⣶⠄⠀⠀⠸⡿⠿⠇⠀⠀⠀⠀⠀⠀⢢⡿⠅⠀⠀⠀⠀⠀⠀⣿",
    "⠀⠈⠻⣦⣒⠸⠛⠻⠖⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⠟⠁⠀⠀⠀⠀⣄⠀⠀⣾",
    "⠀⠀⠀⠈⢙⣷⢶⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⣀⣤⡶⠟⠁⠀⠀⠀⠀⠀⣼⢏⣠⣾⠟",
    "⠀⠀⠀⢀⣾⠃⠀⠀⠉⠛⠛⠻⠶⠶⠶⠶⠞⠋⠁⠀⠀⠀⠀⠀⠀⣰⡾⠛⠛⠉⠀⠀",
    "⠀⠀⠀⠘⣿⠀⠀⠀⠀⠀⢲⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⣠⡾⠏⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠻⣧⡀⠀⠀⣡⣿⠛⠻⠶⣾⠀⠀⠀⠀⠀⠀⠈⢾⡟⠆⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠉⠛⠛⠛⠋⠁⠀⠀⠀⢿⣦⠀⠀⠀⠀⠀⣠⡾⠁⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣶⣤⣀⣦⣴⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀",
]
# Some fonts render "blank" braille (U+2800) with a faint cell outline
# instead of true whitespace — swap it for a real space so it's blank
# everywhere, no matter the font.
BUNNY_ART = [line.replace("⠀", " ") for line in BUNNY_ART]
BUNNY_SAYINGS = ["<3", "*wiggles happily*", "hi!!", "*happy little bounce*", "eee!"]
BUNNY_FED = ["yay, thank you!! <3", "*happy squish*", "nom nom <3"]

RACCOON_ART = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣴⣶⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⠟⠉⠉⠙⠻⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⢀⣴⠟⠋⠀⠀⠀⠙⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⠃⠀⣠⡤⢄⡀⠀⠙⢷⣄⢀⣀⣀⣀⣾⢦⡿⣡⡶⣂⣀⣀⣴⠟⠁⠀⣠⠖⢋⠶⡀⢹⡇⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⠀⢰⠇⣽⣀⡻⣦⠀⠈⠛⠛⠋⠉⠉⠀⠀⠀⠀⠀⠈⠉⠉⠁⠀⠀⢼⣭⣞⣇⣴⡇⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⢸⡃⢠⢷⡱⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠻⢽⣴⡇⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⠀⠘⢶⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⣾⠃⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣌⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⡆⠀⠈⠓⣄⠀⠀⠀⠀⡴⠁⠀⠀⠖⠒⠒⠢⢤⡀⠀⠙⣿⡛⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢨⣿⠇⠀⠀⠀⢀⡠⠎⠀⠀⠀⢀⣀⣀⣀⡀⠀⠘⣶⠾⠿⣶⡇⠀⣀⣤⣤⣄⣀⡀⠀⠙⠲⡄⢹⣟⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡟⠀⠀⠀⡤⠋⠀⠀⣠⡴⠚⠏⠉⠉⠙⠉⠢⣤⡇⠀⠀⠈⢧⡾⠋⠁⠀⡀⠀⠋⢷⣄⠀⠘⢦⢻⣆⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡿⠁⢀⡤⠊⠀⢀⣴⠾⠋⠀⠀⢀⣤⣤⣄⠀⠀⠉⠀⠀⠀⠀⠀⠀⠀⣠⣶⣶⡄⠀⠀⠛⢿⣄⠀⠑⢽⣧⣀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣶⠟⠔⠒⠉⠀⠀⣰⠟⠁⠀⠀⠀⠀⣾⣿⣿⣿⡆⣀⣤⣤⡄⠀⡀⣤⣤⣶⣿⣿⣿⣿⠀⠀⠀⠀⠻⣧⠀⠀⢨⣍⠁⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⠃⠀⠀⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀⠙⠿⠟⣁⠞⠉⠀⠀⣿⣿⣿⣿⡆⠀⠙⣿⠋⠁⠀⠀⠀⠀⠀⢻⡇⠀⠀⣽⠃⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⡄⠀⠀⠀⠀⢻⣇⠀⠀⠀⠀⠀⠀⠀⢀⡼⠋⠀⠀⠀⠀⠉⠛⣿⠋⠀⠀⣀⠈⠻⢄⡀⠀⠀⢀⡰⠏⠀⠀⢠⡿⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣷⡀⠀⠀⠀⠀⠉⠳⠤⢤⣤⡤⠤⠚⠁⠀⠀⣸⣷⣦⣤⣴⠾⠻⠶⠶⠾⠛⠷⣦⡀⠀⠉⠉⠁⠀⠀⠀⣠⡿⠁⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⠟⠁⣀⣀⠀⠀⠀⢶⠄⠀⢀⣤⡌⠻⣧⡀⠀⠀⢀⣠⡾⠟⠁⠀⠀⠀⠀⠀",
    "⠀⠀⣤⣴⣾⠿⠒⠳⢶⣤⡀⠀⠀⢨⣿⠛⠦⠤⠀⠀⠀⠀⠀⠀⠀⠀⣾⠃⠀⠀⠿⠿⠀⠀⠀⠀⠀⠀⠈⠛⠃⢀⣸⣧⣀⠰⠛⣿⠗⠀⠀⠀⠀⠀⠀⠀",
    "⠀⣴⡟⠉⠀⠀⠀⢀⠀⠉⢿⣄⠀⠐⣿⠂⠀⠀⠀⠀⠀⣀⣀⣀⣤⡾⠟⣛⣻⣿⣄⠀⠀⠀⠇⠀⠀⣠⣄⠀⢠⡿⠿⡯⠻⢷⣄⣙⢷⡄⠀⠀⠀⠀⠀⠀",
    "⢸⣏⠃⠀⠀⠀⣠⠖⠶⠞⠋⣿⣀⣾⠏⠀⠀⠀⠀⠀⠈⠉⠉⢻⡋⠀⠀⠈⢩⣴⣿⣄⣴⣤⠀⠀⠀⠟⠛⠀⣿⡿⣶⠀⠀⠀⡿⠉⠈⢻⡆⠀⠀⠀⠀⠀",
    "⣿⡯⠴⠋⠉⠉⠁⠀⠀⢀⣀⢸⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡆⠀⠀⠀⠀⣠⡿⠋⠛⠋⠀⠀⠀⢀⣀⠀⠛⣷⡔⠀⠀⣠⠟⠀⠀⢸⣿⠀⠀⠀⠀⠀",
    "⣿⡇⠀⠀⡀⣠⠖⠒⠖⠋⢩⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣆⡀⠀⣼⡟⠀⠀⠀⠀⣦⠀⠀⠿⠿⠀⢠⣾⣷⡶⠿⠋⠀⠀⠀⣸⡟⠀⠀⠀⠀⠀",
    "⣿⣇⣴⠋⠉⠉⠀⠀⠄⠀⣼⠇⠀⠀⠀⠀⢠⣄⠀⠀⠀⠀⠀⠀⠀⢀⣨⣿⠋⠛⢷⣤⣤⣀⣀⣀⣀⣠⣤⡿⠛⠀⠘⠻⣦⣤⣀⣤⣴⠿⣷⣄⠀⠀⠀⠀",
    "⣿⣷⠀⠀⠀⢀⣀⡰⠛⠙⣿⠀⠀⠀⠀⠀⠈⠙⠷⠶⢶⣤⣶⣶⠾⠟⠉⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠉⠁⠀⠀⠀⠀⠀⠀⠹⠉⠉⠀⠀⠀⠻⣧⠀⠀⠀",
    "⢸⣇⠀⣀⣴⠉⠁⠀⠀⢸⣟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠓⠀⠠⡇⠀⠀⠀⠀⠀⢹⡇⠀⠀",
    "⠈⢿⡏⠀⠀⠀⠀⣀⣾⡙⣯⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠁⠀⠀⠀⠀⠀⢸⡇⠀⠀",
    "⠀⠈⢻⣆⠀⠀⡞⠃⠀⠀⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠎⠀⠀⢀⣠⣤⣤⣿⣁⠀⠀",
    "⠀⠀⠀⠙⢷⣴⣇⠀⠀⢀⡟⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⡶⠶⠛⠿⢿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠋⢀⣴⠿⠋⠁⢴⣗⢻⣿⣷⡀",
    "⠀⠀⠀⠀⠀⠉⠻⠶⣶⣿⣀⣈⣿⣦⡀⠀⠀⠀⠀⢀⡴⠋⠁⠀⢰⣤⡘⣦⣹⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣶⣯⣄⣠⣿⡀⠀⠀⠀⠀⢙⣷⣿⡿⠁",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠛⠷⣦⣤⣄⣸⣃⠀⠀⠀⠀⣸⣧⣼⣿⠟⠓⠶⠶⠶⠾⠛⠛⠛⠛⠉⠉⠀⠀⠉⠙⠛⠛⠛⠛⠛⠛⠛⠛⠉⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠙⠛⠛⠛⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
]
RACCOON_ART = [line.replace("⠀", " ") for line in RACCOON_ART]
RACCOON_SAYINGS = ["*rustles through trash*", "chitter chitter!", "*washes paws*", "ooh, shiny...", "*peeks out from the mask*"]
RACCOON_FED = ["yoink, thanks!", "*happily hoards it*", "chirr~ <3"]

# "small" pets walk back and forth and dock in a small pane/window.
# "large" pets sit in place (gentle up/down wiggle) and always get their own
# square window — add more of either kind here without touching any other code.
#
# 256-color code, and an 8-color fallback for terminals without extended color.
PETS = {
    "duck": {"art": DUCK_ART, "sayings": DUCK_SAYINGS, "fed": DUCK_FED, "color256": 220, "color8": COLOR_YELLOW, "size": "small"},
    "mouse": {"art": MOUSE_ART, "sayings": MOUSE_SAYINGS, "fed": MOUSE_FED, "color256": 217, "color8": COLOR_MAGENTA, "size": "small"},
    "bunny": {"art": BUNNY_ART, "sayings": BUNNY_SAYINGS, "fed": BUNNY_FED, "color256": 117, "color8": COLOR_CYAN, "size": "large"},
    "raccoon": {"art": RACCOON_ART, "sayings": RACCOON_SAYINGS, "fed": RACCOON_FED, "color256": 87, "color8": COLOR_CYAN, "size": "large"},
}

# Bright palette the speech bubble picks from at random, for a bit of sparkle.
BUBBLE_PALETTE_256 = [51, 213, 226, 118, 208, 201]
BUBBLE_PALETTE_8 = [COLOR_CYAN, COLOR_MAGENTA, COLOR_YELLOW, COLOR_GREEN, COLOR_RED, COLOR_MAGENTA]

# --- time-aware moods ---
SLEEPY_SAYINGS = ["*yawns*", "zzz...", "getting sleepy...", "*rubs eyes*", "past my bedtime..."]
NIGHT_START_HOUR = 23  # from 11pm...
NIGHT_END_HOUR = 6  # ...to 6am, the pet gets sleepy: fewer chatter lines, more idling, slower wiggle.

# (month, day) -> flavor for that one day of the year. Takes priority over
# the sleepy/encouragement pools, and gives the pet a themed color for the
# session.
SPECIAL_DATES = {
    (1, 1): {"sayings": ["happy new year!", "*confetti everywhere*", "new year, new bugs to fix"], "color256": 226, "color8": COLOR_YELLOW},
    (2, 14): {"sayings": ["happy valentine's!", "*heart eyes*", "you're my favorite human"], "color256": 201, "color8": COLOR_MAGENTA},
    (10, 31): {"sayings": ["*spooky noises*", "boo!", "trick or treat?"], "color256": 208, "color8": COLOR_RED},
}

# --- rare easter eggs ---
GOLDEN_CHANCE = 0.02  # ~1 in 50 launches: a shiny, differently-colored pet for the session.
GOLDEN_COLOR256 = 214
GOLDEN_COLOR8 = COLOR_GREEN
GOLDEN_SAYING = "*sparkles* ...lucky find!"

STAR_CHANCE_PER_TICK = 1 / 1500  # roughly once every few minutes of continuous running
STAR_SPEED = 2.5
STAR_ROW_FRACTION = 0.15  # a shooting star crosses near the top of the screen


class Pet:
    def __init__(self, kind, max_x, max_y, speed, bubble_pairs):
        self.kind = kind
        self.spec = PETS[kind]
        self.large = self.spec.get("size") == "large"
        art = self.spec["art"]
        self.width = max(len(line) for line in art)
        self.height = len(art)
        self.max_x = max_x
        self.max_y = max_y
        self.speed = speed
        self.bubble_pairs = bubble_pairs
        if self.large:
            # large pets don't wander — they sit centered in their own window.
            self.x = float(max(0, (max_x - self.width) // 2))
            self.y = max(0, (max_y - self.height) // 2)
        else:
            self.x = float(random.randint(0, max(1, max_x - self.width - 1)))
            self.y = max(0, max_y - self.height - 1)
        self.direction = random.choice([-1, 1])
        self.state = "walk"
        self.state_timer = 0
        self.bubble = None
        self.bubble_timer = 0
        self.bubble_pair = 1
        self.sparkle = False
        self.tick = 0
        self._cmd_mtime = None
        self._exit_mtime = None
        self.last_cmd = ""

        self.golden = random.random() < GOLDEN_CHANCE
        self.special_info = self._special_date_info()
        self.festive = self.special_info is not None
        self.star_x = None
        self.star_y = None
        if self.golden:
            self._set_bubble(GOLDEN_SAYING, 20)
        elif self.festive:
            self._set_bubble(random.choice(self.special_info["sayings"]), 20)

    def _is_night(self):
        hour = time.localtime().tm_hour
        if NIGHT_START_HOUR > NIGHT_END_HOUR:
            return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR
        return NIGHT_START_HOUR <= hour < NIGHT_END_HOUR

    def _special_date_info(self):
        now = time.localtime()
        return SPECIAL_DATES.get((now.tm_mon, now.tm_mday))

    def _chatter_pool(self):
        pool = list(self.spec["sayings"])
        if self.festive:
            pool += self.special_info["sayings"]
        elif self._is_night():
            pool += SLEEPY_SAYINGS
        else:
            pool += ENCOURAGEMENTS
        return pool

    def _set_bubble(self, text, timer):
        self.bubble = text
        self.bubble_timer = timer
        self.bubble_pair = random.choice(self.bubble_pairs) if self.bubble_pairs else 1

    def check_command(self):
        try:
            mtime = os.path.getmtime(CMD_FILE)
        except OSError:
            return
        if mtime == self._cmd_mtime:
            return
        self._cmd_mtime = mtime
        try:
            with open(CMD_FILE) as f:
                cmd = f.read().strip()
        except OSError:
            return
        if not cmd:
            return
        self.last_cmd = cmd
        for pattern, options in COMMAND_REACTIONS:
            if pattern.search(cmd):
                self._set_bubble(random.choice(options), 16)
                self.state = "sit"
                self.state_timer = 16
                return

    def check_exit(self):
        try:
            mtime = os.path.getmtime(EXIT_FILE)
        except OSError:
            return
        if mtime == self._exit_mtime:
            return
        self._exit_mtime = mtime
        try:
            with open(EXIT_FILE) as f:
                code = int(f.read().strip())
        except (OSError, ValueError):
            return
        if code == 0:
            return

        first_word = self.last_cmd.split()[0] if self.last_cmd else ""
        if code == 127:
            suggestion = _suggest_command(first_word)
            if suggestion:
                text = random.choice(SUGGESTION_TEMPLATES).format(suggestion)
            else:
                text = random.choice(TYPO_FALLBACKS)
        else:
            text = random.choice(ROAST_LINES)

        self._set_bubble(text, 18)
        self.state = "sit"
        self.state_timer = 18

    def resize(self, max_x, max_y):
        self.max_x = max_x
        self.max_y = max_y
        if self.large:
            self.x = float(max(0, (max_x - self.width) // 2))
            self.y = max(0, (max_y - self.height) // 2)
        else:
            self.y = max(0, max_y - self.height - 1)
            self.x = min(self.x, max(0, max_x - self.width - 1))

    def feed(self):
        self._set_bubble(random.choice(self.spec["fed"]), 14)
        self.sparkle = True
        self.state = "sit"
        self.state_timer = 14

    def _update_star(self):
        if self.star_x is None:
            if random.random() < STAR_CHANCE_PER_TICK:
                self.star_x = 0.0
                self.star_y = max(0, int(self.max_y * STAR_ROW_FRACTION))
            return
        self.star_x += STAR_SPEED
        if self.star_x >= self.max_x:
            self.star_x = None
            self.star_y = None

    def update(self):
        self.tick += 1
        self.check_command()
        self.check_exit()
        self._update_star()

        if self.bubble_timer > 0:
            self.bubble_timer -= 1
            if self.bubble_timer == 0:
                self.bubble = None
                self.sparkle = False

        if self.large:
            # stays put and gently wiggles in place; still reacts to
            # commands/feeding via speech bubble, just never walks.
            if self.bubble is None and random.random() < 0.015:
                self._set_bubble(random.choice(self._chatter_pool()), 10)
            return

        if self.state == "sit":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "walk"
                self.direction = random.choice([-1, 1])
            return

        # occasionally stop to sit/idle — sleepier (idles more) late at night
        sit_chance = 0.03 if self._is_night() else 0.01
        if random.random() < sit_chance:
            self.state = "sit"
            self.state_timer = random.randint(15, 40)
            return

        # occasionally say something (species chatter, encouragement, or a mood-appropriate line)
        if self.bubble is None and random.random() < 0.015:
            self._set_bubble(random.choice(self._chatter_pool()), 10)

        self.x += self.direction * self.speed
        if self.x <= 0:
            self.x = 0
            self.direction = 1
        max_x_pos = max(0, self.max_x - self.width - 1)
        if self.x >= max_x_pos:
            self.x = max_x_pos
            self.direction = -1

    def sprite_lines(self):
        return self.spec["art"]

    def y_offset(self):
        if self.large:
            # slow, gentle bob — independent of walk/sit state, since large
            # pets never walk. Slower still late at night (drowsy).
            cadence = 20 if self._is_night() else 10
            return -1 if (self.tick // cadence) % 2 == 0 else 0
        if self.state == "walk" and (self.tick // 6) % 2 == 0:
            return -1
        return 0


def draw(stdscr, pet, pet_pair):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    lines = pet.sprite_lines()
    x = int(pet.x)
    y = int(pet.y) + pet.y_offset()

    for i, line in enumerate(lines):
        row = y + i
        if 0 <= row < max_y - 1 and x < max_x:
            try:
                stdscr.addstr(row, x, line[: max_x - x], curses.color_pair(pet_pair) | curses.A_BOLD)
            except curses.error:
                pass

    if pet.star_x is not None:
        sx, sy = int(pet.star_x), pet.star_y
        if 0 <= sy < max_y - 1 and 0 <= sx < max_x:
            try:
                stdscr.addstr(sy, sx, "*", curses.A_BOLD)
            except curses.error:
                pass

    if pet.sparkle or pet.golden or pet.festive:
        mid_row = y + max(0, pet.height // 2)
        for sx, ch in ((x - 2, "*"), (x + pet.width + 1, "*")):
            if 0 <= mid_row < max_y - 1 and 0 <= sx < max_x:
                try:
                    stdscr.addstr(mid_row, sx, ch, curses.color_pair(pet.bubble_pair) | curses.A_BOLD)
                except curses.error:
                    pass

    if pet.bubble:
        text = f" {pet.bubble} "
        bx = min(max(0, x), max(0, max_x - len(text) - 1))
        by = max(0, y - 1)
        try:
            stdscr.addstr(by, bx, text, curses.color_pair(pet.bubble_pair) | curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass

    footer = " q: quit   f: feed "
    try:
        stdscr.addstr(max_y - 1, 0, footer[: max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    stdscr.refresh()


def main(stdscr, kind, speed):
    curses.curs_set(0)
    curses.flushinp()  # discard stray bytes buffered by shell/prompt startup so they don't misread as keypresses
    stdscr.nodelay(True)
    stdscr.timeout(max(20, int(120 / speed)))

    max_y, max_x = stdscr.getmaxyx()
    # Constructed before color setup below so pet.golden/pet.special_info
    # (rolled/looked-up in __init__) can pick the pet's color for this run.
    pet = Pet(kind, max_x, max_y, speed=1.0, bubble_pairs=[])

    pet_pair = 1
    bubble_pairs = []
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        use_256 = curses.COLORS >= 256

        if pet.golden:
            pet_color = GOLDEN_COLOR256 if use_256 else GOLDEN_COLOR8
        elif pet.special_info:
            pet_color = pet.special_info["color256"] if use_256 else pet.special_info["color8"]
        else:
            pet_color = PETS[kind]["color256"] if use_256 else PETS[kind]["color8"]
        curses.init_pair(pet_pair, pet_color, -1)

        palette = BUBBLE_PALETTE_256 if use_256 else BUBBLE_PALETTE_8
        for i, color in enumerate(palette, start=2):
            curses.init_pair(i, color, -1)
            bubble_pairs.append(i)

        pet.bubble_pairs = bubble_pairs
        if pet.bubble and bubble_pairs:
            # golden/festive pets set an intro bubble in __init__, before
            # bubble_pairs existed — re-roll its color now that they do.
            pet.bubble_pair = random.choice(bubble_pairs)

    while True:
        ch = stdscr.getch()
        if ch in (ord("q"), ord("Q")):
            break
        elif ch == curses.KEY_RESIZE:
            max_y, max_x = stdscr.getmaxyx()
            pet.resize(max_x, max_y)
        elif ch in (ord("f"), ord("F")):
            pet.feed()

        pet.update()
        draw(stdscr, pet, pet_pair)


def parse_args():
    p = argparse.ArgumentParser(description="A little pet that wanders around your terminal.")
    p.add_argument("--pet", choices=[*PETS.keys(), "random"], default="random")
    p.add_argument("--speed", type=float, default=1.0, help="higher = faster (default 1.0)")
    p.add_argument(
        "--dock",
        action="store_true",
        help="launch docked in a small pane/window instead of taking over this one",
    )
    p.add_argument(
        "--dock-height",
        type=float,
        default=15.0,
        metavar="PERCENT",
        help="iTerm2 only: dock pane height as %% of window height (default 15)",
    )
    return p.parse_args()


def run():
    args = parse_args()

    kind = args.pet
    if kind == "random":
        kind = random.choice(list(PETS.keys()))

    if args.dock:
        from . import dock

        dock.launch(kind, args.speed, args.dock_height)
        return

    if curses is None:
        print("terminal-pet needs Python's `curses` module, which isn't available here.")
        print("On Windows, install it with: pip install windows-curses")
        sys.exit(1)

    locale.setlocale(locale.LC_ALL, "")
    try:
        curses.wrapper(main, kind, args.speed)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
