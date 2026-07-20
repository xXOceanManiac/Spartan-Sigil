#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass

RESET = "\x1b[0m"
WHITE = "\x1b[38;2;248;248;248m"
SIDE_NEAR = "\x1b[38;2;205;205;205m"
SIDE_FAR = "\x1b[38;2;145;145;145m"
FLASH = "\x1b[38;2;255;255;255m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
SAVE = "\x1b7"
RESTORE = "\x1b8"

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

CANVAS_WIDTH = 58
CANVAS_HEIGHT = 25
ROWS = CANVAS_HEIGHT
FRAME_DELAY = 0.18
OWNED_ROWS = ROWS
EDGE_THICKNESS = 3

BRAILLE_MIRROR_BITS = {0: 3, 1: 4, 2: 5, 3: 0, 4: 1, 5: 2, 6: 7, 7: 6}
MIRROR_GLYPHS = str.maketrans(
    {
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
    }
)


@dataclass(frozen=True)
class Frame:
    lines: tuple[str, ...]


def _normalize(lines: list[str]) -> list[str]:
    width = max(len(line) for line in lines)
    return [line.ljust(width, "⠀") for line in lines]


HELMET = _normalize(HELMET)


def _mirror_char(char: str) -> str:
    code = ord(char)
    if 0x2800 <= code <= 0x28FF:
        bits = code - 0x2800
        mirrored = 0
        for src, dst in BRAILLE_MIRROR_BITS.items():
            if bits & (1 << src):
                mirrored |= 1 << dst
        return chr(0x2800 + mirrored)
    return char.translate(MIRROR_GLYPHS)


def _mirror_line(line: str) -> str:
    return "".join(_mirror_char(ch) for ch in reversed(line))


def _solid_ring() -> list[list[str]]:
    grid = [[" " for _ in range(CANVAS_WIDTH)] for _ in range(CANVAS_HEIGHT)]
    cx = (CANVAS_WIDTH - 1) / 2
    cy = (CANVAS_HEIGHT - 1) / 2
    outer_rx, outer_ry = 26.5, 11.2
    inner_rx, inner_ry = 22.8, 8.9

    for y in range(CANVAS_HEIGHT):
        for x in range(CANVAS_WIDTH):
            outer = ((x - cx) / outer_rx) ** 2 + ((y - cy) / outer_ry) ** 2
            inner = ((x - cx) / inner_rx) ** 2 + ((y - cy) / inner_ry) ** 2
            if outer <= 1.0 and inner >= 1.0:
                nx = abs((x - cx) / outer_rx)
                ny = abs((y - cy) / outer_ry)
                if ny > 0.88:
                    grid[y][x] = "▄" if y < cy else "▀"
                elif nx > 0.92:
                    grid[y][x] = "▌" if x > cx else "▐"
                else:
                    grid[y][x] = "█"
    return grid


def _place_helmet(canvas: list[list[str]], mirrored: bool) -> None:
    source = [_mirror_line(line) for line in HELMET] if mirrored else HELMET
    art_width = max(len(line) for line in source)
    top = (CANVAS_HEIGHT - len(source)) // 2
    left = (CANVAS_WIDTH - art_width) // 2

    for row_index, line in enumerate(source):
        y = top + row_index
        if not 0 <= y < CANVAS_HEIGHT:
            continue
        for col_index, char in enumerate(line):
            if char in (" ", "⠀"):
                continue
            x = left + col_index
            if 0 <= x < CANVAS_WIDTH:
                canvas[y][x] = char


def _base_medallion(mirrored: bool) -> list[list[str]]:
    canvas = _solid_ring()
    _place_helmet(canvas, mirrored)
    return canvas


FRONT = _base_medallion(False)
BACK = _base_medallion(True)


def _scale_matrix(matrix: list[list[str]], scale: float) -> list[list[str]]:
    source_width = len(matrix[0])
    visible_width = max(1, round(source_width * scale))
    output = [[" " for _ in range(CANVAS_WIDTH)] for _ in range(CANVAS_HEIGHT)]
    left = (CANVAS_WIDTH - visible_width) // 2

    for y, row in enumerate(matrix):
        for out_x in range(visible_width):
            src_x = min(source_width - 1, int(out_x / max(scale, 0.001)))
            output[y][left + out_x] = row[src_x]
    return output


def _with_side_wall(face: list[list[str]], angle: float) -> list[list[tuple[str, str]]]:
    result = [[(" ", RESET) for _ in range(CANVAS_WIDTH)] for _ in range(CANVAS_HEIGHT)]
    side_strength = abs(math.sin(angle))
    offset = max(0, round(EDGE_THICKNESS * side_strength))
    direction = 1 if math.sin(angle) >= 0 else -1

    for y, row in enumerate(face):
        for x, char in enumerate(row):
            if char == " ":
                continue
            for step in range(offset, 0, -1):
                sx = x + direction * step
                if 0 <= sx < CANVAS_WIDTH:
                    color = SIDE_NEAR if step == 1 else SIDE_FAR
                    glyph = "▓" if step == 1 else "▒"
                    result[y][sx] = (glyph, color)

    for y, row in enumerate(face):
        for x, char in enumerate(row):
            if char != " ":
                result[y][x] = (char, WHITE)
    return result


