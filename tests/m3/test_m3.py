import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from m3.core.config import M3Config
from m3.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS
from m3.core.tool.base import BaseTool
from m3.core.utils.exceptions import (
    M3BuildError,
    M3InitializationError,
    M3PresetError,
    M3ValidationError,
)
from m3.m3 import M3
from m3.tools.registry import ALL_TOOLS


@pytest.fixture
def mock_config() -> M3Config:
    """Fixture for a mock M3Config."""
    return M3Config(env_vars={"TEST_ENV": "value"})


@pytest.fixture
def mock_tool() -> BaseTool:
    """Fixture for a mock BaseTool."""

    class MockTool(BaseTool):
        @classmethod
        def from_dict(cls, params):
            return cls()

        def actions(self):
            pass

        def to_dict(self):
            pass

        def __init__(self):
            super().__init__()
            self.required_env_vars = {}
            self.actions = MagicMock(return_value=[lambda: "test_action"])
            self.to_dict = MagicMock(return_value={"param": "value"})
            self.initialize = MagicMock()
            self.post_load = MagicMock()

    return MockTool()


@pytest.fixture
def mock_preset() -> MagicMock:
    """Fixture for a mock preset M3 instance."""
    mock_m3 = MagicMock(spec=M3)
    mock_m3.tools = [MagicMock(spec=BaseTool)]
    mock_m3.config = MagicMock(spec=M3Config)
    mock_m3.mcp = MagicMock(spec=FastMCP)
    return mock_m3


