# M3: MIMIC-IV + MCP + Models 🏥🤖

> **Query MIMIC-IV medical data using natural language through MCP clients**

<a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white"></a>
<a href="https://modelcontextprotocol.io/"><img alt="MCP" src="https://img.shields.io/badge/MCP-Compatible-green?logo=ai&logoColor=white"></a>
<a href="https://hub.docker.com/"><img alt="Docker" src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml"><img alt="Tests" src="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml"><img alt="Code Quality" src="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/pulls"><img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"></a>

Transform medical data analysis with AI! Ask questions about MIMIC-IV data in plain English and get instant insights. Choose between local demo data (free) or full cloud dataset (BigQuery).

## ✨ Features

- 🔍 **Natural Language Queries**: Ask questions about MIMIC-IV data in plain English
- 🏠 **Local SQLite**: Fast queries on demo database (free, no setup)
- ☁️ **BigQuery Support**: Access full MIMIC-IV dataset on Google Cloud
- 🔒 **Enterprise Security**: OAuth2 authentication with JWT tokens and rate limiting
- 🛡️ **SQL Injection Protection**: Read-only queries with comprehensive validation
- 🐳 **Docker Ready**: Pre-built Docker images for easy deployment

## 🚀 Quick Start

> 💡 **Need more options?** Run `m3 --help` to see all available commands and options.

### 📦 Installation

**We recommend installing M3 via PyPI for the best experience. Docker is available as an alternative for containerized deployments.**

#### Option A: Install from PyPI (Recommended)

**Step 1: Create Virtual Environment**
```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**Step 2: Install M3**
```bash
# Install M3
pip install m3-mcp
```

#### Option B: Install from Source

#### Using standard `pip`
**Step 1: Clone and Navigate**
```bash
# Clone the repository
git clone https://github.com/rafiattrach/m3.git
cd m3
```

**Step 2: Create Virtual Environment**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**Step 3: Install M3**
```bash
# Install M3
pip install .
```

#### Using `UV` (Recommended)
Assuming you have [UV](https://docs.astral.sh/uv/getting-started/installation/) installed.

**Step 1: Clone and Navigate**
```bash
# Clone the repository
git clone https://github.com/rafiattrach/m3.git
cd m3
```

**Step 2: Create `UV` Virtual Environment**
```bash
# Create virtual environment
uv venv
```

**Step 3: Install M3**
```bash
uv sync
# Do not forget to use `uv run` to any subsequent commands to ensure you're using the `uv` virtual environment
```

#### Option C: Docker (Alternative Installation)

**For containerized deployment or when you prefer Docker**

**Step 1: Pull Docker Image**
```bash
# Pull the latest M3 Docker image
docker pull ghcr.io/rafiattrach/m3:latest

# Or build locally
git clone https://github.com/rafiattrach/m3.git
cd m3
docker build -t m3:latest .
```

**Step 2: Run with SQLite (Demo Data)**
```bash
# Create a data volume
docker volume create m3-data

# Initialize demo database
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo

# Start MCP server
docker run -d --name m3-server -p 8080:8080 \
  -v m3-data:/home/m3user/m3_data \
  -e M3_BACKEND=sqlite \
  m3:latest m3-mcp-server
```

**Step 3: Configure MCP Client**
```bash
# Generate MCP client configuration
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 config --quick
```

**For BigQuery with Docker:** See [Docker BigQuery Setup](#docker-bigquery-setup) below.

### 🗄️ Database Configuration

After installation, choose your data source:

#### Option A: Local Demo Database (Recommended for Beginners)

**Perfect for learning and development - completely free!**

1. **Download demo database**:
   ```bash
   m3 init mimic-iv-demo
   ```

2. **Setup MCP Client**:
   ```bash
   m3 config
   ```

   *Alternative: For Claude Desktop specifically:*
   ```bash
   m3 config claude
   ```

3. **Restart your MCP client** and ask:

   - "What tools do you have for MIMIC-IV data?"
   - "Show me patient demographics from the ICU"

#### Option B: BigQuery (Full Dataset)

**For researchers needing complete MIMIC-IV data**

##### Docker BigQuery Setup

**For Docker users only - if you installed via PyPI, skip to [Native BigQuery Setup](#native-bigquery-setup)**

**Step 1: Prepare GCP Credentials**
```bash
# Create directory for credentials
mkdir -p ./gcp-credentials