def _render_colored(matrix: list[list[tuple[str, str]]]) -> tuple[str, ...]:
    rendered: list[str] = []
    for row in matrix:
        chunks: list[str] = []
        current = ""
        for glyph, color in row:
            if color != current:
                chunks.append(color)
                current = color
            chunks.append(glyph)
        chunks.append(RESET)
        rendered.append("".join(chunks))
    return tuple(rendered)


def _build_frames() -> list[Frame]:
    frames: list[Frame] = []
    frame_count = 24
    for index in range(frame_count):
        angle = math.tau * index / frame_count
        mirrored = math.cos(angle) < 0
        source = BACK if mirrored else FRONT
        face_scale = max(0.08, abs(math.cos(angle)))
        scaled = _scale_matrix(source, face_scale)
        extruded = _with_side_wall(scaled, angle)
        frames.append(Frame(_render_colored(extruded)))
    return frames


FRAMES = _build_frames()


def _terminal_size() -> os.terminal_size:
    return shutil.get_terminal_size(fallback=(0, 0))


def _terminal_check() -> tuple[bool, str]:
    if not sys.stdout.isatty():
        return False, "requires an interactive terminal"
    size = _terminal_size()
    minimum_columns = CANVAS_WIDTH + 2
    minimum_lines = CANVAS_HEIGHT + 2
    if size.columns < minimum_columns or size.lines < minimum_lines:
        return False, (
            f"needs at least {minimum_columns} columns × {minimum_lines} rows; "
            f"current terminal is {size.columns} × {size.lines}"
        )
    return True, ""


def _frame_text(frame: Frame) -> str:
    size = _terminal_size()
    left = max(1, (size.columns - CANVAS_WIDTH) // 2 + 1)
    parts: list[str] = []
    for row_offset, line in enumerate(frame.lines):
        parts.append(f"\x1b[{1 + row_offset};{left}H\x1b[2K{line}")
    return "".join(parts)


def draw(index: int) -> None:
    sys.stdout.write(
        SAVE + HIDE + _frame_text(FRAMES[index % len(FRAMES)]) + SHOW + RESTORE
    )
    sys.stdout.flush()


def prepare(rows: int) -> None:
    if rows < ROWS:
        raise ValueError(f"Spartan Sigil requires at least {ROWS} rows")
    sys.stdout.write("\n" * rows)
    sys.stdout.flush()
    draw(0)


def _clear_owned_region() -> None:
    size = _terminal_size()
    for row in range(1, min(OWNED_ROWS, size.lines) + 1):
        sys.stdout.write(f"\x1b[{row};1H\x1b[2K")
    sys.stdout.flush()


def clear_and_collapse() -> None:
    # Delete Bash's reservation and leave the submitted readline text intact.
    size = _terminal_size()
    sys.stdout.write(HIDE + "\x1b[H")
    for _ in range(min(OWNED_ROWS, max(0, size.lines - 1))):
        sys.stdout.write("\x1b[1M")
    sys.stdout.write(RESET + SHOW + "\x1b[H")
    sys.stdout.flush()


def vanish(start_index: int = 0) -> None:
    sequence = [start_index, 3, 5, 6]
    for index in sequence:
        sys.stdout.write(
            SAVE + HIDE + _frame_text(FRAMES[index % len(FRAMES)]) + SHOW + RESTORE
        )
        sys.stdout.flush()
        time.sleep(0.035)
    clear_and_collapse()


def render() -> int:
    stopping = False
    resized = False
    current_index = 0

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    def resize(_signum: int, _frame: object) -> None:
        nonlocal resized
        resized = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGWINCH, resize)

    deadline = time.monotonic()
    try:
        while not stopping:
            if resized:
                _clear_owned_region()
                resized = False
            draw(current_index)
            current_index = (current_index + 1) % len(FRAMES)
            deadline += FRAME_DELAY
            time.sleep(max(0.0, deadline - time.monotonic()))
    finally:
        vanish(current_index)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spartan-sigil",
        description="A rotating Spartan helmet medallion.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="loop until interrupted")
    group.add_argument("--vanish", action="store_true", help="play the vanish once")
    group.add_argument("--prepare", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--render", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, default=ROWS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    global OWNED_ROWS
    OWNED_ROWS = args.rows

    usable, reason = _terminal_check()
    if not usable:
        if args.preview or args.vanish:
            print(f"Spartan Sigil {reason}.", file=sys.stderr)
        return 2

    if args.vanish:
        vanish()
    elif args.prepare:
        prepare(args.rows)
    else:
        if args.preview:
            prepare(args.rows)
        return render()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
