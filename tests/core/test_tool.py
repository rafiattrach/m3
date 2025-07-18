from pathlib import Path
from unittest.mock import patch

import pytest

from m3.core.tool.backend.backends.bigquery import BigQueryBackend
from m3.core.tool.backend.backends.sqlite import SQLiteBackend
from m3.core.tool.backend.base import BackendBase
from m3.core.tool.base import BaseTool
from m3.core.tool.cli.base import BaseToolCLI


class TestBaseTool:
    """Tests for BaseTool."""

    def test_abstract_methods(self):
        """Test BaseTool abstract methods."""
        with pytest.raises(TypeError):
            BaseTool()


class TestBackendBase:
    """Tests for BackendBase."""

    def test_abstract_methods(self):
        """Test BackendBase abstract methods."""
        with pytest.raises(TypeError):
            BackendBase()


class TestSQLiteBackend:
    """Tests for SQLiteBackend."""

    def test_init(self, tmp_path: Path):
        """Test initialization."""
        db_path = tmp_path / "M3_test_environment_test.db"
        backend = SQLiteBackend(path=str(db_path))
        assert backend.path == str(db_path)
        assert backend.connection is None
        if db_path.exists():
            db_path.unlink()

    def test_initialize(self, tmp_path: Path):
        """Test initialize creates connection."""
        db_path = tmp_path / "M3_test_environment_test.db"
        backend = SQLiteBackend(path=str(db_path))
        backend.initialize()
        assert backend.connection is not None
        backend.teardown()
        assert backend.connection is None
        if db_path.exists():
            db_path.unlink()


class TestBigQueryBackend:
    """Tests for BigQueryBackend."""

    @patch("google.cloud.bigquery.Client")
    def test_init(self, mock_client):
        """Test initialization."""
        backend = BigQueryBackend(project="test-project")
        assert backend.project == "test-project"
        assert backend.client is None

    @patch("google.cloud.bigquery.Client")
    def test_initialize(self, mock_client):
        """Test initialize creates client."""
        backend = BigQueryBackend(project="test-project")
        backend.initialize()
        mock_client.assert_called_once_with(project="test-project")
        assert backend.client is not None
        backend.teardown()
        assert backend.client is None


class TestBaseToolCLI:
    """Tests for BaseToolCLI."""

    def test_abstract_methods(self):
        """Test BaseToolCLI abstract methods."""
        with pytest.raises(TypeError):
            BaseToolCLI()
