"""
Dynamic MCP Configuration Generator for M3 Server.
Generates MCP server configurations that can be copied and pasted into any MCP client.
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from m3.config import get_default_database_path

# Error messages
_DATABASE_PATH_ERROR_MSG = (
    "Could not determine default database path for mimic-iv-demo.\n"
    "Please run 'm3 init mimic-iv-demo' first."
)


class MCPConfigGenerator:
    """Generator for MCP server configurations."""

    def __init__(self):
        p = Path(__file__).resolve()
        while p != p.parent and not (p / "pyproject.toml").exists():
            p = p.parent
        self.current_dir = p
        self.default_python = self._get_default_python()

    def _get_default_python(self) -> str:
        """Get the default Python executable path."""
        # Try to use the current virtual environment
        if "VIRTUAL_ENV" in os.environ:
            venv_python = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)

        # Fall back to system python
        return shutil.which("python") or shutil.which("python3") or "python"

    def _validate_python_path(self, python_path: str) -> bool:
        """Validate that the Python path exists and is executable."""
        path = Path(python_path)
        return path.exists() and path.is_file() and os.access(path, os.X_OK)

    def _validate_directory(self, dir_path: str) -> bool:
        """Validate that the directory exists."""
        return Path(dir_path).exists() and Path(dir_path).is_dir()

    def generate_config(
        self,
        server_name: str = "m3",
        python_path: str | None = None,
        working_directory: str | None = None,
        backend: str = "duckdb",
        db_path: str | None = None,
        project_id: str | None = None,
        additional_env: dict[str, str] | None = None,
        module_name: str = "m3.mcp_server",
        oauth2_enabled: bool = False,
        oauth2_config: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generate MCP server configuration."""

        # Use defaults if not provided
        if python_path is None:
            python_path = self.default_python
        if working_directory is None:
            working_directory = str(self.current_dir)

        # Validate inputs
        if not self._validate_python_path(python_path):
            raise ValueError(f"Invalid Python path: {python_path}")
        if not self._validate_directory(working_directory):
            raise ValueError(f"Invalid working directory: {working_directory}")

        # Build environment variables
        env = {
            "PYTHONPATH": str(Path(working_directory) / "src"),
            "M3_BACKEND": backend,
        }

        # Add backend-specific environment variables
        if backend == "duckdb":
            if db_path:
                env["M3_DB_PATH"] = db_path
            # If no db_path, we rely on dynamic resolution in the server

        elif backend == "bigquery" and project_id:
            env["M3_PROJECT_ID"] = project_id
            env["GOOGLE_CLOUD_PROJECT"] = project_id

        # Add OAuth2 configuration if enabled
        if oauth2_enabled and oauth2_config:
            env.update(
                {
                    "M3_OAUTH2_ENABLED": "true",
                    "M3_OAUTH2_ISSUER_URL": oauth2_config.get("issuer_url", ""),
                    "M3_OAUTH2_AUDIENCE": oauth2_config.get("audience", ""),
                    "M3_OAUTH2_REQUIRED_SCOPES": oauth2_config.get(
                        "required_scopes", "read:mimic-data"
                    ),
                    "M3_OAUTH2_JWKS_URL": oauth2_config.get("jwks_url", ""),
                }
            )

            # Optional OAuth2 settings
            if oauth2_config.get("client_id"):
                env["M3_OAUTH2_CLIENT_ID"] = oauth2_config["client_id"]
            if oauth2_config.get("rate_limit_requests"):
                env["M3_OAUTH2_RATE_LIMIT_REQUESTS"] = str(
                    oauth2_config["rate_limit_requests"]
                )

        # Add any additional environment variables
        if additional_env:
            env.update(additional_env)

        # Create the configuration
        config = {
            "mcpServers": {
                server_name: {
                    "command": python_path,
                    "args": ["-m", module_name],
                    "cwd": working_directory,
                    "env": env,
                }
            }
        }

        return config

    def interactive_config(self) -> dict[str, Any]:
        """Interactive configuration builder."""
        print("🔧 M3 MCP Server Configuration Generator")
        print("=" * 50)

        # Server name
        print("\n🏷️  Server Configuration:")
        print("The server name is how your MCP client will identify this server.")
        server_name = (
            input("Server name (press Enter for default 'm3'): ").strip() or "m3"
        )

        # Python path
        print(f"\nDefault Python path: {self.default_python}")
        python_path = input(
            "Python executable path (press Enter for default): "
        ).strip()
        if not python_path:
            python_path = self.default_python

        # Working directory
        print(f"\nDefault working directory: {self.current_dir}")
        working_directory = input(
            "Working directory (press Enter for default): "
        ).strip()
        if not working_directory:
            working_directory = str(self.current_dir)

        # Backend selection - simplified
        print("\nChoose backend:")
        print("1. DuckDB (local database)")
        print("2. BigQuery (Google Cloud)")

        while True:
            backend_choice = input("Choose backend [1]: ").strip() or "1"
            if backend_choice in ["1", "2"]:
                break
            print("Please enter 1 or 2")

        backend = "duckdb" if backend_choice == "1" else "bigquery"

        # Backend-specific configuration
        db_path = None
        project_id = None

        if backend == "duckdb":
            print("\n📁 DuckDB Configuration:")
            default_db_path = get_default_database_path("mimic-iv-demo")
            if default_db_path is None:
                raise ValueError(_DATABASE_PATH_ERROR_MSG)
            print(f"Default database path: {default_db_path}")

            print(
                "\nLeaving database path empty allows switching datasets dynamically via 'm3 use'."
            )
            db_path = (
                input(
                    "DuckDB database path (optional, press Enter for dynamic): "
                ).strip()
                or None
            )

        elif backend == "bigquery":
            print("\n☁️  BigQuery Configuration:")
            project_id = None
            while not project_id:
                project_id = input(
                    "Google Cloud project ID (required for BigQuery): "
                ).strip()
                if not project_id:
                    print(
                        "❌ Project ID is required when using BigQuery backend. Please enter your GCP project ID."
                    )
            print(f"✅ Will use project: {project_id}")

        # OAuth2 Configuration
        oauth2_enabled = False
        oauth2_config = None

        print("\n🔐 OAuth2 Authentication (optional):")
        enable_oauth2 = input("Enable OAuth2 authentication? [y/N]: ").strip().lower()

        if enable_oauth2 in ["y", "yes"]:
            oauth2_enabled = True
            oauth2_config = {}

            print("\nOAuth2 Configuration:")
            oauth2_config["issuer_url"] = input(
                "OAuth2 Issuer URL (e.g., https://auth.example.com): "
            ).strip()
            oauth2_config["audience"] = input(
                "OAuth2 Audience (e.g., m3-api): "
            ).strip()
            oauth2_config["required_scopes"] = (
                input("Required Scopes [read:mimic-data]: ").strip()
                or "read:mimic-data"
            )

            # Optional settings
            jwks_url = input("JWKS URL (optional, auto-discovered if empty): ").strip()
            if jwks_url:
                oauth2_config["jwks_url"] = jwks_url

            rate_limit = input("Rate limit (requests per hour) [100]: ").strip()
            if rate_limit and rate_limit.isdigit():
                oauth2_config["rate_limit_requests"] = rate_limit

            print("✅ OAuth2 configuration added")

        # Additional environment variables
        additional_env = {}
        print("\n🌍 Additional environment variables (optional):")
        print(
            "Enter key=value pairs, one per line. Press Enter on empty line to finish."
        )
        while True:
            env_var = input("Environment variable: ").strip()
            if not env_var:
                break
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                additional_env[key.strip()] = value.strip()
                print(f"✅ Added: {key.strip()}={value.strip()}")
            else:
                print("❌ Invalid format. Use key=value")

        return self.generate_config(
            server_name=server_name,
            python_path=python_path,
            working_directory=working_directory,
            backend=backend,
            db_path=db_path,
            project_id=project_id,
            additional_env=additional_env if additional_env else None,
            module_name="m3.mcp_server",
            oauth2_enabled=oauth2_enabled,
            oauth2_config=oauth2_config,
        )


