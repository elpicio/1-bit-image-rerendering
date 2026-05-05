"""Foreground/background segmentation for dual-dithering."""

from __future__ import annotations

import numpy as np
from PIL import Image
from skimage import filters


def segment_by_brightness(
    image: Image.Image,
    threshold: int = 128,
) -> np.ndarray:
    """Segment image into foreground/background by brightness.

    Args:
        image: Grayscale PIL Image (mode 'L').
        threshold: Pixels darker than this are foreground (0-255).

    Returns:
        Boolean ndarray where True = foreground.
    """
    pixels = np.array(image, dtype=np.uint8)
    return pixels < threshold


def segment_by_edges(
    image: Image.Image,
    dilation: int = 15,
) -> np.ndarray:
    """Segment image using edge density — areas near edges are foreground.

    Args:
        image: Grayscale PIL Image (mode 'L').
        dilation: Radius to expand edge regions (larger = more foreground).

    Returns:
        Boolean ndarray where True = foreground.
    """
    from skimage import morphology

    pixels = np.array(image, dtype=np.float64) / 255.0
    edges = filters.sobel(pixels)
    # Threshold edges and dilate to create foreground regions
    edge_mask = edges > 0.05
    if dilation > 0:
        footprint = morphology.disk(dilation)
        edge_mask = morphology.dilation(edge_mask.astype(np.uint8), footprint).astype(bool)
    return edge_mask


def _dither_with_spacing(image: Image.Image, algo, spacing: int) -> np.ndarray:
    """Apply dithering with optional spacing (downscale→dither→upscale)."""
    original_size = image.size
    work = image
    if spacing > 1:
        new_w = max(1, original_size[0] // spacing)
        new_h = max(1, original_size[1] // spacing)
        work = work.resize((new_w, new_h), Image.Resampling.LANCZOS)

    result = algo.apply(work).convert("L")

    if spacing > 1:
        result = result.resize(original_size, Image.Resampling.NEAREST)

    return np.array(result, dtype=np.uint8)


def apply_dual_dither(
    image: Image.Image,
    fg_mask: np.ndarray,
    fg_algo,
    bg_algo,
    fg_spacing: int = 1,
    bg_spacing: int = 1,
) -> Image.Image:
    """Apply different dithering algorithms to foreground and background.

    Args:
        image: Grayscale PIL Image (mode 'L').
        fg_mask: Boolean ndarray where True = foreground.
        fg_algo: DitherAlgorithm instance for foreground.
        bg_algo: DitherAlgorithm instance for background.
        fg_spacing: Spacing for foreground dithering.
        bg_spacing: Spacing for background dithering.

    Returns:
        Combined result as PIL Image (mode 'L').
    """
    fg_result = _dither_with_spacing(image, fg_algo, fg_spacing)
    bg_result = _dither_with_spacing(image, bg_algo, bg_spacing)

    combined = np.where(fg_mask, fg_result, bg_result)
    return Image.fromarray(combined, mode="L")
