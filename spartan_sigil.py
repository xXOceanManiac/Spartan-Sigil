#!/usr/bin/env python3
"""A single-use rotating Spartan helmet medallion for ANSI terminals."""

from __future__ import annotations

import argparse
import math
import shutil
import signal
import sys
import time

RESET = "\x1b[0m"
WHITE = "\x1b[38;2;248;248;248m"
FLASH = "\x1b[38;2;255;255;255m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
HOME = "\x1b[H"
SAVE = "\x1b7"
RESTORE = "\x1b8"

# Canonical front-facing artwork supplied by the user.
HELMET = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⢀⣤⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⡀⠀⠀⠀⠀",
    "⠀⠀⠀⢀⣾⣿⣿⣿⣿⠟⠋⠉⠀⢤⡄⠀⠀⣄⠉⠛⠿⣿⣿⣿⣿⣿⡦⠀⠀⠀",
    "⠀⠀⠀⣼⣿⣿⣿⠟⠁⠀⠛⣷⡀⠸⠧⠀⠸⠏⠀⠀⠀⠈⠻⡿⠟⠋⠀⠀⠀⠀",
    "⠀⠀⠀⣿⣿⣿⠃⠀⠀⠀⠀⠈⣁⣤⣴⣶⣶⣤⣤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⢿⣿⡇⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⠿⠋⣀⣴⡀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠸⣿⣧⠀⠀⠀⠀⣸⣿⣿⠿⠿⠟⠛⣉⣠⣶⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⢻⣿⣆⠀⠀⠀⢿⣿⡇⢰⣶⣾⣿⡟⠻⢿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠻⣿⣦⠀⠀⠸⣿⡇⠸⣿⣿⣿⡀⠀⠀⠀⠉⠉⢻⡇⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠘⣿⡇⠀⠀⢻⣷⡀⢻⣿⣿⣿⣶⣤⣄⡀⠀⠸⡇⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⢀⡿⠁⠀⠀⢸⣿⠗⠀⠉⠻⣿⣿⣿⣿⣿⣇⠀⠇⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⣠⡞⠁⠀⠀⢀⣾⣿⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⢀⠴⠋⠀⠀⠀⠰⠛⠋⠁⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⠀⠀⠀⠀⠀⠀⠀",
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀",
]

CANVAS_WIDTH = 79
CANVAS_HEIGHT = 33
ROWS = CANVAS_HEIGHT

# Front half, exact edge, then the mirrored backside half.
ROTATION = (
    (1.00, False), (0.82, False), (0.62, False), (0.36, False), (0.12, False),
    (0.36, True), (0.62, True), (0.82, True), (1.00, True),
    (0.82, True), (0.62, True), (0.36, True), (0.12, True), (0.36, False),
)


def normalize(lines: list[str]) -> list[str]:
    width = max(len(line) for line in lines)
    return [line.ljust(width) for line in lines]


HELMET = normalize(HELMET)


# ---------------------------------------------------------------------------
# Braille drawing helpers
# ---------------------------------------------------------------------------

DOT_TO_BIT = {
    (0, 0): 0,  # dot 1
    (0, 1): 1,  # dot 2
    (0, 2): 2,  # dot 3
    (1, 0): 3,  # dot 4
    (1, 1): 4,  # dot 5
    (1, 2): 5,  # dot 6
    (0, 3): 6,  # dot 7
    (1, 3): 7,  # dot 8
}


def blank_pixels() -> list[list[bool]]:
    return [
        [False for _ in range(CANVAS_WIDTH * 2)]
        for _ in range(CANVAS_HEIGHT * 4)
    ]


def set_pixel(pixels: list[list[bool]], x: int, y: int) -> None:
    if 0 <= y < len(pixels) and 0 <= x < len(pixels[0]):
        pixels[y][x] = True


def draw_line(
    pixels: list[list[bool]],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    thickness: int = 1,
) -> None:
    steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) * 2))
    for i in range(steps + 1):
        t = i / steps
        x = round(x0 + (x1 - x0) * t)
        y = round(y0 + (y1 - y0) * t)
        for oy in range(-thickness + 1, thickness):
            for ox in range(-thickness + 1, thickness):
                set_pixel(pixels, x + ox, y + oy)


def ellipse_point(cx: float, cy: float, rx: float, ry: float, angle: float) -> tuple[float, float]:
    return cx + rx * math.cos(angle), cy + ry * math.sin(angle)


