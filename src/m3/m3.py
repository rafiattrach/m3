import json
import logging
import os

from beartype import beartype
from beartype.typing import Any, List, Optional, Union
from fastmcp import FastMCP
from thefuzz import process

from m3.core.config import M3Config
from m3.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS
from m3.core.tool.base import BaseTool
from m3.core.utils.exceptions import (
    M3BuildError,
    M3ConfigError,
    M3InitializationError,
    M3PresetError,
    M3ValidationError,
)
from m3.tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)


@beartype
class M3:
    """M3 core for composing MCP-M3 supported tools with ease-of-use using chaining-style API.

    This class provides an API to configure M3 with config and tools. Tools supported and validated by M3.

    Examples:
        >>> m3 = (
        ...     M3()
        ...     .with_config(M3Config(log_level="DEBUG")) # More is available, refer to M3Config's documentation
        ...     .with_tool(MIMIC(backends=[SQLiteBackend(path="db.sqlite")])) # More is available, refer to MIMIC's documentation
        ...     # more chaining methods exists (e.g. with_tools, with_preset, etc.),
        ... )
        >>> config = m3.build(type="claude")  # Setup M3 directly into Claude Desktop MCP
        >>> m3.save("m3_pipeline.json")  # Serialize your just-created M3 pipeline to JSON
        >>> loaded_m3 = M3.load("m3_pipeline.json").run()  # Load it later / share it to colleagues and start MCP server
    """

    def __init__(
        self,
        config: Optional[M3Config] = None,
        mcp: Optional[FastMCP] = None,
    ) -> None:
        self.config = config or M3Config()
        self.tools = []
        self.mcp = mcp
        self._mcp_config_generators = ALL_MCP_CONFIG_GENERATORS
        self._built = False

    def with_config(self, config: M3Config) -> "M3":
        new = M3(
            config=config,
            mcp=self.mcp,
        )
        new.tools = self.tools[:]
        return new

    def with_tool(self, tool: BaseTool) -> "M3":
        new = M3(
            config=self.config,
            mcp=self.mcp,
        )
        new.tools = [*self.tools, tool]
        return new

    def with_tools(self, tools: List[BaseTool]) -> "M3":
        new = M3(
            config=self.config,
            mcp=self.mcp,
        )
        new.tools = self.tools + tools
        return new

    def with_preset(self, preset_name: str, **kwargs: Any) -> "M3":
        from m3.core.preset.registry import ALL_PRESETS

        if preset_name not in ALL_PRESETS:
            available_presets = list(ALL_PRESETS.keys())
            best_match, score = process.extractOne(preset_name, available_presets) or (
                None,
                0,
            )
            suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
            raise M3PresetError(f"Unknown preset: {preset_name}.{suggestion_text}")
        preset_class = ALL_PRESETS[preset_name]
        config = kwargs.pop("config", self.config)
        try:
            preset_m3 = preset_class.create(config=config, **kwargs)
        except Exception as e:
            raise M3PresetError(
                f"Failed to create preset '{preset_name}'", details=str(e)
            ) from e
        merged_tools = self.tools + preset_m3.tools
        new = M3(
            config=preset_m3.config,
            mcp=preset_m3.mcp or self.mcp,
        )
        new.tools = merged_tools
        return new

    def build(
        self,
        type: str = "fastmcp",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Union[dict, str]:
        try:
            self._validate()
            self._initialize_mcp()
            self._initialize_tools()
            self._register_actions()
            self._built = True
            return self._generate_config(
                type,
                command=command,
                args=args,
                cwd=cwd,
                module_name=module_name,
                pipeline_config_path=pipeline_config_path,
                save_path=save_path,
            )
        except Exception as e:
            raise M3BuildError("Build process failed", details=str(e)) from e

    def run(self) -> None:
        if not self._built:
            raise M3BuildError("Call .build() before .run()")
        try:
            if not self.mcp:
                raise M3InitializationError("MCP not initialized")
            logger.info("Starting MCP server...")
            self.mcp.run()  # type: ignore
        except Exception as e:
            logger.error(f"Failed to run MCP server: {e}")
            raise
        finally:
            self._teardown_tools()
            logger.info("MCP server shutdown complete.")

    def save(self, path: str) -> None:
        if not self._built:
            raise M3BuildError("Call .build() before .save()")
        try:
            config_data = {
                "config": self.config.to_dict(),
                "tools": [
                    {"type": tool.__class__.__name__.lower(), "params": tool.to_dict()}
                    for tool in self.tools
                ],
            }
            with open(path, "w") as f:
                json.dump(config_data, f, indent=4)
            logger.info(f"✅ Saved pipeline config to {path}.")

        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error: {e}")
            raise M3BuildError(f"Failed to serialize: {e}") from e
        except OSError as e:
            logger.error(f"File write error: {e}")
            raise

    @classmethod
    def load(cls, path: str) -> "M3":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found: {path}")
        try:
            with open(path) as f:
                data = json.load(f)
            config = M3Config.from_dict(data["config"])
            instance = cls(config=config)
            for tool_data in data.get("tools", []):
                tool_type = tool_data["type"]
                if tool_type not in ALL_TOOLS:
                    raise M3ValidationError(f"Unknown tool type: {tool_type}")
                tool_cls = ALL_TOOLS[tool_type]
                tool = tool_cls.from_dict(tool_data["params"])
                instance = instance.with_tool(tool)
            instance._post_load()
            instance._built = True
            logger.info(f"Pipeline loaded from {path}")
            return instance
        except (json.JSONDecodeError, KeyError, ValueError, M3ConfigError) as e:
            logger.error(f"Config load error: {e}")
            raise M3ValidationError(f"Invalid config: {e}") from e
        except OSError as e:
            logger.error(f"File read error: {e}")
            raise

    def _validate(self) -> None:
        if not self.tools:
            raise M3ValidationError("At least one tool must be added.")
        self.config.validate_for_tools(self.tools)

    def _initialize_mcp(self) -> None:
        if not self.mcp:
            self.mcp = FastMCP("m3")

    def _initialize_tools(self) -> None:
        for tool in self.tools:
            try:
                tool.initialize()
            except Exception as e:
                raise M3InitializationError(
                    f"Tool initialization failed for {tool.__class__.__name__}",
                    details=str(e),
                ) from e

    def _register_actions(self) -> None:
        actions = [action for tool in self.tools for action in tool.actions()]
        for action in actions:
            self.mcp.tool()(action)  # type: ignore

    def _generate_config(
        self,
        type: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Union[dict, str]:
        if type not in self._mcp_config_generators:
            available_types = list(self._mcp_config_generators.keys())
            best_match, score = process.extractOne(type, available_types) or (None, 0)
            suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
            raise M3ValidationError(f"Unknown config type: {type}.{suggestion_text}")
        generator_class = self._mcp_config_generators[type]
        return generator_class.generate(
            self,
            command=command,
            args=args,
            cwd=cwd,
            module_name=module_name,
            pipeline_config_path=pipeline_config_path,
            save_path=save_path,
        )

    def _teardown_tools(self) -> None:
        for tool in self.tools:
            if hasattr(tool, "backends"):
                for backend in tool.backends.values():
                    backend.teardown()

    def _post_load(self) -> None:
        for tool in self.tools:
            tool.post_load()
        if self.mcp:
            self._register_actions()
        self._built = True
