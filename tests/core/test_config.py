import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from m3.core.config import M3Config
from m3.core.utils.exceptions import M3ConfigError


@pytest.fixture
def temp_env_vars():
    """Fixture to temporarily set environment variables."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestM3Config:
    """Tests for M3Config class."""

    def test_init_default(self):
        """Test default initialization."""
        config = M3Config()
        assert config.log_level == "INFO"
        assert config.env_vars == {}
        assert isinstance(config.project_root, Path)
        assert isinstance(config.data_dir, Path)
        assert isinstance(config.databases_dir, Path)
        assert isinstance(config.raw_files_dir, Path)

    def test_init_with_params(self):
        """Test initialization with parameters."""
        env_vars = {"TEST_KEY": "value"}
        config = M3Config(log_level="DEBUG", env_vars=env_vars)
        assert config.log_level == "DEBUG"
        assert config.env_vars == env_vars

    def test_to_dict(self):
        """Test to_dict method."""
        config = M3Config(env_vars={"KEY": "value"})
        data = config.to_dict()
        assert data["log_level"] == "INFO"
        assert data["env_vars"] == {"KEY": "value"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {"log_level": "DEBUG", "env_vars": {"KEY": "value"}}
        config = M3Config.from_dict(data)
        assert config.log_level == "DEBUG"
        assert config.env_vars == {"KEY": "value"}

    def test_from_dict_missing_key(self):
        """Test from_dict raises error on missing key."""
        data = {"log_level": "INFO"}
        with pytest.raises(M3ConfigError, match="Missing required config key"):
            M3Config.from_dict(data)

    def test_get_env_var(self, temp_env_vars):
        """Test get_env_var method."""
        os.environ["TEST_ENV"] = "env_value"
        config = M3Config(env_vars={"CONFIG_KEY": "config_value"})
        assert config.get_env_var("TEST_ENV") == "env_value"
        assert config.get_env_var("CONFIG_KEY") == "config_value"
        assert config.get_env_var("MISSING", default="default") == "default"

    def test_get_env_var_raise_if_missing(self):
        """Test get_env_var raises if missing and required."""
        config = M3Config()
        with pytest.raises(M3ConfigError, match="Missing required env var"):
            config.get_env_var("MISSING", raise_if_missing=True)

    def test_validate_for_tools_success(self):
        """Test validate_for_tools method success."""
        from m3.core.tool.base import BaseTool

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.__class__.__name__ = "TestTool"
        mock_tool.required_env_vars = {"REQUIRED": None}
        config = M3Config(env_vars={"TESTTOOL_REQUIRED": "value"})
        config.validate_for_tools([mock_tool])

    def test_validate_for_tools_error(self):
        """Test validate_for_tools raises on error."""
        from m3.core.tool.base import BaseTool

        mock_tool = MagicMock(spec=BaseTool)
        mock_tool.__class__.__name__ = "TestTool"
        mock_tool.required_env_vars = {"FAKE_MISSING": None}
        config = M3Config(env_vars={})
        with pytest.raises(M3ConfigError):
            config.validate_for_tools([mock_tool])

    def test_merge_env(self):
        """Test merge_env method."""
        config = M3Config(env_vars={"EXISTING": "old"})
        new_env = {"NEW": "value"}
        config.merge_env(new_env)
        assert config.env_vars["NEW"] == "value"
        assert config.env_vars["EXISTING"] == "old"

    def test_merge_env_conflict(self):
        """Test merge_env raises on conflict."""
        config = M3Config(env_vars={"KEY": "old"})
        with pytest.raises(M3ConfigError, match="Env conflict"):
            config.merge_env({"KEY": "new"})

    @patch("m3.core.config.Path.home")
    def test_project_root_fallback(self, mock_home):
        """Test project root fallback to home."""
        mock_home.return_value = Path("/home/user")
        with patch("pathlib.Path.exists", return_value=False):
            config = M3Config()
            assert config.project_root == Path("/home/user")

    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(M3ConfigError, match="Invalid log level"):
            M3Config(log_level="INVALID")

    def test_get_env_var_error_success(self):
        """Test _get_env_var_error returns None on success."""
        config = M3Config(env_vars={"KEY": "value"})
        assert config._get_env_var_error("KEY", None) is None

    def test_get_env_var_error_missing(self):
        """Test _get_env_var_error returns error message when missing."""
        config = M3Config()
        error = config._get_env_var_error("MISSING", None)
        assert error is not None
        assert "Missing required env var" in error

    def test_get_data_dir_with_env(self, temp_env_vars):
        """Test _get_data_dir uses env var when set."""
        os.environ["M3_DATA_DIR"] = "/custom/data"
        config = M3Config()
        assert config._get_data_dir() == Path("/custom/data")
