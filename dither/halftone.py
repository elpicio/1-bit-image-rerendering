import numpy as np
from PIL import Image

from .base import DitherAlgorithm
from .registry import register


@register
class Halftone(DitherAlgorithm):
    name = "halftone"
    description = "Newspaper print style with circular dots"

    def __init__(self, dot_size: int = 8):
        self.dot_size = dot_size

    def apply(self, image: Image.Image) -> Image.Image:
        pixels = np.array(image, dtype=np.float64)
        h, w = pixels.shape
        ds = self.dot_size

        result = np.full((h, w), 255, dtype=np.uint8)

        # Distance from cell centre (reused for every cell)
        yy, xx = np.mgrid[0:ds, 0:ds]
        centre = ds / 2.0
        dist = np.sqrt((yy - centre + 0.5) ** 2 + (xx - centre + 0.5) ** 2)
        max_radius = centre * np.sqrt(2)

        for cy in range(0, h, ds):
            for cx in range(0, w, ds):
                cell = pixels[cy : cy + ds, cx : cx + ds]
                if cell.size == 0:
                    continue
                ah, aw = cell.shape
                avg = cell.mean() / 255.0  # 0 = black, 1 = white
                radius = max_radius * np.sqrt(max(1.0 - avg, 0.0))
                dot = dist[:ah, :aw] < radius
                result[cy : cy + ah, cx : cx + aw] = np.where(dot, 0, 255)

        return Image.fromarray(result, mode="L").convert("1")
