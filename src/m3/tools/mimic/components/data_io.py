import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import polars as pl
import requests
from beartype import beartype
from beartype.typing import Any, Dict, List
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress

from m3.core.config import M3Config
from m3.core.utils.exceptions import M3ValidationError
from m3.tools.mimic.components.utils import (
    get_dataset_config,
    get_dataset_raw_files_path,
)

logger = logging.getLogger(__name__)

COMMON_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

console = Console()


@beartype
class DataIO:
    def __init__(self, config: M3Config) -> None:
        self.config = config

    def initialize(self, dataset: str, path: Path) -> bool:
        dataset_config = self._get_dataset_config(dataset)
        raw_files_root_dir = self._get_raw_files_path(dataset)
        logger.info(f"Initializing {dataset} at {path}")
        console.print(
            f"[turquoise4]💬 Initializing {dataset} at {path}...[/turquoise4]"
        )

        console.print("[cyan]Downloading dataset files...[/cyan]")
        if not self._download_dataset_files(dataset_config, raw_files_root_dir):
            logger.error(f"Download failed for {dataset}.")
            console.print(f"[red]❌ Download failed for {dataset}.[/red]")
            return False

        console.print("[cyan]Loading files to SQLite...[/cyan]")
        if not self._etl_csv_collection_to_sqlite(raw_files_root_dir, path):
            logger.error(f"ETL failed for {dataset}.")
            console.print(f"[red]❌ ETL failed for {dataset}.[/red]")
            return False

        logger.info(f"Successfully initialized {dataset}.")
        console.print(f"[green]✅ Successfully initialized {dataset}.[/green]")
        return True

    def _get_dataset_config(self, dataset: str) -> Dict[str, Any]:
        config = get_dataset_config(dataset)
        if not config:
            raise M3ValidationError(f"Config not found for '{dataset}'.")
        return config

    def _get_raw_files_path(self, dataset: str) -> Path:
        path = get_dataset_raw_files_path(self.config, dataset)
        if path is None:
            raise M3ValidationError(f"Raw files path not found for '{dataset}'.")
        return path

    def _download_dataset_files(
        self,
        dataset_config: Dict[str, Any],
        raw_files_root_dir: Path,
    ) -> bool:
        base_listing_url = dataset_config["file_listing_url"]
        subdirs_to_scan = dataset_config.get("subdirectories_to_scan", [])
        session = requests.Session()
        session.headers.update({"User-Agent": COMMON_USER_AGENT})
        all_files_to_process = []
        for subdir_name in subdirs_to_scan:
            subdir_listing_url = urljoin(base_listing_url, f"{subdir_name}/")
            csv_urls_in_subdir = self._scrape_urls_from_html_page(
                subdir_listing_url, session
            )
            if not csv_urls_in_subdir:
                continue
            for file_url in csv_urls_in_subdir:
                url_path_obj = Path(urlparse(file_url).path)
                base_listing_url_path_obj = Path(urlparse(base_listing_url).path)
                relative_file_path = (
                    url_path_obj.relative_to(base_listing_url_path_obj)
                    if url_path_obj.as_posix().startswith(
                        base_listing_url_path_obj.as_posix()
                    )
                    else Path(subdir_name) / url_path_obj.name
                )
                local_target_path = raw_files_root_dir / relative_file_path
                all_files_to_process.append((file_url, local_target_path))
        if not all_files_to_process:
            return False
        unique_files_to_process = sorted(set(all_files_to_process), key=lambda x: x[1])
        downloaded_count = 0
        for file_url, target_filepath in unique_files_to_process:
            if not self._download_single_file(file_url, target_filepath, session):
                return False
            downloaded_count += 1
        return downloaded_count == len(unique_files_to_process)

    def _download_single_file(
        self, url: str, target_filepath: Path, session: requests.Session
    ) -> bool:
        try:
            response = session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            target_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(target_filepath, "wb") as file_object:
                with Progress(console=console, transient=True) as progress:
                    task = progress.add_task(
                        f"[cyan]Downloading {target_filepath.name}", total=total_size
                    )
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file_object.write(chunk)
                            progress.update(task, advance=len(chunk))
            return True
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            if target_filepath.exists():
                target_filepath.unlink()
            console.print(f"[red]❌ Download failed for {url}: {e}[/red]")
            return False

    def _scrape_urls_from_html_page(
        self, page_url: str, session: requests.Session, file_suffix: str = ".csv.gz"
    ) -> List[str]:
        found_urls = []
        try:
            page_response = session.get(page_url, timeout=30)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.content, "html.parser")
            for link_tag in soup.find_all("a", href=True):
                href_path = link_tag["href"]
                if (
                    href_path.endswith(file_suffix)
                    and not href_path.startswith(("?", "#"))
                    and ".." not in href_path
                ):
                    absolute_url = urljoin(page_url, href_path)
                    found_urls.append(absolute_url)
        except Exception as e:
            logger.error(f"Scrape failed for {page_url}: {e}")
            console.print(f"[red]❌ Scrape failed for {page_url}: {e}[/red]")
        return found_urls

    def _etl_csv_collection_to_sqlite(
        self, csv_source_dir: Path, db_target_path: Path
    ) -> bool:
        db_target_path.parent.mkdir(parents=True, exist_ok=True)
        db_connection_uri = f"sqlite:///{db_target_path.resolve()}"
        csv_file_paths = list(csv_source_dir.rglob("*.csv.gz"))
        if not csv_file_paths:
            return False
        successfully_loaded_count = 0
        files_with_errors = []
        with Progress(console=console) as progress:
            total_task = progress.add_task(
                "[cyan]Loading CSV files to SQLite...", total=len(csv_file_paths)
            )
            for csv_file_path in csv_file_paths:
                relative_path = csv_file_path.relative_to(csv_source_dir)
                table_name_parts = [part.lower() for part in relative_path.parts]
                table_name = (
                    "_".join(table_name_parts)
                    .replace(".csv.gz", "")
                    .replace("-", "_")
                    .replace(".", "_")
                )
                try:
                    dataframe = self._load_csv_with_robust_parsing(
                        csv_file_path, table_name
                    )
                    dataframe.write_database(
                        table_name=table_name,
                        connection=db_connection_uri,
                        if_table_exists="replace",
                        engine="sqlalchemy",
                    )
                    successfully_loaded_count += 1
                except Exception as e:
                    err_msg = (
                        f"ETL error for '{relative_path}' (table '{table_name}'): {e}"
                    )
                    logger.error(err_msg, exc_info=True)
                    files_with_errors.append(err_msg)
                    console.print(f"[red]❌ {err_msg}[/red]")
                progress.update(total_task, advance=1)

        if files_with_errors:
            logger.warning(f"ETL errors in {len(files_with_errors)} files:")
            for detail in files_with_errors:
                logger.warning(f"  - {detail}")

        return successfully_loaded_count == len(csv_file_paths)

    def _load_csv_with_robust_parsing(
        self, csv_file_path: Path, table_name: str
    ) -> pl.DataFrame:
        try:
            dataframe = pl.read_csv(
                source=csv_file_path,
                infer_schema_length=None,
                try_parse_dates=True,
                ignore_errors=False,
                null_values=["", "NULL", "null", "\\N", "NA"],
            )
            if dataframe.height > 0:
                empty_columns = [
                    column
                    for column in dataframe.columns
                    if dataframe[column].is_null().all()
                ]
                if empty_columns:
                    logger.debug(f"Empty columns in {table_name}: {empty_columns}")
            return dataframe
        except Exception as e:
            raise M3ValidationError(f"Failed to parse CSV {csv_file_path}: {e}") from e
