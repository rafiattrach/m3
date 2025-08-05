import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from m3.core.mcp_config_generator.mcp_config_generators.claude_mcp_config import (
    ClaudeConfigGenerator,
)
from m3.core.mcp_config_generator.mcp_config_generators.fast_mcp_config import (
    FastMCPConfigGenerator,
)
from m3.core.utils.exceptions import M3ValidationError
from m3.m3 import M3


@pytest.fixture
def mock_m3() -> M3:
    """Fixture for mock M3 instance."""
    from m3.core.config import M3Config

    config = M3Config(env_vars={"TEST_ENV": "value"})
    m3 = M3(config=config)
    return m3


class TestClaudeConfigGenerator:
    """Tests for ClaudeConfigGenerator."""

    @patch(
        "shutil.which",
        return_value="/usr/bin/python",
    )
    @patch("os.path.isdir", return_value=True)
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator._get_claude_config_path"
    )
    def test_generate_with_defaults(
        self,
        mock_get_path: MagicMock,
        mock_isdir: MagicMock,
        mock_which: MagicMock,
        mock_m3: M3,
        tmp_path: Path,
    ) -> None:
        """Test generating config with defaults."""
        mock_get_path.return_value = None
        config = ClaudeConfigGenerator.generate(mock_m3)
        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "m3" in config["mcpServers"]
        server = config["mcpServers"]["m3"]
        assert server["command"].endswith("python")
        assert server["args"] == ["-m", "m3.core.server"]
        assert os.path.isdir(server["cwd"])
        assert "TEST_ENV" in server["env"]

    @patch("shutil.which", return_value=None)
    def test_invalid_command_raises_error(
        self, mock_which: MagicMock, mock_m3: M3
    ) -> None:
        """Test invalid command raises error."""
        with pytest.raises(M3ValidationError, match="Invalid command"):
            ClaudeConfigGenerator.generate(mock_m3, command="/invalid/python")

    @patch("os.path.isdir", return_value=False)
    def test_invalid_cwd_raises_error(self, mock_isdir: MagicMock, mock_m3: M3) -> None:
        """Test invalid cwd raises error."""
        with pytest.raises(M3ValidationError, match="Invalid cwd"):
            ClaudeConfigGenerator.generate(mock_m3, cwd="/invalid/dir")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("json.dump")
    @patch(
        "m3.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator._get_claude_config_path"
    )
    @patch("pathlib.Path.exists")
    def test_merge_with_existing_config(
        self,
        mock_exists: MagicMock,
        mock_get_path: MagicMock,
        mock_dump: MagicMock,
        mock_load: MagicMock,
        mock_open_file: MagicMock,
        mock_m3: M3,
        tmp_path: Path,
    ) -> None:
        """Test merging with existing Claude config."""
        mock_path = tmp_path / "claude_config.json"
        mock_get_path.return_value = mock_path
        mock_exists.return_value = True
        mock_load.return_value = {"mcpServers": {"existing": {}}}
        _config = ClaudeConfigGenerator.generate(mock_m3)
        mock_dump.assert_called_once()
        dumped_config = mock_dump.call_args[0][0]
        assert "existing" in dumped_config["mcpServers"]
        assert "m3" in dumped_config["mcpServers"]

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_custom_path(
        self,
        mock_dump: MagicMock,
        mock_open_file: MagicMock,
        mock_m3: M3,
        tmp_path: Path,
    ) -> None:
        """Test saving to custom path."""
        save_path = tmp_path / "custom.json"
        config = ClaudeConfigGenerator.generate(mock_m3, save_path=str(save_path))
        mock_dump.assert_called_once_with(config, mock_open_file(), indent=2)


class TestFastMCPConfigGenerator:
    """Tests for FastMCPConfigGenerator."""

    @patch("shutil.which", return_value="/usr/bin/python")
    @patch("os.path.isdir", return_value=True)
    def test_generate_with_defaults(
        self, mock_isdir: MagicMock, mock_which: MagicMock, mock_m3: M3
    ) -> None:
        """Test generating config with defaults."""
        config = FastMCPConfigGenerator.generate(mock_m3)
        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "m3" in config["mcpServers"]
        server = config["mcpServers"]["m3"]
        assert server["command"].endswith("python")
        assert server["args"] == ["-m", "m3.core.server"]
        assert os.path.isdir(server["cwd"])
        assert "TEST_ENV" in server["env"]

    @patch("shutil.which", return_value=None)
    def test_invalid_command_raises_error(
        self, mock_which: MagicMock, mock_m3: M3
    ) -> None:
        """Test invalid command raises error."""
        with pytest.raises(M3ValidationError, match="Invalid command"):
            FastMCPConfigGenerator.generate(mock_m3, command="/invalid/python")

    @patch("os.path.isdir", return_value=False)
    def test_invalid_cwd_raises_error(self, mock_isdir: MagicMock, mock_m3: M3) -> None:
        """Test invalid cwd raises error."""
        with pytest.raises(M3ValidationError, match="Invalid cwd"):
            FastMCPConfigGenerator.generate(mock_m3, cwd="/invalid/dir")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_custom_path(
        self,
        mock_dump: MagicMock,
        mock_open_file: MagicMock,
        mock_m3: M3,
        tmp_path: Path,
    ) -> None:
        """Test saving to custom path."""
        save_path = tmp_path / "custom.json"
        config = FastMCPConfigGenerator.generate(mock_m3, save_path=str(save_path))
        mock_dump.assert_called_once_with(config, mock_open_file(), indent=2)