def draw_ellipse(
    pixels: list[list[bool]],
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    thickness: int = 1,
) -> None:
    samples = 900
    previous = ellipse_point(cx, cy, rx, ry, 0.0)
    for i in range(1, samples + 1):
        angle = math.tau * i / samples
        current = ellipse_point(cx, cy, rx, ry, angle)
        draw_line(pixels, *previous, *current, thickness=thickness)
        previous = current


def draw_meander_ring(pixels: list[list[bool]]) -> None:
    """Draw a smooth double-ring with a continuous Greek-key/meander path."""
    px_w = CANVAS_WIDTH * 2
    px_h = CANVAS_HEIGHT * 4
    cx = (px_w - 1) / 2
    cy = (px_h - 1) / 2

    outer_rx, outer_ry = 78.0, 62.0
    inner_rx, inner_ry = 57.0, 45.0

    draw_ellipse(pixels, cx, cy, outer_rx, outer_ry, thickness=1)
    draw_ellipse(pixels, cx, cy, outer_rx - 3.0, outer_ry - 3.0, thickness=1)
    draw_ellipse(pixels, cx, cy, inner_rx, inner_ry, thickness=1)
    draw_ellipse(pixels, cx, cy, inner_rx + 3.0, inner_ry + 3.0, thickness=1)

    # A polar square-wave path creates the Greek-key band. Each motif has:
    # outer tangent -> inward radial -> inner tangent -> outward radial.
    motifs = 12
    segment = math.tau / motifs
    r_outer_x, r_outer_y = 73.0, 57.0
    r_inner_x, r_inner_y = 59.0, 46.0

    for motif in range(motifs):
        base = motif * segment
        a0 = base + segment * 0.06
        a1 = base + segment * 0.36
        a2 = base + segment * 0.58
        a3 = base + segment * 0.88

        p0 = ellipse_point(cx, cy, r_outer_x, r_outer_y, a0)
        p1 = ellipse_point(cx, cy, r_outer_x, r_outer_y, a1)
        p2 = ellipse_point(cx, cy, r_inner_x, r_inner_y, a1)
        p3 = ellipse_point(cx, cy, r_inner_x, r_inner_y, a2)
        p4 = ellipse_point(cx, cy, r_outer_x, r_outer_y, a2)
        p5 = ellipse_point(cx, cy, r_outer_x, r_outer_y, a3)

        draw_line(pixels, *p0, *p1, thickness=1)
        draw_line(pixels, *p1, *p2, thickness=1)
        draw_line(pixels, *p2, *p3, thickness=1)
        draw_line(pixels, *p3, *p4, thickness=1)
        draw_line(pixels, *p4, *p5, thickness=1)


def pixels_to_braille(pixels: list[list[bool]]) -> list[list[str]]:
    grid = [[" " for _ in range(CANVAS_WIDTH)] for _ in range(CANVAS_HEIGHT)]
    for cell_y in range(CANVAS_HEIGHT):
        for cell_x in range(CANVAS_WIDTH):
            bits = 0
            for dot_y in range(4):
                for dot_x in range(2):
                    if pixels[cell_y * 4 + dot_y][cell_x * 2 + dot_x]:
                        bits |= 1 << DOT_TO_BIT[(dot_x, dot_y)]
            if bits:
                grid[cell_y][cell_x] = chr(0x2800 + bits)
    return grid


_BORDER_PIXELS = blank_pixels()
draw_meander_ring(_BORDER_PIXELS)
BORDER = pixels_to_braille(_BORDER_PIXELS)


# ---------------------------------------------------------------------------
# Helmet transforms
# ---------------------------------------------------------------------------

BRAILLE_MIRROR_BITS = {
    0: 3,
    1: 4,
    2: 5,
    3: 0,
    4: 1,
    5: 2,
    6: 7,
    7: 6,
}

MIRROR_GLYPHS = str.maketrans({
    "╱": "╲",
    "╲": "╱",
    "(": ")",
    ")": "(",
    "[": "]",
    "]": "[",
    "{": "}",
    "}": "{",
    "<": ">",
    ">": "<",
    "⟨": "⟩",
    "⟩": "⟨",
})


def mirror_braille_char(char: str) -> str:
    code = ord(char)
    if not (0x2800 <= code <= 0x28FF):
        return char.translate(MIRROR_GLYPHS)
    bits = code - 0x2800
    mirrored = 0
    for src_bit, dst_bit in BRAILLE_MIRROR_BITS.items():
        if bits & (1 << src_bit):
            mirrored |= 1 << dst_bit
    return chr(0x2800 + mirrored)


