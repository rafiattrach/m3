import json
import logging
import os
import sqlite3
import tempfile
import zlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import polars as pl
import pytest
import requests
from beartype.typing import Dict, List
from fastmcp import Client
from typer.testing import CliRunner

from m3 import M3CLI
from m3.core.config import M3Config
from m3.core.tool.backend.backends.bigquery import BigQueryBackend
from m3.core.tool.backend.backends.sqlite import SQLiteBackend
from m3.core.utils.exceptions import M3ConfigError, M3ValidationError
from m3.m3 import M3
from m3.tools.mimic.components.auth import Auth
from m3.tools.mimic.components.data_io import COMMON_USER_AGENT, DataIO
from m3.tools.mimic.components.utils import (
    get_dataset_config,
    get_dataset_raw_files_path,
    get_default_database_path,
)
from m3.tools.mimic.mimic import MIMIC


def _bigquery_available() -> bool:
    """Check if BigQuery dependencies are available."""
    try:
        import importlib.util

        return importlib.util.find_spec("google.cloud.bigquery") is not None
    except ImportError:
        return False


def _strip_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes from text."""
    import re

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


runner = CliRunner()
app = M3CLI().app


class DummyResponse:
    """Dummy response for requests mocking."""

    def __init__(
        self,
        content: str | bytes,
        status_code: int = 200,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self.content = content.encode() if isinstance(content, str) else content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(response=self)

    @property
    def reason(self) -> str:
        return "Error"

    def iter_content(self, chunk_size: int = 1) -> List[bytes]:
        yield from [
            self.content[i : i + chunk_size]
            for i in range(0, len(self.content), chunk_size)
        ]


@pytest.fixture
def m3_config() -> M3Config:
    """Fixture for M3Config instance."""
    return M3Config()


@pytest.fixture
def data_io(m3_config: M3Config) -> DataIO:
    """Fixture for DataIO instance."""
    return DataIO(config=m3_config)


@pytest.fixture
def mock_session() -> MagicMock:
    """Fixture for mocked requests Session."""
    return MagicMock(spec=requests.Session)


class TestMimic:
    """Comprehensive tests for MIMIC tool components."""

    def test_oauth2_disabled_by_default(self) -> None:
        """Test that OAuth2 is disabled by default when M3_OAUTH2_ENABLED is not set or false."""
        config: M3Config = M3Config(env_vars={})
        auth: Auth = Auth(config)
        assert not auth.enabled

    def test_oauth2_invalid_configuration_missing_issuer(self) -> None:
        """Test that missing issuer URL raises M3ConfigError."""
        config: M3Config = M3Config(env_vars={"M3_OAUTH2_ENABLED": "true"})
        with pytest.raises(
            M3ConfigError, match="Missing required env var: M3_OAUTH2_ISSUER_URL"
        ):
            Auth(config)

    def test_oauth2_enabled_configuration(self) -> None:
        """Test that OAuth2 is enabled with proper configuration."""
        env_vars: dict[str, str] = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data,write:mimic-data",
        }
        config: M3Config = M3Config(env_vars=env_vars)
        auth: Auth = Auth(config)
        assert auth.enabled
        assert auth.issuer_url == "https://auth.example.com"
        assert auth.audience == "m3-api"
        assert auth.required_scopes == {"read:mimic-data", "write:mimic-data"}

    def test_jwks_url_auto_discovery(self) -> None:
        """Test that JWKS URL is auto-discovered from issuer URL when not set."""
        env_vars: dict[str, str] = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
        }
        config: M3Config = M3Config(env_vars=env_vars)
        auth: Auth = Auth(config)
        assert auth.jwks_url == "https://auth.example.com/.well-known/jwks.json"

    def test_jwks_url_custom(self) -> None:
        """Test that a custom JWKS URL is used when provided."""
        env_vars: dict[str, str] = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_JWKS_URL": "https://custom-jwks.example.com",
        }
        config: M3Config = M3Config(env_vars=env_vars)
        auth: Auth = Auth(config)
        assert auth.jwks_url == "https://custom-jwks.example.com"

    def test_scope_parsing(self) -> None:
        """Test that required scopes are correctly parsed from environment variable."""
        env_vars: dict[str, str] = {
            "M3_OAUTH2_ENABLED": "true",
            "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
            "M3_OAUTH2_AUDIENCE": "m3-api",
            "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data, write:mimic-data , admin",
        }
        config: M3Config = M3Config(env_vars=env_vars)
        auth: Auth = Auth(config)
        assert auth.required_scopes == {"read:mimic-data", "write:mimic-data", "admin"}

    @pytest.mark.asyncio
    async def test_decorator_oauth2_disabled(self) -> None:
        """Test that decorator allows access when OAuth2 is disabled."""
        config: M3Config = M3Config(env_vars={"M3_OAUTH2_ENABLED": "false"})
        auth: Auth = Auth(config)

        @auth.decorator
        def sync_func() -> str:
            return "success"

        result: str = await sync_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_oauth2_disabled_async(self) -> None:
        """Test that decorator allows access for async functions when OAuth2 is disabled."""
        config: M3Config = M3Config(env_vars={"M3_OAUTH2_ENABLED": "false"})
        auth: Auth = Auth(config)

        @auth.decorator
        async def async_func() -> str:
            return "success"

        result: str = await async_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_missing_token(self) -> None:
        """Test that decorator raises an error when token is missing and OAuth2 is enabled."""
        config: M3Config = M3Config(
            env_vars={
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
            }
        )
        auth: Auth = Auth(config)

        @auth.decorator
        def sync_func() -> str:
            return "success"

        with pytest.raises(M3ValidationError, match="Missing OAuth2 access token"):
            await sync_func()

    @pytest.mark.asyncio
    async def test_decorator_invalid_token(self) -> None:
        """Test that decorator raises an error when token is invalid."""
        config = M3Config(
            env_vars={
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
                "M3_OAUTH2_TOKEN": "Bearer invalid_token",
            }
        )
        auth: Auth = Auth(config)

        with patch.object(
            auth, "authenticate", side_effect=M3ValidationError("Invalid token")
        ):

            @auth.decorator
            def sync_func() -> str:
                return "success"

            with pytest.raises(M3ValidationError, match="Invalid token"):
                await sync_func()

    @pytest.mark.asyncio
    async def test_decorator_valid_token(self) -> None:
        """Test that decorator allows access with a valid token."""
        config = M3Config(
            env_vars={
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
                "M3_OAUTH2_TOKEN": "Bearer valid_token",
                "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data",
            }
        )
        auth = Auth(config)

        with patch.object(
            auth,
            "authenticate",
            return_value={"sub": "test-user", "scope": "read:mimic-data"},
        ):

            @auth.decorator
            def sync_func() -> str:
                return "success"

            result: str = await sync_func()
            assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_missing_scope(self) -> None:
        """Test that decorator raises an error when required scopes."""
        config = M3Config(
            env_vars={
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
                "M3_OAUTH2_TOKEN": "Bearer valid_token",
                "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data,write:mimic-data",
            }
        )
        auth: Auth = Auth(config)

        with patch.object(
            auth,
            "authenticate",
            side_effect=M3ValidationError(
                "Missing required scopes: {'write:mimic-data'}"
            ),
        ):

            @auth.decorator
            def sync_func() -> str:
                return "success"

            with pytest.raises(
                M3ValidationError, match="Missing required scopes: {'write:mimic-data'}"
            ):
                await sync_func()

    @pytest.mark.asyncio
    async def test_decorator_bearer_prefix(self) -> None:
        """Test that decorator handles tokens with 'Bearer ' prefix correctly."""
        config = M3Config(
            env_vars={
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                " M3_OAUTH2_AUDIENCE": "m3-api",
                " M3_OAUTH2_TOKEN": "Bearer valid_token",
                "M3_OAUTH2_REQUIRED_SCOPES": "read:mimic-data",
            }
        )
        auth: Auth = Auth(config)

        with patch.object(
            auth,
            "authenticate",
            return_value={"sub": "test-user", "scope": "read:mimic-data"},
        ):

            @auth.decorator
            def sync_func() -> str:
                return "success"

            result: str = await sync_func()
            assert result == "success"

    def test_common_user_agent_header(self) -> None:
        """Test COMMON_USER_AGENT is properly set."""
        assert isinstance(COMMON_USER_AGENT, str)
        assert "Mozilla/" in COMMON_USER_AGENT

    def test_scrape_urls_from_html_page(
        self, data_io: DataIO, mock_session: MagicMock
    ) -> None:
        """Test scraping .csv.gz URLs from HTML page."""
        html = (
            "<html><body>"
            '<a href="file1.csv.gz">ok</a>'
            '<a href="skip.txt">no</a>'
            "</body></html>"
        )
        dummy = DummyResponse(html)
        with patch.object(mock_session, "get", return_value=dummy):
            urls = data_io._scrape_urls_from_html_page(
                "http://example.com/", mock_session
            )
            assert urls == ["http://example.com/file1.csv.gz"]

    def test_scrape_no_matching_suffix(
        self, data_io: DataIO, mock_session: MagicMock
    ) -> None:
        """Test no URLs scraped if no matching suffix."""
        html = '<html><body><a href="file1.txt">ok</a></body></html>'
        dummy = DummyResponse(html)
        with patch.object(mock_session, "get", return_value=dummy):
            urls = data_io._scrape_urls_from_html_page(
                "http://example.com/", mock_session
            )
            assert urls == []

    def test_scrape_urls_error_handling(
        self, data_io: DataIO, mock_session: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test error handling in URL scraping."""
        with patch.object(
            mock_session, "get", side_effect=requests.RequestException("Network error")
        ):
            with caplog.at_level(logging.ERROR):
                urls = data_io._scrape_urls_from_html_page(
                    "http://example.com/", mock_session
                )
                assert urls == []
                assert "Scrape failed" in caplog.text

    def test_download_single_file_success(
        self, data_io: DataIO, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful file download."""
        content = "test content"
        dummy = DummyResponse(content, headers={"content-length": str(len(content))})
        target_path = tmp_path / "test.csv.gz"
        with patch.object(mock_session, "get", return_value=dummy):
            success = data_io._download_single_file(
                "http://example.com/test.csv.gz", target_path, mock_session
            )
            assert success
            assert target_path.exists()
            assert target_path.read_text() == content

    def test_download_single_file_failure(
        self,
        data_io: DataIO,
        mock_session: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test failed file download."""
        target_path = tmp_path / "test.csv.gz"
        with (
            patch.object(
                mock_session,
                "get",
                side_effect=requests.RequestException("Download error"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            success = data_io._download_single_file(
                "http://example.com/test.csv.gz", target_path, mock_session
            )
            assert not success
            assert not target_path.exists()
            assert "Download failed" in caplog.text

    def test_load_csv_with_robust_parsing_success(
        self, data_io: DataIO, tmp_path: Path
    ) -> None:
        """Test successful CSV loading with robust parsing."""
        csv_path = tmp_path / "test.csv.gz"
        content = "col1,col2\n1,2\n3,4\n"
        compressed = zlib.compress(content.encode())
        csv_path.write_bytes(compressed)
        df = data_io._load_csv_with_robust_parsing(csv_path, "test_table")
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2
        assert df.columns == ["col1", "col2"]

    def test_etl_csv_collection_to_sqlite_success(
        self, data_io: DataIO, tmp_path: Path
    ) -> None:
        """Test successful ETL from CSV to SQLite."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        csv_path = source_dir / "test.csv.gz"
        content = "col1,col2\n1,2"
        compressed = zlib.compress(content.encode())
        csv_path.write_bytes(compressed)
        db_path = tmp_path / "M3_test_environment_test.db"
        success = data_io._etl_csv_collection_to_sqlite(source_dir, db_path)
        assert success
        assert db_path.exists()
        if db_path.exists():
            db_path.unlink()

    def test_etl_csv_collection_to_sqlite_no_files(
        self, data_io: DataIO, tmp_path: Path
    ) -> None:
        """Test ETL with no CSV files returns False."""
        source_dir = tmp_path / "empty"
        source_dir.mkdir()
        db_path = tmp_path / "M3_test_environment_test.db"
        success = data_io._etl_csv_collection_to_sqlite(source_dir, db_path)
        assert not success
        if db_path.exists():
            db_path.unlink()

    @patch("m3.tools.mimic.components.data_io.get_dataset_config")
    @patch("m3.tools.mimic.components.data_io.get_dataset_raw_files_path")
    @patch("m3.tools.mimic.components.data_io.DataIO._download_dataset_files")
    @patch("m3.tools.mimic.components.data_io.DataIO._etl_csv_collection_to_sqlite")
    def test_initialize_success(
        self,
        mock_etl: MagicMock,
        mock_download: MagicMock,
        mock_raw_path: MagicMock,
        mock_dataset_config: MagicMock,
        data_io: DataIO,
        tmp_path: Path,
    ) -> None:
        """Test successful dataset initialization."""
        mock_dataset_config.return_value = {"file_listing_url": "http://example.com"}
        mock_raw_path.return_value = tmp_path / "raw"
        mock_download.return_value = True
        mock_etl.return_value = True
        success = data_io.initialize("test_dataset", tmp_path / "db.sqlite")
        assert success

    @patch("m3.tools.mimic.components.data_io.get_dataset_config")
    def test_initialize_invalid_dataset(
        self, mock_dataset_config: MagicMock, data_io: DataIO, tmp_path: Path
    ) -> None:
        """Test initialization with invalid dataset raises error."""
        mock_dataset_config.return_value = None
        with pytest.raises(M3ValidationError, match="Config not found"):
            data_io.initialize("invalid", tmp_path / "db.sqlite")

    @patch("m3.tools.mimic.components.data_io.get_dataset_config")
    @patch("m3.tools.mimic.components.data_io.get_dataset_raw_files_path")
    def test_initialize_invalid_raw_path(
        self,
        mock_raw_path: MagicMock,
        mock_dataset_config: MagicMock,
        data_io: DataIO,
        tmp_path: Path,
    ) -> None:
        """Test initialization with invalid raw path raises error."""
        mock_dataset_config.return_value = {"file_listing_url": "http://example.com"}
        mock_raw_path.return_value = None
        with pytest.raises(M3ValidationError, match="Raw files path not found"):
            data_io.initialize("mimic-iv-demo", tmp_path / "db.sqlite")

    @patch("m3.tools.mimic.components.data_io.DataIO._download_dataset_files")
    def test_initialize_download_failure(
        self, mock_download: MagicMock, data_io: DataIO, tmp_path: Path
    ) -> None:
        """Test initialization fails on download failure."""
        mock_download.return_value = False
        success = data_io.initialize("mimic-iv-demo", tmp_path / "db.sqlite")
        assert not success

    @patch("m3.tools.mimic.components.data_io.DataIO._download_dataset_files")
    @patch("m3.tools.mimic.components.data_io.DataIO._etl_csv_collection_to_sqlite")
    def test_initialize_etl_failure(
        self,
        mock_etl: MagicMock,
        mock_download: MagicMock,
        data_io: DataIO,
        tmp_path: Path,
    ) -> None:
        """Test initialization fails on ETL failure."""
        mock_download.return_value = True
        mock_etl.return_value = False
        success = data_io.initialize("mimic-iv-demo", tmp_path / "db.sqlite")
        assert not success

    def test_get_dataset_config_known(self, m3_config: M3Config) -> None:
        """Test retrieving config for a known dataset."""
        cfg = get_dataset_config("mimic-iv-demo")
        assert isinstance(cfg, dict)
        assert cfg.get("default_db_filename") == "mimic_iv_demo.db"

    def test_get_dataset_config_unknown(self, m3_config: M3Config) -> None:
        """Test retrieving config for an unknown dataset returns None."""
        assert get_dataset_config("not-a-dataset") is None

    def test_default_paths(self, m3_config: M3Config, tmp_path: Path) -> None:
        """Test default path generation and directory creation."""
        with patch.object(m3_config, "databases_dir", tmp_path / "dbs"):
            db_path = get_default_database_path(m3_config, "mimic-iv-demo")

            assert isinstance(db_path, Path)
            assert db_path.parent == tmp_path / "dbs" / "mimic-iv-demo"
            assert db_path.name == "mimic_iv_demo.db"

        with patch.object(m3_config, "raw_files_dir", tmp_path / "raw"):
            raw_path = get_dataset_raw_files_path(m3_config, "mimic-iv-demo")

            assert isinstance(raw_path, Path)
            assert raw_path.exists()
            assert raw_path == tmp_path / "raw" / "mimic-iv-demo"

    def test_raw_path_includes_dataset_name(
        self, m3_config: M3Config, tmp_path: Path
    ) -> None:
        """Test raw files path includes dataset name."""
        with patch.object(m3_config, "raw_files_dir", tmp_path / "raw"):
            raw_path = get_dataset_raw_files_path(m3_config, "mimic-iv-demo")
            assert "mimic-iv-demo" in str(raw_path)
            assert raw_path.exists()

    @patch("m3.tools.mimic.components.data_io.DataIO.initialize")
    @patch("sqlite3.connect")
    def test_mimic_init_respects_custom_db_path(
        self,
        mock_sqlite_connect: MagicMock,
        mock_initialize: MagicMock,
    ) -> None:
        """Test that m3 tools mimic init respects custom db path."""
        mock_initialize.return_value = True
        mock_cursor = mock_sqlite_connect.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = (100,)

        with tempfile.TemporaryDirectory() as temp_dir:
            custom_db_path = Path(temp_dir) / "custom_mimic.db"
            result = runner.invoke(
                app,
                [
                    "tools",
                    "mimic",
                    "init",
                    "--dataset",
                    "mimic-iv-demo",
                    "--db-path",
                    str(custom_db_path),
                ],
            )
            assert result.exit_code == 0
            output = _strip_ansi_codes(result.stdout)
            assert str(custom_db_path) in output
            mock_initialize.assert_called_once_with("mimic-iv-demo", custom_db_path)

        if custom_db_path.exists():
            custom_db_path.unlink()

    @patch("m3.core.config.M3Config")
    def test_tools_mimic_status(self, mock_config: MagicMock) -> None:
        """Test that tools mimic status displays info."""
        mock_config_instance = mock_config.return_value
        mock_config_instance.get_env_var.side_effect = lambda k, d: d
        result = runner.invoke(app, ["tools", "mimic", "status"])
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "MIMIC Tool Status" in output
        assert "Backend" in output
        assert "sqlite" in output

    def test_tools_mimic_configure(self, tmp_path: Path) -> None:
        """Test that tools mimic configure generates config."""
        config_path = tmp_path / "config.json"
        result = runner.invoke(
            app,
            [
                "tools",
                "mimic",
                "configure",
                "--backend",
                "sqlite",
                "--db-path",
                "M3_test_environment_test.db",
                "--output",
                str(config_path),
            ],
            input="\n",
        )
        assert result.exit_code == 0
        output = _strip_ansi_codes(result.stdout)
        assert "✅ Config dict saved to" in output
        assert config_path.exists()
        with open(config_path) as f:
            config = json.load(f)
        assert config["env_vars"]["M3_BACKEND"] == "sqlite"
        assert config["env_vars"]["M3_DB_PATH"] == "M3_test_environment_test.db"
        assert config["tool_params"]["backend_key"] == "sqlite"
        assert len(config["tool_params"]["backends"]) == 1
        assert config["tool_params"]["backends"][0]["type"] == "sqlite"
        assert (
            config["tool_params"]["backends"][0]["params"]["path"]
            == "M3_test_environment_test.db"
        )

        if config_path.exists():
            config_path.unlink()

        if Path("M3_test_environment_test.db").exists():
            Path("M3_test_environment_test.db").unlink()

    @pytest.fixture
    def test_db(self, tmp_path: Path) -> str:
        """Create a test SQLite database."""
        db_path: Path = tmp_path / "M3_test_environment_test.db"

        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()

        # Create icu_icustays table
        cursor.execute(
            """
            CREATE TABLE icu_icustays (
                subject_id INTEGER,
                hadm_id INTEGER,
                stay_id INTEGER,
                intime TEXT,
                outtime TEXT
            )
        """
        )
        cursor.execute(
            """
            INSERT INTO icu_icustays (subject_id, hadm_id, stay_id, intime, outtime)
            VALUES
                (10000032, 20000001, 30000001, '2180-07-23 15:00:00', '2180-07-24 12:00:00'),
                (10000033, 20000002, 30000002, '2180-08-15 10:30:00', '2180-08-16 14:15:00')
        """
        )

        # Create hosp_labevents table
        cursor.execute(
            """
            CREATE TABLE hosp_labevents (
                subject_id INTEGER,
                hadm_id INTEGER,
                itemid INTEGER,
                charttime TEXT,
                value TEXT
            )
        """
        )
        cursor.execute(
            """
            INSERT INTO hosp_labevents (subject_id, hadm_id, itemid, charttime, value)
            VALUES
                (10000032, 20000001, 50912, '2180-07-23 16:00:00', '120'),
                (10000033, 20000002, 50912, '2180-08-15 11:00:00', '95')
        """
        )

        # Create hosp_admissions table for race distribution
        cursor.execute(
            """
            CREATE TABLE hosp_admissions (
                subject_id INTEGER,
                hadm_id INTEGER,
                race TEXT
            )
        """
        )
        cursor.execute(
            """
            INSERT INTO hosp_admissions (subject_id, hadm_id, race)
            VALUES
                (10000032, 20000001, 'WHITE'),
                (10000033, 20000002, 'BLACK/AFRICAN AMERICAN')
        """
        )

        conn.commit()
        conn.close()

        return str(db_path)

    @pytest.mark.asyncio
    async def test_tools_via_client(self, test_db: str) -> None:
        """Test MCP tools through the FastMCP client."""
        with patch.dict(
            os.environ,
            {
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            config = M3Config(env_vars=os.environ.copy())
            mimic = MIMIC(
                backends=[SQLiteBackend(path=test_db)],
                config=config,
                backend_key="sqlite",
            )
            m3 = M3(config=config).with_tool(mimic)
            m3.build()

            async with Client(m3.mcp) as client:  # type: ignore
                result: str = await client.call_tool(
                    "execute_mimic_query",
                    {"sql_query": "SELECT COUNT(*) as count FROM icu_icustays"},
                )
                result_text: str = str(result)
                assert "count" in result_text
                assert "2" in result_text

                result = await client.call_tool(
                    "get_icu_stays", {"patient_id": 10000032, "limit": 10}
                )
                result_text = str(result)
                assert "10000032" in result_text

                result = await client.call_tool(
                    "get_lab_results", {"patient_id": 10000032, "limit": 20}
                )
                result_text = str(result)
                assert "10000032" in result_text

                result = await client.call_tool("get_database_schema", {})
                result_text = str(result)
                assert (
                    "icu_icustays" in result_text
                    and "hosp_labevents" in result_text
                    and "hosp_admissions" in result_text
                )

                result = await client.call_tool(
                    "get_table_info", {"table_name": "icu_icustays"}
                )
                result_text = str(result)
                assert "subject_id" in result_text
                assert "intime" in result_text

                result = await client.call_tool("get_race_distribution", {"limit": 5})
                result_text = str(result)
                assert "WHITE" in result_text
                assert "BLACK/AFRICAN AMERICAN" in result_text

        if Path(test_db).exists():
            Path(test_db).unlink()

    @pytest.mark.asyncio
    async def test_security_checks(self, test_db: str) -> None:
        """Test SQL injection protection."""
        with patch.dict(
            os.environ,
            {
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            config = M3Config(env_vars=os.environ.copy())
            mimic = MIMIC(
                backends=[SQLiteBackend(path=test_db)],
                config=config,
                backend_key="sqlite",
            )
            m3 = M3(config=config).with_tool(mimic)
            m3.build()

            async with Client(m3.mcp) as client:  # type: ignore
                # Test dangerous queries are blocked
                dangerous_queries: list[str] = [
                    "UPDATE icu_icustays SET subject_id = 999",
                    "DELETE FROM icu_icustays",
                    "INSERT INTO icu_icustays VALUES (1, 2, 3, '2020-01-01', '2020-01-02')",
                    "DROP TABLE icu_icustays",
                    "CREATE TABLE test (id INTEGER)",
                    "ALTER TABLE icu_icustays ADD COLUMN test TEXT",
                ]

                for query in dangerous_queries:
                    result: str = await client.call_tool(
                        "execute_mimic_query", {"sql_query": query}
                    )
                    result_text: str = str(result)
                    assert (
                        "Security Error:" in result_text
                        and "Only SELECT" in result_text
                    )

        if Path(test_db).exists():
            Path(test_db).unlink()

    @pytest.mark.asyncio
    async def test_invalid_sql(self, test_db: str) -> None:
        """Test handling of invalid SQL."""
        with patch.dict(
            os.environ,
            {
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            config = M3Config(env_vars=os.environ.copy())
            mimic = MIMIC(
                backends=[SQLiteBackend(path=test_db)],
                config=config,
                backend_key="sqlite",
            )
            m3 = M3(config=config).with_tool(mimic)
            m3.build()

            async with Client(m3.mcp) as client:  # type: ignore
                result: str = await client.call_tool(
                    "execute_mimic_query", {"sql_query": "INVALID SQL QUERY"}
                )
                result_text: str = str(result)
                assert "Query Failed:" in result_text and "syntax error" in result_text

        if Path(test_db).exists():
            Path(test_db).unlink()

    @pytest.mark.asyncio
    async def test_empty_results(self, test_db: str) -> None:
        """Test handling of queries with no results."""
        with patch.dict(
            os.environ,
            {
                "M3_OAUTH2_ENABLED": "false",
            },
            clear=True,
        ):
            config = M3Config(env_vars=os.environ.copy())
            mimic = MIMIC(
                backends=[SQLiteBackend(path=test_db)],
                config=config,
                backend_key="sqlite",
            )
            m3 = M3(config=config).with_tool(mimic)
            m3.build()

            async with Client(m3.mcp) as client:  # type: ignore
                result: str = await client.call_tool(
                    "execute_mimic_query",
                    {
                        "sql_query": "SELECT * FROM icu_icustays WHERE subject_id = 999999"
                    },
                )
                result_text: str = str(result)
                assert "No results found" in result_text

        if Path(test_db).exists():
            Path(test_db).unlink()

    @pytest.mark.asyncio
    async def test_oauth2_authentication_required(self, test_db: str) -> None:
        """Test that OAuth2 authentication is required when enabled."""
        with patch.dict(
            os.environ,
            {
                "M3_OAUTH2_ENABLED": "true",
                "M3_OAUTH2_ISSUER_URL": "https://auth.example.com",
                "M3_OAUTH2_AUDIENCE": "m3-api",
            },
            clear=True,
        ):
            config = M3Config(env_vars=os.environ.copy())
            mimic = MIMIC(
                backends=[SQLiteBackend(path=test_db)],
                config=config,
                backend_key="sqlite",
            )
            m3 = M3(config=config).with_tool(mimic)
            m3.build()

            async with Client(m3.mcp) as client:  # type: ignore
                result: str = await client.call_tool(
                    "execute_mimic_query",
                    {"sql_query": "SELECT COUNT(*) FROM icu_icustays"},
                    raise_on_error=False,
                )
                result_text: str = str(result)
                assert "Missing OAuth2 access token" in result_text

        if Path(test_db).exists():
            Path(test_db).unlink()

    @pytest.mark.skipif(
        not _bigquery_available(), reason="BigQuery dependencies not available"
    )
    @pytest.mark.asyncio
    async def test_bigquery_tools(self) -> None:
        """Test BigQuery tools functionality with mocks."""
        with patch.dict(
            os.environ,
            {
                "M3_PROJECT_ID": "test-project",
                "GOOGLE_CLOUD_PROJECT": "test-project",
            },
            clear=True,
        ):
            import pandas as pd

            with patch("google.auth.default") as mock_auth:
                mock_auth.return_value = (Mock(), "test-project")
                with patch("google.cloud.bigquery.Client") as mock_client:
                    mock_job: Mock = Mock()
                    mock_df: Mock = Mock(spec=pd.DataFrame)
                    mock_df.empty = False
                    mock_df.to_string.return_value = "Mock BigQuery result"
                    mock_df.__len__ = Mock(return_value=5)
                    mock_job.to_dataframe.return_value = mock_df

                    mock_client_instance: Mock = Mock()
                    mock_client_instance.query.return_value = mock_job
                    mock_client.return_value = mock_client_instance

                    config = M3Config(env_vars=os.environ.copy())
                    mimic = MIMIC(
                        backends=[BigQueryBackend(project="test-project")],
                        config=config,
                        backend_key="bigquery",
                    )
                    m3 = M3(config=config).with_tool(mimic)
                    m3.build()

                    async with Client(m3.mcp) as client:  # type: ignore
                        result: str = await client.call_tool(
                            "execute_mimic_query",
                            {
                                "sql_query": "SELECT COUNT(*) FROM `physionet-data.mimiciv_3_1_icu.icustays`"
                            },
                        )
                        result_text: str = str(result)
                        assert "Mock BigQuery result" in result_text

                        result = await client.call_tool(
                            "get_race_distribution", {"limit": 5}
                        )
                        result_text = str(result)
                        assert "Mock BigQuery result" in result_text

                        mock_client.assert_called_once_with(project="test-project")
                        assert mock_client_instance.query.called
