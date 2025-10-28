import logging
from pathlib import Path
from typing import Literal

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

DEFAULT_DATABASES_DIR = _PROJECT_DATA_DIR / "databases"
DEFAULT_RAW_FILES_DIR = _PROJECT_DATA_DIR / "raw_files"


# --------------------------------------------------
# Dataset configurations (add more entries as needed)
# --------------------------------------------------
SUPPORTED_DATASETS = {
    "mimic-iv-demo": {
        "file_listing_url": "https://physionet.org/files/mimic-iv-demo/2.2/",
        "subdirectories_to_scan": ["hosp", "icu"],
        "default_db_filename": "mimic_iv_demo.db",
        "default_duckdb_filename": "mimic_iv_demo.duckdb",
        "primary_verification_table": "hosp_admissions",
    },
    "mimic-iv-full": {
        "file_listing_url": None,
        "subdirectories_to_scan": ["hosp", "icu"],
        "default_db_filename": "mimic_iv_full.db",
        "default_duckdb_filename": "mimic_iv_full.duckdb",
        "primary_verification_table": "hosp_admissions",
    },
}


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def get_dataset_config(dataset_name: str) -> dict | None:
    """Retrieve the configuration for a given dataset (case-insensitive)."""
    return SUPPORTED_DATASETS.get(dataset_name.lower())


def get_default_database_path(dataset_name: str, engine: Literal["sqlite", "duckdb"] = "sqlite") -> Path | None:
    """
    Return the default local DB path for a given dataset and engine,
    under <project_root>/m3_data/databases/.
    """
    cfg = get_dataset_config(dataset_name)

    if not cfg:
        logger.warning(f"Unknown dataset, cannot determine default DB path: {dataset_name}")
        return None

    DEFAULT_DATABASES_DIR.mkdir(parents=True, exist_ok=True)

    db_fname = cfg.get("default_db_filename") if engine == "sqlite" else cfg.get("default_duckdb_filename")
    if not db_fname:
        logger.warning(f"Missing default filename for dataset: {dataset_name}")
        return None
        
    return DEFAULT_DATABASES_DIR / db_fname

def get_dataset_raw_files_path(dataset_name: str) -> Path | None:
    """
    Return the raw-file storage path for a dataset,
    under <project_root>/m3_data/raw_files/<dataset_name>/.
    """
    cfg = get_dataset_config(dataset_name)
    if cfg:
        path = DEFAULT_RAW_FILES_DIR / dataset_name.lower()
        path.mkdir(parents=True, exist_ok=True)
        return path

    logger.warning(f"Unknown dataset, cannot determine raw path: {dataset_name}")
    return None
