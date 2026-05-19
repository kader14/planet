#!/usr/bin/env python3
"""Generate the Open Graph image (1200x630 PNG) for Planet Python Arabic.

This script is run once at design time (not on each cron tick). The output is
committed at ``static/images/og-image.png``. Re-run it after a logo or palette
change:

    pip install Pillow fonttools brotli arabic-reshaper python-bidi
    python3 scripts/make_og_image.py

Strategy: convert our shipped Cairo woff2 to TTF in-memory, then draw a
gradient + logo + Arabic text with Pillow. Arabic shaping is handled by
``arabic_reshaper`` and bidirectional flow by ``bidi.algorithm.get_display``.
"""

import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Site palette ------------------------------------------------------------
GRAD_START = (30, 58, 138)   # #1e3a8a
GRAD_END = (59, 130, 246)    # #3b82f6
WHITE = (255, 255, 255)
ACCENT = (251, 191, 36)      # #fbbf24
TEXT_SOFT = (220, 230, 250)

W, H = 1200, 630


def woff2_to_ttf_bytes(woff2_path: str) -> bytes:
    """Strip the woff2 wrapper and return raw TTF bytes for PIL."""
    f = TTFont(woff2_path)
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    return buf.getvalue()


def font(woff2_rel: str, size: int) -> ImageFont.FreeTypeFont:
    ttf_bytes = woff2_to_ttf_bytes(os.path.join(ROOT, woff2_rel))
    return ImageFont.truetype(io.BytesIO(ttf_bytes), size=size)


def shape_arabic(text: str) -> str:
    """Apply Arabic letter joining + RTL reordering for visual rendering."""
    return get_display(arabic_reshaper.reshape(text))


# --- Build the image -----------------------------------------------------
img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Vertical gradient (matches the site header).
for y in range(H):
    t = y / (H - 1)
    r = int(GRAD_START[0] + (GRAD_END[0] - GRAD_START[0]) * t)
    g = int(GRAD_START[1] + (GRAD_END[1] - GRAD_START[1]) * t)
    b = int(GRAD_START[2] + (GRAD_END[2] - GRAD_START[2]) * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# White circular badge for the "Py" mark (right side, RTL anchor).
circle_d = 240
cx, cy = 920, H // 2
draw.ellipse(
    [cx - circle_d // 2, cy - circle_d // 2, cx + circle_d // 2, cy + circle_d // 2],
    fill=WHITE,
)

# "Py" inside the badge.
py_font = font("static/fonts/cairo-latin.woff2", 140)
draw.text((cx, cy), "Py", font=py_font, fill=GRAD_START, anchor="mm")

# Arabic title and subtitle, right-anchored.
title_font = font("static/fonts/cairo-arabic.woff2", 96)
sub_font = font("static/fonts/cairo-arabic.woff2", 36)

title = shape_arabic("كوكب بايثون")
subtitle = shape_arabic("تجميع تدوينات مجتمع بايثون العربي")

draw.text((720, cy - 40), title, font=title_font, fill=WHITE, anchor="rm")
draw.text((720, cy + 50), subtitle, font=sub_font, fill=TEXT_SOFT, anchor="rm")

# Yellow accent strip under the subtitle.
draw.rectangle([520, cy + 100, 720, cy + 106], fill=ACCENT)

# URL in the bottom-right corner (Latin, no shaping needed).
url_font = font("static/fonts/cairo-latin.woff2", 28)
draw.text((W - 60, H - 50), "planet.pyarabic.com", font=url_font, fill=TEXT_SOFT, anchor="rm")

OUT = os.path.join(ROOT, "static", "images", "og-image.png")
img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
