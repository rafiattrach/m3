"""
EHRSQL Dataset Downloader
Downloads and preprocesses the EHRSQL dataset for M3 benchmarking.
"""

import json
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


class EHRSQLDatasetDownloader:
    """Downloads and manages EHRSQL dataset for M3 benchmarking."""

    # Updated to use EHRSQL 2024 with MIMIC-IV data
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/glee4810/ehrsql-2024/master"

    def __init__(self, data_dir: Path | None = None):
        """Initialize the downloader.

        Args:
            data_dir: Directory to store downloaded data. Defaults to benchmarks/ehrsql/dataset/ehrsql_data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "ehrsql_data"

        self.data_dir = Path(data_dir)
        self.console = Console()

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def download_file(self, url: str, local_path: Path) -> bool:
        """Download a file from URL to local path.

        Args:
            url: URL to download from
            local_path: Local path to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(local_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            return True
        except Exception as e:
            self.console.print(f"[red]Error downloading {url}: {e}[/red]")
            return False

    def download_dataset_files(self) -> bool:
        """Download core EHRSQL dataset files.

        Returns:
            True if all files downloaded successfully
        """
        files_to_download = [
            # MIMIC-IV data files from ehrsql-2024 (correct structure)
            ("data/mimic_iv/train/data.json", "mimic_iv_train_data.json"),
            ("data/mimic_iv/train/label.json", "mimic_iv_train_label.json"),
            ("data/mimic_iv/valid/data.json", "mimic_iv_valid_data.json"),
            ("data/mimic_iv/valid/label.json", "mimic_iv_valid_label.json"),
            ("data/mimic_iv/test/data.json", "mimic_iv_test_data.json"),
            ("data/mimic_iv/tables.json", "mimic_iv_tables.json"),
        ]

        success_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                "Downloading EHRSQL dataset files...", total=len(files_to_download)
            )

            for remote_path, local_filename in files_to_download:
                url = f"{self.GITHUB_BASE_URL}/{remote_path}"
                local_path = self.data_dir / local_filename

                if local_path.exists():
                    self.console.print(
                        f"[yellow]Skipping {local_filename} (already exists)[/yellow]"
                    )
                    success_count += 1
                else:
                    self.console.print(f"Downloading {local_filename}...")
                    if self.download_file(url, local_path):
                        success_count += 1
                        self.console.print(
                            f"[green]✓ Downloaded {local_filename}[/green]"
                        )
                    else:
                        self.console.print(
                            f"[red]✗ Failed to download {local_filename}[/red]"
                        )

                progress.update(task, advance=1)

        return success_count == len(files_to_download)

    def load_dataset(self, split: str) -> list[dict]:
        """Load a specific dataset split for MIMIC-IV.

        Args:
            split: Either 'train', 'valid', or 'test'

        Returns:
            List of dataset examples with questions and SQL queries combined
        """
        data_filename = f"mimic_iv_{split}_data.json"
        label_filename = f"mimic_iv_{split}_label.json"

        data_path = self.data_dir / data_filename
        label_path = self.data_dir / label_filename

        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        if (
            not label_path.exists() and split != "test"
        ):  # Test labels might not be available
            raise FileNotFoundError(f"Label file not found: {label_path}")

        # Load questions
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)

        # Load labels if available
        labels = {}
        if label_path.exists():
            with open(label_path, encoding="utf-8") as f:
                labels = json.load(f)

        # Combine data and labels
        combined_data = []
        for item in data["data"]:
            question_id = item["id"]
            combined_item = {
                "id": question_id,
                "question": item["question"],
                "query": labels.get(question_id),  # None if no label available
                "db_id": "mimic_iv",
                "is_impossible": labels.get(question_id) is None
                or labels.get(question_id) == "null",
            }
            combined_data.append(combined_item)

        return combined_data

    def load_tables(self) -> dict:
        """Load table schema information for MIMIC-IV.

        Returns:
            Table schema information
        """
        filename = "mimic_iv_tables.json"
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Tables file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_answerable_questions(self, split: str) -> list[dict]:
        """Get only answerable questions from a dataset split.

        Args:
            split: Either 'train', 'valid', or 'test'

        Returns:
            List of answerable dataset examples
        """
        dataset = self.load_dataset(split)
        return [item for item in dataset if not item.get("is_impossible", False)]

    def prepare_for_m3(
        self, split: str = "valid", limit: int | None = None
    ) -> list[dict]:
        """Prepare EHRSQL 2024 data for M3 evaluation.

        Args:
            split: Data split to use
            limit: Limit number of examples (for testing)

        Returns:
            List of examples formatted for M3 evaluation
        """
        questions = self.get_answerable_questions(split)

        if limit:
            questions = questions[:limit]

        # Convert to M3 evaluation format
        m3_examples = []
        for item in questions:
            m3_example = {
                "id": item["id"],
                "question": item["question"],
                "expected_sql": item["query"],
                "db_id": item["db_id"],
                "is_impossible": item.get("is_impossible", False),
            }
            m3_examples.append(m3_example)

        return m3_examples


def main():
    """CLI interface for downloading EHRSQL dataset."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download EHRSQL dataset for M3 benchmarking"
    )
    parser.add_argument(
        "--data-dir", type=Path, help="Directory to store downloaded data"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if files exist"
    )

    args = parser.parse_args()

    downloader = EHRSQLDatasetDownloader(args.data_dir)

    console = Console()
    console.print("[bold blue]EHRSQL Dataset Downloader for M3[/bold blue]")
    console.print(f"Data directory: {downloader.data_dir}")

    if args.force:
        # Remove existing files
        for file in downloader.data_dir.glob("*.json"):
            file.unlink()

    success = downloader.download_dataset_files()

    if success:
        console.print("[bold green]✓ All files downloaded successfully![/bold green]")

        # Show summary
        mimic_train = downloader.load_dataset("train")
        mimic_valid = downloader.load_dataset("valid")

        console.print("\n[bold]Dataset Summary:[/bold]")
        console.print(f"MIMIC-IV Train: {len(mimic_train)} examples")
        console.print(f"MIMIC-IV Valid: {len(mimic_valid)} examples")

        answerable_valid = downloader.get_answerable_questions("valid")
        console.print(f"MIMIC-IV Valid (answerable): {len(answerable_valid)} examples")

    else:
        console.print("[bold red]✗ Some files failed to download[/bold red]")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
