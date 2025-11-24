import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import duckdb
import requests
import typer
from bs4 import BeautifulSoup

from m3.config import (
    get_dataset_config,
    get_dataset_parquet_root,
    get_default_database_path,
    logger,
)

########################################################
# Download functionality
########################################################

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

    # Prepare list of (subdir_name, listing_url)
    # If subdirs_to_scan is empty, we scan the base_listing_url directly (root)
    scan_targets = []
    if not subdirs_to_scan:
        scan_targets.append(("", base_listing_url))
    else:
        for subdir in subdirs_to_scan:
            # Ensure slash for directory joining
            subdir_url = urljoin(base_listing_url, f"{subdir}/")
            scan_targets.append((subdir, subdir_url))

    for subdir_name, listing_url in scan_targets:
        logger.info(f"Scanning for CSVs: {listing_url}")
        csv_urls_in_subdir = _scrape_urls_from_html_page(listing_url, session)

        if not csv_urls_in_subdir:
            logger.warning(f"No .csv.gz files found in location: {listing_url}")
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
        logger.error(f"No '.csv.gz' download links found for dataset '{dataset_name}'.")
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


def download_dataset(dataset_name: str, output_root: Path) -> bool:
    """
    Public wrapper to download a supported dataset's CSV files.
    - Currently intended for 'mimic-iv-demo' (public demo); extendable for others.
    - Downloads into output_root preserving subdirectory structure (e.g., hosp/, icu/).
    """
    cfg = get_dataset_config(dataset_name)
    if not cfg:
        logger.error(f"Unsupported dataset: {dataset_name}")
        return False

    # Prevent accidental scraping of credentialed datasets
    if cfg.get("requires_authentication"):
        logger.error(
            f"Dataset '{dataset_name}' requires authentication and cannot be auto-downloaded. "
            "Please download files manually."
        )
        return False

    if not cfg.get("file_listing_url"):
        logger.error(
            f"Dataset '{dataset_name}' does not have a configured listing URL. "
            "This version only supports public demo download."
        )
        return False

    output_root.mkdir(parents=True, exist_ok=True)
    return _download_dataset_files(dataset_name, cfg, output_root)


########################################################
# CSV to Parquet conversion
########################################################


def _csv_to_parquet_all(src_root: Path, parquet_root: Path) -> bool:
    """
    Convert all CSV files in the source directory to Parquet files.
    - Streams via DuckDB COPY to keep memory low
    - Low concurrency to avoid parallel memory spikes
    - Tunable via env:
        M3_CONVERT_MAX_WORKERS (default: 4)
        M3_DUCKDB_MEM         (default: 3GB)
        M3_DUCKDB_THREADS     (default: 2)
    """
    parquet_paths: list[Path] = []
    csv_files = list(src_root.rglob("*.csv.gz"))
    if not csv_files:
        logger.error(f"No CSV files found in {src_root}")
        return False

    # Optional: process small files first so progress moves smoothly
    try:
        csv_files.sort(key=lambda p: p.stat().st_size)
    except Exception:
        pass

    def _convert_one(csv_gz: Path) -> tuple[Path | None, float]:
        """Convert one CSV file and return the output path and time taken."""
        start = time.time()
        rel = csv_gz.relative_to(src_root)
        out = parquet_root / rel.with_suffix("").with_suffix(".parquet")
        out.parent.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect()
        try:
            mem_limit = os.environ.get("M3_DUCKDB_MEM", "3GB")
            threads = int(os.environ.get("M3_DUCKDB_THREADS", "2"))
            con.execute(f"SET memory_limit='{mem_limit}'")
            con.execute(f"PRAGMA threads={threads}")

            # Streamed CSV -> Parquet conversion with robust parsing
            sql = f"""
                COPY (
                  SELECT * FROM read_csv_auto(
                    '{csv_gz.as_posix()}',
                    sample_size=-1,
                    auto_detect=true,
                    nullstr=['', 'NULL', 'NA', 'N/A', '___'],
                    ignore_errors=false
                  )
                )
                TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);
            """
            con.execute(sql)
            elapsed = time.time() - start
            return out, elapsed
        finally:
            con.close()

    start_time = time.time()
    max_workers = max(1, int(os.environ.get("M3_CONVERT_MAX_WORKERS", "4")))

    total_files = len(csv_files)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_convert_one, f): f for f in csv_files}

        logger.info(
            f"Converting {total_files} CSV files to Parquet using {max_workers} workers..."
        )

        for fut in as_completed(futures):
            try:
                result_path, _ = fut.result()
                if result_path is not None:
                    parquet_paths.append(result_path)
                    completed += 1

                    elapsed = time.time() - start_time
                    logger.info(
                        f"Progress: {completed}/{total_files} files "
                        f"({100 * completed / total_files:.1f}%) - "
                        f"Elapsed: {timedelta(seconds=int(elapsed))!s}"
                    )
            except Exception as e:
                csv_file = futures[fut]
                logger.error(f"Parquet conversion failed for {csv_file}: {e}")
                ex.shutdown(cancel_futures=True)
                return False

    elapsed_time = time.time() - start_time
    logger.info(
        f"\u2713 Converted {len(parquet_paths)} files to Parquet under {parquet_root} "
        f"in {timedelta(seconds=int(elapsed_time))!s}"
    )
    return True


