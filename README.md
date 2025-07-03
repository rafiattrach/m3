# M3: MIMIC-IV + MCP + Models 🏥🤖

> **Query MIMIC-IV medical data using natural language through MCP clients**

<a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white"></a>
<a href="https://modelcontextprotocol.io/"><img alt="MCP" src="https://img.shields.io/badge/MCP-Compatible-green?logo=ai&logoColor=white"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml"><img alt="Tests" src="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml"><img alt="Code Quality" src="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/pulls"><img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"></a>

Transform medical data analysis with AI! Ask questions about [MIMIC-IV](https://physionet.org/content/mimiciv) data in plain English and get instant insights, leveraging the power of the Model Context Protocol ([MCP](https://modelcontextprotocol.io/)). Choose between local demo data (free) or full cloud dataset (BigQuery).

## ✨ Features

- 🔍 **Natural Language Queries**: Ask questions about MIMIC-IV data in plain English
- 🏠 **Local SQLite**: Fast queries on demo database (free, no setup)
- ☁️ **BigQuery Support**: Access full MIMIC-IV dataset on Google Cloud
- 🔒 **Enterprise Security**: OAuth2 authentication with JWT tokens and rate limiting
- 🛡️ **SQL Injection Protection**: Read-only queries with comprehensive validation

## 🚀 Quick Start

> 💡 **Need more options?** Run `m3 --help` to see all available commands and options.

### 📦 Installation

Choose your preferred installation method:

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

### Backend Comparison

**SQLite Backend (Default)**
- ✅ **Free**: No cloud costs
- ✅ **Fast**: Local queries
- ✅ **Easy**: No authentication needed
- ❌ **Limited**: Demo dataset only (~1k records)

**BigQuery Backend**
- ✅ **Complete**: Full MIMIC-IV dataset (~500k admissions)
- ✅ **Scalable**: Google Cloud infrastructure
- ✅ **Current**: Latest MIMIC-IV version (3.1)
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

## ▶️ Demo with Claude Desktop

- `Prompt:` *What's in the mimic dataset?*
- `Prompt:` *What percentage of patients stayed more than a week in the hospital? Plot it.*

![m3-demo-claude-desktop-sonnet](https://github.com/user-attachments/assets/0c5aae89-18a9-4f4a-a77d-f4043963399e)


## 🔍 Troubleshooting

### Common Issues

**SQLite "Database not found" errors:**
```bash
# Re-download demo database
m3 init mimic-iv-demo
```

**MCP client server not starting:**
1. Check your MCP client logs (for Claude Desktop: Help → View Logs)
2. Verify configuration file location and format
3. Restart your MCP client completely

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

> 🔧 **OAuth2 Troubleshooting**: See [`OAUTH2_AUTHENTICATION.md`](OAUTH2_AUTHENTICATION.md) for detailed OAuth2 troubleshooting and configuration guides.

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
