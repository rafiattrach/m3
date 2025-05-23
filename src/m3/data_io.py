from pathlib import Path
from urllib.parse import urljoin, urlparse

import polars as pl
import requests
import typer
from bs4 import BeautifulSoup

from m3.config import get_dataset_config, get_dataset_raw_files_path, logger

COMMON_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


def _download_single_file(
    url: str, target_filepath: Path, session: requests.Session
) -> bool:
    """Downloads a single file with progress tracking."""
    logger.debug(f"Attempting to download {url} to {target_filepath}...")
    try:
        response = session.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        file_display_name = target_filepath.name

        target_filepath.parent.mkdir(parents=True, exist_ok=True)
        with (
            open(target_filepath, "wb") as f,
            typer.progressbar(
                length=total_size, label=f"Downloading {file_display_name}"
            ) as progress,
        ):
            for chunk in response.iter_content(chunk_size=8192):  # Standard chunk size
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
        logger.info(f"Successfully downloaded: {file_display_name}")
        return True
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status == 404:
            logger.error(f"Download failed (404 Not Found): {url}.")
        else:
            logger.error(f"HTTP error {status} downloading {url}: {e.response.reason}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout occurred while downloading {url}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"A network or request error occurred downloading {url}: {e}")
    except OSError as e:
        logger.error(f"File system error writing {target_filepath}: {e}")

    # If download failed, attempt to remove partially downloaded file
    if target_filepath.exists():
        try:
            target_filepath.unlink()
        except OSError as e:
            logger.error(f"Could not remove incomplete file {target_filepath}: {e}")
    return False


def _scrape_urls_from_html_page(
    page_url: str, session: requests.Session, file_suffix: str = ".csv.gz"
) -> list[str]:
    """Scrapes a webpage for links ending with a specific suffix."""
    found_urls = []
    logger.debug(f"Scraping for '{file_suffix}' links on page: {page_url}")
    try:
        page_response = session.get(page_url, timeout=30)
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.content, "html.parser")
        for link_tag in soup.find_all("a", href=True):
            href_path = link_tag["href"]
            # Basic validation of the link
            if (
                href_path.endswith(file_suffix)
                and not href_path.startswith(("?", "#"))
                and ".." not in href_path
            ):
                absolute_url = urljoin(page_url, href_path)
                found_urls.append(absolute_url)
    except requests.exceptions.RequestException as e:
        logger.error(f"Could not access or parse page {page_url} for scraping: {e}")
    return found_urls


def _download_dataset_files(
    dataset_name: str, dataset_config: dict, raw_files_root_dir: Path
) -> bool:
    """Downloads all relevant files for a dataset based on its configuration."""
    base_listing_url = dataset_config["file_listing_url"]
    subdirs_to_scan = dataset_config.get("subdirectories_to_scan", [])

    logger.info(
        f"Preparing to download {dataset_name} files from base URL: {base_listing_url}"
    )
    session = requests.Session()
    session.headers.update({"User-Agent": COMMON_USER_AGENT})

    all_files_to_process = []  # List of (url, local_target_path)

    for subdir_name in subdirs_to_scan:
        subdir_listing_url = urljoin(base_listing_url, f"{subdir_name}/")
        logger.info(f"Scanning subdirectory for CSVs: {subdir_listing_url}")
        csv_urls_in_subdir = _scrape_urls_from_html_page(subdir_listing_url, session)

        if not csv_urls_in_subdir:
            logger.warning(
                f"No .csv.gz files found in subdirectory: {subdir_listing_url}"
            )
            continue

        for file_url in csv_urls_in_subdir:
            url_path_obj = Path(urlparse(file_url).path)
            base_listing_url_path_obj = Path(urlparse(base_listing_url).path)
            relative_file_path: Path

            try:
                # Attempt to make file path relative to base URL's path part
                if url_path_obj.as_posix().startswith(
                    base_listing_url_path_obj.as_posix()
                ):
                    relative_file_path = url_path_obj.relative_to(
                        base_listing_url_path_obj
                    )
                else:
                    # Fallback if URL structure is unexpected
                    # (e.g., flat list of files not matching base structure)
                    logger.warning(
                        f"Path calculation fallback for {url_path_obj} vs "
                        f"{base_listing_url_path_obj}. "
                        f"Using {Path(subdir_name) / url_path_obj.name}"
                    )
                    relative_file_path = Path(subdir_name) / url_path_obj.name
            except (
                ValueError
            ) as e_rel:  # Handles cases where relative_to is not possible
                logger.error(
                    f"Path relative_to error for {url_path_obj} from "
                    f"{base_listing_url_path_obj}: {e_rel}. "
                    f"Defaulting to {Path(subdir_name) / url_path_obj.name}"
                )
                relative_file_path = Path(subdir_name) / url_path_obj.name

            local_target_path = raw_files_root_dir / relative_file_path
            all_files_to_process.append((file_url, local_target_path))

    if not all_files_to_process:
        logger.error(
            f"No '.csv.gz' download links found after scanning {base_listing_url} "
            f"and its subdirectories {subdirs_to_scan} for dataset '{dataset_name}'."
        )
        return False

    # Deduplicate and sort for consistent processing order
    unique_files_to_process = sorted(
        list(set(all_files_to_process)), key=lambda x: x[1]
    )
    logger.info(
        f"Found {len(unique_files_to_process)} unique '.csv.gz' files to download "
        f"for {dataset_name}."
    )

    downloaded_count = 0
    for file_url, target_filepath in unique_files_to_process:
        if not _download_single_file(file_url, target_filepath, session):
            logger.error(
                f"Critical download failed for '{target_filepath.name}'. "
                "Aborting dataset download."
            )
            return False  # Stop if any single download fails
        downloaded_count += 1

    # Success only if all identified files were downloaded
    return downloaded_count == len(unique_files_to_process)


