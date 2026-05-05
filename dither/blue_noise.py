import numpy as np
from PIL import Image

from .base import DitherAlgorithm
from .registry import register

_cache: dict[int, np.ndarray] = {}


def _generate_blue_noise(size: int = 64, seed: int = 42) -> np.ndarray:
    """Generate a blue noise threshold matrix via FFT frequency-domain filtering.

    1. Generate white noise
    2. FFT -> suppress low frequencies (high-pass) -> IFFT
    3. Rank-order the result so every threshold level produces the correct
       pixel count while maintaining blue-noise spatial distribution.

    The result tiles seamlessly due to the periodic nature of the DFT.
    """
    if size in _cache:
        return _cache[size]

    rng = np.random.default_rng(seed)
    white = rng.random((size, size))

    # FFT
    F = np.fft.fft2(white)

    # High-pass filter: attenuate low frequencies
    yy, xx = np.mgrid[0:size, 0:size]
    fy = np.minimum(yy, size - yy).astype(np.float64)
    fx = np.minimum(xx, size - xx).astype(np.float64)
    freq = np.sqrt(fy**2 + fx**2)
    sigma = size / 8.0
    hp = 1.0 - np.exp(-(freq**2) / (2.0 * sigma**2))
    hp[0, 0] = 0.0  # kill DC component

    filtered = np.real(np.fft.ifft2(F * hp))

    # Rank-order -> uniform threshold matrix in [0, 1)
    flat = filtered.ravel()
    ranks = np.empty_like(flat)
    ranks[np.argsort(flat)] = np.arange(len(flat), dtype=np.float64)
    matrix = ranks.reshape(size, size) / (size * size)

    _cache[size] = matrix
    return matrix


@register
class BlueNoise(DitherAlgorithm):
    name = "bluenoise"
    description = "Organic, film-grain-like dithering (no visible grid pattern)"

    def __init__(self, size: int = 64):
        self.size = size

    def apply(self, image: Image.Image) -> Image.Image:
        threshold = _generate_blue_noise(self.size)
        pixels = np.array(image, dtype=np.float64)
        h, w = pixels.shape
        n = self.size

        tiled = np.tile(threshold, (h // n + 1, w // n + 1))[:h, :w]
        result = (pixels / 255.0 > tiled).astype(np.uint8) * 255
        return Image.fromarray(result, mode="L").convert("1")
