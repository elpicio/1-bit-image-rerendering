"""Foreground / background colorization for 1-bit images."""

from __future__ import annotations

import numpy as np
from PIL import Image


def parse_color(color_str: str) -> tuple[int, int, int]:
    """Parse a color string into (R, G, B). Supports:
    - Hex: '#FF00AA', 'FF00AA', '#f0a' (3-digit)
    - CSS rgb/rgba: 'rgb(255, 0, 170)', 'rgba(255, 0, 170, 1)'
    - CSS hsl/hsla: 'hsl(320, 100%, 50%)', 'hsla(320, 100%, 50%, 1)'
    """
    import colorsys
    import re

    s = color_str.strip()

    # rgb(R, G, B) or rgba(R, G, B, A) — values may be floats
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", s)
    if m:
        return (
            min(255, int(round(float(m.group(1))))),
            min(255, int(round(float(m.group(2))))),
            min(255, int(round(float(m.group(3))))),
        )

    # hsl(H, S%, L%) or hsla(H, S%, L%, A)
    m = re.match(r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%", s)
    if m:
        h = float(m.group(1)) / 360.0
        sat = float(m.group(2)) / 100.0
        light = float(m.group(3)) / 100.0
        r, g, b = colorsys.hls_to_rgb(h, light, sat)
        return (int(r * 255), int(g * 255), int(b * 255))

    # Hex
    s = s.lstrip("#")
    if len(s) == 3:
        s = s[0] * 2 + s[1] * 2 + s[2] * 2
    if len(s) == 6:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

    raise ValueError(f"Cannot parse color: '{color_str}'")


def apply_colors(
    image: Image.Image,
    fg_color: str | None = None,
    bg_color: str | None = None,
) -> Image.Image:
    """Replace black/white pixels with custom foreground/background colors.

    Args:
        image: 1-bit or grayscale image.
        fg_color: Hex color for black (foreground) pixels. None = keep black.
        bg_color: Hex color for white (background) pixels. None = keep white.

    Returns:
        RGB image if any color is specified, otherwise the original image.
    """
    if fg_color is None and bg_color is None:
        return image

    fg = parse_color(fg_color) if fg_color else (0, 0, 0)
    bg = parse_color(bg_color) if bg_color else (255, 255, 255)

    bw = np.array(image.convert("L"), dtype=np.uint8)
    rgb = np.zeros((*bw.shape, 3), dtype=np.uint8)
    white_mask = bw > 128
    rgb[~white_mask] = fg
    rgb[white_mask] = bg
    return Image.fromarray(rgb)
