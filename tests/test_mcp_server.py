"""
Tests for the MCP server functionality.
"""

import os
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastmcp import Client

# Mock the database path check during import to handle CI environments
with patch("pathlib.Path.exists", return_value=True):
    with patch(
        "m3.mcp_server.get_default_database_path", return_value=Path("/fake/test.db")
    ):
        from m3.mcp_server import _init_backend, mcp


def _bigquery_available():
    """Check if BigQuery dependencies are available."""
    try:
        import importlib.util

        return importlib.util.find_spec("google.cloud.bigquery") is not None
    except ImportError:
        return False


class TestMCPServerSetup:
    """Test MCP server setup and configuration."""

    def test_server_instance_exists(self):
        """Test that the FastMCP server instance exists."""
        assert mcp is not None
        assert mcp.name == "m3"

    def test_backend_init_sqlite_default(self):
        """Test SQLite backend initialization with defaults."""
        with patch.dict(os.environ, {"M3_BACKEND": "sqlite"}, clear=True):
            with patch("m3.mcp_server.get_default_database_path") as mock_path:
                mock_path.return_value = Path("/fake/path.db")
                with patch("pathlib.Path.exists", return_value=True):
                    _init_backend()
                    # If no exception raised, initialization succeeded

    def test_backend_init_sqlite_custom_path(self):
        """Test SQLite backend initialization with custom path."""
        with patch.dict(
            os.environ,
            {"M3_BACKEND": "sqlite", "M3_DB_PATH": "/custom/path.db"},
            clear=True,
        ):
            with patch("pathlib.Path.exists", return_value=True):
                _init_backend()
                # If no exception raised, initialization succeeded

    def test_backend_init_sqlite_missing_db(self):
        """Test SQLite backend initialization with missing database."""
        with patch.dict(os.environ, {"M3_BACKEND": "sqlite"}, clear=True):
            with patch("m3.mcp_server.get_default_database_path") as mock_path:
                mock_path.return_value = Path("/fake/path.db")
                with patch("pathlib.Path.exists", return_value=False):
                    with pytest.raises(FileNotFoundError):
                        _init_backend()

    @pytest.mark.skipif(
        not _bigquery_available(), reason="BigQuery dependencies not available"
    )
    def test_backend_init_bigquery(self):
        """Test BigQuery backend initialization."""
        with patch.dict(
            os.environ,
            {"M3_BACKEND": "bigquery", "M3_PROJECT_ID": "test-project"},
            clear=True,
        ):
            with patch("google.cloud.bigquery.Client") as mock_client:
                mock_client.return_value = Mock()
                _init_backend()
                # If no exception raised, initialization succeeded
                mock_client.assert_called_once_with(project="test-project")

    def test_backend_init_invalid(self):
        """Test initialization with invalid backend."""
        with patch.dict(os.environ, {"M3_BACKEND": "invalid"}, clear=True):
            with pytest.raises(ValueError, match="Unsupported backend"):
                _init_backend()


