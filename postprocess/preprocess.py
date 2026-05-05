"""Pre-processing steps applied before dithering."""

from __future__ import annotations

import numpy as np
from PIL import Image


def adjust_contrast_brightness(
    image: Image.Image,
    contrast: float = 1.0,
    brightness: int = 0,
) -> Image.Image:
    """Adjust contrast and brightness of a grayscale image.

    Args:
        image: PIL Image in mode 'L'.
        contrast: Multiplier (1.0 = no change, >1 = higher contrast).
        brightness: Offset added after contrast (-128 to 128).

    Returns:
        Adjusted grayscale image.
    """
    if contrast == 1.0 and brightness == 0:
        return image

    pixels = np.array(image, dtype=np.float64)
    # Contrast: scale around midpoint 128
    pixels = (pixels - 128.0) * contrast + 128.0 + brightness
    pixels = np.clip(pixels, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels, mode="L")
