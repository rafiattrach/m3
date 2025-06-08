#!/usr/bin/env python3
"""
Automation script to configure Goose with M3 MCP server for MIMIC-IV demo evaluation.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def get_m3_config():
    """Generate M3 MCP configuration using m3 config command."""
    try:
        # Get current working directory (should be M3 project root)
        project_root = Path.cwd()
        db_path = project_root / "data" / "databases" / "mimic_iv_demo.db"

        if not db_path.exists():
            print(f"❌ MIMIC-IV demo database not found at {db_path}")
            print("Please run 'm3 init mimic-iv-demo' first")
            return None

        # Generate M3 MCP config with absolute path to avoid working directory issues
        cmd = [
            "m3",
            "config",
            "--quick",
            "--backend",
            "sqlite",
            "--db-path",
            str(db_path),  # Use absolute path
            "--server-name",
            "m3-mimic-demo",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode != 0:
            print(f"❌ Failed to generate M3 config: {result.stderr}")
            return None

        # Extract JSON from output - more robust approach
        output = result.stdout

        # Find the start and end of JSON block
        json_start_marker = "{"

        start_idx = output.find(json_start_marker)
        if start_idx == -1:
            print("❌ Could not find JSON start in m3 config output")
            return None

        # Find the matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i, char in enumerate(output[start_idx:], start_idx):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        if brace_count != 0:
            print("❌ Could not find matching closing brace in JSON")
            return None

        json_text = output[start_idx:end_idx]

        # Clean up line wraps and formatting issues
        json_text = json_text.replace("\n", " ").replace("\r", " ")
        # Remove excessive whitespace
        json_text = re.sub(r"\s+", " ", json_text)

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Extracted JSON text: {json_text}")
            return None

    except Exception as e:
        print(f"❌ Error generating M3 config: {e}")
        return None


def find_goose_config():
    """Find Goose configuration file."""
    # Common Goose config locations
    possible_paths = [
        Path.home() / ".config" / "goose" / "config.yaml",
        Path.home() / ".goose" / "config.yaml",
        Path.home()
        / "Library"
        / "Application Support"
        / "goose"
        / "config.yaml",  # macOS
    ]

    for path in possible_paths:
        if path.exists():
            return path

    # If no config exists, create one at the standard location
    config_dir = Path.home() / ".config" / "goose"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def update_goose_config(m3_config):
    """Update Goose configuration with M3 MCP server."""
    goose_config_path = find_goose_config()

    # Load existing config or create new one
    if goose_config_path.exists():
        with open(goose_config_path) as f:
            goose_config = yaml.safe_load(f) or {}
    else:
        goose_config = {}

    # Ensure extensions section exists
    if "extensions" not in goose_config:
        goose_config["extensions"] = {}

    # Add M3 MCP server configuration in the proper Goose format
    server_name = next(iter(m3_config["mcpServers"].keys()))
    server_config = m3_config["mcpServers"][server_name]

    goose_config["extensions"][server_name] = {
        "args": server_config["args"],
        "bundled": None,
        "cmd": server_config["command"],
        "cwd": server_config["cwd"],
        "description": "M3 MCP server for MIMIC-IV demo database access",
        "enabled": True,  # Enable by default
        "env_keys": list(server_config["env"].keys()),
        "envs": server_config["env"],
        "name": server_name,
        "timeout": 300,
        "type": "stdio",
    }

    # Write updated config
    with open(goose_config_path, "w") as f:
        yaml.dump(goose_config, f, default_flow_style=False, indent=2)

    return goose_config_path


def main():
    """Main function to setup Goose with M3 MCP server."""
    print("🦆 Setting up Goose with M3 MCP server for MIMIC-IV demo...")

    # Step 1: Generate M3 config
    print("\n📋 Generating M3 MCP configuration...")
    m3_config = get_m3_config()
    if not m3_config:
        sys.exit(1)

    print("✅ M3 configuration generated successfully")

    # Step 2: Update Goose config
    print("\n🔧 Updating Goose configuration...")
    goose_config_path = update_goose_config(m3_config)
    print(f"✅ Goose config updated at: {goose_config_path}")

    # Step 3: Verify setup
    print("\n🔍 Verifying setup...")
    print("M3 MCP Server configuration:")
    print(json.dumps(m3_config, indent=2))

    print("\n🦆 Setup complete! Your Goose is now configured to use M3 MCP server.")
    print(f"📍 Config location: {goose_config_path}")
    print("\nTo test the setup:")
    print("1. Run: goose session")
    print("2. Ask: 'What tools do you have available?'")
    print("3. Try: 'Show me the schema for MIMIC-IV demo database'")


if __name__ == "__main__":
    main()