def mirror_line(line: str) -> str:
    return "".join(mirror_braille_char(char) for char in reversed(line))


def compress_line(line: str, scale: float) -> str:
    source = list(line)
    visible = max(1, round(len(source) * scale))
    output: list[str] = []
    for x in range(visible):
        source_x = min(len(source) - 1, int(x / scale))
        output.append(source[source_x])
    return "".join(output).rstrip()


def compose(scale: float, mirrored: bool = False, flash: bool = False) -> list[str]:
    canvas = [row[:] for row in BORDER]

    source = [mirror_line(line) for line in HELMET] if mirrored else HELMET
    transformed = [compress_line(line, scale) for line in source]
    art_width = max((len(line) for line in transformed), default=1)

    top = (CANVAS_HEIGHT - len(transformed)) // 2
    left = (CANVAS_WIDTH - art_width) // 2

    for row_index, line in enumerate(transformed):
        y = top + row_index
        for column_index, char in enumerate(line):
            if char not in (" ", "⠀"):
                x = left + column_index
                if 0 <= y < CANVAS_HEIGHT and 0 <= x < CANVAS_WIDTH:
                    canvas[y][x] = char

    color = FLASH if flash else WHITE
    return [color + "".join(row).rstrip() + RESET for row in canvas]


FRAMES = [compose(scale, mirrored) for scale, mirrored in ROTATION]


# ---------------------------------------------------------------------------
# Terminal rendering
# ---------------------------------------------------------------------------

def frame(index: int) -> str:
    lines = FRAMES[index % len(FRAMES)]
    return "\r\n".join("\x1b[2K" + line for line in lines)


def draw(index: int) -> None:
    sys.stdout.write(SAVE + HIDE + HOME + frame(index) + SHOW + RESTORE)
    sys.stdout.flush()


def prepare(rows: int) -> None:
    if rows != ROWS:
        raise ValueError(f"Spartan Sigil requires {ROWS} rows")
    sys.stdout.write("\n" * ROWS)
    sys.stdout.flush()
    draw(0)


def clear_and_collapse() -> None:
    sys.stdout.write(HIDE + HOME)
    for _ in range(ROWS):
        sys.stdout.write("\x1b[1M")
    sys.stdout.write(RESET + SHOW + HOME)
    sys.stdout.flush()


def vanish() -> None:
    for index, delay in ((2, 0.040), (3, 0.040), (4, 0.050)):
        sys.stdout.write(SAVE + HIDE + HOME + frame(index) + SHOW + RESTORE)
        sys.stdout.flush()
        time.sleep(delay)

    flash_lines = compose(0.08, mirrored=False, flash=True)
    flash_frame = "\r\n".join("\x1b[2K" + line for line in flash_lines)
    sys.stdout.write(SAVE + HIDE + HOME + flash_frame + SHOW + RESTORE)
    sys.stdout.flush()
    time.sleep(0.045)
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
            deadline += 0.10
            time.sleep(max(0.0, deadline - time.monotonic()))
    finally:
        vanish()
    return 0


def terminal_check() -> tuple[bool, str]:
    if not sys.stdout.isatty():
        return False, "requires an interactive terminal"
    size = shutil.get_terminal_size(fallback=(0, 0))
    minimum_columns = CANVAS_WIDTH + 2
    minimum_lines = CANVAS_HEIGHT + 3
    if size.columns < minimum_columns or size.lines < minimum_lines:
        return False, (
            f"needs at least {minimum_columns} columns × {minimum_lines} rows; "
            f"current terminal is {size.columns} × {size.lines}."
        )
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spartan-sigil",
        description="A rotating Spartan helmet inside a Greek-key medallion.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="loop until interrupted")
    group.add_argument("--vanish", action="store_true", help="play the vanish once")
    group.add_argument("--prepare", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--render", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, default=ROWS, help=argparse.SUPPRESS)
    args = parser.parse_args()

    usable, reason = terminal_check()
    if not usable:
        if args.preview or args.vanish:
            print(f"Spartan Sigil {reason}", file=sys.stderr)
        return 2

    if args.vanish:
        vanish()
    elif args.prepare:
        prepare(args.rows)
    else:
        prepare(args.rows) if args.preview else None
        return render()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)