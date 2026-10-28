#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RESET = "\x1b[0m"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
SAVE = "\x1b7"
RESTORE = "\x1b8"

# Two square luminance samples per terminal cell preserve the sculpture's shape.
CANVAS_WIDTH = 64
CANVAS_HEIGHT = 32
HELMET_HEIGHT = 30
ROWS = CANVAS_HEIGHT + 1
FRAME_DELAY = 0.06
INTRO_DURATION = 1.2
OWNED_ROWS = ROWS
ASSET = Path(__file__).resolve().parent / "assets" / "helmet-luminance.json"

# Pre-rasterized Roman capitals retain font antialiasing at terminal resolution.
# Pillow and the source font are only needed when rebuilding this asset.
TITLE = json.loads(ASSET.with_name("wordmark.json").read_text())


def _overlay_title(shaded: list[list[int]], phase: float,
                   opacity: float, progress: float) -> None:
    width, height = TITLE["width"], TITLE["height"]
    left, top = (CANVAS_WIDTH - width) // 2, 48
    mask: dict[tuple[int, int], float] = {}
    for index, glyph in enumerate(TITLE["glyphs"]):
        reveal = max(0.0, min(1.0, (progress * 1.25 - index / 6 * 0.9) / 0.35))
        reveal = reveal * reveal * (3 - 2 * reveal)
        for offset, coverage in enumerate(glyph):
            if coverage > 3:
                point = left + offset % width, top + offset // width
                mask[point] = min(1.0, mask.get(point, 0.0) + coverage / 255 * reveal)

    def blend(x: int, y: int, value: float, alpha: float) -> None:
        if 0 <= y < len(shaded) and 0 <= x < CANVAS_WIDTH:
            shaded[y][x] = round(shaded[y][x] * (1 - alpha) + value * opacity * alpha)

    # A close, soft shadow lifts thin strokes without a heavy cartoon outline.
    shadow: dict[tuple[int, int], float] = {}
    for (x, y), alpha in mask.items():
        for dx, dy, strength in ((0, 1, 0.80), (1, 1, 0.45),
                                  (-1, 0, 0.35), (1, 0, 0.35), (0, -1, 0.35)):
            point = x + dx, y + dy
            shadow[point] = max(shadow.get(point, 0.0), alpha * strength)
    for (x, y), alpha in shadow.items():
        blend(x, y, 14, alpha)
    light_x = 31.5 + 27 * math.sin(phase)
    for (x, y), alpha in mask.items():
        glint = math.exp(-((x - light_x) / 9) ** 2)
        silver = 238 - 22 * (y - top) / (height - 1) + 17 * glint
        blend(x, y, silver, alpha)


@dataclass(frozen=True)
class Frame:
    lines: tuple[str, ...]


def _load_pixels() -> list[list[int]]:
    data = json.loads(ASSET.read_text())
    width, height = data["width"], data["height"]
    pixels = data["pixels"]
    if (width, height) != (CANVAS_WIDTH, CANVAS_HEIGHT * 2):
        raise ValueError("helmet asset has incorrect dimensions")
    if len(pixels) != width * height or any(
        type(value) is not int or not 0 <= value <= 255 for value in pixels
    ):
        raise ValueError("helmet asset has invalid luminance samples")
    return [pixels[y * width:(y + 1) * width] for y in range(height)]


def _build_frame(pixels: list[list[int]], phase: float = 0.0,
                 opacity: float = 1.0, title_progress: float = 1.0) -> Frame:
    # Perspective on the original relief: a small rocking turn, never edge-on.
    # Inverse projection and bilinear sampling keep the bevels from shimmering.
    yaw = 0.28 * math.sin(phase)
    turn_cos, turn_sin = math.cos(yaw), math.sin(yaw)
    roll = 0.018 * math.sin(phase)
    roll_cos, roll_sin = math.cos(roll), math.sin(roll)
    light_x = 31.5 + 34 * math.sin(phase + 0.35)
    bob = 0.55 * math.sin(phase * 2)
    shaded = []
    for y in range(HELMET_HEIGHT * 2):
        row = []
        for x in range(CANVAS_WIDTH):
            dx = (x - 31.5) / 0.90
            dy = (y - 29.5 - bob) / 0.90
            rx = dx * roll_cos + dy * roll_sin
            ry = -dx * roll_sin + dy * roll_cos
            u = rx / (turn_cos - rx * turn_sin / 110)
            perspective = 1 + u * turn_sin / 110
            sx, sy = u + 31.5, ry * perspective + 31.5
            if not (0 <= sx < 63 and 0 <= sy < 63):
                row.append(0)
                continue
            ix, iy = int(sx), int(sy)
            fx, fy = sx - ix, sy - iy
            value = (
                (pixels[iy][ix] * (1 - fx) + pixels[iy][ix + 1] * fx) * (1 - fy)
                + (pixels[iy + 1][ix] * (1 - fx) + pixels[iy + 1][ix + 1] * fx) * fy
            )
            beam = math.exp(-((sx - light_x + (sy - 32) * 0.28) / 6.5) ** 2)
            light = 0.85 + 0.12 * math.cos(phase) + 0.36 * beam
            row.append(0 if value < 7 else min(255, round(opacity * value * light)))
        shaded.append(row)
    shaded.extend([[0] * CANVAS_WIDTH for _ in range((CANVAS_HEIGHT - HELMET_HEIGHT) * 2)])
    _overlay_title(shaded, phase, opacity, title_progress)
    lines = []
    for y in range(0, len(shaded), 2):
        chunks = []
        previous = None
        for top, bottom in zip(shaded[y], shaded[y + 1]):
            # Quantization reduces escape traffic without losing the bevels.
            top, bottom = (round(value / 4) * 4 for value in (top, bottom))
            top, bottom = min(255, top), min(255, bottom)
            colors = (top, bottom)
            if colors != previous:
                if not top and not bottom:
                    chunks.append(RESET)
                else:
                    fg = f"38;2;{top};{top};{top}" if top else "39"
                    bg = f"48;2;{bottom};{bottom};{bottom}" if bottom else "49"
                    chunks.append(f"\x1b[{fg};{bg}m")
                previous = colors
            if not top:
                # With a transparent upper pixel, use the lower half as foreground.
                if bottom:
                    chunks.append(f"\x1b[38;2;{bottom};{bottom};{bottom};49m▄")
                    previous = None
                else:
                    chunks.append(" ")
            else:
                chunks.append("▀")
        lines.append("".join(chunks) + RESET)
    return Frame(tuple(lines))


