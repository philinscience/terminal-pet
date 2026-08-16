# terminal-pet

A tiny ASCII duck, mouse, bunny, or raccoon that lives in your terminal. It's
actually useful: type `gti status` and it pops up a speech bubble —
*"did you mean 'git'?"*

It also comments on what you're running, roasts you (gently) when something
fails for real, and throws in random encouragement.

## Quick start

```
pip install -e .
terminal-pet-install-hook   # teaches it to watch your commands (one-time)
terminal-pet --dock         # docks it, keep working normally
```

Open a new terminal tab (or `source ~/.zshrc` / `source ~/.bashrc`) and type a typo to see it in action.

`--pet duck`, `--pet mouse`, `--pet bunny`, or `--pet raccoon` picks the species.
`q` quits, `f` feeds it.

Pets come in two sizes:
- **Small** (duck, mouse): wander back and forth, docked in a small pane
  (iTerm2) or small window (Terminal.app).
- **Large** (bunny, raccoon): sits in place with a gentle up/down wiggle,
  always in its own separate square window — on both iTerm2 and Terminal.app,
  sized to fit that pet's art.

## Platform support

- **macOS**: fully supported, including `--dock` (a separate pane/window)
  in iTerm2 and Terminal.app.
- **Linux**: the pet itself works fine (same `curses` machinery as macOS),
  and the command-reaction hook supports both zsh and bash. `--dock` isn't
  implemented — there's no single scripting story across Linux terminal
  emulators the way AppleScript covers iTerm2/Terminal.app, so `--dock` just
  falls back to running the pet directly in your current window instead of
  erroring.
- **Windows**: not supported. Stock Windows Python doesn't ship `curses` at
  all (you'd need `pip install windows-curses`, and even then rendering and
  the shell hook would need real testing this project hasn't had) — running
  `terminal-pet` there prints a clear message rather than crashing, but
  nothing further is implemented.

## Notes

- For precise pane sizing in iTerm2 (`--dock-height PERCENT`, default 15%,
  small pets only), install `pip install -e ".[iterm]"` and enable Settings >
  General > Magic > "Enable Python API". Without it, `--dock` still works,
  just as a plain 50/50 split.
- The hook stores your last command + exit code as plain text in
  `~/.terminal_pet/` so the pet can read them — worth knowing if a command
  ever contains a secret inline.