class TestM3:
    """Tests for M3 class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        m3 = M3()
        assert isinstance(m3.config, M3Config)
        assert m3.tools == []
        assert m3.mcp is None
        assert m3._mcp_config_generators == ALL_MCP_CONFIG_GENERATORS
        assert not m3._built

    def test_init_with_params(self, mock_config: M3Config) -> None:
        """Test initialization with parameters."""
        mock_mcp = MagicMock(spec=FastMCP)
        m3 = M3(config=mock_config, mcp=mock_mcp)
        assert m3.config == mock_config
        assert m3.mcp == mock_mcp

    def test_with_config(self, mock_config: M3Config) -> None:
        """Test chaining with_config."""
        m3 = M3()
        new_m3 = m3.with_config(mock_config)
        assert new_m3 != m3
        assert new_m3.config == mock_config
        assert new_m3.tools == m3.tools
        assert new_m3.mcp == m3.mcp

    def test_with_tool(self, mock_tool: BaseTool) -> None:
        """Test chaining with_tool."""
        m3 = M3()
        new_m3 = m3.with_tool(mock_tool)
        assert new_m3 != m3
        assert new_m3.tools == [mock_tool]
        assert new_m3.config == m3.config
        assert new_m3.mcp == m3.mcp

    def test_with_tools(self, mock_tool: BaseTool) -> None:
        """Test chaining with_tools."""
        m3 = M3()
        new_m3 = m3.with_tools([mock_tool, mock_tool])
        assert new_m3 != m3
        assert len(new_m3.tools) == 2
        assert new_m3.config == m3.config
        assert new_m3.mcp == m3.mcp

    @patch("m3.core.preset.registry.ALL_PRESETS", {"test_preset": MagicMock()})
    def test_with_preset_success(self, mock_preset: MagicMock) -> None:
        """Test chaining with_preset success."""
        mock_preset_class = MagicMock()
        mock_preset_class.create.return_value = mock_preset
        with patch.dict(
            "m3.core.preset.registry.ALL_PRESETS", {"test_preset": mock_preset_class}
        ):
            m3 = M3()
            new_m3 = m3.with_preset("test_preset")
            assert new_m3 != m3
            assert new_m3.tools == mock_preset.tools
            assert new_m3.config == mock_preset.config
            assert new_m3.mcp == mock_preset.mcp

    def test_with_preset_unknown(self) -> None:
        """Test with_preset raises for unknown preset."""
        m3 = M3()
        with pytest.raises(M3PresetError, match="Unknown preset"):
            m3.with_preset("unknown")

    @patch("m3.core.preset.registry.ALL_PRESETS", {"test_preset": MagicMock()})
    def test_with_preset_failure(self) -> None:
        """Test with_preset handles creation failure."""
        mock_preset_class = MagicMock()
        mock_preset_class.create.side_effect = Exception("Creation failed")
        with patch.dict(
            "m3.core.preset.registry.ALL_PRESETS", {"test_preset": mock_preset_class}
        ):
            m3 = M3()
            with pytest.raises(M3PresetError, match="Failed to create preset"):
                m3.with_preset("test_preset")

    def test_build_success(self, mock_tool: BaseTool) -> None:
        """Test successful build."""
        with patch.dict(ALL_MCP_CONFIG_GENERATORS, {"test": MagicMock()}):
            mock_generator = ALL_MCP_CONFIG_GENERATORS["test"]
            mock_generator.generate.return_value = {"config": "test"}
            mock_mcp = MagicMock(spec=FastMCP)
            mock_mcp.tool.return_value = lambda x: x
            m3 = M3(mcp=mock_mcp).with_tool(mock_tool)
            result = m3.build(type="test")
            assert result == {"config": "test"}
            assert m3._built
            mock_tool.initialize.assert_called_once()
            mock_generator.generate.assert_called_once()

    def test_build_no_tools(self) -> None:
        """Test build fails with no tools."""
        m3 = M3()
        with pytest.raises(M3BuildError):
            m3.build()

    def test_build_validation_failure(self, mock_tool: BaseTool) -> None:
        """Test build fails on validation."""
        mock_tool.required_env_vars = {"MISSING": None}
        m3 = M3().with_tool(mock_tool)
        with pytest.raises(M3BuildError):
            m3.build()

    def test_build_init_failure(self, mock_tool: BaseTool) -> None:
        """Test build fails on tool init."""
        mock_tool.initialize.side_effect = Exception("Init failed")
        m3 = M3().with_tool(mock_tool)
        with pytest.raises(M3BuildError):
            m3.build()

    def test_build_unknown_type(self) -> None:
        """Test build fails on unknown config type."""
        m3 = M3()
        with pytest.raises(M3BuildError):
            m3.build(type="unknown")

    def test_run_not_built(self) -> None:
        """Test run fails if not built."""
        m3 = M3()
        with pytest.raises(M3BuildError, match="Call .build()"):
            m3.run()

    def test_run_no_mcp(self) -> None:
        """Test run fails if no MCP."""
        m3 = M3()
        m3._built = True
        with pytest.raises(M3InitializationError, match="MCP not initialized"):
            m3.run()

    def test_run_success(self, mock_tool: BaseTool) -> None:
        """Test successful run."""
        mock_mcp = MagicMock(spec=FastMCP)
        m3 = M3(mcp=mock_mcp).with_tool(mock_tool)
        m3._built = True
        with patch.object(m3, "_teardown_tools") as mock_teardown:
            m3.run()
            mock_mcp.run.assert_called_once()
            mock_teardown.assert_called_once()

    def test_run_exception(self, mock_tool: BaseTool) -> None:
        """Test run handles exception."""
        mock_mcp = MagicMock(spec=FastMCP)
        mock_mcp.run.side_effect = Exception("Run failed")
        m3 = M3(mcp=mock_mcp).with_tool(mock_tool)
        m3._built = True
        with patch.object(m3, "_teardown_tools") as mock_teardown:
            with pytest.raises(Exception, match="Run failed"):
                m3.run()
            mock_teardown.assert_called_once()

    def test_save_not_built(self) -> None:
        """Test save fails if not built."""
        m3 = M3()
        with pytest.raises(M3BuildError, match="Call .build()"):
            m3.save("test.json")

    def test_save_success(self, tmp_path: Path, mock_tool: BaseTool) -> None:
        """Test successful save."""
        path = tmp_path / "config.json"
        m3 = M3().with_tool(mock_tool)
        m3._built = True
        m3.save(str(path))
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert "config" in data
        assert "tools" in data
        assert len(data["tools"]) == 1

    def test_save_serialization_error(self, mock_tool: BaseTool) -> None:
        """Test save handles serialization error."""
        mock_tool.to_dict.side_effect = TypeError("Serialization failed")
        m3 = M3().with_tool(mock_tool)
        m3._built = True
        with pytest.raises(M3BuildError, match="Failed to serialize"):
            m3.save("test.json")

    def test_load_success(self, tmp_path: Path) -> None:
        """Test successful load."""
        path = tmp_path / "config.json"
        data = {
            "config": {"log_level": "INFO", "env_vars": {}},
            "tools": [{"type": "mocktool", "params": {"param": "value"}}],
        }
        with open(path, "w") as f:
            json.dump(data, f)

        with patch.dict(ALL_TOOLS, {"mocktool": MagicMock()}):
            mock_tool_cls = ALL_TOOLS["mocktool"]
            mock_tool = MagicMock(spec=BaseTool)
            mock_tool_cls.from_dict.return_value = mock_tool
            m3 = M3.load(str(path))
            assert isinstance(m3, M3)
            assert m3._built
            mock_tool.post_load.assert_called_once()

    def test_load_file_not_found(self) -> None:
        """Test load fails if file not found."""
        with pytest.raises(FileNotFoundError):
            M3.load("nonexistent.json")

    def test_load_invalid_config(self, tmp_path: Path) -> None:
        """Test load fails on invalid config."""
        path = tmp_path / "invalid.json"
        with open(path, "w") as f:
            json.dump({"invalid": "data"}, f)
        with pytest.raises(M3ValidationError, match="Invalid config"):
            M3.load(str(path))

    def test_load_unknown_tool(self, tmp_path: Path) -> None:
        """Test load fails on unknown tool."""
        path = tmp_path / "config.json"
        data = {
            "config": {"log_level": "INFO", "env_vars": {}},
            "tools": [{"type": "unknown", "params": {}}],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        with pytest.raises(M3ValidationError, match="Unknown tool type"):
            M3.load(str(path))

    def test_teardown_tools(self, mock_tool: BaseTool) -> None:
        """Test teardown of tools."""
        mock_backend = MagicMock()
        mock_tool.backends = {"test": mock_backend}
        m3 = M3().with_tool(mock_tool)
        m3._teardown_tools()
        mock_backend.teardown.assert_called_once()

    def test_post_load(self, mock_tool: BaseTool) -> None:
        """Test post_load calls tool post_load."""
        m3 = M3().with_tool(mock_tool)
        m3._post_load()
        mock_tool.post_load.assert_called_once()
        assert m3._built

    @patch("builtins.open")
    def test_save_oserror(
        self, mock_open: MagicMock, mock_tool: BaseTool, caplog
    ) -> None:
        """Test save handles OSError during file write."""
        mock_open.side_effect = OSError("Permission denied")
        m3 = M3().with_tool(mock_tool)
        m3._built = True
        with pytest.raises(OSError) as exc_info:
            m3.save("test.json")
        assert "Permission denied" in str(exc_info.value)
        assert "File write error: Permission denied" in caplog.text

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_load_oserror(
        self, mock_open: MagicMock, mock_exists: MagicMock, caplog
    ) -> None:
        """Test load handles OSError during file read."""
        mock_open.side_effect = OSError("Permission denied")
        with pytest.raises(OSError) as exc_info:
            M3.load("test.json")
        assert "Permission denied" in str(exc_info.value)
        assert "File read error: Permission denied" in caplog.text

    def test_generate_config_unknown_type_no_suggestion(self) -> None:
        """Test _generate_config raises for unknown type without suggestion."""
        with patch.dict(ALL_MCP_CONFIG_GENERATORS, {"unrelated": MagicMock()}):
            m3 = M3()
            with pytest.raises(M3ValidationError) as exc_info:
                m3._generate_config(type="unknown")
            assert "Unknown config type: unknown." in str(exc_info.value)
            assert "Did you mean" not in str(exc_info.value)

    def test_generate_config_unknown_type_with_suggestion(self) -> None:
        """Test _generate_config raises for unknown type with suggestion."""
        with patch.dict(ALL_MCP_CONFIG_GENERATORS, {"fastmcp": MagicMock()}):
            m3 = M3()
            with pytest.raises(M3ValidationError) as exc_info:
                m3._generate_config(type="fastmc")
            assert "Unknown config type: fastmc. Did you mean 'fastmcp'?" in str(
                exc_info.value
            )
