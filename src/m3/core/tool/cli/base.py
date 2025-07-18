from abc import ABC, abstractmethod

import typer
from beartype import beartype
from beartype.typing import Any, Dict, TypedDict


class ToolConfig(TypedDict):
    env_vars: Dict[str, str]
    tool_params: Dict[str, Any]


@beartype
class BaseToolCLI(ABC):
    """Base class for M3 tool CLI implementations, defining tool-based command structure."""

    @classmethod
    @abstractmethod
    def get_app(cls) -> typer.Typer:
        raise NotImplementedError("Subclasses must provide Typer app.")

    @classmethod
    @abstractmethod
    def init(cls, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Subclasses must implement init as tool starting block."
        )

    @classmethod
    @abstractmethod
    def configure(cls) -> ToolConfig:
        raise NotImplementedError(
            "Subclasses must implement configure method to return ToolConfig."
        )

    @classmethod
    @abstractmethod
    def status(cls, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement status.")
