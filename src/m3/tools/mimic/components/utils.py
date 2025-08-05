import logging
from pathlib import Path

import yaml
from beartype import beartype
from beartype.typing import Any, Dict

from m3.core.config import M3Config
from m3.core.utils.exceptions import M3ValidationError

logger = logging.getLogger(__name__)


@beartype
def load_supported_datasets() -> Dict[str, Dict[str, Any]]:
    yaml_path = Path(__file__).parent.parent / "configurations" / "datasets.yaml"
    if not yaml_path.exists():
        raise RuntimeError(f"datasets.yaml not found at {yaml_path}")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


@beartype
def get_dataset_config(dataset_name: str) -> Dict[str, Any] | None:
    datasets = load_supported_datasets()
    return datasets.get(dataset_name.lower())


@beartype
def get_default_database_path(base_config: M3Config, dataset_name: str) -> Path | None:
    cfg = get_dataset_config(dataset_name)
    if not cfg:
        return None
    default_filename = cfg.get("default_db_filename", f"{dataset_name}.db")
    env_key = f"M3_{dataset_name.upper()}_DATA_DIR"
    default_dir_str = base_config.get_env_var(env_key)
    default_dir = (
        Path(default_dir_str)
        if default_dir_str
        else base_config.databases_dir / dataset_name
    )
    return default_dir / default_filename


@beartype
def get_dataset_raw_files_path(base_config: M3Config, dataset_name: str) -> Path | None:
    cfg = get_dataset_config(dataset_name)
    if not cfg:
        logger.warning(f"Unknown dataset: {dataset_name}")
        return None
    env_key = f"M3_{dataset_name.upper()}_RAW_DIR"
    raw_dir_str = base_config.get_env_var(env_key)
    path = (
        Path(raw_dir_str)
        if raw_dir_str
        else base_config.raw_files_dir / dataset_name.lower()
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


@beartype
def load_security_config() -> Dict[str, Any]:
    yaml_path = Path(__file__).parent.parent / "configurations" / "security.yaml"
    if not yaml_path.exists():
        raise RuntimeError(f"security.yaml not found at {yaml_path}")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


@beartype
def load_env_vars_config() -> Dict[str, Any]:
    yaml_path = Path(__file__).parent.parent / "configurations" / "env_vars.yaml"
    if not yaml_path.exists():
        raise M3ValidationError(f"env_vars.yaml not found at {yaml_path}")
    try:
        with open(yaml_path) as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError("Invalid YAML structure; expected a dictionary.")
        logger.debug(f"Loaded env_vars.yaml from {yaml_path}")
        return config
    except (yaml.YAMLError, ValueError) as e:
        raise M3ValidationError(f"Failed to load env_vars.yaml: {e}") from e


def validate_limit(limit: int) -> bool:
    return isinstance(limit, int) and 0 < limit <= 1000
