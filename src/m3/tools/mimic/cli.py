import json
import logging
import os
from pathlib import Path

import typer
from beartype import beartype
from beartype.typing import Annotated, Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from m3.core.config import M3Config
from m3.core.tool.cli.base import BaseToolCLI, ToolConfig
from m3.core.utils.exceptions import M3ValidationError
from m3.core.utils.helpers import get_config
from m3.tools.mimic.components.data_io import DataIO
from m3.tools.mimic.components.utils import (
    get_default_database_path,
    load_supported_datasets,
)

logger = logging.getLogger(__name__)

console = Console()


@beartype
class MimicCLI(BaseToolCLI):
    @classmethod
    def get_app(cls) -> typer.Typer:
        app = typer.Typer(
            help="MIMIC-IV tool commands.",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        app.command(help="Initialise the dataset and database.")(cls.init)
        app.command(help="Configure the MIMIC-IV tool.")(cls.configure)
        app.command(help="Display the current status of the MIMIC-IV tool.")(cls.status)
        return app

    @classmethod
    def init(
        cls,
        dataset: Annotated[
            str,
            typer.Option(
                "--dataset",
                "-d",
                help="Dataset name to initialize (e.g., 'mimic-iv-demo').",
            ),
        ] = "mimic-iv-demo",
        db_path: Annotated[
            Optional[str],
            typer.Option(
                "--db-path",
                "-p",
                help="Path to save the SQLite DB (defaults to a standard location).",
            ),
        ] = None,
        force: Annotated[
            bool,
            typer.Option(
                "--force", "-f", help="Force re-download and re-initialization."
            ),
        ] = False,
    ) -> None:
        datasets = load_supported_datasets()
        if dataset.lower() not in datasets:
            console.print("[red]❌ Unknown dataset. Available:[/red]")
            table = Table(show_header=False)
            for ds in datasets.keys():
                table.add_row(f"[cyan]{ds}[/cyan]")
            console.print(table)
            raise typer.Exit(code=1)

        config = get_config()
        _db_path = (
            Path(db_path) if db_path else get_default_database_path(config, dataset)
        )
        if _db_path is None:
            console.print("[red]❌ Cannot determine DB path.[/red]")
            raise typer.Exit(code=1)

        if _db_path.exists() and not force:
            console.print(
                f"[yellow]⚠️ DB exists at {_db_path}. Use --force to overwrite.[/yellow]"
            )
            raise typer.Exit(code=1)

        data_io = DataIO(config)
        success = data_io.initialize(dataset, _db_path)

        if success:
            console.print(f"[green]✅ Initialized {dataset} at {_db_path}.[/green]")
        else:
            console.print(f"[red]❌ Initialization failed for {dataset}.[/red]")
            raise typer.Exit(code=1)

    @classmethod
    def configure(
        cls,
        backend: Annotated[
            Optional[str],
            typer.Option("--backend", "-b", help="Backend ('sqlite' or 'bigquery')."),
        ] = None,
        db_path: Annotated[
            Optional[str],
            typer.Option("--db-path", help="SQLite DB path (if backend=sqlite)."),
        ] = None,
        project_id: Annotated[
            Optional[str],
            typer.Option("--project-id", help="GCP Project ID (if backend=bigquery)."),
        ] = None,
        enable_oauth2: Annotated[
            bool,
            typer.Option("--enable-oauth2", "-o", help="Enable OAuth2."),
        ] = False,
        issuer_url: Annotated[
            Optional[str],
            typer.Option("--issuer-url", help="OAuth2 Issuer URL."),
        ] = None,
        audience: Annotated[
            Optional[str],
            typer.Option("--audience", help="OAuth2 Audience."),
        ] = None,
        required_scopes: Annotated[
            Optional[str],
            typer.Option(
                "--required-scopes", help="OAuth2 Required Scopes (comma-separated)."
            ),
        ] = None,
        jwks_url: Annotated[
            Optional[str],
            typer.Option("--jwks-url", help="OAuth2 JWKS URL (optional)."),
        ] = None,
        rate_limit_requests: Annotated[
            int,
            typer.Option("--rate-limit-requests", help="OAuth2 Rate Limit Requests."),
        ] = 100,
        output: Annotated[
            Optional[str],
            typer.Option("--output", "-o", help="Output path for config JSON."),
        ] = None,
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-v", help="Print config dict."),
        ] = False,
    ) -> ToolConfig:
        env_vars: Dict[str, str] = {}
        tool_params: Dict[str, Any] = {}

        console.print("[turquoise4]💬 Configuring MIMIC-IV tool...[/turquoise4]")

        if not backend:
            backend = typer.prompt(
                "Backend (sqlite/bigquery)", default="sqlite"
            ).lower()

        if backend not in ["sqlite", "bigquery"]:
            console.print("[red]❌ Invalid backend. Use 'sqlite' or 'bigquery'.[/red]")
            raise typer.Exit(code=1)

        env_vars["M3_BACKEND"] = backend
        tool_params["backend_key"] = backend

        backends_list = []
        if backend == "sqlite":
            if db_path is None:
                default_db = get_default_database_path(get_config(), "mimic-iv-demo")
                if default_db is None:
                    raise M3ValidationError("Cannot determine default DB path")
                console.print(f"[yellow]💬 Default DB path: {default_db}[/yellow]")
                db_path = typer.prompt(
                    "SQLite DB path (Enter for default)", default=str(default_db)
                )
            if db_path and not Path(db_path).exists():
                console.print(
                    f"[yellow]⚠️ DB path {db_path} does not exist. Using default path.[/yellow]"
                )
                db_path = str(get_default_database_path(get_config(), "mimic-iv-demo"))
            env_vars["M3_DB_PATH"] = db_path
            backends_list.append({"type": "sqlite", "params": {"path": db_path}})
        elif backend == "bigquery":
            if project_id is None:
                project_id = typer.prompt("GCP Project ID (required)")
            if not project_id:
                raise M3ValidationError("Project ID required for BigQuery")
            env_vars["M3_PROJECT_ID"] = project_id
            env_vars["GOOGLE_CLOUD_PROJECT"] = project_id
            backends_list.append(
                {"type": "bigquery", "params": {"project": project_id}}
            )

        tool_params["backends"] = backends_list

        if enable_oauth2:
            if issuer_url is None:
                issuer_url = typer.prompt("Issuer URL")
            if audience is None:
                audience = typer.prompt("Audience")
            if required_scopes is None:
                required_scopes = typer.prompt(
                    "Scopes [read:mimic-data]", default="read:mimic-data"
                )
            env_vars.update(
                {
                    "M3_OAUTH2_ENABLED": "true",
                    "M3_OAUTH2_ISSUER_URL": issuer_url,
                    "M3_OAUTH2_AUDIENCE": audience,
                    "M3_OAUTH2_REQUIRED_SCOPES": required_scopes,
                }
            )
            if jwks_url is None:
                jwks_url = typer.prompt("JWKS URL (optional)", default="")
                jwks_url = jwks_url.strip()
            if jwks_url:
                env_vars["M3_OAUTH2_JWKS_URL"] = jwks_url
            env_vars["M3_OAUTH2_RATE_LIMIT_REQUESTS"] = str(rate_limit_requests)

        console.print(
            "\n[turquoise4]💬 Additional env vars (key=value, Enter to finish):[/turquoise4]"
        )
        additional_env = {}
        while True:
            env_var = typer.prompt("", default="", show_default=False)
            if not env_var:
                break
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                additional_env[key.strip()] = value.strip()
            else:
                console.print("[red]Invalid: Use key=value[/red]")
        env_vars.update(additional_env)

        config_dict = {"env_vars": env_vars, "tool_params": tool_params}

        output = output or "mimic_config.json"
        with open(output, "w") as f:
            json.dump(config_dict, f, indent=4)
        console.print(f"[green]✅ Config dict saved to {output}[/green]")

        if verbose:
            console.print(
                Panel(
                    json.dumps(config_dict, indent=2),
                    title="[bold green]Configuration[/bold green]",
                    border_style="green",
                )
            )
        return config_dict

    @classmethod
    def status(cls, verbose: bool = False) -> None:
        try:
            config = M3Config(env_vars=os.environ.copy())
            _db_path = (
                str(get_default_database_path(config, "mimic-iv-demo")) or "Default"
            )

            table = Table(title="[bold green]MIMIC Tool Status[/bold green]")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_row("Backend", config.get_env_var("M3_BACKEND", "sqlite"))
            table.add_row("DB Path", config.get_env_var("M3_DB_PATH", _db_path))
            table.add_row(
                "OAuth2 Enabled", config.get_env_var("M3_OAUTH2_ENABLED", "No")
            )
            console.print(table)
            if verbose:
                env_table = Table(
                    title="[bold green]Environment Variables (M3_*)[/bold green]"
                )
                env_table.add_column("Key", style="cyan")
                env_table.add_column("Value", style="magenta")
                for key, value in sorted(config.env_vars.items()):
                    if key.startswith("M3_"):
                        env_table.add_row(key, value)
                console.print(env_table)
        except Exception as e:
            console.print(f"[red]❌ Error getting status: {e}[/red]")
            logger.error(f"Status failed: {e}")
