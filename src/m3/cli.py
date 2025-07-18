import importlib
import inspect
import json
import logging
import os
import sys
from pathlib import Path
from typing import no_type_check

import rich.box as box
import typer
from beartype import beartype
from beartype.typing import Annotated, Dict, Optional, Type
from rich.cells import cell_len
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich_pyfiglet import RichFiglet
from thefuzz import process

from m3 import __version__
from m3.core.config import M3Config
from m3.core.preset.registry import ALL_PRESETS
from m3.core.tool.cli.base import BaseToolCLI
from m3.core.utils.exceptions import M3ConfigError, M3PresetError, M3ValidationError
from m3.core.utils.logging import setup_logging
from m3.m3 import M3
from m3.tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)

console = Console()


@beartype
class M3CLI:
    """M3 Command Line Interface (M3-CLI), manages all M3 supported MCP tools and servers.

    Provides a command-line interface to interact with M3's modular MCP tools and servers.
    If you would like to do it programmatically, you can use the `M3` class directly.

    CLI Usage Examples:
        ```bash
        # Show CLI version
        m3 --version

        # List available presets
        m3 list-presets

        # List available tools
        m3 list-tools

        # Run M3 with default preset (starts the MCP server)
        m3 run --presets default_m3

        # Run with custom pipeline JSON (assuming custom_pipeline.json exists and is a M3 saved pipeline)
        m3 run --pipeline custom_pipeline.json

        # Build M3 config without running
        m3 build --presets default_m3 --output m3_config.json

        # Build with multiple presets
        m3 build --presets preset1,preset2 --config-type claude --output m3_config.json # By default, --output is not mandatory.

        # Search for presets or M3-supported MCP tools matching the search query
        m3 search mimic-IV # Will output matching presets and tools

        # Add a tool to a newly-created pipeline
        m3 pipeline mimic --new-pipeline custom_pipeline.json

        # Add a tool to an existing pipeline
        m3 pipeline mimic --to-pipeline existing_pipeline.json

        # Tool-specific subcommands (e.g., for mimic tool in this very example) — `m3 tools <tool_name> <command>`
        m3 tools mimic init --dataset mimic-iv-demo --db-path demo.db
        m3 tools mimic configure --backend sqlite --enable-oauth2 # If you do not specify --backend, it'll launch CLI-interactive configuration.
        m3 tools mimic status # More used internally, but you can use it to check the status of the mimic tool if env vars are applied.
        m3 tools mimic --help
    """

    def __init__(self) -> None:
        self._display_banner()
        self.app: typer.Typer = typer.Typer(
            help="\n\n",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        self.tools_app: typer.Typer = typer.Typer(help="Tool-specific commands.")
        self.app.callback()(self.main_callback)
        self.app.command(
            help="List all available `M3` presets, which are pre-configured pipelines ready to run out-of-the-box."
        )(self.list_presets)
        self.app.command(
            help="List all available tools supported by `M3` for integration into MCP pipelines."
        )(self.list_tools)
        self.app.command(
            help="`Run` the `M3` `fastMCP` instance (from `--presets` or a `pipeline` config), build the MCP server config, and start the server (defaults to `FastMCP`)."
        )(self.run)
        self.app.command(
            help="`Build` a MCP server configuration (e.g., for `Claude Desktop` or `FastMCP`) from a `pipeline` without starting the server."
        )(self.build)
        self.app.command(
            help="`Compose` || `extend` an `M3` pipeline by adding a M3-MCP tool and generating its configuration; Hint: follow next by `build`ing you pipeline, e.g for `Claude Desktop`."
        )(self.pipeline)
        self.app.add_typer(
            self.tools_app,
            name="tools",
            help="Access tool-specific subcommands. For details, run `m3 tools <tool_name> --help`.",
        )
        self.app.command(
            help="`Search` for `M3` presets or supported MCP tools based on a query, such as `mimic-IV`."
        )(self.search)
        self.tool_clis = self._load_tool_clis()

    def __call__(self) -> None:
        self.app()

    @staticmethod
    def version_callback(value: bool) -> None:
        if value:
            console.print(f"[bold green]💬 M3 CLI Version: {__version__}[/bold green]")
            raise typer.Exit()

    @no_type_check
    def main_callback(
        self,
        version: Annotated[
            bool,
            typer.Option(
                "--version",
                "-v",
                callback=version_callback.__func__,
                is_eager=True,
                help="Show CLI version.",
            ),
        ] = False,
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-V", help="Enable DEBUG level logging."),
        ] = False,
    ) -> None:
        level = "DEBUG" if verbose else "INFO"
        setup_logging(level=level)
        if verbose:
            logger.debug("Verbose mode enabled.")

    def list_presets(self) -> None:
        console.print("[bold green]💬 Available Presets[/bold green]")
        table = Table(title="")
        table.add_column("Preset", style="cyan")
        for preset in ALL_PRESETS.keys():
            table.add_row(preset)
        console.print(table)

    def list_tools(self) -> None:
        console.print("[bold green]💬 Available Tools[/bold green]")
        table = Table(title="")
        table.add_column("Tool", style="cyan")
        for tool in ALL_TOOLS.keys():
            table.add_row(tool)
        console.print(table)

    def run(
        self,
        pipeline: Annotated[
            Optional[str],
            typer.Option("--pipeline", help="Pipeline JSON path (!= Presets)."),
        ] = None,
        presets: Annotated[
            Optional[str],
            typer.Option(
                "--presets",
                help="Comma-separated M3 pipeline presets if no pipeline in hand.",
            ),
        ] = "default_m3",
        config_type: Annotated[
            str,
            typer.Option(
                "--config-type",
                help="Final MCP host Configuration type for build (e.g., `fastmcp`, `claude`. etc).",
            ),
        ] = "fastmcp",
        config_path: Annotated[
            Optional[str],
            typer.Option(
                "--config-path",
                "-c",
                help="Path where to save your M3 pipeline JSON configuration (defaults to `m3_pipeline.json` or the --pipeline path if provided).",
            ),
        ] = None,
        show_status: Annotated[
            bool,
            typer.Option(
                "--show-status",
                help="Display tool status post-build. Mostly used internally.",
            ),
        ] = True,
        command: Annotated[
            Optional[str],
            typer.Option(
                "--command",
                help="Custom command for Final MCP server (e.g., `python3` or a specific path).",
            ),
        ] = None,
        args: Annotated[
            Optional[str],
            typer.Option(
                "--args",
                help="Comma-separated arguments for Final MCP server (e.g., `[-m,custom.module]`).",
            ),
        ] = None,
        cwd: Annotated[
            Optional[str],
            typer.Option("--cwd", help="Working directory for Final MCP server."),
        ] = None,
        module_name: Annotated[
            Optional[str],
            typer.Option(
                "--module-name",
                help="Module name for default arguments (e.g., `custom.runner`).",
            ),
        ] = None,
    ) -> None:
        console.print("[bold green]💬 Starting M3 run...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError(
                    "Cannot specify both --pipeline and --config-path. When using --pipeline, the pipeline is loaded and saved back to the same file."
                )
            config = M3Config(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "m3_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(
                    f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]"
                )
                m3 = M3.load(pipeline)
            else:
                m3 = M3(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(
                            preset, available_presets
                        ) or (
                            None,
                            0,
                        )
                        suggestion_text = (
                            f" Did you mean '{best_match}'?" if score >= 80 else ""
                        )
                        raise M3PresetError(
                            f"Unknown preset: {preset}. Use `m3 list-presets`.{suggestion_text}"
                        )
                    console.print(
                        f"[bold green]💬 Applying preset '{preset}'...[/bold green]"
                    )
                    m3 = m3.with_preset(preset)
            console.print(
                f"[bold green]💬 Building M3 with config type '{config_type}'...[/bold green]"
            )
            args_list = args.split(",") if args else None
            m3.build(
                type=config_type,
                command=command,
                args=args_list,
                cwd=cwd,
                module_name=module_name,
                pipeline_config_path=_config_path,
                save_path=None,
            )
            m3.save(_config_path)
            console.print(
                f"[bold green]💬 ✅ Saved pipeline config to {_config_path}.[/bold green]"
            )
            if show_status:
                self._status()
            console.print("[bold green]💬 Starting M3 MCP server...[/bold green]")
            m3.run()
        except (M3ValidationError, M3PresetError, ValueError) as e:
            logger.error(f"Run failed: {e}")
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e
        except Exception as e:
            logger.error(f"Unexpected error in run: {e}")
            console.print(f"[red]❌ Unexpected error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def build(
        self,
        pipeline: Annotated[
            Optional[str],
            typer.Option("--pipeline", help="Pipeline JSON path (!= Presets)."),
        ] = None,
        presets: Annotated[
            Optional[str],
            typer.Option(
                "--presets",
                help="Comma-separated M3 pipeline presets if no pipeline in hand.",
            ),
        ] = "default_m3",
        config_type: Annotated[
            str,
            typer.Option(
                "--config-type",
                help="Configuration type for the MCP server (e.g., `fastmcp`, `claude`, etc.).",
            ),
        ] = "fastmcp",
        config_path: Annotated[
            Optional[str],
            typer.Option(
                "--config-path",
                "-c",
                help="Path where to save your M3 pipeline JSON configuration (defaults to `m3_pipeline.json` or the --pipeline path if provided).",
            ),
        ] = None,
        output: Annotated[
            Optional[str],
            typer.Option(
                "--output",
                "-o",
                help="Output path for the Final MCP server configuration (defaults depends on `config_type` but could be e.g `m3_claude_config.json` for `claude`).",
            ),
        ] = None,
        show_status: Annotated[
            bool,
            typer.Option(
                "--show-status",
                help="Display tool status post-build. Mostly used internally.",
            ),
        ] = True,
        command: Annotated[
            Optional[str],
            typer.Option(
                "--command",
                help="Custom command for MCP server (e.g., `python3` or a specific path).",
            ),
        ] = None,
        args: Annotated[
            Optional[str],
            typer.Option(
                "--args",
                help="Comma-separated arguments for MCP server (e.g., `[-m,custom.module]`).",
            ),
        ] = None,
        cwd: Annotated[
            Optional[str],
            typer.Option("--cwd", help="Working directory for MCP server."),
        ] = None,
        module_name: Annotated[
            Optional[str],
            typer.Option(
                "--module-name",
                help="Module name for default arguments (e.g., `custom.runner`).",
            ),
        ] = None,
    ) -> None:
        console.print("[bold green]💬 Starting M3 build...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError(
                    "Cannot specify both --pipeline and --config-path. When using --pipeline, the pipeline is loaded and saved back to the same file."
                )
            config = M3Config(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "m3_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(
                    f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]"
                )
                m3 = M3.load(pipeline)
            else:
                m3 = M3(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(
                            preset, available_presets
                        ) or (
                            None,
                            0,
                        )
                        suggestion_text = (
                            f" Did you mean '{best_match}'?" if score >= 80 else ""
                        )
                        raise M3PresetError(
                            f"Unknown preset: {preset}. Use `m3 list-presets`.{suggestion_text}"
                        )
                    console.print(
                        f"[bold green]💬 Applying preset '{preset}'...[/bold green]"
                    )
                    m3 = m3.with_preset(preset)
            _save_path = os.path.abspath(output) if output else None
            console.print(
                f"[bold green]💬 Building M3 with config type '{config_type}'...[/bold green]"
            )
            args_list = args.split(",") if args else None
            m3.build(
                type=config_type,
                command=command,
                args=args_list,
                cwd=cwd,
                module_name=module_name,
                pipeline_config_path=_config_path,
                save_path=_save_path,
            )
            m3.save(_config_path)
            console.print("[bold green]💬 ✅ Pipeline config saved.[/bold green]")
            if show_status:
                self._status()
        except (M3ValidationError, M3PresetError, ValueError) as e:
            logger.error(f"Build failed: {e}")
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e
        except Exception as e:
            logger.error(f"Unexpected error in build: {e}")
            console.print(f"[red]❌ Unexpected error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def pipeline(
        self,
        tool_name: Annotated[
            str,
            typer.Argument(
                help="Tool to incorporate to your newly-designed or already-ready M3 pipeline (e.g., `mimic`)."
            ),
        ],
        to_pipeline: Annotated[
            Optional[str],
            typer.Option(
                "--to-pipeline",
                help="Whether or not you are adding to an existing M3 pipeline. If so, provide the path to the pipeline JSON file. It'll append the tool to the existing pipeline.",
            ),
        ] = None,
        new_pipeline: Annotated[
            Optional[str],
            typer.Option(
                "--new-pipeline",
                help="Whether or not you are creating a new M3 pipeline. If so, provide the path to the new pipeline JSON file (defaults to `m3_pipeline.json`).",
            ),
        ] = "m3_pipeline.json",
        tool_config: Annotated[
            Optional[str],
            typer.Option(
                "--tool-config",
                help="Path to pre-generated tool config JSON (from 'm3 tools <tool> configure --output ...'). If provided, uses this instead of interactive configuration.",
            ),
        ] = None,
    ) -> None:
        console.print(
            f"[bold green]💬 Adding tool '{tool_name}' to pipeline...[/bold green]"
        )
        if tool_name not in ALL_TOOLS:
            raise M3ValidationError(f"Unknown tool: {tool_name}. Use `m3 list-tools`.")

        try:
            tool_cli_class = self._get_tool_cli_class(tool_name)

            if tool_config:
                if not Path(tool_config).exists():
                    raise M3ValidationError(
                        f"Tool config file not found: {tool_config}"
                    )
                with open(tool_config) as f:
                    tool_dict = json.load(f)
            else:
                tool_dict = tool_cli_class.configure()

            pipeline_path = to_pipeline or new_pipeline
            if to_pipeline and Path(to_pipeline).exists():
                m3: M3 = M3.load(to_pipeline)
                console.print(f"[bold green]💬 Appending to {to_pipeline}[/bold green]")
            else:
                m3 = M3()
                console.print(
                    f"[bold green]💬 Creating new pipeline at {pipeline_path}[/bold green]"
                )

            prefixed_env = {
                f"{key}": value  # In the future, to avoid tools-vars conflicts, we could f"{tool_name.upper()}_{key}"
                for key, value in tool_dict.get("env_vars", {}).items()
            }

            m3.config.merge_env(prefixed_env)

            tool_cls = ALL_TOOLS[tool_name]
            tool_params = tool_dict.get("tool_params", {})
            tool = tool_cls.from_dict(tool_params)
            m3 = m3.with_tool(tool)

            m3.build()
            m3.save(pipeline_path)
            console.print(
                f"[bold green]💬 ✅ Pipeline updated: {pipeline_path} (tools: {len(m3.tools)})[/bold green]"
            )
        except M3ConfigError as e:
            logger.error(f"Env merge failed: {e}")
            console.print(f"[red]❌ Env conflict: {e}[/red]")
            raise typer.Exit(1) from e
        except M3ValidationError as e:
            logger.error(f"Validation failed: {e}")
            console.print(f"[red]❌ {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            logger.error(f"Failed to add {tool_name}: {e}", exc_info=True)
            console.print(f"[red]❌ Failed to add {tool_name}: {e}[/red]")
            raise typer.Exit(1) from e

    def search(
        self,
        query: Annotated[
            str,
            typer.Argument(help="Search query for presets or tools. E.g., `mimic-IV`."),
        ],
        type_: Annotated[
            str,
            typer.Option(
                "--type", help="Search type: `presets` or `tools` (default: both)."
            ),
        ] = "both",
        limit: Annotated[
            int,
            typer.Option(
                "--limit", help="Number of results to display. This is very optional."
            ),
        ] = 5,
    ) -> None:
        console.print(f"[bold green]💬 Searching for '{query}'...[/bold green]")
        if type_ not in ["presets", "tools", "both"]:
            console.print(
                "[red]❌ Invalid type. Use `presets`, `tools`, or `both`.[/red]"
            )
            raise typer.Exit(code=1)

        results = []
        if type_ in ["presets", "both"]:
            presets = list(ALL_PRESETS.keys())
            preset_matches = process.extract(query, presets, limit=limit)
            results.append(("Presets", preset_matches))
        if type_ in ["tools", "both"]:
            tools = list(ALL_TOOLS.keys())
            tool_matches = process.extract(query, tools, limit=limit)
            results.append(("Tools", tool_matches))

        for category, matches in results:
            table = Table(title=f"[bold green]💬 {category} matches[/bold green]")
            table.add_column("Match", style="cyan")
            table.add_column("Score", style="magenta")
            for match, score in matches:
                table.add_row(match, str(score))
            console.print(table)

    def _load_tool_clis(self) -> Dict[str, typer.Typer]:
        tool_clis = {}
        for tool_name in ALL_TOOLS:
            if cli := self._load_tool_cli(tool_name):
                tool_clis[tool_name] = cli
                self.tools_app.add_typer(
                    cli,
                    name=tool_name,
                    help=f"{tool_name.capitalize()} tool commands.",
                )
        if not tool_clis:
            raise M3ValidationError(
                "At least one tool CLI must be available to use M3's CLI."
            )
        return tool_clis

    @staticmethod
    def _load_tool_cli(tool_name: str) -> Optional[typer.Typer]:
        try:
            module_path = f"m3.tools.{tool_name}.cli"
            module = importlib.import_module(module_path)
            tool_cli_classes = [
                obj
                for name, obj in inspect.getmembers(module)
                if inspect.isclass(obj)
                and issubclass(obj, BaseToolCLI)
                and obj != BaseToolCLI
            ]
            if not tool_cli_classes:
                logger.warning(
                    f"No subclass of BaseToolCLI found in module for '{tool_name}'."
                )
                return None
            if len(tool_cli_classes) > 1:
                raise M3ValidationError(
                    f"Multiple BaseToolCLI subclasses found in module for '{tool_name}'."
                )
            tool_cli_class = tool_cli_classes[0]
            app = tool_cli_class.get_app()
            if not app:
                logger.warning(f"Tool '{tool_name}' returned None for get_app().")
                return None
            logger.debug(f"Loaded CLI for tool '{tool_name}'.")
            if not hasattr(tool_cli_class, "status"):
                raise M3ValidationError(
                    f"Tool '{tool_name}' must implement 'status' method."
                )
            if not hasattr(tool_cli_class, "init"):
                logger.debug(f"Tool '{tool_name}' does not support 'init'.")
            if not hasattr(tool_cli_class, "configure"):
                raise M3ValidationError(
                    f"Tool '{tool_name}' must implement 'configure' method."
                )
            return app
        except ImportError as e:
            logger.debug(f"No CLI for tool '{tool_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load CLI for '{tool_name}': {e}")
            return None

    @staticmethod
    def _get_tool_cli_class(tool_name: str) -> Type[BaseToolCLI]:
        try:
            module_path = f"m3.tools.{tool_name}.cli"
            module = importlib.import_module(module_path)
            tool_cli_classes = [
                obj
                for name, obj in inspect.getmembers(module)
                if inspect.isclass(obj)
                and issubclass(obj, BaseToolCLI)
                and obj != BaseToolCLI
            ]
            if not tool_cli_classes:
                raise M3ValidationError(
                    f"No subclass of BaseToolCLI found in module for '{tool_name}'."
                )
            if len(tool_cli_classes) > 1:
                raise M3ValidationError(
                    f"Multiple BaseToolCLI subclasses found in module for '{tool_name}'."
                )
            return tool_cli_classes[0]
        except ImportError as e:
            logger.error(f"Failed to import CLI module for '{tool_name}': {e}")
            raise M3ValidationError(
                f"CLI module import failed for '{tool_name}': {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error loading CLI class for '{tool_name}': {e}",
                exc_info=True,
            )
            raise M3ValidationError(
                f"Unexpected error loading CLI for '{tool_name}': {e}"
            ) from e

    def _status(
        self,
        tool: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        console.print("[bold green]💬 Checking status...[/bold green]")
        if tool and tool not in self.tool_clis:
            available_tools = list(self.tool_clis.keys())
            best_match, score = process.extractOne(tool, available_tools) or (None, 0)
            suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
            console.print(
                f"[red]❌ Unknown tool: {tool}. Use `m3 list-tools`.{suggestion_text}[/red]"
            )
            raise typer.Exit(code=1)

        tools_to_check = [tool] if tool else list(self.tool_clis.keys())

        for _tool in tools_to_check:
            try:
                tool_cli_class = self._get_tool_cli_class(_tool)
                tool_cli_class.status(verbose=verbose)
            except M3ValidationError as e:
                logger.error(f"Failed to load CLI class for '{_tool}': {e}")
                console.print(f"[red]❌ Error loading CLI for '{_tool}': {e}[/red]")
            except Exception as e:
                logger.error(f"Status failed for '{_tool}': {e}", exc_info=True)
                console.print(f"[red]❌ Error getting status for '{_tool}': {e}[/red]")

    @staticmethod
    def _display_banner() -> None:
        if any(arg in sys.argv for arg in ["--help", "-h"]):
            rich_fig = RichFiglet(
                "M3",
                font="ansi_shadow",
                colors=["#750014", "#750014", "#750014", "#FFFFFF", "#FFFFFF"],
                horizontal=True,
                remove_blank_lines=True,
            )
            entries = [
                ("🗂️", " Repo", "https://github.com/rafiattrach/m3"),
                ("📚", "Documentation", "https://rafiattrach.github.io/m3/"),
                ("📄", "Paper", "https://arxiv.org/abs/2507.01053"),
                ("🏎️", " Version", __version__),
            ]
            max_label_len = max(
                cell_len(emoji + " " + key + ":") for emoji, key, value in entries
            )
            group_items = [
                Text(""),
                Text(""),
                rich_fig,
                Text(""),
                Text(
                    "Simplifying secure clinical data access with conversational AI — M3 ",
                    style="bold italic turquoise4",
                ),
                Text(""),
            ]
            for i, (emoji, key, value) in enumerate(entries):
                label_plain = emoji + " " + key + ":"
                label_len = cell_len(label_plain)
                spaces = " " * (max_label_len - label_len + 2)
                line = f"[turquoise4]{label_plain}[/turquoise4]{spaces}{value}"
                group_items.append(Text.from_markup(line))
                if i == 1:
                    group_items.append(Text(""))
            group_items += [Text(""), Text("")]
            content = Group(*group_items)
            console.print(
                Panel(
                    content,
                    title="M3 CLI",
                    width=80,
                    title_align="left",
                    expand=False,
                    box=box.ROUNDED,
                    padding=(1, 5),
                )
            )


def main_cli() -> None:
    M3CLI()()


if __name__ == "__main__":
    main_cli()
