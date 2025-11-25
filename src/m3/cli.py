import logging
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from m3 import __version__
from m3.config import (
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
    init_duckdb_from_parquet,
    verify_table_rowcount,
)
from m3.datasets import DatasetRegistry

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
                f"Supported: {', '.join([ds.name for ds in DatasetRegistry.list_all()])}"
            ),
            metavar="DATASET_NAME",
        ),
    ] = "mimic-iv-demo",
    src: Annotated[
        str | None,
        typer.Option(
            "--src",
            help=(
                "Path to existing raw CSV.gz root (hosp/, icu/). If provided, download is skipped."
            ),
        ),
    ] = None,
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
    Initialize a local dataset in one step by detecting what's already present:
    - If Parquet exists: only initialize DuckDB views
    - If raw CSV.gz exists but Parquet is missing: convert then initialize
    - If neither exists: download (demo only), convert, then initialize

    Notes:
    - Auto-download is based on the dataset definition URL.
    - For datasets without a download URL (e.g. mimic-iv-full), you must provide the --src path or place files in the expected location.
    """
    logger.info(f"CLI 'init' called for dataset: '{dataset_name}'")

    dataset_key = dataset_name.lower()
    dataset_config = get_dataset_config(dataset_key)
    if not dataset_config:
        typer.secho(
            f"Error: Dataset '{dataset_name}' is not supported or not configured.",
            fg=typer.colors.RED,
            err=True,
        )
        typer.secho(
            f"Supported datasets are: {', '.join([ds.name for ds in DatasetRegistry.list_all()])}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve roots
    pq_root = get_dataset_parquet_root(dataset_key)
    if pq_root is None:
        typer.secho(
            "Could not determine dataset directories.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    csv_root_default = pq_root.parent.parent / "raw_files" / dataset_key
    csv_root = Path(src).resolve() if src else csv_root_default

    # Presence detection (check for any parquet or csv.gz files)
    parquet_present = any(pq_root.rglob("*.parquet"))
    raw_present = any(csv_root.rglob("*.csv.gz"))

    typer.echo(f"Detected dataset: '{dataset_key}'")
    typer.echo(f"Raw root: {csv_root}  (present={raw_present})")
    typer.echo(f"Parquet root: {pq_root}  (present={parquet_present})")

    # Step 1: Ensure raw dataset exists (download if missing, for requires_authentication datasets, inform and return)
    if not raw_present and not parquet_present:
        requires_auth = dataset_config.get("requires_authentication", False)

        if requires_auth:
            base_url = dataset_config.get("file_listing_url")

            typer.secho(
                f"❌ Files not found for credentialed dataset '{dataset_key}'.",
                fg=typer.colors.RED,
            )
            typer.echo("To download this credentialed dataset:")
            typer.echo(
                f"1. Ensure you have signed the DUA at: {base_url or 'https://physionet.org'}"
            )
            typer.echo(
                "2. Run this command (you will be asked for your PhysioNet password):"
            )
            typer.echo("")

            # Wget command tailored to the user's path
            wget_cmd = f"wget -r -N -c -np --user YOUR_USERNAME --ask-password {base_url} -P {csv_root}"
            typer.secho(f"   {wget_cmd}", fg=typer.colors.CYAN)
            typer.echo("")
            typer.echo(f"3. Re-run 'm3 init {dataset_key}'")
            return

        listing_url = dataset_config.get("file_listing_url")
        if listing_url:
            out_dir = csv_root_default
            out_dir.mkdir(parents=True, exist_ok=True)

            typer.echo(f"Downloading dataset: '{dataset_key}'")
            typer.echo(f"Listing URL: {listing_url}")
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

            # Point csv_root to the downloaded location
            csv_root = out_dir
            raw_present = True
        else:
            typer.secho(
                f"Auto-download is not available for '{dataset_key}'.",
                fg=typer.colors.YELLOW,
            )
            typer.secho(
                (
                    "To initialize this dataset:\n"
                    "1) Download the raw data manually.\n"
                    f"2) Place the raw CSV.gz files under: {csv_root_default}\n"
                    "   (or use --src to point to their location)\n"
                    f"3) Then re-run: m3 init {dataset_key}"
                ),
                fg=typer.colors.WHITE,
            )
            return

    # Step 2: Ensure Parquet exists (convert if missing)
    if not parquet_present:
        typer.echo(f"Converting dataset: '{dataset_key}'")
        typer.echo(f"CSV root: {csv_root}")
        typer.echo(f"Parquet destination: {pq_root}")
        ok = convert_csv_to_parquet(dataset_key, csv_root, pq_root)
        if not ok:
            typer.secho(
                "Conversion failed. Please check logs for details.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        typer.secho("✅ Conversion complete.", fg=typer.colors.GREEN)

    # Step 3: Initialize DuckDB over Parquet
    final_db_path = (
        Path(db_path_str).resolve()
        if db_path_str
        else get_default_database_path(dataset_key)
    )
    if not final_db_path:
        typer.secho(
            f"Critical Error: Could not determine database path for '{dataset_name}'.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    final_db_path.parent.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Initializing dataset: '{dataset_name}'")
    typer.echo(f"DuckDB path: {final_db_path}")
    typer.echo(f"Parquet root: {pq_root}")

    if not pq_root or not pq_root.exists():
        typer.secho(
            f"Parquet directory not found at {pq_root}.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    init_successful = init_duckdb_from_parquet(
        dataset_name=dataset_key, db_target_path=final_db_path
    )
    if not init_successful:
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

    verification_table_name = dataset_config.get("primary_verification_table")
    if not verification_table_name:
        logger.warning(
            f"No 'primary_verification_table' configured for '{dataset_name}'. Skipping DB query test."
        )
        typer.secho(
            (
                f"Dataset '{dataset_name}' initialized to {final_db_path}. "
                f"Parquet at {pq_root}."
            ),
            fg=typer.colors.GREEN,
        )
    else:
        try:
            record_count = verify_table_rowcount(final_db_path, verification_table_name)
            typer.secho(
                f"Database verification successful: Found {record_count} records in table '{verification_table_name}'.",
                fg=typer.colors.GREEN,
            )
            typer.secho(
                f"Dataset '{dataset_name}' ready at {final_db_path}. Parquet at {pq_root}.",
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
    set_active_dataset(dataset_key)


@app.command("use")
def use_cmd(
    target: Annotated[
        str,
        typer.Argument(
            help="Select active dataset: name (e.g., mimic-iv-full)", metavar="TARGET"
        ),
    ],
):
    """Set the active dataset selection for the project."""
    target = target.lower()

    # 1. Check if dataset is registered
    # We use detect_available_local_datasets just to get the list + status,
    # but we could also just check DatasetRegistry directly.
    availability = detect_available_local_datasets().get(target)

    if not availability:
        typer.secho(
            f"Dataset '{target}' not found or not registered.",
            fg=typer.colors.RED,
            err=True,
        )
        # List available
        supported = ", ".join([ds.name for ds in DatasetRegistry.list_all()])
        typer.secho(f"Supported datasets: {supported}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # 2. Set it active immediately (don't block on files)
    set_active_dataset(target)
    typer.secho(f"Active dataset set to '{target}'.", fg=typer.colors.GREEN)

    # 3. Warn if local files are missing (helpful info, not a blocker)
    if not availability["parquet_present"]:
        typer.secho(
            f"⚠️  Note: Local Parquet files not found at {availability['parquet_root']}.",
            fg=typer.colors.YELLOW,
        )
        typer.echo(
            "   This is fine if you are using the BigQuery backend.\n"
            "   If you intend to use DuckDB (local), run 'm3 init' first."
        )
    else:
        typer.secho(
            "  Local: Available",
        )

    # 4. Check BigQuery support
    ds_def = DatasetRegistry.get(target)
    if ds_def:
        if not ds_def.bigquery_dataset_ids:
            typer.secho(
                "⚠️  Warning: This dataset is not configured for BigQuery.",
                fg=typer.colors.YELLOW,
            )
            typer.echo("   If you are using the BigQuery backend, queries will fail.")
        else:
            typer.echo(f"  BigQuery: Available (Project: {ds_def.bigquery_project_id})")


@app.command("status")
def status_cmd():
    """Show active dataset, local DB path, Parquet presence, quick counts and sizes."""
    active = get_active_dataset() or "(unset)"
    typer.secho(
        f"Active dataset: {active}",
        fg=typer.colors.BRIGHT_GREEN if active != "(unset)" else typer.colors.YELLOW,
    )

    availability = detect_available_local_datasets()
    if not availability:
        typer.echo("No datasets detected.")
        return

    for label, info in availability.items():
        typer.secho(f"\n=== {label.upper()} ===", fg=typer.colors.BRIGHT_BLUE)

        parquet_icon = "✅" if info["parquet_present"] else "❌"
        db_icon = "✅" if info["db_present"] else "❌"

        typer.echo(f"  parquet_present: {parquet_icon}  db_present: {db_icon}")
        typer.echo(f"  parquet_root: {info['parquet_root']}")
        typer.echo(f"  db_path: {info['db_path']}")

        if info["parquet_present"]:
            try:
                size_bytes = compute_parquet_dir_size(Path(info["parquet_root"]))
                size_gb = float(size_bytes) / (1024**3)
                typer.echo(f"  parquet_size_gb: {size_gb:.4f} GB")
            except Exception:
                typer.echo("  parquet_size_gb: (skipped)")

        # Show BigQuery status
        ds_def = DatasetRegistry.get(label)
        if ds_def:
            bq_status = "✅" if ds_def.bigquery_dataset_ids else "❌"
            typer.echo(f"  BigQuery Support: {bq_status}")

        # Try a quick rowcount on the verification table if db present
        cfg = get_dataset_config(label)
        if info["db_present"] and cfg:
            try:
                count = verify_table_rowcount(
                    Path(info["db_path"]), cfg["primary_verification_table"]
                )
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
        typer.secho(
            "❌ Error: --project-id can only be used with --backend bigquery",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # bigquery: requires project_id, db_path not allowed
    if backend == "bigquery" and db_path:
        typer.secho(
            "❌ Error: --db-path can only be used with --backend duckdb",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    if backend == "bigquery" and not project_id:
        typer.secho(
            "❌ Error: --project-id is required when using --backend bigquery",
            fg=typer.colors.RED,
            err=True,
        )
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

        # For duckdb, pass db_path only if explicitly provided.
        # If omitted, the server will resolve it dynamically based on the active dataset.
        if backend == "duckdb" and db_path:
            inferred_db_path = Path(db_path).resolve()
            cmd.extend(["--db-path", str(inferred_db_path)])

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


if __name__ == "__main__":
    app()
