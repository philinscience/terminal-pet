"""Installs the shell hook that records the last command you ran, so the pet
can react to it.

Writes ~/.terminal_pet/hook.{zsh,bash} and sources them from ~/.zshrc and
~/.bashrc respectively (idempotent — safe to run more than once, e.g. after
a reinstall or upgrade). Both are installed unconditionally so it works
whichever shell you end up using — harmless if you only ever use one.
"""

import os

HOOK_DIR = os.path.expanduser("~/.terminal_pet")

ZSH_HOOK_PATH = os.path.join(HOOK_DIR, "hook.zsh")
ZSHRC = os.path.expanduser("~/.zshrc")
ZSH_HOOK_CONTENT = """# terminal pet: records the last command you ran (and whether it succeeded)
# so the pet can react to it.
typeset -g _TERMINAL_PET_DIR="$HOME/.terminal_pet"
mkdir -p "$_TERMINAL_PET_DIR" 2>/dev/null

_terminal_pet_report() {
  print -r -- "$1" > "$_TERMINAL_PET_DIR/lastcmd" 2>/dev/null
}

_terminal_pet_precmd() {
  local _tp_exit=$?
  print -r -- "$_tp_exit" > "$_TERMINAL_PET_DIR/lastexit" 2>/dev/null
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec _terminal_pet_report
add-zsh-hook precmd _terminal_pet_precmd
"""

BASH_HOOK_PATH = os.path.join(HOOK_DIR, "hook.bash")
BASHRC = os.path.expanduser("~/.bashrc")
BASH_HOOK_CONTENT = """# terminal pet: records the last command you ran (and whether it succeeded)
# so the pet can react to it.
_TERMINAL_PET_DIR="$HOME/.terminal_pet"
mkdir -p "$_TERMINAL_PET_DIR" 2>/dev/null

_terminal_pet_preexec() {
  case "$BASH_COMMAND" in
    _terminal_pet_precmd*) return ;;
  esac
  printf '%s' "$BASH_COMMAND" > "$_TERMINAL_PET_DIR/lastcmd" 2>/dev/null
}
trap '_terminal_pet_preexec' DEBUG

_terminal_pet_precmd() {
  local _tp_exit=$?
  printf '%s' "$_tp_exit" > "$_TERMINAL_PET_DIR/lastexit" 2>/dev/null
}
case ";$PROMPT_COMMAND;" in
  *";_terminal_pet_precmd;"*) ;;
  *) PROMPT_COMMAND="_terminal_pet_precmd${PROMPT_COMMAND:+; $PROMPT_COMMAND}" ;;
esac
"""

MARKER = "# terminal pet: react to commands you run"


def _install(hook_path, hook_content, rc_path, rc_label):
    with open(hook_path, "w") as f:
        f.write(hook_content)
    print(f"Wrote hook script to {hook_path}")

    source_line = f"source '{hook_path}'"
    existing = ""
    if os.path.exists(rc_path):
        with open(rc_path) as f:
            existing = f.read()

    if source_line in existing:
        print(f"Already sourced from {rc_label} — nothing else to do.")
        return

    with open(rc_path, "a") as f:
        f.write(f"\n{MARKER}\n{source_line}\n")
    print(f"Added hook to {rc_label}.")


def run():
    os.makedirs(HOOK_DIR, exist_ok=True)
    _install(ZSH_HOOK_PATH, ZSH_HOOK_CONTENT, ZSHRC, "~/.zshrc")
    _install(BASH_HOOK_PATH, BASH_HOOK_CONTENT, BASHRC, "~/.bashrc")
    print("Open a new terminal session (or `source ~/.zshrc` / `source ~/.bashrc`) to activate it.")


def _uninstall_rc(hook_path, rc_path, rc_label):
    if not os.path.exists(rc_path):
        return

    source_line = f"source '{hook_path}'"
    with open(rc_path) as f:
        lines = f.readlines()

    out = []
    removed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == MARKER:
            removed = True
            i += 1
            if i < len(lines) and lines[i].strip() == source_line:
                i += 1
            # drop the blank line _install() adds right before the marker
            if out and out[-1].strip() == "":
                out.pop()
            continue
        out.append(line)
        i += 1

    if not removed:
        print(f"No hook entry found in {rc_label} — nothing to remove there.")
        return

    with open(rc_path, "w") as f:
        f.writelines(out)
    print(f"Removed hook from {rc_label}.")


def uninstall():
    _uninstall_rc(ZSH_HOOK_PATH, ZSHRC, "~/.zshrc")
    _uninstall_rc(BASH_HOOK_PATH, BASHRC, "~/.bashrc")

    for path in (ZSH_HOOK_PATH, BASH_HOOK_PATH):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed {path}")

    for fname in ("lastcmd", "lastexit"):
        fpath = os.path.join(HOOK_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    if os.path.isdir(HOOK_DIR) and not os.listdir(HOOK_DIR):
        os.rmdir(HOOK_DIR)

    print("Open a new terminal session (or restart your shell) for the change to fully take effect.")


if __name__ == "__main__":
    run()
