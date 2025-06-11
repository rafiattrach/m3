import logging
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from m3 import __version__
from m3.config import (
    SUPPORTED_DATASETS,
    get_dataset_config,
    get_dataset_raw_files_path,
    get_default_database_path,
    logger,
)
from m3.data_io import initialize_dataset

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
                "Dataset to initialize. Default: 'mimic-iv-demo'. "
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
            help="Custom path for the SQLite DB. Uses a default if not set.",
        ),
    ] = None,
):
    """
    Download a supported dataset (e.g., 'mimic-iv-demo') and load it into a local SQLite

    Raw downloaded files are stored in a `m3_data/raw_files/<dataset_name>/` subdirectory
    and are **not** deleted after processing.
    The SQLite database is stored in `m3_data/databases/` or path specified by `--db-path`.
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

    # Currently, only mimic-iv-demo is fully wired up as an example.
    # This check can be removed or adapted as more datasets are supported.
    if dataset_key != "mimic-iv-demo":
        typer.secho(
            (
                f"Warning: While '{dataset_name}' is configured, only 'mimic-iv-demo' "
                "is fully implemented for initialization in this version."
            ),
            fg=typer.colors.YELLOW,
        )

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

    # Ensure parent directory for the database exists
    final_db_path.parent.mkdir(parents=True, exist_ok=True)

    raw_files_storage_path = get_dataset_raw_files_path(
        dataset_key
    )  # Will be created if doesn't exist
    typer.echo(f"Initializing dataset: '{dataset_name}'")
    typer.echo(f"Target database path: {final_db_path}")
    typer.echo(f"Raw files will be stored at: {raw_files_storage_path.resolve()}")

    initialization_successful = initialize_dataset(
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

    # Basic verification by querying a known table
    verification_table_name = dataset_config.get("primary_verification_table")
    if not verification_table_name:
        logger.warning(
            f"No 'primary_verification_table' configured for '{dataset_name}'. "
            "Skipping DB query test."
        )
        typer.secho(
            (
                f"Dataset '{dataset_name}' initialized to {final_db_path}. "
                f"Raw files at {raw_files_storage_path.resolve()}."
            ),
            fg=typer.colors.GREEN,
        )
        typer.secho(
            "Skipped database query test as no verification table is set in config.",
            fg=typer.colors.YELLOW,
        )
        return

    try:
        conn = sqlite3.connect(final_db_path)
        cursor = conn.cursor()
        # A simple count query is usually safe and informative.
        query = f"SELECT COUNT(*) FROM {verification_table_name};"
        logger.debug(f"Executing verification query: '{query}' on {final_db_path}")
        cursor.execute(query)
        count_result = cursor.fetchone()
        conn.close()

        if count_result is None:
            raise sqlite3.Error(
                f"Query on table '{verification_table_name}' returned no result (None)."
            )

        record_count = count_result[0]
        typer.secho(
            (
                f"Database verification successful: Found {record_count} records in "
                f"table '{verification_table_name}'."
            ),
            fg=typer.colors.GREEN,
        )
        typer.secho(
            (
                f"Dataset '{dataset_name}' ready at {final_db_path}. "
                f"Raw files at {raw_files_storage_path.resolve()}."
            ),
            fg=typer.colors.BRIGHT_GREEN,
        )
    except sqlite3.Error as e:
        logger.error(
            (
                f"SQLite error during verification query on table "
                f"'{verification_table_name}': {e}"
            ),
            exc_info=True,
        )
        typer.secho(
            (
                f"Error verifying table '{verification_table_name}': {e}. "
                f"The database was created at {final_db_path}, but the test query "
                "failed. The data might be incomplete or corrupted."
            ),
            fg=typer.colors.RED,
            err=True,
        )
    except Exception as e:  # Catch any other unexpected errors
        logger.error(
            f"Unexpected error during database verification: {e}", exc_info=True
        )
        typer.secho(
            f"An unexpected error occurred during database verification: {e}",
            fg=typer.colors.RED,
            err=True,
        )


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
            help="Backend to use (sqlite or bigquery). Default: sqlite",
        ),
    ] = "sqlite",
    db_path: Annotated[
        str | None,
        typer.Option(
            "--db-path",
            "-p",
            help="Path to SQLite database (for sqlite backend)",
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
    if backend == "sqlite" and project_id:
        typer.secho(
            "❌ Error: --project-id can only be used with --backend bigquery",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if backend == "bigquery" and db_path:
        typer.secho(
            "❌ Error: --db-path can only be used with --backend sqlite",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Require project_id for BigQuery backend
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

        # Build command arguments
        cmd = [sys.executable, str(script_path)]

        if backend != "sqlite":
            cmd.extend(["--backend", backend])

        if backend == "sqlite" and db_path:
            cmd.extend(["--db-path", db_path])
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

        if backend != "sqlite":
            cmd.extend(["--backend", backend])

        if server_name != "m3":
            cmd.extend(["--server-name", server_name])

        if python_path:
            cmd.extend(["--python-path", python_path])

        if working_directory:
            cmd.extend(["--working-directory", working_directory])

        if backend == "sqlite" and db_path:
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
