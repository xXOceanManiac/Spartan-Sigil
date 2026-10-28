# Spartan Sigil
![Alt Text](Spartan-Sigil/assets/thumbnail.png)

A sculpted silver Spartan helmet above your first Bash prompt. Monochrome
half-block shading preserves the master artwork’s recessed eyes, brushed metal,
and beveled edges. The medallion gently rocks in perspective while a bright
reflection sweeps across the silver. Large Roman-style `SPARTAN` capitals overlap the lower shield, with smooth
serifs, restrained silver shading, and a soft shadow. It emerges letter by letter
over the first 1.2 seconds, then shimmers with the helmet.
Submitting your first command fades both away and reclaims the reserved rows.

## Install

```bash
cd ~/Desktop/Spartan-Sigil
./install.sh
```

Open a new terminal to see it. Re-running the installer upgrades the managed
Bash block. The first install preserves `~/.bashrc.spartan-sigil.bak`.
The renderer uses Python 3’s standard library and needs no image libraries at runtime.
Keep the project directory in place: `~/.local/bin/spartan-sigil` links to it.

## Use

- `spartan-sigil --preview` — animate until interrupted.
- `spartan-sigil --still` — print the shaded helmet without animation.
- `spartan-sigil --vanish` — play the fade and remove its reserved rows.
- Set `SPARTAN_SIGIL=off` before launching Bash to suppress the startup artwork.
- `./uninstall.sh` — remove the managed Bash block and executable symlink.

Designed for Konsole, Bash, and a dark UTF-8 terminal with 24-bit color.
Startup skips noninteractive shells, SSH, `TERM=dumb`, and terminals smaller
than 66 columns × 35 rows. The helmet and animated wordmark occupy 64 columns × 32 rows with
one row of breathing room before the prompt.

## Files

- `spartan_sigil.py` — dependency-free grayscale renderer and animation.
- `assets/spartan-sigil-master.png` — original silver medallion artwork.
- `assets/helmet-luminance.json` — precomputed 64 × 64 grayscale terminal samples.
- `assets/wordmark.json` — antialiased Roman capitals; no runtime font dependency.
- `tools/build_wordmark.py` — optional lettering rebuild with Pillow and Nimbus Roman.
- `install.sh` / `uninstall.sh` — user-local Bash integration.
