import logging
from collections.abc import Callable
from pathlib import Path

import yaml
from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from m3.core.config import M3Config
from m3.core.tool.base import BaseTool
from m3.core.utils.exceptions import M3ValidationError

logger = logging.getLogger(__name__)


@beartype
class M3ToolBuilder(BaseTool):
    """M3ToolBuilder: Intelligent tool generator for M3 ecosystem using knowledge base to create new tools."""

    def __init__(
        self,
        config: Optional[M3Config] = None,
        knowledge_path: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self.config = config or M3Config()
        default_knowledge_path = (
            Path(__file__).parent / "configurations" / "knowledge.yaml"
        )
        try:
            env_knowledge_path_str = self.config.get_env_var(
                "M3_TOOLBUILDER_KNOWLEDGE_PATH",
                default=None,
                raise_if_missing=False,
            )
            resolved_knowledge_path = knowledge_path or (
                Path(env_knowledge_path_str).resolve()
                if env_knowledge_path_str
                else default_knowledge_path.resolve()
            )
            self.knowledge_path = resolved_knowledge_path
            logger.info(f"Resolved knowledge path: {self.knowledge_path}")
            self.knowledge = self._load_knowledge()
        except (OSError, ValueError) as exc:
            logger.error(f"Failed to resolve knowledge path: {exc}")
            raise M3ValidationError(
                f"Invalid knowledge path configuration: {exc}"
            ) from exc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_path": str(self.knowledge_path),
        }

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> "M3ToolBuilder":
        knowledge_path: Optional[Path] = (
            Path(params["knowledge_path"]) if "knowledge_path" in params else None
        )
        return cls(
            knowledge_path=knowledge_path,
        )

    def actions(self) -> List[Callable]:
        return [
            self.about_m3_tools,
            self.best_practices,
            self.generate_tool,
        ]

    def generate_tool(
        self,
        tool_name: str,
        description: str,
        features: List[str],
    ) -> Dict[str, str]:
        try:
            best_practices = self.best_practices(tool_name)
            about_m3_tools = self.about_m3_tools()
            tool_code = self._generate_tool(tool_name, description, features)
            cli_code = self._generate_cli(tool_name)
            init_code = self._generate_init(tool_name)
            structure = self._generate_structure(tool_name, print_output=True)
            return {
                "best_practices": best_practices,
                "about_m3_tools": about_m3_tools,
                "tool_code": tool_code,
                "cli_code": cli_code,
                "init_code": init_code,
                "structure": structure,
            }
        except Exception as exc:
            logger.error(f"Error generating full tool for {tool_name}: {exc}")
            raise M3ValidationError(f"Failed to generate full tool: {exc}") from exc

    def _generate_tool(
        self,
        tool_name: str,
        description: str,
        features: List[str],
    ) -> str:
        tool_name_cap = tool_name.capitalize()
        formatted_features = "\n".join(f"    - {feature}" for feature in features)
        template = """
import logging
from collections.abc import Callable

from beartype import beartype
from beartype.typing import Any, Dict, List # No from typing, use beartype.typing, very important.

from m3.core.tool.base import BaseTool # Do not forget the .base

logger = logging.getLogger(__name__)

@beartype
class {tool_name_cap}(BaseTool):
    \"\"\"{description}\"\"\"

    def __init__(self) -> None:
        super().__init__()
        self.required_env_vars = {{}}  # Add required env vars here, e.g., {{"MY_VAR": None}} for mandatory, or default value

    def actions(self) -> List[Callable]:
        return []  # Add action functions here

    def initialize(self) -> None:
        # Optional: Add setup logic, e.g., backend initialization, connections
        # Features:
        # {features}
        pass

    def teardown(self) -> None:
        # Optional: Add cleanup logic, e.g., close connections, release resources
        pass

    def to_dict(self) -> Dict[str, Any]:
        # Implement serialization: return dictionary of init params/state for saving
        return {{}}

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> "{tool_name_cap}":
        # Implement deserialization: reconstruct instance from params
        return cls()
"""
        code = template.format(
            tool_name_cap=tool_name_cap,
            description=description,
            features=formatted_features,
        )
        return code.strip()

    def _generate_cli(
        self,
        tool_name: str,
    ) -> str:
        tool_name_cap = tool_name.capitalize()
        tool_name_lower = tool_name.lower()
        template = """
import typer
from beartype import beartype
from beartype.typing import Optional
from rich.console import Console

from m3.core.tool.cli.base import BaseToolCLI, ToolConfig

console = Console()

@beartype
class {tool_name_cap}CLI(BaseToolCLI):
    \"\"\"{tool_name_cap} Command Line Interface.\"\"\"

    @classmethod
    def get_app(cls) -> Optional[typer.Typer]:
        app = typer.Typer(
            help="{tool_name_cap} tool commands.",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        app.command(help="Initialize the {tool_name_cap} tool.")(cls.init)
        app.command(help="Configure the {tool_name_cap} tool.")(cls.configure)
        app.command(help="Display the current status of the {tool_name_cap} tool.")(cls.status)
        return app

    @classmethod
    def init(cls) -> dict:
        pass  # Implement init logic

    @classmethod
    def configure(cls) -> ToolConfig:
        pass  # Implement configure logic

    @classmethod
    def status(cls, verbose: bool = False) -> None:
        pass  # Implement status logic
"""
        code = template.format(
            tool_name_cap=tool_name_cap,
            tool_name_lower=tool_name_lower,
        )
        return code.strip()

    def _generate_init(
        self,
        tool_name: str,
    ) -> str:
        tool_name_cap = tool_name.capitalize()
        tool_name_lower = tool_name.lower()
        template = """
from .{tool_name_lower} import {tool_name_cap}
from .cli import {tool_name_cap}CLI

__all__ = [
    "{tool_name_cap}",
    "{tool_name_cap}CLI",
]
"""
        code = template.format(
            tool_name_cap=tool_name_cap,
            tool_name_lower=tool_name_lower,
        )
        return code.strip()

    def about_m3_tools(self) -> str:
        return "\n\n".join(
            [
                self.knowledge["principles"]["idea_behind_m3_tools"],
                self.knowledge["principles"]["importance_of_architecture"],
                self.knowledge["principles"]["what_is_a_tool"],
            ]
        )

    def best_practices(self, tool_name: str) -> str:
        practices = "\n\n".join(
            [
                self.knowledge["principles"]["python_best_practices"],
            ]
        )
        practices = practices.format(tool_name=tool_name)
        return practices

    def _generate_structure(self, tool_name: str, print_output: bool = False) -> str:
        tool_name_lower = tool_name.lower()
        template = """
Recommended directory structure and file names for the '{tool_name_cap}' tool:

m3/
└── tools/
    └── {tool_name_lower}/
        ├── __init__.py   # Exports the tool and CLI classes
        ├── {tool_name_lower}.py   # Main tool class implementation
        ├── cli.py   # CLI class for command-line interactions
        └── configurations/   # Optional directory for YAML configs
            └── knowledge.yaml   # Or other config files as needed; prefer YAML over hardcoding in code
"""
        structure = template.format(
            tool_name_cap=tool_name.capitalize(),
            tool_name_lower=tool_name_lower,
        ).strip()
        if print_output:
            logger.info(
                f"Generated directory structure for '{tool_name}':\n{structure}"
            )
        return structure

    def load_m3_codebase(self) -> str:
        codebase_path = self.knowledge_path.parent / "tools_codebase.txt"
        if not codebase_path.exists():
            raise M3ValidationError(f"Tools codebase file not found at {codebase_path}")
        try:
            return codebase_path.read_text()
        except OSError as os_error:
            logger.error(f"Failed to read tools codebase file: {os_error}")
            raise M3ValidationError(
                f"File access error for tools codebase: {os_error}"
            ) from os_error

    def _load_knowledge(self) -> Dict[str, Any]:
        if not self.knowledge_path.exists():
            raise M3ValidationError(
                f"Knowledge YAML not found at {self.knowledge_path}"
            )
        try:
            with open(self.knowledge_path) as file_handle:
                return yaml.safe_load(file_handle)
        except yaml.YAMLError as yaml_error:
            logger.error(
                f"Failed to parse knowledge YAML at {self.knowledge_path}: {yaml_error}"
            )
            raise M3ValidationError(
                f"Invalid YAML in knowledge file: {yaml_error}"
            ) from yaml_error
        except OSError as os_error:
            logger.error(
                f"Failed to open knowledge file at {self.knowledge_path}: {os_error}"
            )
            raise M3ValidationError(
                f"File access error for knowledge YAML: {os_error}"
            ) from os_error
