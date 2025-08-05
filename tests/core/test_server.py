import os
from unittest.mock import Mock, patch

import pytest

from m3.core.utils.exceptions import M3ValidationError
from m3.m3 import M3


class TestMCPServer:
    """Tests for MCP server."""

    def test_server_can_be_imported_as_module(self) -> None:
        """Test that the server can be imported as a module."""
        import m3.core.server

        assert hasattr(m3.core.server, "main")
        assert callable(m3.core.server.main)

    @patch.dict(os.environ, {"M3_CONFIG_PATH": "test_config.json"})
    @patch("m3.core.server.M3.load")
    def test_main_success(self, mock_load: Mock) -> None:
        """Test main function with valid config."""
        mock_m3 = Mock(spec=M3)
        mock_load.return_value = mock_m3
        from m3.core.server import main

        main()
        mock_load.assert_called_once_with("test_config.json")
        mock_m3.build.assert_called_once()
        mock_m3.run.assert_called_once()

    @patch.dict(os.environ, clear=True)
    def test_main_no_config_path(self) -> None:
        """Test main raises error when M3_CONFIG_PATH is not set."""
        from m3.core.server import main

        with pytest.raises(M3ValidationError, match="M3_CONFIG_PATH env var not set"):
            main()

    @patch.dict(os.environ, {"M3_CONFIG_PATH": "invalid.json"})
    @patch("m3.core.server.M3.load")
    def test_main_load_failure(self, mock_load: Mock) -> None:
        """Test main handles load failure."""
        mock_load.side_effect = FileNotFoundError("Config not found")
        from m3.core.server import main

        with pytest.raises(FileNotFoundError):
            main()

    @patch.dict(os.environ, {"M3_CONFIG_PATH": "test.json"})
    @patch("m3.core.server.M3.load")
    def test_main_build_failure(self, mock_load: Mock) -> None:
        """Test main handles build failure."""
        mock_m3 = Mock(spec=M3)
        mock_load.return_value = mock_m3
        mock_m3.build.side_effect = M3ValidationError("Build failed")
        from m3.core.server import main

        with pytest.raises(M3ValidationError):
            main()
