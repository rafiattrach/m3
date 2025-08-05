import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from beartype import beartype
from beartype.typing import Any, Dict, Optional

from m3.core.tool.backend.base import BackendBase
from m3.core.utils.exceptions import M3InitializationError

logger = logging.getLogger(__name__)


@beartype
class BaseTool(ABC):
    """Base class for M3 tools, providing shared structure for initialization and lifecycle."""

    def __init__(self) -> None:
        self.required_env_vars: Dict[str, Optional[str]] = {}
        self.backends: Dict[str, BackendBase] = {}

    @abstractmethod
    def actions(self) -> list[Callable]:
        raise NotImplementedError(
            "Subclasses must implement 'actions' method to return list of callable tools/functions."
        )

    def initialize(self) -> None:
        try:
            for backend in self.backends.values():
                backend.initialize()
        except Exception as e:
            raise M3InitializationError(
                "Tool initialization failed during backend setup", details=str(e)
            ) from e
        self._initialize()

    def teardown(self) -> None:
        self._teardown()
        try:
            for backend in self.backends.values():
                backend.teardown()
        except Exception as e:
            logger.error(f"Teardown error: {e}", exc_info=True)

    def post_load(self) -> None:
        self._post_load()
        self.initialize()

    def _initialize(self) -> None:  # noqa: B027
        pass

    def _teardown(self) -> None:  # noqa: B027
        pass

    def _post_load(self) -> None:  # noqa: B027
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "Subclasses must implement 'to_dict' method to serialize initialization parameters."
        )

    @classmethod
    @abstractmethod
    def from_dict(cls, params: Dict[str, Any]) -> "BaseTool":
        raise NotImplementedError(
            "Subclasses must implement 'from_dict' method to reconstruct from serialized parameters."
        )
