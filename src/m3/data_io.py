from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Literal
import polars as pl
import requests
import typer
from bs4 import BeautifulSoup
import duckdb
import time
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

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


########################################################
# DuckDB functions
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

            # Streamed CSV -> Parquet conversion
            # 'all_varchar=true' avoids expensive/wide type inference;
            # if you prefer typed inference, drop it and keep sample_size=-1.
            sql = f"""
                COPY (
                  SELECT * FROM read_csv_auto('{csv_gz.as_posix()}', sample_size=-1, all_varchar=true)
                )
                TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);
            """
            con.execute(sql)
            elapsed = time.time() - start
            return out, elapsed
        finally:
            con.close()

    start_time = time.time()
    cpu_cnt = os.cpu_count() or 4
    # Increase default to 2 for better throughput
    max_workers = max(1, int(os.environ.get("M3_CONVERT_MAX_WORKERS", "4")))
    
    total_files = len(csv_files)
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_convert_one, f): f for f in csv_files}
        
        # Manual progress tracking for better time estimates
        logger.info(f"Converting {total_files} CSV files to Parquet using {max_workers} workers...")
        
        for fut in as_completed(futures):
            try:
                result_path, file_time = fut.result()
                if result_path is not None:
                    parquet_paths.append(result_path)
                    completed += 1
                    
                    # Log elapsed time
                    elapsed = time.time() - start_time
                    logger.info(
                        f"Progress: {completed}/{total_files} files "
                        f"({100*completed/total_files:.1f}%) - "
                        f"Elapsed: {str(timedelta(seconds=int(elapsed)))} - "
                    )
            except Exception as e:
                csv_file = futures[fut]
                logger.error(f"Parquet conversion failed for {csv_file}: {e}")
                ex.shutdown(cancel_futures=True)
                return False

    elapsed_time = time.time() - start_time
    logger.info(
        f"✓ Converted {len(parquet_paths)} files to Parquet under {parquet_root} "
        f"in {str(timedelta(seconds=int(elapsed_time)))}"
    )
    return True


def _create_duckdb_with_views(db_path: Path, parquet_root: Path) -> bool:
    """
    Create a DuckDB database and define one view per Parquet file,
    using the proper table naming structure that matches MIMIC-IV expectations.
    
    For example:
    - hosp/admissions.parquet → view: hosp_admissions
    - icu/chartevents.parquet → view: icu_chartevents
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
            parts = list(rel.parent.parts) + [rel.stem]  # stem removes .parquet
            
            # Clean and join parts
            view_name = "_".join(
                p.lower().replace("-", "_").replace(".", "_") 
                for p in parts if p != "."
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
                        f"({100*idx/len(parquet_files):.1f}%) - "
                        f"Last: {view_name} - "
                        f"ETA: {str(timedelta(seconds=int(eta_seconds)))}"
                    )
            except Exception as e:
                logger.error(f"Failed to create view {view_name} from {pq}: {e}")
                raise

        con.commit()
        elapsed_time = time.time() - start_time
        logger.info(
            f"✓ Created {created} views in {db_path} in "
            f"{str(timedelta(seconds=int(elapsed_time)))}"
        )
        
        # List all created views for verification
        views_result = con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name").fetchall()
        logger.info(f"Created views: {', '.join(v[0] for v in views_result[:10])}{'...' if len(views_result) > 10 else ''}")
        
        return True
    finally:
        con.close()


def build_duckdb_from_existing_raw(dataset_name: str, db_target_path: Path) -> bool:
    """
    Build a DuckDB database from existing raw CSVs (no downloads).
    - Converts CSVs under m3_data/raw_files/<dataset>/ to Parquet
    - Creates views in DuckDB that point to those Parquet files
    """
    raw_files_root_dir = get_dataset_raw_files_path(dataset_name)
    if not raw_files_root_dir or not raw_files_root_dir.exists():
        logger.error(
            f"Raw files directory not found for dataset '{dataset_name}'. "
            "Run 'm3 init mimic-iv-demo' first for the demo, or place full data under "
            f"{(raw_files_root_dir or Path()).resolve()}."
        )
        return False

    parquet_root = raw_files_root_dir.parent / "parquet" / dataset_name
    parquet_root.mkdir(parents=True, exist_ok=True)

    if not _csv_to_parquet_all(raw_files_root_dir, parquet_root):
        return False

    logger.info("✓ Created all parquet files")

    return _create_duckdb_with_views(db_target_path, parquet_root)


########################################################
# Verification functions
########################################################

def verify_table_rowcount(
    engine: Literal["sqlite", "duckdb"],
    db_path: Path,
    table_name: str,
) -> int:
    if engine == "sqlite":
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cur.fetchone()
            if row is None:
                raise sqlite3.Error("No result")
            return int(row[0])
        finally:
            conn.close()
    else:  # duckdb
        import duckdb
        con = duckdb.connect(str(db_path))
        try:
            row = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            if row is None:
                raise RuntimeError("No result")
            return int(row[0])
        finally:
            con.close()
