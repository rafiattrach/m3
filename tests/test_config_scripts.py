"""Tests for MCP configuration scripts."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m3.mcp_client_configs.dynamic_mcp_config import MCPConfigGenerator


class TestMCPConfigGenerator:
    """Test the MCPConfigGenerator class."""

    def test_generate_config_sqlite_default(self):
        """Test generating SQLite config with defaults."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            config = generator.generate_config()

            assert config["mcpServers"]["m3"]["env"]["M3_BACKEND"] == "sqlite"
            assert "M3_PROJECT_ID" not in config["mcpServers"]["m3"]["env"]
            assert config["mcpServers"]["m3"]["args"] == ["-m", "m3.mcp_server"]

    def test_generate_config_bigquery_with_project(self):
        """Test generating BigQuery config with project ID."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            config = generator.generate_config(
                backend="bigquery", project_id="test-project"
            )

            assert config["mcpServers"]["m3"]["env"]["M3_BACKEND"] == "bigquery"
            assert config["mcpServers"]["m3"]["env"]["M3_PROJECT_ID"] == "test-project"
            assert (
                config["mcpServers"]["m3"]["env"]["GOOGLE_CLOUD_PROJECT"]
                == "test-project"
            )

    def test_generate_config_sqlite_with_db_path(self):
        """Test generating SQLite config with custom database path."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            config = generator.generate_config(
                backend="sqlite", db_path="/custom/path/database.db"
            )

            assert config["mcpServers"]["m3"]["env"]["M3_BACKEND"] == "sqlite"
            assert (
                config["mcpServers"]["m3"]["env"]["M3_DB_PATH"]
                == "/custom/path/database.db"
            )

    def test_generate_config_custom_server_name(self):
        """Test generating config with custom server name."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            config = generator.generate_config(server_name="custom-m3")

            assert "custom-m3" in config["mcpServers"]
            assert "m3" not in config["mcpServers"]

    def test_generate_config_additional_env_vars(self):
        """Test generating config with additional environment variables."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            config = generator.generate_config(
                additional_env={"DEBUG": "true", "LOG_LEVEL": "info"}
            )

            env = config["mcpServers"]["m3"]["env"]
            assert env["DEBUG"] == "true"
            assert env["LOG_LEVEL"] == "info"
            assert env["M3_BACKEND"] == "sqlite"  # Default should still be there

    def test_validation_invalid_python_path(self):
        """Test that invalid Python path raises error."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=False),
            patch.object(generator, "_validate_directory", return_value=True),
        ):
            with pytest.raises(ValueError, match="Invalid Python path"):
                generator.generate_config(python_path="/invalid/python")

    def test_validation_invalid_directory(self):
        """Test that invalid working directory raises error."""
        generator = MCPConfigGenerator()

        with (
            patch.object(generator, "_validate_python_path", return_value=True),
            patch.object(generator, "_validate_directory", return_value=False),
        ):
            with pytest.raises(ValueError, match="Invalid working directory"):
                generator.generate_config(working_directory="/invalid/dir")
