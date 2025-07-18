import logging
import os
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from m3.core.tool.base import BaseTool
from m3.core.utils.exceptions import M3ConfigError
from m3.core.utils.logging import setup_logging

logger = logging.getLogger(__name__)


@beartype
class M3Config:
    def __init__(
        self,
        log_level: str = "INFO",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> None:
        self.log_level = log_level
        self.env_vars = env_vars or {}
        self._set_paths()
        self._apply_config()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_level": self.log_level,
            "env_vars": self.env_vars.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "M3Config":
        try:
            return cls(
                log_level=data["log_level"],
                env_vars=data["env_vars"],
            )
        except KeyError as e:
            raise M3ConfigError(f"Missing required config key: {e}") from e

    def get_env_var(
        self, key: str, default: Optional[Any] = None, raise_if_missing: bool = False
    ) -> Any:
        value = self.env_vars.get(key, os.getenv(key, default))
        if value is None and raise_if_missing:
            raise M3ConfigError(
                f"Missing required env var: {key}",
                details="Check your environment variables or config initialization.",
            )
        logger.debug(f"Accessed env var '{key}': {'[set]' if value else '[unset]'}")
        return value or ""

    def validate_for_tools(self, tools: List[BaseTool]) -> None:
        errors = []
        for tool in tools:
            for req_key, req_default in tool.required_env_vars.items():
                prefixed_key = f"{tool.__class__.__name__.upper()}_{req_key}"
                if prefixed_key in self.env_vars or prefixed_key in os.environ:
                    key_for_error_check = prefixed_key
                else:
                    key_for_error_check = req_key
                error_message = self._get_env_var_error(
                    key_for_error_check, req_default
                )
                if error_message:
                    errors.append(
                        f"Config validation failed for tool '{tool.__class__.__name__}': {error_message}"
                    )
        if errors:
            raise M3ConfigError("\n".join(errors))
        logger.info(f"Validated config for {len(tools)} tools.")

    def merge_env(self, new_env: Dict[str, str], prefix: str = "") -> None:
        for key, value in new_env.items():
            prefixed_key = f"{prefix}{key}" if prefix else key
            if prefixed_key in self.env_vars and self.env_vars[prefixed_key] != value:
                raise M3ConfigError(
                    f"Env conflict: {prefixed_key} ({self.env_vars[prefixed_key]} vs {value})"
                )
            self.env_vars[prefixed_key] = value
            logger.debug(f"Merged env: {prefixed_key} = {value}")

    def _set_paths(self) -> None:
        self.project_root = self._get_project_root()
        self.data_dir = self._get_data_dir()
        self.databases_dir = self.data_dir / "databases"
        self.raw_files_dir = self.data_dir / "raw_files"

    def _get_project_root(self) -> Path:
        package_root = Path(__file__).resolve().parents[3]
        if (package_root / "pyproject.toml").exists():
            return package_root
        return Path.home()

    def _get_data_dir(self) -> Path:
        data_dir_str = self.get_env_var("M3_DATA_DIR")
        if data_dir_str:
            return Path(data_dir_str)
        return self.project_root / "m3_data"

    def _apply_config(self) -> None:
        try:
            setup_logging(level=self.log_level)
        except ValueError as e:
            raise M3ConfigError(
                f"Invalid log level: {self.log_level}",
                details="Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
            ) from e

        for key, value in self.env_vars.items():
            os.environ[key] = value

    def _get_env_var_error(self, key: str, default: Optional[str]) -> Optional[str]:
        try:
            self.get_env_var(key, default=default, raise_if_missing=default is None)
            return None
        except M3ConfigError as e:
            return str(e)
