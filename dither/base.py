from abc import ABC, abstractmethod

from PIL import Image


class DitherAlgorithm(ABC):
    """Base class for all dithering algorithms.

    To add a new algorithm:
    1. Create a new file in the dither/ directory
    2. Subclass DitherAlgorithm, set `name` and `description`
    3. Implement the `apply` method
    4. Decorate the class with `@register` from dither.registry
    5. Import the module in dither/__init__.py
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def apply(self, image: Image.Image) -> Image.Image:
        """Apply dithering to a grayscale image.

        Args:
            image: PIL Image in mode 'L' (8-bit grayscale).

        Returns:
            PIL Image in mode '1' (1-bit black and white).
        """
        pass
