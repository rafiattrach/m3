import json
import logging
import os
import shutil
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from m3.core.mcp_config_generator.base import MCPConfigGenerator
from m3.core.utils.exceptions import M3ValidationError

logger = logging.getLogger(__name__)


@beartype
class ClaudeConfigGenerator(MCPConfigGenerator):
    @classmethod
    def generate(
        cls,
        m3: "m3.m3.M3",  # noqa: F821
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        _command = cls._get_command(command, m3)
        _module_name = cls._get_module_name(module_name, m3)
        _args = cls._get_args(args, m3, _module_name)
        _cwd = cls._get_cwd(cwd, m3)

        if not shutil.which(_command):
            raise M3ValidationError(f"Invalid command '{_command}': Not found on PATH.")
        if not os.path.isdir(_cwd):
            raise M3ValidationError(f"Invalid cwd '{_cwd}': Directory does not exist.")

        env = m3.config.env_vars.copy()
        if pipeline_config_path:
            env["M3_CONFIG_PATH"] = pipeline_config_path

        logger.debug(
            f"Generating Claude config with command='{_command}', args={_args}, cwd='{_cwd}', pipeline_config_path='{pipeline_config_path}'"
        )

        claude_config = {
            "mcpServers": {
                "m3": {
                    "command": _command,
                    "args": _args,
                    "cwd": _cwd,
                    "env": env,
                }
            }
        }

        cls._save_config(claude_config, save_path)

        logger.debug("Claude config generated successfully")
        return claude_config

    @staticmethod
    def _get_command(command: Optional[str], m3: "m3.m3.M3") -> str:  # noqa: F821
        if command is not None:
            return command

        if "VIRTUAL_ENV" in os.environ:
            venv_python = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)

        default_python = shutil.which("python") or shutil.which("python3") or "python"
        return m3.config.get_env_var("M3_COMMAND", default_python)

    @staticmethod
    def _get_module_name(module_name: Optional[str], m3: "m3.m3.M3") -> str:  # noqa: F821
        if module_name is not None:
            return module_name

        return m3.config.get_env_var("M3_MODULE", "m3.core.server")

    @staticmethod
    def _get_args(
        args: Optional[List[str]],
        m3: "m3.m3.M3",  # noqa: F821
        module_name: str,
    ) -> List[str]:
        if args is not None:
            return args

        return m3.config.get_env_var("M3_ARGS", ["-m", module_name])

    @staticmethod
    def _get_cwd(cwd: Optional[str], m3: "m3.m3.M3") -> str:  # noqa: F821
        if cwd is not None:
            return cwd

        return m3.config.get_env_var("M3_CWD", os.getcwd())

    @staticmethod
    def _save_config(config: Dict[str, Any], save_path: Optional[str]) -> None:
        if not save_path:
            claude_config_path = ClaudeConfigGenerator._get_claude_config_path()
            if claude_config_path:
                existing_config = {}
                if claude_config_path.exists():
                    with open(claude_config_path) as f:
                        existing_config = json.load(f)
                existing_config.setdefault("mcpServers", {}).update(
                    config["mcpServers"]
                )
                with open(claude_config_path, "w") as f:
                    json.dump(existing_config, f, indent=2)
                logger.info(
                    f"✅ Claude config merged and saved to {claude_config_path}."
                )
                return
            else:
                save_path = "m3_claude_config.json"

        with open(save_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"✅ Claude config saved to {save_path}")

    @staticmethod
    def _get_claude_config_path() -> Optional[Path]:
        home = Path.home()
        paths = [
            home
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",  # macOS
            home
            / "AppData"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json",  # Windows
            home / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
        ]
        return next((path for path in paths if path.parent.exists()), None)
