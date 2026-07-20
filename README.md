# Spartan Sigil

Spartan Sigil places a compact rotating bronze Spartan helmet above the first
interactive Bash prompt in Konsole.  When that first command is submitted, it
compresses into a gold edge flash, removes its reserved rows, and never returns
for that shell session.

## Install

```bash
cd ~/Desktop/Spartan-Sigil
./install.sh
```

This creates `~/.local/bin/spartan-sigil` as a symbolic link to the project
renderer and adds one managed `Spartan Sigil` block to `~/.bashrc`. The first
install preserves `~/.bashrc.spartan-sigil.bak`.

Remove it with `./uninstall.sh`; it removes only that block and the symlink.

## Use

`spartan-sigil --preview` runs the animation until interrupted.  
`spartan-sigil --vanish` plays the collapse once.  
Set `SPARTAN_SIGIL=off` before launching Bash to suppress it for one shell.

It is intended for Ubuntu 24.04, KDE Plasma 5.27, X11, Konsole, Bash, and a
UTF-8 24-bit color terminal. It skips noninteractive, SSH, `TERM=dumb`, and
small terminal sessions.

## Files

- `spartan_sigil.py` — ANSI renderer and vanish sequence
- `install.sh` — idempotent user-local install and Bash integration
- `uninstall.sh` — focused removal