def convert_csv_to_parquet(
    dataset_name: str, csv_root: Path, parquet_root: Path
) -> bool:
    """
    Public wrapper to convert CSV.gz files to Parquet for a dataset.
    - csv_root: root folder containing hosp/ and icu/ CSV.gz files
    - parquet_root: destination root for Parquet files mirroring structure
    """
    if not csv_root.exists():
        logger.error(f"CSV root not found: {csv_root}")
        return False
    parquet_root.mkdir(parents=True, exist_ok=True)
    return _csv_to_parquet_all(csv_root, parquet_root)


########################################################
# DuckDB functions
########################################################


def init_duckdb_from_parquet(dataset_name: str, db_target_path: Path) -> bool:
    """
    Initialize or refresh a DuckDB for the dataset by creating views over Parquet.

    Parquet root must exist under:
    <project_root>/m3_data/parquet/<dataset_name>/
    """
    dataset_config = get_dataset_config(dataset_name)
    if not dataset_config:
        logger.error(f"Configuration for dataset '{dataset_name}' not found.")
        return False

    parquet_root = get_dataset_parquet_root(dataset_name)
    if not parquet_root or not parquet_root.exists():
        logger.error(
            f"Missing Parquet directory for '{dataset_name}' at {parquet_root}. "
            "Place Parquet files under the expected path or run the future download command."
        )
        return False

    logger.info(
        f"Creating or refreshing views in {db_target_path} for Parquet under {parquet_root}"
    )
    return _create_duckdb_with_views(db_target_path, parquet_root)


def _create_duckdb_with_views(db_path: Path, parquet_root: Path) -> bool:
    """
    Create a DuckDB database and define one view per Parquet file,
    using a generic table naming structure: folder_subfolder_filename.

    For example:
    - hosp/admissions.parquet → view: hosp_admissions
    - icu/chartevents.parquet → view: icu_chartevents
    - data.parquet → view: data
    """
    con = duckdb.connect(str(db_path))
    try:
        # Find all parquet files
        parquet_files = list(parquet_root.rglob("*.parquet"))
        if not parquet_files:
            logger.error(f"No Parquet files found in {parquet_root}")
            return False

        # Optimize DuckDB settings
        cpu_count = os.cpu_count() or 4
        con.execute(f"PRAGMA threads={cpu_count}")
        con.execute("SET memory_limit='8GB'")  # adjust to your machine

        logger.info(f"Creating {len(parquet_files)} views in DuckDB...")
        start_time = time.time()
        created = 0

        for idx, pq in enumerate(parquet_files, 1):
            # Get relative path from parquet_root
            rel = pq.relative_to(parquet_root)

            # Build view name from directory structure + filename
            # e.g., hosp/admissions.parquet -> hosp_admissions
            parts = [*list(rel.parent.parts), rel.stem]  # stem removes .parquet

            # Clean and join parts
            view_name = "_".join(
                p.lower().replace("-", "_").replace(".", "_") for p in parts if p != "."
            )

            # Create view pointing to the specific parquet file
            sql = f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT * FROM read_parquet('{pq.as_posix()}');
            """

            try:
                con.execute(sql)
                created += 1

                # Progress logging
                if idx % 5 == 0 or idx == len(parquet_files):
                    elapsed = time.time() - start_time
                    avg_time = elapsed / idx
                    eta_seconds = avg_time * (len(parquet_files) - idx)
                    logger.info(
                        f"Progress: {idx}/{len(parquet_files)} views "
                        f"({100 * idx / len(parquet_files):.1f}%) - "
                        f"Last: {view_name} - "
                        f"ETA: {timedelta(seconds=int(eta_seconds))!s}"
                    )
            except Exception as e:
                logger.error(f"Failed to create view {view_name} from {pq}: {e}")
                raise

        con.commit()
        elapsed_time = time.time() - start_time
        logger.info(
            f"✓ Created {created} views in {db_path} in "
            f"{timedelta(seconds=int(elapsed_time))!s}"
        )

        # List all created views for verification
        views_result = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type='VIEW' ORDER BY table_name"
        ).fetchall()
        logger.info(
            f"Created views: {', '.join(v[0] for v in views_result[:10])}{'...' if len(views_result) > 10 else ''}"
        )

        return True
    finally:
        con.close()


########################################################
# Verification and utilities
########################################################


def verify_table_rowcount(db_path: Path, table_name: str) -> int:
    con = duckdb.connect(str(db_path))
    try:
        row = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        if row is None:
            raise RuntimeError("No result")
        return int(row[0])
    finally:
        con.close()


def ensure_duckdb_for_dataset(
    dataset_key: str,
) -> tuple[bool, Path | None, Path | None]:
    """
    Ensure DuckDB exists and views are created for the dataset.
    Returns (ok, db_path, parquet_root).
    """
    db_path = get_default_database_path(dataset_key)
    parquet_root = get_dataset_parquet_root(dataset_key)
    if not parquet_root or not parquet_root.exists():
        logger.error(
            f"Parquet directory missing: {parquet_root}. Expected at <project_root>/m3_data/parquet/{dataset_key}/"
        )
        return False, db_path, parquet_root
    ok = _create_duckdb_with_views(db_path, parquet_root)
    return ok, db_path, parquet_root


def compute_parquet_dir_size(parquet_root: Path) -> int:
    total = 0
    for p in parquet_root.rglob("*.parquet"):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total
