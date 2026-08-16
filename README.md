# terminal-pet

A tiny ASCII duck, mouse, bunny, or raccoon that lives in your terminal. It's
actually useful: type `gti status` and it pops up a speech bubble —
*"did you mean 'git'?"*

It also comments on what you're running, roasts you (gently) when something
fails for real, and throws in random encouragement.

![demo](assets/demo.gif)

## Quick start

```
pip install -e .
terminal-pet setup          # one-time guided setup + hook install
terminal-pet                # launches using your saved defaults
```

Open a new terminal tab (or `source ~/.zshrc` / `source ~/.bashrc`) and type a typo to see it in action.

`--pet duck`, `--pet mouse`, `--pet bunny`, or `--pet raccoon` picks the species.
`q` quits, `f` feeds it.

Useful commands:
- `terminal-pet check` verifies hook install, terminal support, and config/state access.
- `terminal-pet setup --yes --pet raccoon --chattiness chaos` skips prompts and saves defaults directly.
- `terminal-pet --no-roasts --chattiness quiet` lets you override your saved personality just for one run.

Pets come in two sizes:
- **Small** (duck, mouse): wander back and forth, docked in a small pane
  (iTerm2, Terminal.app, or tmux) or small window (Terminal.app).
- **Large** (bunny, raccoon): sits in place with a gentle up/down wiggle,
  always in its own separate window — a square window sized to fit that
  pet's art on iTerm2/Terminal.app, or a new tmux window.

## Platform support

- **macOS**: fully supported, including `--dock` (a separate pane/window)
  in iTerm2 and Terminal.app.
- **Linux**: the pet itself works fine (same `curses` machinery as macOS),
  and the command-reaction hook supports both zsh and bash. `--dock` works
  if you're inside a tmux session (`tmux split-window` for small pets, a new
  tmux window for large ones) — this is also what makes docking work when
  you SSH into a Linux box from a Mac, since the AppleScript/iTerm2-API
  tricks can only ever control the terminal app on your local machine, not
  a remote process. Outside tmux, `--dock` falls back to running the pet
  directly in your current window instead of erroring.
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
- Personality settings live in `~/.terminal_pet/config.json`. You can tune
  `quiet`, `normal`, or `chaos`, plus toggle encouragements, roasts, typo
  help, seasonal reactions, and sparkle effects.
- Pets now also get sleepy from a quiet session, not just the late hour. Run
  a command or feed them and they perk back up.
- The hook stores your last command + exit code as plain text in
  `~/.terminal_pet/` so the pet can read them — worth knowing if a command
  ever contains a secret inline.
