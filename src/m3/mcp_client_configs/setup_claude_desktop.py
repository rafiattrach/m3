"""
Setup script for M3 MCP Server with Claude Desktop.
Automatically configures Claude Desktop to use the M3 MCP server.
"""

import json
import os
import shutil
from pathlib import Path


def get_claude_config_path():
    """Get the Claude Desktop configuration file path."""
    home = Path.home()

    # macOS path
    claude_config = (
        home
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )
    if claude_config.parent.exists():
        return claude_config

    # Windows path
    claude_config = (
        home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    )
    if claude_config.parent.exists():
        return claude_config

    # Linux path
    claude_config = home / ".config" / "Claude" / "claude_desktop_config.json"
    if claude_config.parent.exists():
        return claude_config

    raise FileNotFoundError("Could not find Claude Desktop configuration directory")


def get_current_directory():
    """Get the current M3 project directory."""
    return Path(__file__).parent.parent.absolute()


def get_python_path():
    """Get the Python executable path."""
    # Try to use the current virtual environment
    if "VIRTUAL_ENV" in os.environ:
        venv_python = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

    # Fall back to system python
    return shutil.which("python") or shutil.which("python3") or "python"


def create_mcp_config(
    backend="sqlite",
    db_path=None,
    project_id=None,
    oauth2_enabled=False,
    oauth2_config=None,
):
    """Create MCP server configuration."""
    current_dir = get_current_directory()
    python_path = get_python_path()

    config = {
        "mcpServers": {
            "m3": {
                "command": python_path,
                "args": ["-m", "m3.mcp_server"],
                "cwd": str(current_dir),
                "env": {"PYTHONPATH": str(current_dir / "src"), "M3_BACKEND": backend},
            }
        }
    }

    # Add backend-specific environment variables
    if backend == "sqlite" and db_path:
        config["mcpServers"]["m3"]["env"]["M3_DB_PATH"] = db_path
    elif backend == "bigquery" and project_id:
        config["mcpServers"]["m3"]["env"]["M3_PROJECT_ID"] = project_id
        config["mcpServers"]["m3"]["env"]["GOOGLE_CLOUD_PROJECT"] = project_id

    # Add OAuth2 configuration if enabled
    if oauth2_enabled and oauth2_config:
        config["mcpServers"]["m3"]["env"].update(
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
            config["mcpServers"]["m3"]["env"]["M3_OAUTH2_CLIENT_ID"] = oauth2_config[
                "client_id"
            ]
        if oauth2_config.get("rate_limit_requests"):
            config["mcpServers"]["m3"]["env"]["M3_OAUTH2_RATE_LIMIT_REQUESTS"] = str(
                oauth2_config["rate_limit_requests"]
            )

    return config


def setup_claude_desktop(
    backend="sqlite",
    db_path=None,
    project_id=None,
    oauth2_enabled=False,
    oauth2_config=None,
):
    """Setup Claude Desktop with M3 MCP server."""
    try:
        claude_config_path = get_claude_config_path()
        print(f"Found Claude Desktop config at: {claude_config_path}")

        # Load existing config or create new one
        existing_config = {}
        if claude_config_path.exists() and claude_config_path.stat().st_size > 0:
            try:
                with open(claude_config_path) as f:
                    existing_config = json.load(f)
                print("Loaded existing Claude Desktop configuration")
            except json.JSONDecodeError:
                print("Found corrupted config file, creating new configuration")
                existing_config = {}
        else:
            print("Creating new Claude Desktop configuration")

        # Create MCP config
        mcp_config = create_mcp_config(
            backend, db_path, project_id, oauth2_enabled, oauth2_config
        )

        # Merge configurations
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        existing_config["mcpServers"].update(mcp_config["mcpServers"])

        # Ensure directory exists
        claude_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write updated config
        with open(claude_config_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        print("✅ Successfully configured Claude Desktop!")
        print(f"📁 Config file: {claude_config_path}")
        print(f"🔧 Backend: {backend}")

        if backend == "sqlite":
            db_path_display = db_path or "default (m3_data/databases/mimic_iv_demo.db)"
            print(f"💾 Database: {db_path_display}")
        elif backend == "bigquery":
            project_display = project_id or "physionet-data"
            print(f"☁️  Project: {project_display}")

        if oauth2_enabled:
            print("🔐 OAuth2 Authentication: Enabled")
            if oauth2_config:
                print(f"🔗 Issuer: {oauth2_config.get('issuer_url', 'Not configured')}")
                print(f"👥 Audience: {oauth2_config.get('audience', 'Not configured')}")
                print(
                    f"🔑 Required Scopes: {oauth2_config.get('required_scopes', 'read:mimic-data')}"
                )
            print("\n⚠️  Security Notice:")
            print("   - OAuth2 authentication is now required for all API calls")
            print("   - Ensure you have a valid access token with the required scopes")
            print(
                "   - Set M3_OAUTH2_TOKEN environment variable with your Bearer token"
            )
        else:
            print("🔓 OAuth2 Authentication: Disabled")

        print("\n🔄 Please restart Claude Desktop to apply changes")

        return True

    except Exception as e:
        print(f"❌ Error setting up Claude Desktop: {e}")
        return False


def main():
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup M3 MCP Server with Claude Desktop"
    )
    parser.add_argument(
        "--backend",
        choices=["sqlite", "bigquery"],
        default="sqlite",
        help="Backend to use (default: sqlite)",
    )
    parser.add_argument(
        "--db-path", help="Path to SQLite database (for sqlite backend)"
    )
    parser.add_argument(
        "--project-id", help="Google Cloud project ID (for bigquery backend)"
    )
    parser.add_argument(
        "--enable-oauth2", action="store_true", help="Enable OAuth2 authentication"
    )
    parser.add_argument(
        "--oauth2-issuer", help="OAuth2 issuer URL (e.g., https://auth.example.com)"
    )
    parser.add_argument("--oauth2-audience", help="OAuth2 audience (e.g., m3-api)")
    parser.add_argument(
        "--oauth2-scopes",
        default="read:mimic-data",
        help="Required OAuth2 scopes (comma-separated)",
    )

    args = parser.parse_args()

    # Validate backend-specific arguments
    if args.backend == "sqlite" and args.project_id:
        print("❌ Error: --project-id can only be used with --backend bigquery")
        exit(1)

    if args.backend == "bigquery" and args.db_path:
        print("❌ Error: --db-path can only be used with --backend sqlite")
        exit(1)

    # Require project_id for BigQuery backend
    if args.backend == "bigquery" and not args.project_id:
        print("❌ Error: --project-id is required when using --backend bigquery")
        exit(1)

    print("🚀 Setting up M3 MCP Server with Claude Desktop...")
    print(f"📊 Backend: {args.backend}")

    # Prepare OAuth2 configuration if enabled
    oauth2_config = None
    if args.enable_oauth2:
        if not args.oauth2_issuer or not args.oauth2_audience:
            print(
                "❌ Error: --oauth2-issuer and --oauth2-audience are required when --enable-oauth2 is used"
            )
            exit(1)

        oauth2_config = {
            "issuer_url": args.oauth2_issuer,
            "audience": args.oauth2_audience,
            "required_scopes": args.oauth2_scopes,
        }

    success = setup_claude_desktop(
        backend=args.backend,
        db_path=args.db_path,
        project_id=args.project_id,
        oauth2_enabled=args.enable_oauth2,
        oauth2_config=oauth2_config,
    )

    if success:
        print("\n🎉 Setup complete! You can now use M3 tools in Claude Desktop.")
        print(
            "\n💡 Try asking Claude: 'What tools do you have available for MIMIC-IV data?'"
        )
    else:
        print("\n💥 Setup failed. Please check the error messages above.")
        exit(1)


if __name__ == "__main__":
    main()
