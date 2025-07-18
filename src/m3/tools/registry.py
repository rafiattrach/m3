import importlib
import inspect
import logging
import os

from beartype import beartype

from m3.core.tool.base import BaseTool
from m3.core.tool.cli.base import BaseToolCLI
from m3.core.utils.exceptions import M3ValidationError

logger = logging.getLogger(__name__)

TOOLS_DIR = os.path.dirname(__file__)

ALL_TOOLS = {}


@beartype
def _initialize() -> None:
    """
    Automatically discover and register tools from subdirectories in tools/.
    """
    for entry in os.scandir(TOOLS_DIR):
        if entry.is_dir() and not entry.name.startswith("_"):
            tool_name = entry.name.lower()
            try:
                main_module_path = f"m3.tools.{tool_name}.{tool_name}"
                main_module = importlib.import_module(main_module_path)

                tool_classes = [
                    obj
                    for name, obj in inspect.getmembers(main_module)
                    if inspect.isclass(obj)
                    and issubclass(obj, BaseTool)
                    and obj != BaseTool
                ]
                if len(tool_classes) != 1:
                    raise M3ValidationError(
                        f"Tool '{tool_name}' must have exactly one subclass of BaseTool in {main_module_path}.py. Found: {len(tool_classes)}"
                    )
                tool_class = tool_classes[0]

                cli_module_path = f"m3.tools.{tool_name}.cli"
                cli_module = importlib.import_module(cli_module_path)

                cli_classes = [
                    obj
                    for name, obj in inspect.getmembers(cli_module)
                    if inspect.isclass(obj)
                    and issubclass(obj, BaseToolCLI)
                    and obj != BaseToolCLI
                ]
                if len(cli_classes) != 1:
                    raise M3ValidationError(
                        f"Tool '{tool_name}' must have exactly one subclass of BaseToolCLI in {cli_module_path}.py. Found: {len(cli_classes)}"
                    )

                ALL_TOOLS[tool_name] = tool_class
            except ImportError as e:
                logger.warning(
                    f"Failed to import modules for tool '{tool_name}': {e!s}. Skipping registration (components not fully available)."
                )
            except M3ValidationError as e:
                logger.warning(
                    f"Validation failed for tool '{tool_name}': {e!s}. Skipping registration (BaseTool or BaseToolCLI not available as required)."
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error discovering tool '{tool_name}': {e!s}. Skipping registration.",
                    exc_info=True,
                )


_initialize()
