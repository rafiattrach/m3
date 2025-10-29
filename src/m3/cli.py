import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from m3 import __version__
from m3.config import (
    SUPPORTED_DATASETS,
    detect_available_local_datasets,
    get_active_dataset,
    get_dataset_config,
    get_dataset_parquet_root,
    get_default_database_path,
    logger,
    set_active_dataset,
)
from m3.data_io import (
    compute_parquet_dir_size,
    convert_csv_to_parquet,
    download_dataset,
    initialize_duckdb_from_parquet,
    verify_table_rowcount,
)

app = typer.Typer(
    name="m3",
    help="M3 CLI: Initialize local clinical datasets like MIMIC-IV Demo.",
    add_completion=False,
    rich_markup_mode="markdown",
)


def version_callback(value: bool):
    if value:
        typer.echo(f"M3 CLI Version: {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show CLI version.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-V", help="Enable DEBUG level logging for m3 components."
        ),
    ] = False,
):
    """
    Main callback for the M3 CLI. Sets logging level.
    """
    m3_logger = logging.getLogger("m3")  # Get the logger from config.py
    if verbose:
        m3_logger.setLevel(logging.DEBUG)
        for handler in m3_logger.handlers:  # Ensure handlers also respect the new level
            handler.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled via CLI flag.")
    else:
        # Default to INFO as set in config.py
        m3_logger.setLevel(logging.INFO)
        for handler in m3_logger.handlers:
            handler.setLevel(logging.INFO)


