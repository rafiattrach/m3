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


def create_mcp_config(backend="sqlite", db_path=None, project_id=None):
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

    return config


def setup_claude_desktop(backend="sqlite", db_path=None, project_id=None):
    """Setup Claude Desktop with M3 MCP server."""
    try:
        claude_config_path = get_claude_config_path()
        print(f"Found Claude Desktop config at: {claude_config_path}")

        # Load existing config or create new one
        if claude_config_path.exists():
            with open(claude_config_path) as f:
                existing_config = json.load(f)
            print("Loaded existing Claude Desktop configuration")
        else:
            existing_config = {}
            print("Creating new Claude Desktop configuration")

        # Create MCP config
        mcp_config = create_mcp_config(backend, db_path, project_id)

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
            db_path_display = db_path or "default (data/databases/mimic_iv_demo.db)"
            print(f"💾 Database: {db_path_display}")
        elif backend == "bigquery":
            project_display = project_id or "physionet-data"
            print(f"☁️  Project: {project_display}")

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

    args = parser.parse_args()

    print("🚀 Setting up M3 MCP Server with Claude Desktop...")
    print(f"📊 Backend: {args.backend}")

    success = setup_claude_desktop(
        backend=args.backend, db_path=args.db_path, project_id=args.project_id
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