class TestMCPTools:
    """Test MCP tools functionality."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test SQLite database."""
        db_path = tmp_path / "test.db"

        # Create test database with MIMIC-IV-like structure
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create icu_icustays table
        cursor.execute("""
            CREATE TABLE icu_icustays (
                subject_id INTEGER,
                hadm_id INTEGER,
                stay_id INTEGER,
                intime TEXT,
                outtime TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO icu_icustays (subject_id, hadm_id, stay_id, intime, outtime)
            VALUES
                (10000032, 20000001, 30000001, '2180-07-23 15:00:00', '2180-07-24 12:00:00'),
                (10000033, 20000002, 30000002, '2180-08-15 10:30:00', '2180-08-16 14:15:00')
        """)

        # Create hosp_labevents table
        cursor.execute("""
            CREATE TABLE hosp_labevents (
                subject_id INTEGER,
                hadm_id INTEGER,
                itemid INTEGER,
                charttime TEXT,
                value TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO hosp_labevents (subject_id, hadm_id, itemid, charttime, value)
            VALUES
                (10000032, 20000001, 50912, '2180-07-23 16:00:00', '120'),
                (10000033, 20000002, 50912, '2180-08-15 11:00:00', '95')
        """)

        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.mark.asyncio
    async def test_tools_via_client(self, test_db):
        """Test MCP tools through the FastMCP client."""
        # Set up environment for SQLite backend with OAuth2 disabled
        with patch.dict(
            os.environ,
            {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": test_db,
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            # Initialize backend
            _init_backend()

            # Test via FastMCP client
            async with Client(mcp) as client:
                # Test execute_mimic_query tool
                result = await client.call_tool(
                    "execute_mimic_query",
                    {"sql_query": "SELECT COUNT(*) as count FROM icu_icustays"},
                )
                result_text = str(result)
                assert "count" in result_text
                assert "2" in result_text

                # Test get_icu_stays tool
                result = await client.call_tool(
                    "get_icu_stays", {"patient_id": 10000032, "limit": 10}
                )
                result_text = str(result)
                assert "10000032" in result_text

                # Test get_lab_results tool
                result = await client.call_tool(
                    "get_lab_results", {"patient_id": 10000032, "limit": 20}
                )
                result_text = str(result)
                assert "10000032" in result_text

                # Test get_database_schema tool
                result = await client.call_tool("get_database_schema", {})
                result_text = str(result)
                assert "icu_icustays" in result_text or "hosp_labevents" in result_text

    @pytest.mark.asyncio
    async def test_security_checks(self, test_db):
        """Test SQL injection protection."""
        with patch.dict(
            os.environ,
            {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": test_db,
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            _init_backend()

            async with Client(mcp) as client:
                # Test dangerous queries are blocked
                dangerous_queries = [
                    "UPDATE icu_icustays SET subject_id = 999",
                    "DELETE FROM icu_icustays",
                    "INSERT INTO icu_icustays VALUES (1, 2, 3, '2020-01-01', '2020-01-02')",
                    "DROP TABLE icu_icustays",
                    "CREATE TABLE test (id INTEGER)",
                    "ALTER TABLE icu_icustays ADD COLUMN test TEXT",
                ]

                for query in dangerous_queries:
                    result = await client.call_tool(
                        "execute_mimic_query", {"sql_query": query}
                    )
                    result_text = str(result)
                    assert (
                        "Security Error:" in result_text
                        and "Only SELECT" in result_text
                    )

    @pytest.mark.asyncio
    async def test_invalid_sql(self, test_db):
        """Test handling of invalid SQL."""
        with patch.dict(
            os.environ,
            {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": test_db,
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            _init_backend()

            async with Client(mcp) as client:
                result = await client.call_tool(
                    "execute_mimic_query", {"sql_query": "INVALID SQL QUERY"}
                )
                result_text = str(result)
                assert "Query Failed:" in result_text and "syntax error" in result_text

    @pytest.mark.asyncio
    async def test_empty_results(self, test_db):
        """Test handling of queries with no results."""
        with patch.dict(
            os.environ,
            {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": test_db,
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            _init_backend()

            async with Client(mcp) as client:
                result = await client.call_tool(
                    "execute_mimic_query",
                    {
                        "sql_query": "SELECT * FROM icu_icustays WHERE subject_id = 999999"
                    },
                )
                result_text = str(result)
                assert "No results found" in result_text

    @pytest.mark.asyncio
    async def test_oauth2_authentication_required(self, test_db):
        """Test that OAuth2 authentication is required when enabled."""
        # Set up environment for SQLite backend with OAuth2 enabled
        with patch.dict(
            os.environ,
            {
                "M3_BACKEND": "sqlite",
                "M3_DB_PATH": test_db,
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
            },
            clear=True,
        ):
            _init_backend()

            async with Client(mcp) as client:
                # Test that tools require authentication
                result = await client.call_tool(
                    "execute_mimic_query",
                    {"sql_query": "SELECT COUNT(*) FROM icu_icustays"},
                )
                result_text = str(result)
                assert "Missing OAuth2 access token" in result_text


class TestBigQueryIntegration:
    """Test BigQuery integration with mocks (no real API calls)."""

    @pytest.mark.skipif(
        not _bigquery_available(), reason="BigQuery dependencies not available"
    )
    @pytest.mark.asyncio
    async def test_bigquery_tools(self):
        """Test BigQuery tools functionality with mocks."""
        with patch.dict(
            os.environ,
            {"M3_BACKEND": "bigquery", "M3_PROJECT_ID": "test-project"},
            clear=True,
        ):
            with patch("google.cloud.bigquery.Client") as mock_client:
                # Mock BigQuery client and query results
                mock_job = Mock()
                mock_df = Mock()
                mock_df.empty = False
                mock_df.to_string.return_value = "Mock BigQuery result"
                mock_df.__len__ = Mock(return_value=5)
                mock_job.to_dataframe.return_value = mock_df

                mock_client_instance = Mock()
                mock_client_instance.query.return_value = mock_job
                mock_client.return_value = mock_client_instance

                _init_backend()

                async with Client(mcp) as client:
                    # Test execute_mimic_query tool
                    result = await client.call_tool(
                        "execute_mimic_query",
                        {
                            "sql_query": "SELECT COUNT(*) FROM `physionet-data.mimiciv_3_1_icu.icustays`"
                        },
                    )
                    result_text = str(result)
                    assert "Mock BigQuery result" in result_text

                    # Test get_race_distribution tool
                    result = await client.call_tool(
                        "get_race_distribution", {"limit": 5}
                    )
                    result_text = str(result)
                    assert "Mock BigQuery result" in result_text

                    # Verify BigQuery client was called
                    mock_client.assert_called_once_with(project="test-project")
                    assert mock_client_instance.query.called


class TestServerIntegration:
    """Test overall server integration."""

    def test_server_main_function_exists(self):
        """Test that the main function exists and is callable."""
        from m3.mcp_server import main

        assert callable(main)

    def test_server_can_be_imported_as_module(self):
        """Test that the server can be imported as a module."""
        import m3.mcp_server

        assert hasattr(m3.mcp_server, "mcp")
        assert hasattr(m3.mcp_server, "main")