@app.command("init")
def dataset_init_cmd(
    dataset_name: Annotated[
        str,
        typer.Argument(
            help=(
                "Dataset to initialize (local). Default: 'mimic-iv-demo'. "
                f"Supported: {', '.join(SUPPORTED_DATASETS.keys())}"
            ),
            metavar="DATASET_NAME",
        ),
    ] = "mimic-iv-demo",
    db_path_str: Annotated[
        str | None,
        typer.Option(
            "--db-path",
            "-p",
            help="Custom path for the DuckDB file. Uses a default if not set.",
        ),
    ] = None,
):
    """
    Initialize a local dataset by creating DuckDB views over existing Parquet files.

    - Parquet must already exist under <project_root>/m3_data/parquet/<dataset_name>/
    - DuckDB file will be at <project_root>/m3_data/databases/<dataset>.duckdb
    """
    logger.info(f"CLI 'init' called for dataset: '{dataset_name}'")

    dataset_key = dataset_name.lower()  # Normalize for lookup
    dataset_config = get_dataset_config(dataset_key)

    if not dataset_config:
        typer.secho(
            f"Error: Dataset '{dataset_name}' is not supported or not configured.",
            fg=typer.colors.RED,
            err=True,
        )
        typer.secho(
            f"Supported datasets are: {', '.join(SUPPORTED_DATASETS.keys())}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=1)

    final_db_path = (
        Path(db_path_str).resolve()
        if db_path_str
        else get_default_database_path(dataset_key, "duckdb")
    )
    if not final_db_path:
        typer.secho(
            f"Critical Error: Could not determine database path for '{dataset_name}'.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Ensure parent directory for the database exists
    final_db_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_root = get_dataset_parquet_root(dataset_key)
    typer.echo(f"Initializing dataset: '{dataset_name}'")
    typer.echo(f"DuckDB path: {final_db_path}")
    typer.echo(f"Parquet root: {parquet_root}")

    if not parquet_root or not parquet_root.exists():
        typer.secho(
            f"Parquet directory not found at {parquet_root}.\n",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    initialization_successful = initialize_duckdb_from_parquet(
        dataset_name=dataset_key, db_target_path=final_db_path
    )

    if not initialization_successful:
        typer.secho(
            (
                f"Dataset '{dataset_name}' initialization FAILED. "
                "Please check logs for details."
            ),
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    logger.info(
        f"Dataset '{dataset_name}' initialization seems complete. "
        "Verifying database integrity..."
    )

    # Basic verification by querying a known table (fast check)
    verification_table_name = dataset_config.get("primary_verification_table")
    if not verification_table_name:
        logger.warning(
            f"No 'primary_verification_table' configured for '{dataset_name}'. "
            "Skipping DB query test."
        )
        typer.secho(
            (
                f"Dataset '{dataset_name}' initialized to {final_db_path}. "
                f"Parquet at {parquet_root}."
            ),
            fg=typer.colors.GREEN,
        )
        typer.secho(
            "Skipped database query test as no verification table is set in config.",
            fg=typer.colors.YELLOW,
        )
        return

    try:
        record_count = verify_table_rowcount(final_db_path, verification_table_name)
        typer.secho(
            f"Database verification successful: Found {record_count} records in table '{verification_table_name}'.",
            fg=typer.colors.GREEN,
        )
        typer.secho(
            f"Dataset '{dataset_name}' ready at {final_db_path}. Parquet at {parquet_root}.",
            fg=typer.colors.BRIGHT_GREEN,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during database verification: {e}", exc_info=True
        )
        typer.secho(
            f"An unexpected error occurred during database verification: {e}",
            fg=typer.colors.RED,
            err=True,
        )
    # Set active dataset to match init target
    if dataset_key == "mimic-iv-demo":
        set_active_dataset("demo")
    elif dataset_key == "mimic-iv-full":
        set_active_dataset("full")


@app.command("use")
def use_cmd(
    target: Annotated[
        str,
        typer.Argument(help="Select active dataset: demo | full | bigquery", metavar="TARGET"),
    ]
):
    """Set the active dataset selection for the project."""
    target = target.lower()
    if target not in ("demo", "full", "bigquery"):
        typer.secho("Target must be one of: demo, full, bigquery", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if target in ("demo", "full"):
        availability = detect_available_local_datasets()[target]
        if not availability["parquet_present"]:
            typer.secho(
                f"Parquet directory missing at {availability['parquet_root']}. Cannot activate '{target}'.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    set_active_dataset(target)
    typer.secho(f"Active dataset set to '{target}'.", fg=typer.colors.GREEN)


@app.command("status")
def status_cmd():
    """Show active dataset, local DB path, Parquet presence, quick counts and sizes."""
    active = get_active_dataset() or "(unset)"
    typer.secho(f"Active dataset: {active}", fg=typer.colors.BRIGHT_GREEN if active != "(unset)" else typer.colors.YELLOW)

    availability = detect_available_local_datasets()

    for label in ("demo", "full"):
        info = availability[label]
        typer.secho(f"\n=== {label.upper()} ===", fg=typer.colors.BRIGHT_BLUE)

        parquet_icon = "✅" if info["parquet_present"] else "❌"
        db_icon = "✅" if info["db_present"] else "❌"

        typer.echo(f"  parquet_present: {parquet_icon}  db_present: {db_icon}")
        typer.echo(f"  parquet_root: {info['parquet_root']}")
        typer.echo(f"  db_path: {info['db_path']}")

        if info["parquet_present"]:
            try:
                size_bytes = compute_parquet_dir_size(Path(info["parquet_root"]))
                size_gb = float(size_bytes) / (1024 ** 3)
                typer.echo(f"  parquet_size_gb: {size_gb:.4f} GB")
            except Exception:
                typer.echo("  parquet_size_gb: (skipped)")

        # Try a quick rowcount on the verification table if db present
        ds_name = "mimic-iv-demo" if label == "demo" else "mimic-iv-full"
        cfg = get_dataset_config(ds_name)
        if info["db_present"] and cfg:
            try:
                count = verify_table_rowcount(Path(info["db_path"]), cfg["primary_verification_table"])
                typer.echo(f"  {cfg['primary_verification_table']}_rowcount: {count:,}")
            except Exception:
                typer.echo("  rowcount: (skipped)")


@app.command("config")
def config_cmd(
    client: Annotated[
        str | None,
        typer.Argument(
            help="MCP client to configure. Use 'claude' for Claude Desktop auto-setup, or omit for universal config generator.",
            metavar="CLIENT",
        ),
    ] = None,
    backend: Annotated[
        str,
        typer.Option(
            "--backend",
            "-b",
            help="Backend to use (duckdb or bigquery). Default: duckdb",
        ),
    ] = "duckdb",
    db_path: Annotated[
        str | None,
        typer.Option(
            "--db-path",
            "-p",
            help="Path to DuckDB database (for duckdb backend)",
        ),
    ] = None,
    project_id: Annotated[
        str | None,
        typer.Option(
            "--project-id",
            help="Google Cloud project ID (required for bigquery backend)",
        ),
    ] = None,
    python_path: Annotated[
        str | None,
        typer.Option(
            "--python-path",
            help="Path to Python executable",
        ),
    ] = None,
    working_directory: Annotated[
        str | None,
        typer.Option(
            "--working-directory",
            help="Working directory for the server",
        ),
    ] = None,
    server_name: Annotated[
        str,
        typer.Option(
            "--server-name",
            help="Name for the MCP server",
        ),
    ] = "m3",
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help="Save configuration to file instead of printing",
        ),
    ] = None,
    quick: Annotated[
        bool,
        typer.Option(
            "--quick",
            "-q",
            help="Use quick mode with provided arguments (non-interactive)",
        ),
    ] = False,
):
    """
    Configure M3 MCP server for various clients.

    Examples:

    • m3 config                    # Interactive universal config generator

    • m3 config claude             # Auto-configure Claude Desktop

    • m3 config --quick            # Quick universal config with defaults

    • m3 config claude --backend bigquery --project-id my-project
    """
    try:
        from m3 import mcp_client_configs

        script_dir = Path(mcp_client_configs.__file__).parent
    except ImportError:
        typer.secho(
            "❌ Error: Could not find m3.mcp_client_configs package",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Validate backend-specific arguments
    # duckdb: db_path allowed, project_id not allowed
    if backend == "duckdb" and project_id:
        typer.secho("❌ Error: --project-id can only be used with --backend bigquery", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # bigquery: requires project_id, db_path not allowed
    if backend == "bigquery" and db_path:
        typer.secho("❌ Error: --db-path can only be used with --backend duckdb", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    if backend == "bigquery" and not project_id:
        typer.secho("❌ Error: --project-id is required when using --backend bigquery", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if client == "claude":
        # Run the Claude Desktop setup script
        script_path = script_dir / "setup_claude_desktop.py"

        if not script_path.exists():
            typer.secho(
                f"Error: Claude Desktop setup script not found at {script_path}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # Build command arguments with smart defaults inferred from runtime config
        cmd = [sys.executable, str(script_path)]

        # Always pass backend if not duckdb; duckdb is the script default
        if backend != "duckdb":
            cmd.extend(["--backend", backend])

        # For duckdb, infer db_path from active dataset if not provided
        if backend == "duckdb":
            effective_db_path = db_path
            if not effective_db_path:
                active = get_active_dataset()
                # Default to demo if unset
                dataset_key = "mimic-iv-full" if active == "full" else "mimic-iv-demo"
                guessed = get_default_database_path(dataset_key, "duckdb")
                if guessed is not None:
                    effective_db_path = str(guessed)
            if effective_db_path:
                cmd.extend(["--db-path", effective_db_path])
        elif backend == "bigquery" and project_id:
            cmd.extend(["--project-id", project_id])

        try:
            result = subprocess.run(cmd, check=True, capture_output=False)
            if result.returncode == 0:
                typer.secho(
                    "✅ Claude Desktop configuration completed!", fg=typer.colors.GREEN
                )
        except subprocess.CalledProcessError as e:
            typer.secho(
                f"❌ Claude Desktop setup failed with exit code {e.returncode}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=e.returncode)
        except FileNotFoundError:
            typer.secho(
                "❌ Python interpreter not found. Please ensure Python is installed.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    else:
        # Run the dynamic config generator
        script_path = script_dir / "dynamic_mcp_config.py"

        if not script_path.exists():
            typer.secho(
                f"Error: Dynamic config script not found at {script_path}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # Build command arguments
        cmd = [sys.executable, str(script_path)]

        if quick:
            cmd.append("--quick")

        if backend != "duckdb":
            cmd.extend(["--backend", backend])

        if server_name != "m3":
            cmd.extend(["--server-name", server_name])

        if python_path:
            cmd.extend(["--python-path", python_path])

        if working_directory:
            cmd.extend(["--working-directory", working_directory])

        if backend == "duckdb" and db_path:
            cmd.extend(["--db-path", db_path])
        elif backend == "bigquery" and project_id:
            cmd.extend(["--project-id", project_id])

        if output:
            cmd.extend(["--output", output])

        if quick:
            typer.echo("🔧 Generating M3 MCP configuration...")
        else:
            typer.echo("🔧 Starting interactive M3 MCP configuration...")

        try:
            result = subprocess.run(cmd, check=True, capture_output=False)
            if result.returncode == 0 and quick:
                typer.secho(
                    "✅ Configuration generated successfully!", fg=typer.colors.GREEN
                )
        except subprocess.CalledProcessError as e:
            typer.secho(
                f"❌ Configuration generation failed with exit code {e.returncode}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=e.returncode)
        except FileNotFoundError:
            typer.secho(
                "❌ Python interpreter not found. Please ensure Python is installed.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)


@app.command("download")
def download_cmd(
    dataset: Annotated[
        str,
        typer.Argument(
            help=(
                "Dataset to download (currently only supports 'mimic-iv-demo'). "
                f"Configured: {', '.join(SUPPORTED_DATASETS.keys())}"
            ),
            metavar="DATASET_NAME",
        ),
    ],
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Directory to store downloaded files. Default: <project_root>/m3_data/raw_files/<dataset>/"
            ),
        ),
    ] = None,
):
    """
    Download public dataset files (demo only in this version).

    - For 'mimic-iv-demo', downloads CSV.gz files under hosp/ and icu/ subdirectories.
    - Files are saved to the output directory, preserving the original structure.
    - This command does not convert CSV to Parquet.
    """
    dataset_key = dataset.lower()
    if dataset_key != "mimic-iv-demo":
        typer.secho(
            "Currently only 'mimic-iv-demo' is supported by 'm3 download'.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    cfg = get_dataset_config(dataset_key)
    if not cfg or not cfg.get("file_listing_url"):
        typer.secho(
            f"Dataset '{dataset}' is not configured for download.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Default output: <project_root>/m3_data/raw_files/<dataset>/
    if output:
        out_dir = Path(output).resolve()
    else:
        # Build from the parquet root: <root>/m3_data/parquet/<dataset> -> <root>/m3_data/raw_files/<dataset>
        pq = get_dataset_parquet_root(dataset_key)
        out_dir = pq.parent.parent / "raw_files" / dataset_key

    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Downloading dataset: '{dataset}'")
    typer.echo(f"Listing URL: {cfg.get('file_listing_url')}")
    typer.echo(f"Output directory: {out_dir}")

    ok = download_dataset(dataset_key, out_dir)
    if not ok:
        typer.secho(
            "Download failed. Please check logs for details.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.secho("✅ Download complete.", fg=typer.colors.GREEN)
    typer.secho(
        "Next step: Run 'm3 convert' to convert the downloaded CSV files to Parquet.",
        fg=typer.colors.YELLOW,
    )


@app.command("convert")
def convert_cmd(
    dataset: Annotated[
        str,
        typer.Argument(
            help=(
                "Dataset to convert (csv.gz → parquet). Expected CSVs under raw_files/<dataset>."
            ),
            metavar="DATASET_NAME",
        ),
    ],
    src: Annotated[
        str | None,
        typer.Option(
            "--src",
            "-s",
            help="Root directory containing CSV.gz files (default: <project_root>/m3_data/raw_files/<dataset>)",
        ),
    ] = None,
    dst: Annotated[
        str | None,
        typer.Option(
            "--dst",
            "-d",
            help="Destination Parquet root (default: <project_root>/m3_data/parquet/<dataset>)",
        ),
    ] = None,
):
    """
    Convert all CSV.gz files for a dataset to Parquet, mirroring structure (hosp/, icu/).
    Uses DuckDB streaming COPY for low memory usage.
    """
    dataset_key = dataset.lower()
    cfg = get_dataset_config(dataset_key)
    if not cfg:
        typer.secho(
            f"Unsupported dataset: {dataset}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Defaults
    pq_root_default = get_dataset_parquet_root(dataset_key)
    # raw_files default relative to project root
    if pq_root_default is None:
        typer.secho("Could not determine dataset directories.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if src:
        csv_root = Path(src).resolve()
    else:
        csv_root = pq_root_default.parent.parent / "raw_files" / dataset_key

    if dst:
        parquet_root = Path(dst).resolve()
    else:
        parquet_root = pq_root_default

    typer.echo(f"Converting dataset: '{dataset}'")
    typer.echo(f"CSV root: {csv_root}")
    typer.echo(f"Parquet destination: {parquet_root}")

    ok = convert_csv_to_parquet(dataset_key, csv_root, parquet_root)
    if not ok:
        typer.secho(
            "Conversion failed. Please check logs for details.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.secho("✅ Conversion complete.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