PIXELS = _load_pixels()
# Frames are built lazily, keeping startup and short-lived helper calls quick.
FRAME_COUNT = 128
FRAMES: dict[int, Frame] = {}


def frame_at(index: int) -> Frame:
    index %= FRAME_COUNT
    if index not in FRAMES:
        FRAMES[index] = _build_frame(PIXELS, math.tau * index / FRAME_COUNT)
    return FRAMES[index]


def _terminal_size() -> os.terminal_size:
    return shutil.get_terminal_size(fallback=(0, 0))


def _terminal_check() -> tuple[bool, str]:
    if not sys.stdout.isatty():
        return False, "requires an interactive terminal"
    size = _terminal_size()
    minimum_columns = CANVAS_WIDTH + 2
    minimum_lines = ROWS + 2
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


def draw(index: int, title_progress: float = 1.0) -> None:
    frame = (frame_at(index) if title_progress >= 1.0 else
             _build_frame(PIXELS, math.tau * index / FRAME_COUNT,
                          title_progress=title_progress))
    sys.stdout.write(
        SAVE + HIDE + _frame_text(frame) + SHOW + RESTORE
    )
    sys.stdout.flush()


def prepare(rows: int) -> None:
    if rows < ROWS:
        raise ValueError(f"Spartan Sigil requires at least {ROWS} rows")
    sys.stdout.write("\n" * rows)
    sys.stdout.flush()
    draw(0, title_progress=0.0)


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
    sys.stdout.write(RESET + SHOW + "\x1b[2;1H")
    sys.stdout.flush()


def vanish(start_index: int = 0, title_progress: float = 1.0) -> None:
    for opacity in (0.72, 0.40, 0.16):
        frame = _build_frame(PIXELS, math.tau * start_index / FRAME_COUNT,
                             opacity, title_progress)
        sys.stdout.write(SAVE + _frame_text(frame) + RESTORE)
        sys.stdout.flush()
        time.sleep(0.025)
    clear_and_collapse()


def render() -> int:
    stopping = False
    resized = False
    current_index = 0
    last_index = 0
    title_progress = 0.0

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    def resize(_signum: int, _frame: object) -> None:
        nonlocal resized
        resized = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGWINCH, resize)

    started = deadline = time.monotonic()
    try:
        while not stopping:
            if resized:
                _clear_owned_region()
                resized = False
            title_progress = min(1.0, (time.monotonic() - started) / INTRO_DURATION)
            draw(current_index, title_progress)
            last_index = current_index
            current_index = (current_index + 1) % FRAME_COUNT
            deadline += FRAME_DELAY
            time.sleep(max(0.0, deadline - time.monotonic()))
    finally:
        vanish(last_index, title_progress)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spartan-sigil",
        description="A silver Spartan relief with rocking motion and animated highlights.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="loop until interrupted")
    group.add_argument("--still", action="store_true", help="print the helmet without animation")
    group.add_argument("--vanish", action="store_true", help="play the vanish once")
    group.add_argument("--prepare", action="store_true", help=argparse.SUPPRESS)
    group.add_argument("--render", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--rows", type=int, default=ROWS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    global OWNED_ROWS
    OWNED_ROWS = args.rows
    if args.rows < ROWS:
        parser.error(f"--rows must be at least {ROWS}")

    usable, reason = _terminal_check()
    if not usable:
        if args.preview or args.vanish or args.still:
            print(f"Spartan Sigil {reason}.", file=sys.stderr)
        return 2

    if args.still:
        print("\n".join(frame_at(0).lines))
    elif args.vanish:
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
