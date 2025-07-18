from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import m3.core.preset.registry as preset_registry
from m3.cli import M3CLI
from m3.core.config import M3Config


def _strip_ansi_codes(text: str) -> str:
    """Strip ANSI (rich) escape codes from text."""
    import re

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


runner = CliRunner()
app = M3CLI().app


class TestM3CLI:
    """Tests for M3CLI commands and related functionality."""

    def test_version(self) -> None:
        """Test version command."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "M3 CLI Version" in result.stdout

    def test_list_presets(self) -> None:
        """Test list-presets command."""
        result = runner.invoke(app, ["list-presets"])
        assert result.exit_code == 0
        assert "Available Presets" in result.stdout

    def test_list_tools(self) -> None:
        """Test list-tools command."""
        result = runner.invoke(app, ["list-tools"])
        assert result.exit_code == 0
        assert "Available Tools" in result.stdout

    @patch("m3.m3.M3.run")
    @patch("m3.m3.M3.build")
    @patch("m3.m3.M3.save")
    def test_run_with_preset(
        self, mock_save: MagicMock, mock_build: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test run with preset."""
        with patch("m3.core.preset.registry.ALL_PRESETS", {"default_m3": MagicMock()}):
            mock_preset_class = preset_registry.ALL_PRESETS["default_m3"]
            mock_preset_m3 = MagicMock()
            mock_preset_m3.config = M3Config()
            mock_preset_m3.mcp = None
            mock_preset_m3.tools = []
            mock_preset_class.configure_mock(**{"create.return_value": mock_preset_m3})
            result = runner.invoke(app, ["run", "--presets", "default_m3"])
            assert result.exit_code == 0
            output = _strip_ansi_codes(result.stdout)
            assert "Applying preset 'default_m3'" in output
            mock_build.assert_called_once()
            mock_save.assert_called_once()
            mock_run.assert_called_once()

    @patch("sqlite3.connect")
    def test_build_with_preset(self, mock_connect: MagicMock) -> None:
        """Test build with preset."""
        mock_conn = mock_connect.return_value
        mock_conn.cursor.return_value = MagicMock()  # Mock cursor if needed
        result = runner.invoke(app, ["build", "--presets", "default_m3"])
        assert result.exit_code == 0

    def test_search_presets(self) -> None:
        """Test search for presets."""
        result = runner.invoke(app, ["search", "default", "--type", "presets"])
        assert result.exit_code == 0
        assert "Presets matches" in result.stdout

    def test_search_invalid_type(self) -> None:
        """Test search with invalid type."""
        result = runner.invoke(app, ["search", "query", "--type", "invalid"])
        assert result.exit_code != 0
        assert "Invalid type" in result.stdout

    @patch("m3.tools.mimic.cli.MimicCLI.configure")
    def test_add_tool(self, mock_configure: MagicMock) -> None:
        """Test pipeline command."""
        mock_configure.return_value = {
            "env_vars": {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": "M3_test_environment_test.db",
            },
            "tool_params": {
                "backends": [
                    {
                        "type": "sqlite",
                        "params": {"path": "M3_test_environment_test.db"},
                    }
                ],
                "backend_key": "sqlite",
            },
        }
        result = runner.invoke(app, ["pipeline", "mimic"])
        assert result.exit_code == 0

    def test_tools_help(self) -> None:
        """Test tools help."""
        result = runner.invoke(app, ["tools", "--help"])
        assert result.exit_code == 0
        assert "Access tool-specific subcommands" in result.stdout

    def test_run_with_invalid_preset(self) -> None:
        """Test run with invalid preset raises error."""
        result = runner.invoke(app, ["run", "--presets", "invalid_preset"])
        assert result.exit_code != 0
        output = _strip_ansi_codes(result.output)
        assert "Unknown preset" in output

    @patch("m3.tools.mimic.cli.MimicCLI.configure")
    def test_add_tool_new_pipeline(self, mock_configure: MagicMock) -> None:
        """Test adding tool to new pipeline."""
        mock_configure.return_value = {
            "env_vars": {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": "M3_test_environment_test.db",
            },
            "tool_params": {
                "backends": [
                    {
                        "type": "sqlite",
                        "params": {"path": "M3_test_environment_test.db"},
                    }
                ],
                "backend_key": "sqlite",
            },
        }
        result = runner.invoke(
            app, ["pipeline", "mimic", "--new-pipeline", "M3_test_env_new.json"]
        )
        assert result.exit_code == 0
        pipeline_path = Path("M3_test_env_new.json")
        if pipeline_path.exists():
            pipeline_path.unlink()

    @patch("m3.tools.mimic.cli.MimicCLI.configure")
    def test_add_tool_existing_pipeline(self, mock_configure: MagicMock) -> None:
        """Test adding tool to existing pipeline."""
        mock_configure.return_value = {
            "env_vars": {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": "M3_test_environment_test.db",
            },
            "tool_params": {
                "backends": [
                    {
                        "type": "sqlite",
                        "params": {"path": "M3_test_environment_test.db"},
                    }
                ],
                "backend_key": "sqlite",
            },
        }
        result = runner.invoke(
            app, ["pipeline", "mimic", "--to-pipeline", "M3_test_env_existing.json"]
        )
        assert result.exit_code == 0
        pipeline_path = Path("M3_test_env_existing.json")
        if pipeline_path.exists():
            pipeline_path.unlink()

    def test_add_tool_unknown(self) -> None:
        """Test adding unknown tool raises error."""
        result = runner.invoke(app, ["pipeline", "unknown"])
        assert result.exit_code != 0
        assert "Unknown tool" in str(result.exception)

    def test_help_shows_correct_commands(self) -> None:
        """Test that the help message shows the some key commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Usage" in output
        assert "list-presets" in output
        assert "list-tools" in output
        assert "tools" in output

    def test_unknown_command_reports_error(self) -> None:
        """Test that an unknown command reports an error."""
        result = runner.invoke(app, ["not-a-cmd"])
        assert result.exit_code != 0
        output = _strip_ansi_codes(result.output)
        assert "No such command" in output

    @patch("sqlite3.connect")
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator.generate"
    )
    def test_build_claude_success(
        self, mock_generate: MagicMock, mock_connect: MagicMock
    ) -> None:
        """Test successful build for Claude Desktop."""
        mock_generate.return_value = {"mcpServers": {"m3": {}}}
        mock_conn = mock_connect.return_value
        mock_conn.cursor.return_value = MagicMock()
        result = runner.invoke(app, ["build", "--config-type", "claude"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Pipeline config saved" in output

    @patch("sqlite3.connect")
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.fast_mcp_config.FastMCPConfigGenerator.generate"
    )
    def test_build_fast_success(
        self, mock_generate: MagicMock, mock_connect: MagicMock
    ) -> None:
        """Test successful build for Fast MCP Config Generator."""
        mock_generate.return_value = {"mcpServers": {"m3": {}}}
        mock_conn = mock_connect.return_value
        mock_conn.cursor.return_value = MagicMock()
        result = runner.invoke(app, ["build", "--config-type", "fastmcp"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Pipeline config saved" in output

    @patch("sqlite3.connect")
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.universal_mcp_config.UniversalConfigGenerator.generate"
    )
    def test_build_universal_success(
        self, mock_generate: MagicMock, mock_connect: MagicMock
    ) -> None:
        """Test successful build for Universal MCP Config Generator."""
        mock_generate.return_value = {"mcpServers": {"m3": {}}}
        mock_conn = mock_connect.return_value
        mock_conn.cursor.return_value = MagicMock()
        result = runner.invoke(app, ["build", "--config-type", "universal"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Pipeline config saved" in output

    @patch("sqlite3.connect")
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.fast_mcp_config.FastMCPConfigGenerator.generate"
    )
    def test_build_script_failure(
        self, mock_generate: MagicMock, mock_connect: MagicMock
    ) -> None:
        """Test error handling when build fails (default fast config)."""
        mock_generate.side_effect = Exception("Build failed")
        mock_conn = mock_connect.return_value
        mock_conn.cursor.return_value = MagicMock()
        result = runner.invoke(app, ["build"])
        assert result.exit_code != 0
        output = _strip_ansi_codes(result.output)
        assert "Build failed" in output

    def test_search_tools(self) -> None:
        """Test that search finds tools."""
        result = runner.invoke(app, ["search", "mimic", "--type", "tools"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Tools matches" in output
        assert "mimic" in output

    def test_search_presets_and_tools_combined(self) -> None:
        """Test that search finds both presets and tools when type is all."""
        result = runner.invoke(app, ["search", "m3"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "Presets matches" in output or "Tools matches" in output
