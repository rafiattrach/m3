from abc import ABC, abstractmethod

from beartype import beartype

from m3.core.config import M3Config
from m3.m3 import M3


@beartype
class Preset(ABC):
    @classmethod
    @abstractmethod
    def create(cls, config: M3Config | None = None, **kwargs: dict) -> M3:
        """Create an M3 instance based on the provided configuration and kwargs."""
