#!/usr/bin/env python3
"""A compact, single-use Spartan helmet animation for ANSI terminals."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import time

RESET = "\x1b[0m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
HOME = "\x1b[H"
SAVE = "\x1b7"
RESTORE = "\x1b8"

# Marker characters are translated into metal surfaces.  Spaces remain the
# terminal's native background, making the helmet feel at home in any theme.
FRAMES = [
    [
        "        ╭───────╮        ",
        "     ╭──╯cccccgg╰──╮     ",
        "    ╱  dcccccgggaaa  ╲    ",
        "   ╱  dc╭───────╮aa  ╲   ",
        "  │  dc│  ╲   ╱  │aa  │  ",
        "  │  dc│   ╲_╱   │aa  │  ",
        "  │  dc╲╲       ╱╱aa  │  ",
        "  │   dc╲╲_____/╱aa   │  ",
        "   ╲    dc╲___╱aa    ╱   ",
        "    ╲gggg╲_V_/aaaa╱    ",
        "       ╲___V___╱       ",
    ],
    [
        "       ╭──────╮         ",
        "    ╭──╯ccccgg╰─╮       ",
        "   ╱ dccccgggaaa ╲      ",
        "  │ dc╭─────╮aaa │      ",
        "  │ dc│ ╲ ╱ │aaa │      ",
        "  │ dc│  V  │aaa │      ",
        "  │ dc╲     ╱aaa │      ",
        "  │  dc╲___╱aaa  │      ",
        "   ╲  dc╲_╱aa   ╱       ",
        "    ╲ggg╲V╱aa ╱        ",
        "      ╲__V__╱          ",
    ],
    [
        "       ╭────╮           ",
        "     ╭─╯ccgg╰╮          ",
        "    ╱ dcggaaa╲          ",
        "    │d╭───╮aa│          ",
        "    │d│╲ ╱│aa│          ",
        "    │d│ V │aa│          ",
        "    │d╲   ╱aa│          ",
        "    │ dc╲_╱aa│          ",
        "     ╲ dcVaa╱           ",
        "      ╲gV a╱            ",
        "        ╲V╱             ",
    ],
    [
        "          ╭─╮           ",
        "          │g│           ",
        "          │g│           ",
        "          │a│           ",
        "          │a│           ",
        "          │a│           ",
        "          │c│           ",
        "          │c│           ",
        "          │d│           ",
        "          │d│           ",
        "          ╲V╱           ",
    ],
    [
        "           ╭────╮       ",
        "          ╭╯ggcc╰─╮     ",
        "          ╱aaaggcd ╲    ",
        "          │aa╭───╮d│    ",
        "          │aa│╲ ╱│d│    ",
        "          │aa│ V │d│    ",
        "          │aa╲   ╱d│    ",
        "          │aa╲_╱cd │    ",
        "           ╲aaVcd ╱     ",
        "            ╲a Vg╱      ",
        "             ╲V╱        ",
    ],
    [
        "         ╭──────╮       ",
        "       ╭─╯ggcccc╰──╮    ",
        "      ╱ aaagggccccd ╲   ",
        "      │ aaa╭─────╮cd │  ",
        "      │ aaa│ ╲ ╱ │cd │  ",
        "      │ aaa│  V  │cd │  ",
        "      │ aaa╲     ╱cd │  ",
        "      │  aaa╲___╱cd  │  ",
        "       ╲   aa╲_╱cd  ╱   ",
        "        ╲ aa╲V╱ggg╱    ",
        "          ╲__V__╱      ",
    ],
]

COLORS = {
    "d": "\x1b[38;2;82;48;29m",   # dark bronze
    "c": "\x1b[38;2;159;88;43m",  # copper
    "a": "\x1b[38;2;210;139;55m", # amber
    "g": "\x1b[38;2;245;211;132m",# pale gold
}
OUTLINE = "\x1b[38;2;190;116;53m"
ROWS = len(FRAMES[0])


def paint(line: str) -> str:
    result: list[str] = []
    color = RESET
    for char in line:
        target = COLORS.get(char, OUTLINE if char != " " else RESET)
        glyph = "▓" if char in COLORS else char
        if target != color:
            result.append(target)
            color = target
        result.append(glyph)
    return "".join(result) + RESET


def frame(index: int) -> str:
    # Clear every owned row before repainting it; no whole-screen clears.
    lines = FRAMES[index % len(FRAMES)]
    return "\r\n".join("\x1b[2K" + paint(line) for line in lines)


def draw(index: int) -> None:
    sys.stdout.write(SAVE + HIDE + HOME + frame(index) + SHOW + RESTORE)
    sys.stdout.flush()


def prepare(rows: int) -> None:
    # The installer asks for the fixed eleven-row design.  This guard keeps the
    # CLI sane if it is used directly with a different value.
    if rows != ROWS:
        raise ValueError(f"Spartan Sigil requires {ROWS} rows")
    sys.stdout.write("\n" * ROWS)
    sys.stdout.flush()
    draw(0)


def clear_and_collapse() -> None:
    # At PS0 the submitted line has just advanced to the row below the sigil.
    # Deleting the owned rows pulls that line up with no blank startup banner.
    sys.stdout.write(HIDE + HOME)
    for _ in range(ROWS):
        sys.stdout.write("\x1b[1M")
    sys.stdout.write(RESET + SHOW + HOME)
    sys.stdout.flush()


def vanish() -> None:
    # A short, deliberate compression ending in a gold edge flash.
    for index, delay in ((2, 0.065), (3, 0.065), (3, 0.045)):
        sys.stdout.write(SAVE + HIDE + HOME + frame(index) + SHOW + RESTORE)
        sys.stdout.flush()
        time.sleep(delay)
    clear_and_collapse()


def render() -> int:
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    index = 0
    deadline = time.monotonic()
    try:
        while not stopping:
            draw(index)
            index = (index + 1) % len(FRAMES)
            deadline += 0.10  # 10 fps: calm enough to type under.
            time.sleep(max(0.0, deadline - time.monotonic()))
    finally:
        vanish()
    return 0


def terminal_is_large_enough() -> bool:
    size = shutil.get_terminal_size(fallback=(0, 0))
    return size.columns >= 42 and size.lines >= 16


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spartan-sigil", description="A single-use rotating Spartan terminal sigil."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="loop until interrupted")
    group.add_argument("--vanish", action="store_true", help="play the vanish once")
    group.add_argument("--prepare", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--render", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, default=ROWS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not sys.stdout.isatty() or not terminal_is_large_enough():
        return 2
    if args.vanish:
        vanish()
    elif args.prepare:
        prepare(args.rows)
    else:  # preview and the shell's private --render mode both loop.
        prepare(args.rows) if args.preview else None
        return render()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
