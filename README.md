# M3: MIMIC-IV + MCP + Models 🏥🤖

<div align="center">
  <img src="webapp/public/m3_logo_transparent.png" alt="M3 Logo" width="300"/>
</div>

> **Query MIMIC-IV medical data using natural language through MCP clients**

<a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white"></a>
<a href="https://modelcontextprotocol.io/"><img alt="MCP" src="https://img.shields.io/badge/MCP-Compatible-green?logo=ai&logoColor=white"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml"><img alt="Tests" src="https://github.com/rafiattrach/m3/actions/workflows/tests.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml"><img alt="Code Quality" src="https://github.com/rafiattrach/m3/actions/workflows/pre-commit.yaml/badge.svg"></a>
<a href="https://github.com/rafiattrach/m3/pulls"><img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"></a>

Transform medical data analysis with AI! Ask questions about MIMIC-IV data in plain English and get instant insights. Choose between local demo data (free) or full cloud dataset (BigQuery).

## Features

- **Natural Language Queries**: Ask questions about MIMIC-IV data in plain English
- **Local SQLite**: Fast queries on demo database (free, no setup)
- **BigQuery Support**: Access full MIMIC-IV dataset on Google Cloud
- **Enterprise Security**: OAuth2 authentication with JWT tokens and rate limiting
- **SQL Injection Protection**: Read-only queries with comprehensive validation

## 🚀 Quick Start

