import numpy as np
from PIL import Image

from .base import DitherAlgorithm
from .registry import register


def _bayer_matrix(n: int) -> np.ndarray:
    """Generate a Bayer threshold matrix of size 2^n x 2^n recursively."""
    if n == 0:
        return np.array([[0]])
    m = _bayer_matrix(n - 1)
    return np.block([
        [4 * m + 0, 4 * m + 2],
        [4 * m + 3, 4 * m + 1],
    ])


def _apply_ordered(image: Image.Image, matrix: np.ndarray) -> Image.Image:
    """Apply ordered dithering using a threshold matrix."""
    pixels = np.array(image, dtype=np.float64)
    h, w = pixels.shape
    n = matrix.shape[0]

    # Normalize matrix to (0, 1)
    threshold = (matrix + 0.5) / (n * n)

    # Tile to cover the whole image
    tiled = np.tile(threshold, (h // n + 1, w // n + 1))[:h, :w]

    result = (pixels / 255.0 > tiled).astype(np.uint8) * 255
    return Image.fromarray(result, mode="L").convert("1")


@register
class Bayer2x2(DitherAlgorithm):
    name = "bayer2x2"
    description = "Coarse 2x2 ordered dithering, very retro"

    def apply(self, image: Image.Image) -> Image.Image:
        return _apply_ordered(image, _bayer_matrix(1))


@register
class Bayer4x4(DitherAlgorithm):
    name = "bayer4x4"
    description = "Classic 4x4 ordered dithering, Game Boy feel"

    def apply(self, image: Image.Image) -> Image.Image:
        return _apply_ordered(image, _bayer_matrix(2))


@register
class Bayer8x8(DitherAlgorithm):
    name = "bayer8x8"
    description = "Smooth 8x8 ordered dithering, good detail retention"

    def apply(self, image: Image.Image) -> Image.Image:
        return _apply_ordered(image, _bayer_matrix(3))
