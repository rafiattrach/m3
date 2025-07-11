from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from beartype.roar import BeartypeCallHintParamViolation

from m3.auth import OAuth2Validator, generate_test_token
from m3.cli import dataset_init_cmd
from m3.config import (
    get_dataset_config,
    get_dataset_raw_files_path,
    get_default_database_path,
)
from m3.data_io import (
    _download_single_file,
    _etl_csv_collection_to_sqlite,
    _load_csv_with_robust_parsing,
    _scrape_urls_from_html_page,
    initialize_dataset,
)
from m3.mcp_client_configs.dynamic_mcp_config import MCPConfigGenerator
from m3.mcp_client_configs.setup_claude_desktop import create_mcp_config

with patch("pathlib.Path.exists", return_value=True):
    with patch(
        "m3.mcp_server.get_default_database_path", return_value=Path("/fake/test.db")
    ):
        from m3.mcp_server import (
            _is_safe_query,
            _validate_limit,
        )


class TestTypeChecks:
    """
    Test class for verifying type checks enforced by beartype across M3.
    """

    @pytest.mark.parametrize("invalid_input", [123, ["list"], {"dict": 1}, None])
    def test_config_get_dataset_config(self, invalid_input):
        """Test get_dataset_config with invalid dataset_name types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            get_dataset_config(invalid_input)

    @pytest.mark.parametrize("invalid_input", [123, ["list"], {"dict": 1}, None])
    def test_config_get_default_database_path(self, invalid_input):
        """Test get_default_database_path with invalid dataset_name types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            get_default_database_path(invalid_input)

    @pytest.mark.parametrize("invalid_input", [123, ["list"], {"dict": 1}, None])
    def test_config_get_dataset_raw_files_path(self, invalid_input):
        """Test get_dataset_raw_files_path with invalid dataset_name types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            get_dataset_raw_files_path(invalid_input)

    def test_data_io_download_single_file_invalid_url(self):
        """Test _download_single_file with invalid url type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _download_single_file(123, Path("/tmp/file"), requests.Session())

    def test_data_io_download_single_file_invalid_target_filepath(self):
        """Test _download_single_file with invalid target_filepath type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _download_single_file("http://example.com", "/tmp/file", requests.Session())

    def test_data_io_download_single_file_invalid_session(self):
        """Test _download_single_file with invalid session type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _download_single_file("http://example.com", Path("/tmp/file"), 123)

    def test_data_io_scrape_urls_from_html_page_invalid_page_url(self):
        """Test _scrape_urls_from_html_page with invalid page_url type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _scrape_urls_from_html_page(123, requests.Session())

    def test_data_io_scrape_urls_from_html_page_invalid_session(self):
        """Test _scrape_urls_from_html_page with invalid session type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _scrape_urls_from_html_page("http://example.com", 123)

    def test_data_io_scrape_urls_from_html_page_invalid_file_suffix(self):
        """Test _scrape_urls_from_html_page with invalid file_suffix type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _scrape_urls_from_html_page(
                "http://example.com", requests.Session(), file_suffix=123
            )

    def test_data_io_load_csv_with_robust_parsing_invalid_csv_file_path(self):
        """Test _load_csv_with_robust_parsing with invalid csv_file_path type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _load_csv_with_robust_parsing("/invalid/path", "table_name")

    def test_data_io_load_csv_with_robust_parsing_invalid_table_name(self):
        """Test _load_csv_with_robust_parsing with invalid table_name type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _load_csv_with_robust_parsing(Path("/tmp/file.csv"), 123)

    def test_data_io_etl_csv_collection_to_sqlite_invalid_csv_source_dir(self):
        """Test _etl_csv_collection_to_sqlite with invalid csv_source_dir type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _etl_csv_collection_to_sqlite("/invalid/path", Path("/tmp/db.db"))

    def test_data_io_etl_csv_collection_to_sqlite_invalid_db_target_path(self):
        """Test _etl_csv_collection_to_sqlite with invalid db_target_path type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _etl_csv_collection_to_sqlite(Path("/tmp"), "/invalid/path")

    def test_data_io_initialize_dataset_invalid_dataset_name(self):
        """Test initialize_dataset with invalid dataset_name type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            initialize_dataset(123, Path("/tmp/db.db"))

    def test_data_io_initialize_dataset_invalid_db_target_path(self):
        """Test initialize_dataset with invalid db_target_path type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            initialize_dataset("mimic-iv-demo", "/invalid/path")

    @pytest.mark.parametrize(
        "invalid_limit", ["string", 3.14, None, [1], {"key": "value"}]
    )
    def test_mcp_server_validate_limit(self, invalid_limit):
        """Test _validate_limit with invalid limit types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _validate_limit(invalid_limit)

    @pytest.mark.parametrize("invalid_sql_query", [123, ["list"], {"dict": 1}, None])
    def test_mcp_server_is_safe_query_sql_query(self, invalid_sql_query):
        """Test _is_safe_query with invalid sql_query types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _is_safe_query(invalid_sql_query)

    @pytest.mark.parametrize(
        "invalid_internal_tool", ["string", 123, [1], {"key": "value"}]
    )
    def test_mcp_server_is_safe_query_internal_tool(self, invalid_internal_tool):
        """Test _is_safe_query with invalid internal_tool types."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _is_safe_query("SELECT * FROM table", internal_tool=invalid_internal_tool)

    def test_auth_oauth2_validator_wrong_config(self):
        """Test OAuth2Validator.__init__ with invalid config type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            _ = OAuth2Validator(123)

    def test_auth_generate_test_token_invalid_issuer(self):
        """Test generate_test_token with invalid issuer type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            generate_test_token(issuer=123)

    def test_auth_generate_test_token_invalid_audience(self):
        """Test generate_test_token with invalid audience type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            generate_test_token(audience=123)

    def test_auth_generate_test_token_invalid_subject(self):
        """Test generate_test_token with invalid subject type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            generate_test_token(subject=123)

    def test_auth_generate_test_token_invalid_scopes(self):
        """Test generate_test_token with invalid scopes type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            generate_test_token(scopes="invalid")

    def test_auth_generate_test_token_invalid_expires_in(self):
        """Test generate_test_token with invalid expires_in type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            generate_test_token(expires_in="string")

    def test_cli_dataset_init_cmd_invalid_dataset_name(self):
        """Test dataset_init_cmd with invalid dataset_name type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            dataset_init_cmd(123)

    def test_cli_dataset_init_cmd_invalid_db_path_str(self):
        """Test dataset_init_cmd with invalid db_path_str type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            dataset_init_cmd(db_path_str=123)

    def test_dynamic_mcp_config_generate_config_invalid_server_name(self):
        """Test MCPConfigGenerator.generate_config with invalid server_name type."""
        generator = MCPConfigGenerator()
        with pytest.raises(BeartypeCallHintParamViolation):
            generator.generate_config(server_name=123)

    def test_setup_claude_desktop_create_mcp_config_invalid_backend(self):
        """Test create_mcp_config with invalid backend type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            create_mcp_config(backend=123)

    def test_setup_claude_desktop_create_mcp_config_invalid_db_path(self):
        """Test create_mcp_config with invalid db_path type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            create_mcp_config(db_path=123)

    def test_setup_claude_desktop_create_mcp_config_invalid_project_id(self):
        """Test create_mcp_config with invalid project_id type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            create_mcp_config(project_id=123)

    def test_setup_claude_desktop_create_mcp_config_invalid_oauth2_enabled(self):
        """Test create_mcp_config with invalid oauth2_enabled type."""
        with pytest.raises(BeartypeCallHintParamViolation):
            create_mcp_config(oauth2_enabled="string")