def print_config_info(config: dict[str, Any]):
    """Print configuration information."""
    # Get the first (and likely only) server configuration
    server_name = next(iter(config["mcpServers"].keys()))
    server_config = config["mcpServers"][server_name]

    print("\n📋 Configuration Summary:")
    print("=" * 30)
    print(f"🏷️  Server name: {server_name}")
    print(f"🐍 Python path: {server_config['command']}")
    print(f"📁 Working directory: {server_config['cwd']}")
    print(f"🔧 Backend: {server_config['env'].get('M3_BACKEND', 'unknown')}")

    if "M3_DB_PATH" in server_config["env"]:
        print(f"💾 Database path: {server_config['env']['M3_DB_PATH']}")
    elif server_config["env"].get("M3_BACKEND") in ("duckdb",):
        # Show the default path when using DuckDB backend
        default_path = get_default_database_path("mimic-iv-demo")
        if default_path is None:
            raise ValueError(_DATABASE_PATH_ERROR_MSG)
        print(f"💾 Database path: {default_path}")

    if "M3_PROJECT_ID" in server_config["env"]:
        print(f"☁️  Project ID: {server_config['env']['M3_PROJECT_ID']}")

    # Show additional env vars
    additional_env = {
        k: v
        for k, v in server_config["env"].items()
        if k
        not in [
            "PYTHONPATH",
            "M3_BACKEND",
            "M3_DB_PATH",
            "M3_PROJECT_ID",
            "GOOGLE_CLOUD_PROJECT",
        ]
    }
    if additional_env:
        print("🌍 Additional environment variables:")
        for key, value in additional_env.items():
            print(f"   {key}: {value}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate MCP server configuration for M3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python dynamic_mcp_config.py

  # Quick generation with defaults
  python dynamic_mcp_config.py --quick

  # Custom configuration
  python dynamic_mcp_config.py --python-path /usr/bin/python3 --backend bigquery --project-id my-project

  # Save to file
  python dynamic_mcp_config.py --output config.json
        """,
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Generate configuration with defaults (non-interactive)",
    )
    parser.add_argument(
        "--server-name", default="m3", help="Name for the MCP server (default: m3)"
    )
    parser.add_argument("--python-path", help="Path to Python executable")
    parser.add_argument("--working-directory", help="Working directory for the server")
    parser.add_argument(
        "--backend",
        choices=["duckdb", "bigquery"],
        default="duckdb",
        help="Backend to use (default: duckdb)",
    )
    parser.add_argument(
        "--db-path", help="Path to DuckDB database (for duckdb backend)"
    )
    parser.add_argument(
        "--project-id", help="Google Cloud project ID (for bigquery backend)"
    )
    parser.add_argument(
        "--env",
        action="append",
        help="Additional environment variables (format: KEY=VALUE)",
    )
    parser.add_argument(
        "--output", "-o", help="Save configuration to file instead of printing"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty print JSON (default: True)",
    )

    args = parser.parse_args()

    # Validate backend-specific arguments
    if args.backend in ("duckdb",) and args.project_id:
        print(
            "❌ Error: --project-id can only be used with --backend bigquery",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.backend == "bigquery" and args.db_path:
        print(
            "❌ Error: --db-path can only be used with --backend duckdb",
            file=sys.stderr,
        )
        sys.exit(1)

    # Require project_id for BigQuery backend
    if args.backend == "bigquery" and not args.project_id:
        print(
            "❌ Error: --project-id is required when using --backend bigquery",
            file=sys.stderr,
        )
        sys.exit(1)

    generator = MCPConfigGenerator()

    try:
        if args.quick:
            # Quick mode with command line arguments
            additional_env = {}
            if args.env:
                for env_var in args.env:
                    if "=" in env_var:
                        key, value = env_var.split("=", 1)
                        additional_env[key.strip()] = value.strip()

            config = generator.generate_config(
                server_name=args.server_name,
                python_path=args.python_path,
                working_directory=args.working_directory,
                backend=args.backend,
                db_path=args.db_path,
                project_id=args.project_id,
                additional_env=additional_env if additional_env else None,
                module_name="m3.mcp_server",
            )
        else:
            # Interactive mode
            config = generator.interactive_config()

        # Print configuration info
        print_config_info(config)

        # Output the configuration
        json_output = json.dumps(config, indent=2 if args.pretty else None)

        if args.output:
            # Save to file
            with open(args.output, "w") as f:
                f.write(json_output)
            print(f"\n💾 Configuration saved to: {args.output}")
        else:
            # Print to terminal
            print("\n📋 MCP Configuration (copy and paste this into your MCP client):")
            print("=" * 70)
            print(json_output)
            print("=" * 70)
            print(
                "\n💡 Copy the JSON above and paste it into your MCP client configuration."
            )

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
