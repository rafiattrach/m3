import logging
from abc import ABC, abstractmethod

from beartype import beartype
from beartype.typing import Any, Dict

logger = logging.getLogger(__name__)


@beartype
class BackendBase(ABC):
    """Base abstract class for M3 tool various backends needs."""

    @abstractmethod
    def execute(self, query: str) -> str:
        raise NotImplementedError("Subclasses must implement 'execute' method.")

    @abstractmethod
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement 'initialize' method.")

    @abstractmethod
    def teardown(self) -> None:
        raise NotImplementedError("Subclasses must implement 'teardown' method.")

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement 'to_dict' method.")

    @classmethod
    @abstractmethod
    def from_dict(cls, params: Dict[str, Any]) -> "BackendBase":
        raise NotImplementedError("Subclasses must implement 'from_dict' method.")

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)