# Download your service account key to this directory
# (from Google Cloud Console > IAM & Admin > Service Accounts)
cp /path/to/your-service-account-key.json ./gcp-credentials/service-account.json
```

**Step 2: Run with BigQuery Backend**
```bash
# Start M3 with BigQuery backend
docker run -d --name m3-bigquery \
  -p 8080:8080 \
  -v ./gcp-credentials:/app/credentials:ro \
  -e M3_BACKEND=bigquery \
  -e M3_PROJECT_ID=your-gcp-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json \
  m3:latest m3-mcp-server
```

**Step 3: Configure MCP Client**
```bash
# Generate BigQuery MCP configuration
docker run --rm \
  -v ./gcp-credentials:/app/credentials:ro \
  -e M3_BACKEND=bigquery \
  -e M3_PROJECT_ID=your-gcp-project-id \
  m3:latest m3 config --quick --backend bigquery --project-id your-gcp-project-id
```

##### Native BigQuery Setup

##### Prerequisites
- Google Cloud account and project with billing enabled
- Access to MIMIC-IV on BigQuery (requires PhysioNet credentialing)

##### Setup Steps

1. **Install Google Cloud CLI**:

   **macOS (with Homebrew):**
   ```bash
   brew install google-cloud-sdk
   ```

   **Windows:** Download from https://cloud.google.com/sdk/docs/install

   **Linux:**
   ```bash
   curl https://sdk.cloud.google.com | bash
   ```

2. **Authenticate**:
   ```bash
   gcloud auth application-default login
   ```
   *This will open your browser - choose the Google account that has access to your BigQuery project with MIMIC-IV data.*

3. **Setup MCP Client for BigQuery**:
   ```bash
   m3 config
   ```

   *Alternative: For Claude Desktop specifically:*
   ```bash
   m3 config claude --backend bigquery --project-id YOUR_PROJECT_ID
   ```

4. **Test BigQuery Access** - Restart your MCP client and ask:
   ```
   Use the get_race_distribution function to show me the top 5 races in MIMIC-IV admissions.
   ```

## 🔧 Advanced Configuration

Need to configure other MCP clients or customize settings? Use these commands:

### Interactive Configuration (Universal)
```bash
m3 config
```
Generates configuration for any MCP client with step-by-step guidance.

### Quick Configuration Examples
```bash
# Quick universal config with defaults
m3 config --quick

# Universal config with custom database
m3 config --quick --backend sqlite --db-path /path/to/database.db

# Save config to file for other MCP clients
m3 config --output my_config.json
```

### 🔐 OAuth2 Authentication (Optional)

For production deployments requiring secure access to medical data:

```bash
# Enable OAuth2 with Claude Desktop
m3 config claude --enable-oauth2 \
  --oauth2-issuer https://your-auth-provider.com \
  --oauth2-audience m3-api \
  --oauth2-scopes "read:mimic-data"

# Or configure interactively
m3 config  # Choose OAuth2 option during setup
```

**Supported OAuth2 Providers:**
- Auth0, Google Identity Platform, Microsoft Azure AD, Keycloak
- Any OAuth2/OpenID Connect compliant provider

**Key Benefits:**
- 🔒 **JWT Token Validation**: Industry-standard security
- 🎯 **Scope-based Access**: Fine-grained permissions
- 🛡️ **Rate Limiting**: Abuse protection
- 📊 **Audit Logging**: Security monitoring

> 📖 **Complete OAuth2 Setup Guide**: See [`docs/OAUTH2_AUTHENTICATION.md`](docs/OAUTH2_AUTHENTICATION.md) for detailed configuration, troubleshooting, and production deployment guidelines.

## 🐳 Advanced Docker Usage

### Docker Compose for Production Deployments

**Step 1: Create Docker Compose Configuration**
```yaml
version: '3.8'

services:
  m3-sqlite:
    image: m3:latest
    container_name: m3-sqlite
    environment:
      - M3_BACKEND=sqlite
    volumes:
      - m3-data:/home/m3user/m3_data
    ports:
      - "8080:8080"
    command: m3-mcp-server
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "m3", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3

  m3-bigquery:
    image: m3:latest
    container_name: m3-bigquery
    environment:
      - M3_BACKEND=bigquery
      - M3_PROJECT_ID=${GCP_PROJECT_ID}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
    volumes:
      - m3-data:/home/m3user/m3_data
      - ./gcp-credentials:/app/credentials:ro
    ports:
      - "8081:8080"
    command: m3-mcp-server
    restart: unless-stopped

