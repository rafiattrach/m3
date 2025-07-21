import json
import logging
import os
from pathlib import Path

import typer
from beartype import beartype
from beartype.typing import Annotated, Dict, Optional
from rich.console import Console

from m3.core.tool.cli.base import BaseToolCLI, ToolConfig

logger = logging.getLogger(__name__)

console = Console()


@beartype
class M3ToolBuilderCLI(BaseToolCLI):
    """M3ToolBuilder Command Line Interface."""

    @classmethod
    def get_app(cls) -> Optional[typer.Typer]:
        app = typer.Typer(
            help="M3ToolBuilder tool commands.",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        app.command(help="Initialize the M3ToolBuilder tool.")(cls.init)
        app.command(help="Configure the M3ToolBuilder tool.")(cls.configure)
        app.command(help="Display the current status of the M3ToolBuilder tool.")(
            cls.status
        )
        return app

    @classmethod
    def init(
        cls,
        dataset: Annotated[
            Optional[str],
            typer.Option(
                "--dataset",
                help="Dataset to initialize (e.g., 'mimic-iv-demo'). If not provided, uses default knowledge base.",
            ),
        ] = None,
    ) -> Dict[str, str]:
        console.print("[turquoise4]💬 Initializing M3ToolBuilder...[/turquoise4]")
        knowledge_path = Path(__file__).parent / "configurations" / "knowledge.yaml"
        if not knowledge_path.exists():
            raise ValueError(f"Knowledge base not found at {knowledge_path}")
        console.print("[green]✅ Knowledge base loaded successfully.[/green]")
        return {"status": "initialized", "dataset": dataset or "default"}

    @classmethod
    def configure(
        cls,
        output: Annotated[
            Optional[str],
            typer.Option(
                "--output",
                "-o",
                help="Path to save configuration JSON (defaults to 'm3toolbuilder_config.json').",
            ),
        ] = "m3toolbuilder_config.json",
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-v", help="Enable verbose output."),
        ] = False,
    ) -> ToolConfig:
        console.print("[turquoise4]💬 Configuring M3ToolBuilder...[/turquoise4]")
        env_vars = {
            "M3_TOOLBUILDER_KNOWLEDGE_PATH": str(
                Path(__file__).parent / "configurations" / "knowledge.yaml"
            ),
        }
        tool_params = {}
        config_dict = {"env_vars": env_vars, "tool_params": tool_params}

        with open(output, "w") as f:
            json.dump(config_dict, f, indent=4)
        console.print(f"[green]✅ Config saved to {output}.[/green]")

        if verbose:
            console.print(json.dumps(config_dict, indent=2))
        return config_dict

    @classmethod
    def status(
        cls,
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-v", help="Enable verbose output."),
        ] = False,
    ) -> None:
        console.print("[turquoise4]💬 M3ToolBuilder Status:[/turquoise4]")
        knowledge_path = os.getenv("M3_TOOLBUILDER_KNOWLEDGE_PATH", "Not set")
        console.print(f"Knowledge Base: {knowledge_path}")
        if verbose:
            console.print("Environment Variables:")
            for key, value in os.environ.items():
                if key.startswith("M3_TOOLBUILDER_"):
                    console.print(f"  {key}: {value}")
