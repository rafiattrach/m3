# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M3 (MIMIC-IV + MCP + Models) enables natural language querying of MIMIC-IV medical data through MCP (Model Context Protocol) clients. It supports both local SQLite demo data and full BigQuery cloud access.

## Development Commands

### Installation & Setup
```bash
# Development installation
pip install -e ".[dev]"
pre-commit install

# Production installation  
pip install -e .
```

### CLI Commands
```bash
# Initialize demo dataset
m3 init mimic-iv-demo [--db-path PATH]

# Configure MCP clients
m3 config [CLIENT] [--backend sqlite|bigquery] [--project-id ID] [--quick]

# Run MCP server directly
m3-mcp-server
```

### Testing
```bash
# Run all tests (includes mocks for BigQuery)
pytest

# Run specific test files
pytest tests/test_mcp_server.py -v
pytest tests/test_cli.py -v
```

### Code Quality
```bash
# Linting and formatting (via pre-commit)
ruff check --fix
ruff format

# Manual pre-commit run
pre-commit run --all-files
```

## Architecture

### Core Components
- **`cli.py`**: Typer-based CLI with `init` and `config` commands
- **`mcp_server.py`**: FastMCP server providing 5 medical data query tools
- **`config.py`**: Configuration management and dataset definitions
- **`data_io.py`**: Data downloading and ETL pipeline using Polars
- **`mcp_client_configs/`**: Configuration scripts for various MCP clients

### Backend System
- **SQLite backend**: Local demo data for development/testing
- **BigQuery backend**: Full MIMIC-IV dataset access via Google Cloud
- Backend switching via environment variables or CLI flags

### MCP Tools Provided
1. `execute_mimic_query`: General SQL queries with injection protection
2. `get_patient_demographics`: Patient demographic information
3. `get_lab_results`: Laboratory test results
4. `get_race_distribution`: Patient race/ethnicity statistics
5. `get_database_schema`: Database structure information

## Environment Variables

### Backend Configuration
- `M3_BACKEND`: "sqlite" (default) or "bigquery"
- `M3_DB_PATH`: Custom SQLite database path
- `M3_PROJECT_ID`: Google Cloud project ID for BigQuery
- `GOOGLE_CLOUD_PROJECT`: Alternative project ID variable

### OAuth2 Authentication (Optional)
- `M3_OAUTH2_ENABLED`: "true" to enable OAuth2 authentication
- `M3_OAUTH2_ISSUER_URL`: OAuth2 provider issuer URL
- `M3_OAUTH2_AUDIENCE`: OAuth2 audience (API identifier)
- `M3_OAUTH2_REQUIRED_SCOPES`: Required scopes (comma-separated)
- `M3_OAUTH2_TOKEN`: Client access token (Bearer token)
- `M3_OAUTH2_JWKS_URL`: Custom JWKS URL (auto-discovered if not set)
- `M3_OAUTH2_RATE_LIMIT_REQUESTS`: Rate limit per hour (default: 100)

See `OAUTH2_AUTHENTICATION.md` for complete OAuth2 configuration guide.

## Dependencies

**Build System**: setuptools with pyproject.toml

**Key Dependencies**:
- `typer[rich]`: CLI framework
- `fastmcp`: MCP server implementation
- `polars[pyarrow]`: Data processing
- `google-cloud-bigquery`: BigQuery support
- `sqlparse`: SQL security validation

## Testing Approach

- Unit tests for each module
- Integration tests for MCP server functionality
- Mock-based BigQuery testing (no real API calls)
- Security testing for SQL injection prevention
- CLI command testing with Typer's test runner

## Security Considerations

- SQL injection protection using sqlparse
- Read-only query enforcement
- Input validation for all MCP tool parameters
- Secure credential handling for BigQuery access

## Entry Points

- `m3`: Main CLI command (`m3.cli:app`)
- `m3-mcp-server`: Direct MCP server execution (`m3.mcp_server:main`)