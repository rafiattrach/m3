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
    assert "No such command" in result.stdout
