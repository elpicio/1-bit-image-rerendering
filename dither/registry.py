from __future__ import annotations

from .base import DitherAlgorithm

_registry: dict[str, type[DitherAlgorithm]] = {}


def register(cls: type[DitherAlgorithm]) -> type[DitherAlgorithm]:
    """Class decorator to register a dithering algorithm."""
    _registry[cls.name] = cls
    return cls


def get_algorithm(name: str, **kwargs) -> DitherAlgorithm:
    """Get an algorithm instance by name."""
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise ValueError(f"Unknown algorithm: '{name}'. Available: {available}")
    return _registry[name](**kwargs)


def list_algorithms() -> dict[str, str]:
    """Return {name: description} for all registered algorithms."""
    return {name: cls.description for name, cls in sorted(_registry.items())}
