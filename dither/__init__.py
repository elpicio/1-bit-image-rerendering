from .registry import get_algorithm, list_algorithms

# Import modules to trigger algorithm registration
from . import blue_noise as _blue_noise
from . import error_diffusion as _error_diffusion
from . import halftone as _halftone
from . import ordered as _ordered
from . import threshold as _threshold

__all__ = [
    "get_algorithm",
    "list_algorithms",
]
