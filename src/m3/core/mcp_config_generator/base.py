from abc import ABC, abstractmethod

from beartype import beartype
from beartype.typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from m3.m3 import M3


@beartype
class MCPConfigGenerator(ABC):
    @classmethod
    @abstractmethod
    def generate(
        cls,
        m3: "M3",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> dict | str:
        """
        Generate an MCP configuration based on the provided M3 instance.
        """
