import tempfile
from pathlib import Path
from unittest.mock import patch

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
