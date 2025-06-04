import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

import m3.cli as cli_module
from m3.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def inject_version(monkeypatch):
    monkeypatch.setattr(cli_module, "__version__", "0.0.1")


def test_help_shows_app_name():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "M3 CLI" in result.stdout


def test_version_option_exits_zero_and_shows_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "M3 CLI Version: 0.0.1" in result.stdout


def test_unknown_command_reports_error():
    result = runner.invoke(app, ["not-a-cmd"])
    assert result.exit_code != 0
    # Check both stdout and stderr since error messages might go to either depending on environment
    error_message = "No such command 'not-a-cmd'"
    assert (
        error_message in result.stdout
        or (hasattr(result, "stderr") and error_message in result.stderr)
        or error_message in result.output
    )


@patch("m3.cli.initialize_dataset")
@patch("sqlite3.connect")
def test_init_command_respects_custom_db_path(
    mock_sqlite_connect, mock_initialize_dataset
):
    """Test that m3 init --db-path correctly uses custom database path override."""
    # Setup mocks
    mock_initialize_dataset.return_value = True

    # Mock sqlite connection and cursor for verification query
    mock_cursor = mock_sqlite_connect.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = (100,)  # Mock row count result

    with tempfile.TemporaryDirectory() as temp_dir:
        custom_db_path = Path(temp_dir) / "custom_mimic.db"
        # Resolve the path to handle symlinks (like /var -> /private/var on macOS)
        resolved_custom_db_path = custom_db_path.resolve()

        # Run the init command with custom db path
        result = runner.invoke(
            app, ["init", "mimic-iv-demo", "--db-path", str(custom_db_path)]
        )

        # Assert command succeeded
        assert result.exit_code == 0

        # Verify the output mentions the custom path (either original or resolved form)
        assert (
            str(custom_db_path) in result.stdout
            or str(resolved_custom_db_path) in result.stdout
        )
        assert "Target database path:" in result.stdout

        # Verify initialize_dataset was called with the resolved custom path
        mock_initialize_dataset.assert_called_once_with(
            dataset_name="mimic-iv-demo", db_target_path=resolved_custom_db_path
        )

        # Verify sqlite connection was attempted with the resolved custom path
        mock_sqlite_connect.assert_called_with(resolved_custom_db_path)


def test_config_validation_sqlite_with_project_id():
    """Test that sqlite backend rejects project-id parameter."""
    result = runner.invoke(
        app, ["config", "claude", "--backend", "sqlite", "--project-id", "test"]
    )
    assert result.exit_code == 1
    # Check output - error messages from typer usually go to stdout
    assert "project-id can only be used with --backend bigquery" in result.output


def test_config_validation_bigquery_with_db_path():
    """Test that bigquery backend rejects db-path parameter."""
    result = runner.invoke(
        app, ["config", "claude", "--backend", "bigquery", "--db-path", "/test/path"]
    )
    assert result.exit_code == 1
    # Check output - error messages from typer usually go to stdout
    assert "db-path can only be used with --backend sqlite" in result.output


def test_config_validation_bigquery_requires_project_id():
    """Test that bigquery backend requires project-id parameter."""
    result = runner.invoke(app, ["config", "claude", "--backend", "bigquery"])
    assert result.exit_code == 1
    # Check output - error messages from typer usually go to stdout
    assert "project-id is required when using --backend bigquery" in result.output


@patch("subprocess.run")
def test_config_claude_success(mock_subprocess):
    """Test successful Claude Desktop configuration."""
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "claude"])
    assert result.exit_code == 0
    assert "Claude Desktop configuration completed" in result.stdout

    # Verify subprocess was called with correct script
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "setup_claude_desktop.py" in call_args[1]  # Script path is second argument


@patch("subprocess.run")
def test_config_universal_quick_mode(mock_subprocess):
    """Test universal config generator in quick mode."""
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "--quick"])
    assert result.exit_code == 0
    assert "Generating M3 MCP configuration" in result.stdout

    # Verify subprocess was called with dynamic config script
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "dynamic_mcp_config.py" in call_args[1]  # Script path is second argument
    assert "--quick" in call_args


@patch("subprocess.run")
def test_config_script_failure(mock_subprocess):
    """Test error handling when config script fails."""
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, "cmd")

    result = runner.invoke(app, ["config", "claude"])
    assert result.exit_code == 1
    # Just verify that the command failed with the right exit code
    # The specific error message may vary
