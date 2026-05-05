import numpy as np
from PIL import Image

from .base import DitherAlgorithm
from .registry import register


@register
class Threshold(DitherAlgorithm):
    name = "threshold"
    description = "Simple binary threshold (no dithering)"

    def __init__(self, threshold: int = 128):
        self.threshold = threshold

    def apply(self, image: Image.Image) -> Image.Image:
        pixels = np.array(image, dtype=np.uint8)
        result = np.where(pixels >= self.threshold, 255, 0).astype(np.uint8)
        return Image.fromarray(result, mode="L").convert("1")
