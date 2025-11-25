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
    # exit code 0 for successful help display
    assert result.exit_code == 0
    # help output contains the app name
    assert "M3 CLI" in result.stdout


def test_version_option_exits_zero_and_shows_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "M3 CLI Version: 0.0.1" in result.stdout


def test_unknown_command_reports_error():
    result = runner.invoke(app, ["not-a-cmd"])
    # unknown command should fail
    assert result.exit_code != 0
    # Check both stdout and stderr since error messages might go to either depending on environment
    error_message = "No such command 'not-a-cmd'"
    assert (
        error_message in result.stdout
        or (hasattr(result, "stderr") and error_message in result.stderr)
        or error_message in result.output
    )


@patch("m3.cli.init_duckdb_from_parquet")
@patch("m3.cli.verify_table_rowcount")
def test_init_command_duckdb_custom_path(mock_rowcount, mock_init):
    """Test that m3 init --db-path uses custom database path override and DuckDB flow."""
    mock_init.return_value = True
    mock_rowcount.return_value = 100

    with tempfile.TemporaryDirectory() as temp_dir:
        custom_db_path = Path(temp_dir) / "custom_mimic.duckdb"
        resolved_custom_db_path = custom_db_path.resolve()
        # Also ensure a deterministic parquet path exists for the dataset discovery.
        with patch("m3.cli.get_dataset_parquet_root") as mock_parquet_root:
            repo_root = Path(__file__).resolve().parents[1]
            mock_parquet_root.return_value = repo_root / "m3_data/parquet/mimic-iv-demo"
            with patch.object(Path, "exists", return_value=True):
                result = runner.invoke(
                    app, ["init", "mimic-iv-demo", "--db-path", str(custom_db_path)]
                )

        assert result.exit_code == 0
        assert (
            str(custom_db_path) in result.stdout
            or str(resolved_custom_db_path) in result.stdout
        )
        assert "DuckDB path:" in result.stdout

        # initializer should be called with the resolved path
        mock_init.assert_called_once_with(
            dataset_name="mimic-iv-demo", db_target_path=resolved_custom_db_path
        )
        # verification query should be attempted
        mock_rowcount.assert_called()


def test_config_validation_bigquery_with_db_path():
    """Test that bigquery backend rejects db-path parameter."""
    result = runner.invoke(
        app, ["config", "claude", "--backend", "bigquery", "--db-path", "/test/path"]
    )
    # should fail when db-path is provided with bigquery
    assert result.exit_code == 1
    assert "db-path can only be used with --backend duckdb" in result.output


def test_config_validation_bigquery_requires_project_id():
    """Test that bigquery backend requires project-id parameter."""
    result = runner.invoke(app, ["config", "claude", "--backend", "bigquery"])
    # missing project-id should fail for bigquery backend
    assert result.exit_code == 1
    assert "project-id is required when using --backend bigquery" in result.output


def test_config_validation_duckdb_with_project_id():
    """Test that duckdb backend rejects project-id parameter."""
    result = runner.invoke(
        app, ["config", "claude", "--backend", "duckdb", "--project-id", "test"]
    )
    # should fail when project-id is provided with duckdb
    assert result.exit_code == 1
    # Check output - error messages from typer usually go to stdout
    assert "project-id can only be used with --backend bigquery" in result.output


@patch("subprocess.run")
def test_config_claude_success(mock_subprocess):
    """Test successful Claude Desktop configuration."""
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "claude"])
    assert result.exit_code == 0
    assert "Claude Desktop configuration completed" in result.stdout

    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    # correct script should be invoked
    assert "setup_claude_desktop.py" in call_args[1]


@patch("subprocess.run")
def test_config_universal_quick_mode(mock_subprocess):
    """Test universal config generator in quick mode."""
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "--quick"])
    assert result.exit_code == 0
    assert "Generating M3 MCP configuration" in result.stdout

    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "dynamic_mcp_config.py" in call_args[1]
    assert "--quick" in call_args


@patch("subprocess.run")
def test_config_script_failure(mock_subprocess):
    """Test error handling when config script fails."""
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, "cmd")

    result = runner.invoke(app, ["config", "claude"])
    # command should return failure exit code when subprocess fails
    assert result.exit_code == 1
    # Just verify that the command failed with the right exit code
    # The specific error message may vary


@patch("subprocess.run")
@patch("m3.cli.get_default_database_path")
@patch("m3.cli.get_active_dataset")
def test_config_claude_infers_db_path_demo(
    mock_active, mock_get_default, mock_subprocess
):
    mock_active.return_value = None  # unset -> default to demo
    mock_get_default.return_value = Path("/tmp/inferred-demo.duckdb")
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "claude"])
    assert result.exit_code == 0

    # subprocess run should NOT be called with inferred --db-path (dynamic resolution)
    call_args = mock_subprocess.call_args[0][0]
    assert "--db-path" not in call_args


@patch("subprocess.run")
@patch("m3.cli.get_default_database_path")
@patch("m3.cli.get_active_dataset")
def test_config_claude_infers_db_path_full(
    mock_active, mock_get_default, mock_subprocess
):
    mock_active.return_value = "mimic-iv-full"
    mock_get_default.return_value = Path("/tmp/inferred-full.duckdb")
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["config", "claude"])
    assert result.exit_code == 0

    call_args = mock_subprocess.call_args[0][0]
    assert "--db-path" not in call_args


@patch("m3.cli.set_active_dataset")
@patch("m3.cli.detect_available_local_datasets")
def test_use_full_happy_path(mock_detect, mock_set_active):
    mock_detect.return_value = {
        "mimic-iv-demo": {
            "parquet_present": False,
            "db_present": False,
            "parquet_root": "/tmp/demo",
            "db_path": "/tmp/demo.duckdb",
        },
        "mimic-iv-full": {
            "parquet_present": True,
            "db_present": False,
            "parquet_root": "/tmp/full",
            "db_path": "/tmp/full.duckdb",
        },
    }

    result = runner.invoke(app, ["use", "mimic-iv-full"])
    assert result.exit_code == 0
    assert "Active dataset set to 'mimic-iv-full'." in result.stdout
    mock_set_active.assert_called_once_with("mimic-iv-full")


@patch("m3.cli.compute_parquet_dir_size", return_value=123)
@patch("m3.cli.get_active_dataset", return_value="mimic-iv-full")
@patch("m3.cli.detect_available_local_datasets")
def test_status_happy_path(mock_detect, mock_active, mock_size):
    mock_detect.return_value = {
        "mimic-iv-demo": {
            "parquet_present": True,
            "db_present": False,
            "parquet_root": "/tmp/demo",
            "db_path": "/tmp/demo.duckdb",
        },
        "mimic-iv-full": {
            "parquet_present": True,
            "db_present": False,
            "parquet_root": "/tmp/full",
            "db_path": "/tmp/full.duckdb",
        },
    }

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Active dataset: mimic-iv-full" in result.stdout
    size_gb = 123 / (1024**3)
    assert f"parquet_size_gb: {size_gb:.4f} GB" in result.stdout