volumes:
  m3-data:
```

**Step 2: Run Services**
```bash
# Start SQLite service
docker-compose up -d m3-sqlite

# Start BigQuery service (with credentials)
export GCP_PROJECT_ID=your-project-id
docker-compose up -d m3-bigquery

# View logs
docker-compose logs -f m3-sqlite
```

### Docker Image Information

- **Image Size**: ~936MB (optimized multi-stage build)
- **Base Image**: `python:slim` (latest stable Python)
- **Architecture**: Multi-stage build for minimal size
- **User**: Non-root user (`m3user`) for security
- **Health Check**: Built-in container health monitoring
- **Data Path**: `/home/m3user/m3_data`

> 📖 **Complete Docker Guide**: See [`DOCKER.md`](DOCKER.md) for comprehensive Docker usage, troubleshooting, and production deployment guidelines.

### Backend Comparison

**SQLite Backend (Default)**
- ✅ **Free**: No cloud costs
- ✅ **Fast**: Local queries
- ✅ **Easy**: No authentication needed
- ✅ **Simple Setup**: Works with both PyPI and Docker
- ❌ **Limited**: Demo dataset only (~1k records)

**BigQuery Backend**
- ✅ **Complete**: Full MIMIC-IV dataset (~500k admissions)
- ✅ **Scalable**: Google Cloud infrastructure
- ✅ **Current**: Latest MIMIC-IV version (3.1)
- ✅ **Flexible**: Works with both PyPI and Docker
- ❌ **Costs**: BigQuery usage fees apply

## 🛠️ Available MCP Tools

When your MCP client processes questions, it uses these tools automatically:

- **get_database_schema**: List all available tables
- **get_table_info**: Get column info and sample data for a table
- **execute_mimic_query**: Execute SQL SELECT queries
- **get_icu_stays**: ICU stay information and length of stay data
- **get_lab_results**: Laboratory test results
- **get_race_distribution**: Patient race distribution

## 🧪 Example Prompts

Try asking your MCP client these questions:

**Demographics & Statistics:**

- `Prompt:` *What is the race distribution in MIMIC-IV admissions?*
- `Prompt:` *Show me patient demographics for ICU stays*
- `Prompt:` *How many total admissions are in the database?*

**Clinical Data:**

- `Prompt:` *Find lab results for patient X*
- `Prompt:` *What lab tests are most commonly ordered?*
- `Prompt:` *Show me recent ICU admissions*

**Data Exploration:**

- `Prompt:` *What tables are available in the database?*
- `Prompt:` *What tools do you have for MIMIC-IV data?*

## 🎩 Pro Tips

- Do you want to pre-approve the usage of all tools in Claude Desktop? Use the prompt below and then select **Always Allow**
   - `Prompt:` *Can you please call all your tools in a logical sequence?*

## 🔍 Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check container logs
docker logs m3-server

# Check container status
docker ps -a

# Remove and recreate container
docker stop m3-server && docker rm m3-server
docker run -d --name m3-server -p 8080:8080 m3:latest m3-mcp-server
```

**"Database not found" in Docker:**
```bash
# Initialize database in Docker volume
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo

# Verify database exists
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest ls -la /home/m3user/m3_data/databases/
```

**BigQuery authentication issues in Docker:**
```bash
# Check credentials mount
docker run --rm -v ./gcp-credentials:/app/credentials:ro m3:latest ls -la /app/credentials/

# Verify service account key
docker run --rm -v ./gcp-credentials:/app/credentials:ro m3:latest \
  cat /app/credentials/service-account.json | jq '.type'
```

**Docker image build fails:**
```bash
# Clear Docker cache
docker system prune -a

# Build with no cache
docker build --no-cache -t m3:latest .

# Check disk space
docker system df
```

### Common Issues

**SQLite "Database not found" errors:**
```bash
# Native installation
m3 init mimic-iv-demo

# Docker installation
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo
```

**MCP client server not starting:**
1. Check your MCP client logs (for Claude Desktop: Help → View Logs)
2. Verify configuration file location and format
3. Restart your MCP client completely
4. For Docker: Check container health with `docker ps`

