# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M3 (MIMIC-IV + MCP + Models) is a Python CLI tool and MCP server that enables natural language querying of MIMIC-IV medical data. It supports both local SQLite databases (demo data) and BigQuery (full dataset) backends with OAuth2 authentication for secure access.

## Key Architecture

### Core Components
- **CLI (`src/m3/cli.py`)**: Main command-line interface using Typer
- **MCP Server (`src/m3/mcp_server.py`)**: FastMCP-based server providing medical data tools
- **Config (`src/m3/config.py`)**: Configuration management and dataset handling
- **Auth (`src/m3/auth.py`)**: OAuth2 authentication with JWT validation
- **Data I/O (`src/m3/data_io.py`)**: Database initialization and data processing

### Dual Backend Support
- **SQLite Backend**: Local demo database (~1k records) for development/testing
- **BigQuery Backend**: Full MIMIC-IV dataset on Google Cloud Platform
- Backend switching via environment variables or CLI arguments

### Security Features
- SQL injection protection with sqlparse validation
- OAuth2/JWT authentication for production deployments
- Rate limiting and audit logging
- Read-only query enforcement

## Common Development Commands

### Python Development
```bash
# Using UV (recommended)
uv sync                    # Install dependencies
uv run pytest             # Run tests
uv run pytest tests/test_mcp_server.py -v  # Run specific test file
uv run ruff check         # Lint code
uv run ruff format        # Format code
uv run pre-commit run --all-files  # Run pre-commit hooks

# Using standard pip
pip install -e ".[dev]"   # Install in development mode
pytest                    # Run tests
ruff check                # Lint code
ruff format               # Format code
```

### CLI Commands
```bash
m3 --help                 # Show CLI help
m3 init mimic-iv-demo     # Initialize demo database
m3 config                 # Interactive MCP client configuration
m3 config claude          # Configure Claude Desktop specifically
m3-mcp-server            # Start MCP server directly
```

### Web Application (React)
```bash
cd webapp
npm start                 # Start development server
npm run build            # Build for production
npm test                 # Run tests
```

## Testing

### Test Structure
- **Unit Tests**: Core functionality testing with mocks
- **Integration Tests**: MCP server and OAuth2 authentication
- **BigQuery Tests**: Mocked BigQuery client testing

### Key Test Files
- `tests/test_mcp_server.py`: MCP server functionality
- `tests/test_oauth2_auth.py`: OAuth2 authentication flows
- `tests/test_config.py`: Configuration management
- `tests/test_data_io.py`: Database operations

## Environment Configuration

### Required Environment Variables
- `M3_BACKEND`: "sqlite" or "bigquery"
- `M3_PROJECT_ID`: Google Cloud project ID (BigQuery only)
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project (BigQuery only)

### OAuth2 Configuration
- `M3_OAUTH2_ENABLED`: Enable OAuth2 authentication
- `M3_OAUTH2_ISSUER_URL`: OAuth2 issuer URL
- `M3_OAUTH2_AUDIENCE`: JWT audience claim
- `M3_OAUTH2_TOKEN`: Bearer token for testing

## MCP Tools Available

The MCP server provides these tools for medical data querying:
- `get_database_schema`: List available tables
- `get_table_info`: Get column information and sample data
- `execute_mimic_query`: Execute secure SELECT queries
- `get_icu_stays`: ICU admission data
- `get_lab_results`: Laboratory test results
- `get_race_distribution`: Patient demographics

## Database Locations

### Default Paths
- **SQLite databases**: `~/m3_data/databases/` (pip install) or `./m3_data/databases/` (development)
- **Raw data files**: `~/m3_data/raw_files/` (pip install) or `./m3_data/raw_files/` (development)

### Demo Database
- Default filename: `mimic_iv_demo.db`
- Primary verification table: `hosp_admissions`
- Downloaded from PhysioNet MIMIC-IV demo dataset

## Dependencies

### Core Dependencies
- `typer`: CLI framework
- `fastmcp`: MCP server implementation
- `sqlalchemy`: Database ORM
- `polars`: Data processing
- `google-cloud-bigquery`: BigQuery client
- `pyjwt[crypto]`: JWT authentication
- `sqlparse`: SQL validation

### Development Dependencies
- `pytest`: Testing framework
- `ruff`: Linting and formatting
- `pre-commit`: Git hooks

## Docker Support

### Building Docker Image
```bash
docker build -t m3:latest .
```

### Running M3 in Docker
```bash
# SQLite backend
docker run -d --name m3-server -p 8080:8080 -e M3_BACKEND=sqlite m3:latest m3-mcp-server

# BigQuery backend
docker run -d --name m3-server -p 8080:8080 \
  -e M3_BACKEND=bigquery \
  -e M3_PROJECT_ID=your-project-id \
  -v ./gcp-credentials:/app/credentials:ro \
  m3:latest m3-mcp-server
```

### Docker Image Details
- **Size**: ~936MB (multi-stage build optimized)
- **Base**: python:slim (latest stable Python)
- **User**: Non-root user (m3user)
- **Health Check**: Built-in health monitoring
- **Data Path**: `/home/m3user/m3_data`

See `DOCKER.md` for comprehensive Docker usage guide.

## Security Considerations

- All SQL queries are validated with sqlparse to prevent injection
- Only SELECT and PRAGMA statements allowed
- Rate limiting implemented for OAuth2 endpoints
- JWT tokens validated with proper cryptographic verification
- Read-only access enforced at database level