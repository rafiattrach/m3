import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Any

from m3.datasets import DatasetDefinition, DatasetRegistry

APP_NAME = "m3"

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(APP_NAME)


# -------------------------------------------------------------------
# Data directory rooted at project root (two levels up from this file)
# -------------------------------------------------------------------
def _get_project_root() -> Path:
    """
    Determine project root:
    - If cloned repo: use repository root (two levels up from this file)
    - If pip installed: ALWAYS use home directory
    """
    package_root = Path(__file__).resolve().parents[2]

    # Check if we're in a cloned repository (has pyproject.toml at root)
    if (package_root / "pyproject.toml").exists():
        return package_root

    # Pip installed: ALWAYS use home directory (simple and consistent)
    return Path.home()


_PROJECT_ROOT = _get_project_root()
_PROJECT_DATA_DIR = _PROJECT_ROOT / "m3_data"

_DEFAULT_DATABASES_DIR = _PROJECT_DATA_DIR / "databases"
_DEFAULT_PARQUET_DIR = _PROJECT_DATA_DIR / "parquet"
_RUNTIME_CONFIG_PATH = _PROJECT_DATA_DIR / "config.json"
_CUSTOM_DATASETS_DIR = _PROJECT_DATA_DIR / "datasets"


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def _load_custom_datasets():
    """Load custom dataset definitions from JSON files in m3_data/datasets/."""
    if not _CUSTOM_DATASETS_DIR.exists():
        logger.warning(
            f"Custom datasets directory does not exist: {_CUSTOM_DATASETS_DIR}"
        )
        return

    for f in _CUSTOM_DATASETS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            # Basic validation/loading
            ds = DatasetDefinition(**data)
            DatasetRegistry.register(ds)
        except Exception as e:
            logger.warning(f"Failed to load custom dataset from {f}: {e}")


def get_dataset_config(dataset_name: str) -> dict | None:
    """Retrieve the configuration for a given dataset (case-insensitive)."""
    # Ensure custom datasets are loaded
    _load_custom_datasets()

    ds = DatasetRegistry.get(dataset_name.lower())
    return dataclasses.asdict(ds) if ds else None


def get_default_database_path(dataset_name: str) -> Path | None:
    """
    Return the default local DuckDB path for a given dataset,
    under <project_root>/m3_data/databases/.
    """
    cfg = get_dataset_config(dataset_name)
    if not cfg:
        logger.warning(
            f"Unknown dataset, cannot determine default DB path: {dataset_name}"
        )
        return None

    _DEFAULT_DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    db_fname = cfg.get("default_duckdb_filename")
    if not db_fname:
        logger.warning(f"Missing default DuckDB filename for dataset: {dataset_name}")
        return None
    return _DEFAULT_DATABASES_DIR / db_fname


def get_dataset_parquet_root(dataset_name: str) -> Path | None:
    """
    Return the Parquet root for a dataset under
    <project_root>/m3_data/parquet/<dataset_name>/.
    """
    cfg = get_dataset_config(dataset_name)
    if not cfg:
        logger.warning(
            f"Unknown dataset, cannot determine Parquet root: {dataset_name}"
        )
        return None
    path = _DEFAULT_PARQUET_DIR / dataset_name.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


# -----------------------------
# Runtime config (active dataset)
# -----------------------------
def _ensure_data_dirs():
    _DEFAULT_DATABASES_DIR.mkdir(parents=True, exist_ok=True)
    _DEFAULT_PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    _PROJECT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CUSTOM_DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def _get_default_runtime_config() -> dict:
    # We initialize with empty overrides.
    # Paths are derived dynamically from registry unless overridden here.
    return {
        "active_dataset": None,
        "duckdb_paths": {},  # Map dataset_name -> path
        "parquet_roots": {},  # Map dataset_name -> path
    }


def load_runtime_config() -> dict:
    """Load runtime configuration from <project_root>/m3_data/config.json or use default"""
    _ensure_data_dirs()
    if _RUNTIME_CONFIG_PATH.exists():
        try:
            return json.loads(_RUNTIME_CONFIG_PATH.read_text())
        except Exception:
            logger.warning("Could not parse runtime config; using defaults")
    # defaults
    return _get_default_runtime_config()


def save_runtime_config(cfg: dict) -> None:
    _ensure_data_dirs()
    _RUNTIME_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def _has_parquet_files(path: Path | None) -> bool:
    return bool(path and path.exists() and any(path.rglob("*.parquet")))


def detect_available_local_datasets() -> dict[str, dict[str, Any]]:
    """Return presence flags for all registered datasets."""
    _load_custom_datasets()
    cfg = load_runtime_config()

    results = {}

    # Check all registered datasets
    for ds in DatasetRegistry.list_all():
        name = ds.name

        # Determine paths (check config overrides first)
        parquet_root_str = cfg.get("parquet_roots", {}).get(name)
        parquet_root = (
            Path(parquet_root_str)
            if parquet_root_str
            else get_dataset_parquet_root(name)
        )

        db_path_str = cfg.get("duckdb_paths", {}).get(name)
        db_path = Path(db_path_str) if db_path_str else get_default_database_path(name)

        results[name] = {
            "parquet_present": _has_parquet_files(parquet_root),
            "db_present": bool(db_path and db_path.exists()),
            "parquet_root": str(parquet_root) if parquet_root else "",
            "db_path": str(db_path) if db_path else "",
        }

    return results


def get_active_dataset() -> str | None:
    """Get the active dataset name."""
    # Ensure custom datasets are loaded so they can be found in the registry
    _load_custom_datasets()

    # Priority 1: Environment variable
    env_dataset = os.getenv("M3_DATASET")
    if env_dataset:
        return env_dataset

    # Priority 2: Config file
    cfg = load_runtime_config()
    active = cfg.get("active_dataset")

    # Priority 3: Auto-detect default: prefer demo, then full
    if not active:
        availability = detect_available_local_datasets()
        if availability.get("mimic-iv-demo", {}).get("parquet_present"):
            active = "mimic-iv-demo"
        elif availability.get("mimic-iv-full", {}).get("parquet_present"):
            active = "mimic-iv-full"
        else:
            active = None

    return active


def set_active_dataset(choice: str) -> None:
    # Allow registered names
    valid_names = {ds.name for ds in DatasetRegistry.list_all()}

    if choice not in valid_names:
        # It might be a new custom dataset not yet loaded in this process?
        # We'll allow it if it's in the registry now.
        _load_custom_datasets()
        if not DatasetRegistry.get(choice):
            raise ValueError(
                f"active_dataset must be a registered dataset. Got: {choice}"
            )

    cfg = load_runtime_config()
    cfg["active_dataset"] = choice
    save_runtime_config(cfg)


def get_duckdb_path_for(choice: str) -> Path | None:
    return get_default_database_path(choice)


def get_parquet_root_for(choice: str) -> Path | None:
    return get_dataset_parquet_root(choice)
