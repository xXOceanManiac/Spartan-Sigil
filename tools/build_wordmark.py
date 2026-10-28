"""Rebuild the antialiased terminal lettering (development only; requires Pillow)."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--font", default="/usr/share/fonts/opentype/urw-base35/NimbusRoman-Regular.otf")
args = parser.parse_args()
font = ImageFont.truetype(args.font, 160)
word = "SPARTAN"
tracking = 24
advances = [font.getlength(letter) + tracking for letter in word]
width = round(sum(advances) - tracking)
top = min(font.getbbox(letter)[1] for letter in word)
bottom = max(font.getbbox(letter)[3] for letter in word)
glyphs = []
cursor = 0
for letter, advance in zip(word, advances):
    canvas = Image.new("L", (width, bottom - top))
    ImageDraw.Draw(canvas).text((cursor, -top), letter, font=font, fill=255)
    canvas = canvas.resize((52, 10), Image.Resampling.LANCZOS)
    glyphs.append(list(canvas.getdata()))
    cursor += advance
destination = Path(__file__).resolve().parents[1] / "assets" / "wordmark.json"
destination.write_text(json.dumps({
    "word": word, "font": "Nimbus Roman Regular", "width": 52, "height": 10,
    "glyphs": glyphs,
}, separators=(",", ":")) + "\n")