def _load_csv_with_robust_parsing(csv_file_path: Path, table_name: str) -> pl.DataFrame:
    """
    Load a CSV file with proper type inference by scanning the entire file.
    """
    df = pl.read_csv(
        source=csv_file_path,
        infer_schema_length=None,  # Scan entire file for proper type inference
        try_parse_dates=True,
        ignore_errors=False,
        null_values=["", "NULL", "null", "\\N", "NA"],
    )

    # Log empty columns (this is normal, not an error)
    if df.height > 0:
        empty_columns = [col for col in df.columns if df[col].is_null().all()]
        if empty_columns:
            logger.info(
                f"  Table '{table_name}': Found {len(empty_columns)} empty column(s): "
                f"{', '.join(empty_columns[:5])}"
                + (
                    f" (and {len(empty_columns) - 5} more)"
                    if len(empty_columns) > 5
                    else ""
                )
            )

    return df


def _etl_csv_collection_to_sqlite(csv_source_dir: Path, db_target_path: Path) -> bool:
    """Loads all .csv.gz files from a directory structure into an SQLite database."""
    db_target_path.parent.mkdir(parents=True, exist_ok=True)
    # Polars uses this format for SQLite connections
    db_connection_uri = f"sqlite:///{db_target_path.resolve()}"
    logger.info(
        f"Starting ETL: loading CSVs from '{csv_source_dir}' to SQLite DB "
        f"at '{db_target_path}'"
    )

    csv_file_paths = list(csv_source_dir.rglob("*.csv.gz"))
    if not csv_file_paths:
        logger.error(
            "ETL Error: No .csv.gz files found (recursively) in source directory: "
            f"{csv_source_dir}"
        )
        return False

    successfully_loaded_count = 0
    files_with_errors = []
    logger.info(f"Found {len(csv_file_paths)} .csv.gz files for ETL process.")

    for i, csv_file_path in enumerate(csv_file_paths):
        # Generate table name from file path relative to the source directory
        # e.g., source_dir/hosp/admissions.csv.gz -> hosp_admissions
        relative_path = csv_file_path.relative_to(csv_source_dir)
        table_name_parts = [part.lower() for part in relative_path.parts]
        table_name = (
            "_".join(table_name_parts)
            .replace(".csv.gz", "")
            .replace("-", "_")
            .replace(".", "_")
        )

        logger.info(
            f"[{i + 1}/{len(csv_file_paths)}] ETL: Processing '{relative_path}' "
            f"into SQLite table '{table_name}'..."
        )

        try:
            # Use the robust parsing function
            df = _load_csv_with_robust_parsing(csv_file_path, table_name)

            df.write_database(
                table_name=table_name,
                connection=db_connection_uri,
                if_table_exists="replace",  # Overwrite table if it exists
                engine="sqlalchemy",  # Recommended engine for Polars with SQLite
            )
            logger.info(
                f"  Successfully loaded '{relative_path}' into table '{table_name}' "
                f"({df.height} rows, {df.width} columns)."
            )
            successfully_loaded_count += 1

        except Exception as e:
            err_msg = (
                f"Unexpected error during ETL for '{relative_path}' "
                f"(target table '{table_name}'): {e}"
            )
            logger.error(err_msg, exc_info=True)
            files_with_errors.append(f"{relative_path}: {e!s}")
            # Continue to process other files even if one fails

    if files_with_errors:
        logger.warning(
            "ETL completed with errors during processing for "
            f"{len(files_with_errors)} file(s):"
        )
        for detail in files_with_errors:
            logger.warning(f"  - {detail}")

    # Strict success: all found files must be loaded without Polars/DB errors.
    if successfully_loaded_count == len(csv_file_paths):
        logger.info(
            f"All {len(csv_file_paths)} CSV files successfully processed & loaded into "
            f"{db_target_path}."
        )
        return True
    elif successfully_loaded_count > 0:
        logger.warning(
            f"Partially completed ETL: Loaded {successfully_loaded_count} out of "
            f"{len(csv_file_paths)} files. Some files encountered errors during "
            "their individual processing and were not loaded."
        )
        return False
    else:  # No files were successfully loaded
        logger.error(
            "ETL process failed: No CSV files were successfully loaded into the "
            f"database from {csv_source_dir}."
        )
        return False


def initialize_dataset(dataset_name: str, db_target_path: Path) -> bool:
    """Initializes a dataset: downloads files and loads them into a database."""
    dataset_config = get_dataset_config(dataset_name)
    if not dataset_config:
        logger.error(f"Configuration for dataset '{dataset_name}' not found.")
        return False

    raw_files_root_dir = get_dataset_raw_files_path(dataset_name)
    raw_files_root_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting initialization for dataset: {dataset_name}")
    download_ok = _download_dataset_files(
        dataset_name, dataset_config, raw_files_root_dir
    )

    if not download_ok:
        logger.error(
            f"Download phase failed for dataset '{dataset_name}'. ETL skipped."
        )
        return False

    logger.info(f"Download phase complete for '{dataset_name}'. Starting ETL phase.")
    etl_ok = _etl_csv_collection_to_sqlite(raw_files_root_dir, db_target_path)

    if not etl_ok:
        logger.error(f"ETL phase failed for dataset '{dataset_name}'.")
        return False

    logger.info(
        f"Dataset '{dataset_name}' successfully initialized. "
        f"Database at: {db_target_path}"
    )
    return True