### OAuth2 Authentication Issues

**"Missing OAuth2 access token" errors:**
```bash
# Set your access token
export M3_OAUTH2_TOKEN="Bearer your-access-token-here"
```

**"OAuth2 authentication failed" errors:**
- Verify your token hasn't expired
- Check that required scopes are included in your token
- Ensure your OAuth2 provider configuration is correct

**Rate limit exceeded:**
- Wait for the rate limit window to reset
- Contact your administrator to adjust limits if needed

> 🔧 **OAuth2 Troubleshooting**: See [`OAUTH2_AUTHENTICATION.md`](docs/OAUTH2_AUTHENTICATION.md) for detailed OAuth2 troubleshooting and configuration guides.

### BigQuery Issues

**"Access Denied" errors:**
- Ensure you have MIMIC-IV access on PhysioNet
- Verify your Google Cloud project has BigQuery API enabled
- Check that you're authenticated: `gcloud auth list`

**"Dataset not found" errors:**
- Confirm your project ID is correct
- Ensure you have access to `physionet-data` project

**Authentication issues:**
```bash
# Re-authenticate
gcloud auth application-default login

# Check current authentication
gcloud auth list
```

## 👩‍💻 For Developers

### Development Setup

#### Option A: Standard `pip` Development Setup (Recommended)
**Step 1: Clone and Navigate**
```bash
# Clone the repository
git clone https://github.com/rafiattrach/m3.git
cd m3
```

**Step 2: Create and Activate Virtual Environment**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**Step 3: Install Development Dependencies**
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"
# Install pre-commit hooks
pre-commit install
```

#### Option B: Development Setup with `UV` (Also Recommended)
**Step 1: Clone and Navigate**
```bash
# Clone the repository
git clone https://github.com/rafiattrach/m3.git
cd m3
```

**Step 2: Create and Activate `UV` Virtual Environment**
```bash
# Create virtual environment
uv venv
```

**Step 3: Install Development Dependencies**
```bash
# Install in development mode with dev dependencies (by default, UV runs in editable mode)
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Do not forget to use `uv run` to any subsequent commands to ensure you're using the `uv` virtual environment
```

#### Option C: Docker Development Setup (Alternative)

**For developers who prefer containerized development environments**

**Step 1: Clone and Build**
```bash
# Clone the repository
git clone https://github.com/rafiattrach/m3.git
cd m3

# Build development Docker image
docker build -t m3:dev .
```

**Step 2: Development with Volume Mounts**
```bash
# Run with source code mounted for development
docker run --rm -it \
  -v $(pwd)/src:/app/src \
  -v m3-data:/home/m3user/m3_data \
  m3:dev /bin/bash

# Or run specific commands
docker run --rm -v $(pwd)/src:/app/src m3:dev m3 --version
```

**Step 3: Testing in Docker**
```bash
# Run tests in Docker
docker run --rm -v $(pwd):/app -w /app m3:dev pytest

# Run linting
docker run --rm -v $(pwd):/app -w /app m3:dev ruff check
```

### Testing

```bash
pytest  # All tests (includes OAuth2 and BigQuery mocks)
pytest tests/test_mcp_server.py -v  # MCP server tests
pytest tests/test_oauth2_auth.py -v  # OAuth2 authentication tests
```

### Test BigQuery Locally

```bash
# Set environment variables
export M3_BACKEND=bigquery
export M3_PROJECT_ID=your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id

# Optional: Test with OAuth2 authentication
export M3_OAUTH2_ENABLED=true
export M3_OAUTH2_ISSUER_URL=https://your-provider.com
export M3_OAUTH2_AUDIENCE=m3-api
export M3_OAUTH2_TOKEN="Bearer your-test-token"

# Test MCP server
m3-mcp-server
```

## 🔮 Roadmap

- 🏠 **Local Full Dataset**: Complete MIMIC-IV locally (no cloud costs)
- 🔧 **Advanced Tools**: More specialized medical data functions
- 📊 **Visualization**: Built-in plotting and charting tools
- 🔐 **Enhanced Security**: Role-based access control, audit logging
- 🌐 **Multi-tenant Support**: Organization-level data isolation

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

*Built with ❤️ for the medical AI community*

**Need help?** Open an issue on GitHub or check our troubleshooting guide above.