> 📺 **Prefer video tutorials?** Check out [step-by-step video guides](https://rafiattrach.github.io/m3/) covering setup, PhysioNet configuration, and more.

### Install uv (required for `uvx`)

We use `uvx` to run the MCP server. Install `uv` from the official installer, then verify with `uv --version`.

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:
```bash
uv --version
```

### BigQuery Setup (Optional - Full Dataset)

**Skip this if using SQLite demo database.**

1. **Install Google Cloud SDK:**
   - macOS: `brew install google-cloud-sdk`
   - Windows/Linux: https://cloud.google.com/sdk/docs/install

2. **Authenticate:**
   ```bash
   gcloud auth application-default login
   ```
   *Opens your browser - choose the Google account with BigQuery access to MIMIC-IV.*

### MCP Client Configuration

Paste one of the following into your MCP client config, then restart your client.

**Supported clients:** [Claude Desktop](https://www.claude.com/download), [Cursor](https://cursor.com/download), [Goose](https://block.github.io/goose/), and [more](https://github.com/punkpeye/awesome-mcp-clients).

<table>
<tr>
<td width="50%">

**SQLite (Demo Database)**

Free, local, no setup required.

```json
{
  "mcpServers": {
    "m3": {
      "command": "uvx",
      "args": ["m3-mcp"],
      "env": {
        "M3_BACKEND": "sqlite"
      }
    }
  }
}
```

*Demo database (136MB, 100 patients, 275 admissions) downloads automatically on first query.*

</td>
<td width="50%">

**BigQuery (Full Dataset)**

Requires GCP credentials and PhysioNet access.

```json
{
  "mcpServers": {
    "m3": {
      "command": "uvx",
      "args": ["m3-mcp"],
      "env": {
        "M3_BACKEND": "bigquery",
        "M3_PROJECT_ID": "your-project-id"
      }
    }
  }
}
```

*Replace `your-project-id` with your Google Cloud project ID.*

</td>
</tr>
</table>

**That's it!** Restart your MCP client and ask:
- "What tools do you have for MIMIC-IV data?"
- "Show me patient demographics from the ICU"
- "What is the race distribution in admissions?"

---

## Backend Comparison

| Feature | SQLite (Demo) | BigQuery (Full) |
|---------|---------------|-----------------|
| **Cost** | Free | BigQuery usage fees |
| **Setup** | Zero config | GCP credentials required |
| **Data Size** | 100 patients, 275 admissions | 365k patients, 546k admissions |
| **Speed** | Fast (local) | Network latency |
| **Use Case** | Learning, development | Research, production |

---

## Alternative Installation Methods

> Already have Docker or prefer pip? Here are other ways to run m3:

### 🐳 Docker (No Python Required)

<table>
<tr>
<td width="50%">

**SQLite:**
```bash
git clone https://github.com/rafiattrach/m3.git && cd m3
docker build -t m3:lite --target lite .
docker run -d --name m3-server m3:lite tail -f /dev/null
```

</td>
<td width="50%">

**BigQuery:**
```bash
git clone https://github.com/rafiattrach/m3.git && cd m3
docker build -t m3:bigquery --target bigquery .
docker run -d --name m3-server \
  -e M3_BACKEND=bigquery \
  -e M3_PROJECT_ID=your-project-id \
  -v $HOME/.config/gcloud:/root/.config/gcloud:ro \
  m3:bigquery tail -f /dev/null
```

</td>
</tr>
</table>

**MCP config (same for both):**
```json
{
  "mcpServers": {
    "m3": {
      "command": "docker",
      "args": ["exec", "-i", "m3-server", "python", "-m", "m3.mcp_server"]
    }
  }
}
```

Stop: `docker stop m3-server && docker rm m3-server`

### pip Install + CLI Tools

```bash
pip install m3-mcp
```

> 💡 **CLI commands:** Run `m3 --help` to see all available options.

**Useful CLI commands:**
- `m3 init mimic-iv-demo` - Download demo database
- `m3 config` - Generate MCP configuration interactively
- `m3 config claude --backend bigquery --project-id YOUR_PROJECT_ID` - Quick BigQuery setup

**Example MCP config:**
```json
{
  "mcpServers": {
    "m3": {
      "command": "m3-mcp-server",
      "env": {
        "M3_BACKEND": "sqlite"
      }
    }
  }
}
```

### Local Development

For contributors:

```bash
git clone https://github.com/rafiattrach/m3.git && cd m3
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

**MCP config:**
```json
{
  "mcpServers": {
    "m3": {
      "command": "/path/to/m3/.venv/bin/python",
      "args": ["-m", "m3.mcp_server"],
      "cwd": "/path/to/m3",
      "env": {
        "M3_BACKEND": "sqlite"
      }
    }
  }
}
```

## Advanced Configuration

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

### OAuth2 Authentication (Optional)

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

---

## Available MCP Tools

When your MCP client processes questions, it uses these tools automatically:

- **get_database_schema**: List all available tables
- **get_table_info**: Get column info and sample data for a table
- **execute_mimic_query**: Execute SQL SELECT queries
- **get_icu_stays**: ICU stay information and length of stay data
- **get_lab_results**: Laboratory test results
- **get_race_distribution**: Patient race distribution

## Example Prompts

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

## Troubleshooting

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

## For Developers

> See "Local Development" section above for setup instructions.

### Running Tests

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

## Roadmap

- **Local Full Dataset**: Complete MIMIC-IV locally (no cloud costs)
- **Advanced Tools**: More specialized medical data functions
- **Visualization**: Built-in plotting and charting tools
- **Enhanced Security**: Role-based access control, audit logging
- **Multi-tenant Support**: Organization-level data isolation

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Citation

If you use M3 in your research, please cite:

```bibtex
@article{attrach2025conversational,
  title={Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis},
  author={Attrach, Rafi Al and Moreira, Pedro and Fani, Rajna and Umeton, Renato and Celi, Leo Anthony},
  journal={arXiv preprint arXiv:2507.01053},
  year={2025}
}
```

You can also use the "Cite this repository" button at the top of the GitHub page for other formats.

## Related Projects

M3 has been forked and adapted by the community:
- [MCPStack-MIMIC](https://github.com/MCP-Pipeline/mcpstack-mimic) - Integrates M3 with other MCP servers (Jupyter, sklearn, etc.)

---

*Built with ❤️ for the medical AI community*

**Need help?** Open an issue on GitHub or check our troubleshooting guide above.
