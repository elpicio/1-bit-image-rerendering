"""Edge detection and overlay for stylized rendering."""

from __future__ import annotations

import numpy as np
from PIL import Image
from skimage import feature, filters, morphology


def detect_edges(
    image: Image.Image,
    method: str = "canny",
    strength: float = 1.0,
    width: int = 1,
) -> np.ndarray:
    """Detect edges in a grayscale image.

    Args:
        image: PIL Image in mode 'L'.
        method: 'canny' or 'sobel'.
        strength: Edge sensitivity. For Canny, controls sigma (lower = more edges).
                  For Sobel, controls threshold (lower = more edges). Range 0.1-3.0.
        width: Line width in pixels. 1 = thin, 2+ = dilated.

    Returns:
        Boolean ndarray where True = edge pixel.
    """
    pixels = np.array(image, dtype=np.float64) / 255.0

    if method == "canny":
        # strength maps inversely to sigma: low strength = high sigma = fewer edges
        sigma = max(0.1, 3.0 - strength * 1.5)
        edges = feature.canny(pixels, sigma=sigma)
    elif method == "sobel":
        sobel = filters.sobel(pixels)
        # strength maps inversely to threshold
        thresh = max(0.01, 0.3 / strength)
        edges = sobel > thresh
    else:
        raise ValueError(f"Unknown edge method: '{method}'. Use 'canny' or 'sobel'.")

    # Dilate for thicker lines
    if width > 1:
        footprint = morphology.disk(width - 1)
        edges = morphology.dilation(edges.astype(np.uint8), footprint).astype(bool)

    return edges


def overlay_edges(
    dithered: Image.Image,
    edges: np.ndarray,
) -> Image.Image:
    """Overlay edge pixels as pure black onto a dithered image.

    Args:
        dithered: The dithered result (mode 'L' or '1').
        edges: Boolean ndarray from detect_edges().

    Returns:
        PIL Image with edges burned in as black.
    """
    result = np.array(dithered.convert("L"), dtype=np.uint8)
    result[edges] = 0
    return Image.fromarray(result, mode="L")
