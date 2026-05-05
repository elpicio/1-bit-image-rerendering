import numpy as np
from PIL import Image

from .base import DitherAlgorithm
from .registry import register


def _apply_error_diffusion(
    image: Image.Image,
    kernel: list[tuple[int, int, float]],
    divisor: float,
) -> Image.Image:
    """Generic error diffusion implementation.

    Args:
        image: Grayscale PIL Image (mode 'L').
        kernel: List of (dx, dy, weight) specifying how error is distributed.
        divisor: Sum used to normalize weights.
    """
    pixels = np.array(image, dtype=np.float64)
    h, w = pixels.shape

    # Precompute normalized weights
    nk = [(dx, dy, weight / divisor) for dx, dy, weight in kernel]

    for y in range(h):
        for x in range(w):
            old = pixels[y, x]
            new = 255.0 if old >= 128.0 else 0.0
            pixels[y, x] = new
            err = old - new
            for dx, dy, wn in nk:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    pixels[ny, nx] += err * wn

    return Image.fromarray((pixels > 128).astype(np.uint8) * 255, mode="L").convert("1")


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------


@register
class FloydSteinberg(DitherAlgorithm):
    name = "floyd-steinberg"
    description = "Classic error diffusion, natural and detailed"

    def apply(self, image: Image.Image) -> Image.Image:
        kernel = [
            (1, 0, 7),
            (-1, 1, 3),
            (0, 1, 5),
            (1, 1, 1),
        ]
        return _apply_error_diffusion(image, kernel, divisor=16)


@register
class Atkinson(DitherAlgorithm):
    name = "atkinson"
    description = "High contrast, classic Macintosh aesthetic (only 3/4 error diffused)"

    def apply(self, image: Image.Image) -> Image.Image:
        # Each neighbour gets 1/8 of error; 6 neighbours = 6/8 = 3/4 total
        kernel = [
            (1, 0, 1),
            (2, 0, 1),
            (-1, 1, 1),
            (0, 1, 1),
            (1, 1, 1),
            (0, 2, 1),
        ]
        return _apply_error_diffusion(image, kernel, divisor=8)


@register
class JarvisJudiceNinke(DitherAlgorithm):
    name = "jarvis"
    description = "Smoother than Floyd-Steinberg, 12-neighbour diffusion"

    def apply(self, image: Image.Image) -> Image.Image:
        kernel = [
            (1, 0, 7), (2, 0, 5),
            (-2, 1, 3), (-1, 1, 5), (0, 1, 7), (1, 1, 5), (2, 1, 3),
            (-2, 2, 1), (-1, 2, 3), (0, 2, 5), (1, 2, 3), (2, 2, 1),
        ]
        return _apply_error_diffusion(image, kernel, divisor=48)


@register
class Stucki(DitherAlgorithm):
    name = "stucki"
    description = "Optimized for print reproduction, smooth gradients"

    def apply(self, image: Image.Image) -> Image.Image:
        kernel = [
            (1, 0, 8), (2, 0, 4),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2),
            (-2, 2, 1), (-1, 2, 2), (0, 2, 4), (1, 2, 2), (2, 2, 1),
        ]
        return _apply_error_diffusion(image, kernel, divisor=42)


@register
class Burkes(DitherAlgorithm):
    name = "burkes"
    description = "Fast approximation of Stucki, bit-shift friendly"

    def apply(self, image: Image.Image) -> Image.Image:
        kernel = [
            (1, 0, 8), (2, 0, 4),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 8), (1, 1, 4), (2, 1, 2),
        ]
        return _apply_error_diffusion(image, kernel, divisor=32)


@register
class Sierra(DitherAlgorithm):
    name = "sierra"
    description = "Quality close to Jarvis, created for King's Quest"

    def apply(self, image: Image.Image) -> Image.Image:
        kernel = [
            (1, 0, 5), (2, 0, 3),
            (-2, 1, 2), (-1, 1, 4), (0, 1, 5), (1, 1, 4), (2, 1, 2),
            (-1, 2, 2), (0, 2, 3), (1, 2, 2),
        ]
        return _apply_error_diffusion(image, kernel, divisor=32)
