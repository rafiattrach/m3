import json
import logging
from pathlib import Path

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

# --------------------------------------------------
# Dataset configurations (add more entries as needed)
# --------------------------------------------------
SUPPORTED_DATASETS = {
    "mimic-iv-demo": {
        "file_listing_url": "https://physionet.org/files/mimic-iv-demo/2.2/",
        "subdirectories_to_scan": ["hosp", "icu"],
        "default_duckdb_filename": "mimic_iv_demo.duckdb",
        "primary_verification_table": "hosp_admissions",
    },
    "mimic-iv-full": {
        "file_listing_url": None,
        "subdirectories_to_scan": ["hosp", "icu"],
        "default_duckdb_filename": "mimic_iv_full.duckdb",
        "primary_verification_table": "hosp_admissions",
    },
}

# Dataset name aliases used on the CLI
CLI_DATASET_ALIASES = {
    "demo": "mimic-iv-demo",
    "full": "mimic-iv-full",
}


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def get_dataset_config(dataset_name: str) -> dict | None:
    """Retrieve the configuration for a given dataset (case-insensitive)."""
    return SUPPORTED_DATASETS.get(dataset_name.lower())


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


def _get_default_runtime_config() -> dict:
    return {
        "active_dataset": None,
        "duckdb_paths": {
            "demo": str(get_default_database_path("mimic-iv-demo") or ""),
            "full": str(get_default_database_path("mimic-iv-full") or ""),
        },
        "parquet_roots": {
            "demo": str(get_dataset_parquet_root("mimic-iv-demo") or ""),
            "full": str(get_dataset_parquet_root("mimic-iv-full") or ""),
        },
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


def detect_available_local_datasets() -> dict:
    """Return presence flags for demo/full based on Parquet roots and DuckDB files."""
    cfg = load_runtime_config()
    demo_parquet_path = (
        Path(cfg["parquet_roots"]["demo"])
        if cfg["parquet_roots"]["demo"]
        else get_dataset_parquet_root("mimic-iv-demo")
    )
    full_parquet_path = (
        Path(cfg["parquet_roots"]["full"])
        if cfg["parquet_roots"]["full"]
        else get_dataset_parquet_root("mimic-iv-full")
    )
    demo_db_path = (
        Path(cfg["duckdb_paths"]["demo"])
        if cfg["duckdb_paths"]["demo"]
        else get_default_database_path("mimic-iv-demo")
    )
    full_db_path = (
        Path(cfg["duckdb_paths"]["full"])
        if cfg["duckdb_paths"]["full"]
        else get_default_database_path("mimic-iv-full")
    )
    return {
        "demo": {
            "parquet_present": _has_parquet_files(demo_parquet_path),
            "db_present": bool(demo_db_path and demo_db_path.exists()),
            "parquet_root": str(demo_parquet_path) if demo_parquet_path else "",
            "db_path": str(demo_db_path) if demo_db_path else "",
        },
        "full": {
            "parquet_present": _has_parquet_files(full_parquet_path),
            "db_present": bool(full_db_path and full_db_path.exists()),
            "parquet_root": str(full_parquet_path) if full_parquet_path else "",
            "db_path": str(full_db_path) if full_db_path else "",
        },
    }


def get_active_dataset() -> str | None:
    cfg = load_runtime_config()
    active = cfg.get("active_dataset")
    if active in CLI_DATASET_ALIASES:
        return CLI_DATASET_ALIASES[active]
    if active == "bigquery":
        return "bigquery"
    # Auto-detect default: prefer demo, then full
    availability = detect_available_local_datasets()
    if availability["demo"]["parquet_present"]:
        return CLI_DATASET_ALIASES["demo"]
    if availability["full"]["parquet_present"]:
        return CLI_DATASET_ALIASES["full"]

    logger.warning("Unknown active_dataset value in config: %s", active)
    return None


def set_active_dataset(choice: str) -> None:
    if choice not in ("demo", "full", "bigquery"):
        raise ValueError("active_dataset must be one of: demo, full, bigquery")
    cfg = load_runtime_config()
    cfg["active_dataset"] = choice
    save_runtime_config(cfg)


def get_duckdb_path_for(choice: str) -> Path | None:
    key = "mimic-iv-demo" if choice == "demo" else "mimic-iv-full"
    return get_default_database_path(key) if choice in ("demo", "full") else None


def get_parquet_root_for(choice: str) -> Path | None:
    key = "mimic-iv-demo" if choice == "demo" else "mimic-iv-full"
    return get_dataset_parquet_root(key) if choice in ("demo", "full") else None
