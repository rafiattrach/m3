import logging
import os
from pathlib import Path

from beartype import beartype

from m3.core.config import M3Config
from m3.core.preset.base import Preset
from m3.core.tool.backend.backends.bigquery import BigQueryBackend
from m3.core.tool.backend.backends.sqlite import SQLiteBackend
from m3.core.utils.exceptions import M3PresetError, M3ValidationError
from m3.m3 import M3
from m3.tools.mimic import MIMIC
from m3.tools.mimic.components.utils import get_default_database_path

logger = logging.getLogger(__name__)


@beartype
class DefaultM3Preset(Preset):
    @classmethod
    def create(
        cls,
        config: M3Config | None = None,
        **kwargs: dict,
    ) -> M3:
        _config = config or M3Config(env_vars=os.environ.copy())
        _backend = cls._determine_backend(_config)
        _backends = cls._create_backends(_config, _backend)
        _tool = MIMIC(backends=_backends, backend_key=_backend, config=_config)
        m3 = M3(config=_config).with_tool(_tool)
        cls._build_and_validate_m3(m3)
        return m3

    @classmethod
    def _determine_backend(cls, config: M3Config) -> str:
        _backend = config.get_env_var("M3_BACKEND", "sqlite").lower()
        logger.info(f"Creating default preset with backend: {_backend}")
        return _backend

    @classmethod
    def _create_backends(
        cls, config: M3Config, backend: str
    ) -> list[SQLiteBackend | BigQueryBackend]:
        if backend == "sqlite":
            db_path = config.get_env_var("M3_DB_PATH")
            default_db = get_default_database_path(config, "mimic-iv-demo")
            if default_db is None:
                raise M3PresetError("Cannot determine default DB path for preset")
            path = Path(db_path) if db_path else default_db
            logger.debug(f"Using SQLite DB path: {path}")
            return [SQLiteBackend(str(path))]
        elif backend == "bigquery":
            project_id = config.get_env_var("M3_PROJECT_ID", raise_if_missing=True)
            logger.debug(f"Using BigQuery project ID: {project_id}")
            return [BigQueryBackend(project_id)]
        else:
            raise M3PresetError(f"Invalid backend for preset: {backend}")

    @classmethod
    def _build_and_validate_m3(cls, m3: M3) -> None:
        try:
            m3.build()
            logger.info("Preset build successful")
        except M3ValidationError as e:
            logger.error(f"Preset build failed: {e}")
            raise M3PresetError("Preset build validation failed", details=str(e)) from e
