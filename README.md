# M3: MIMIC-IV + MCP + Models 🏥🤖

> **Query MIMIC-IV medical data using natural language through MCP clients**

Transform medical data analysis with AI! Ask questions about MIMIC-IV data in plain English and get instant insights. Choose between local demo data (free) or full cloud dataset (BigQuery).

## ✨ Features

- 🔍 **Natural Language Queries**: Ask questions about MIMIC-IV data in plain English
- 🏠 **Local SQLite**: Fast queries on demo database (free, no setup)
- ☁️ **BigQuery Support**: Access full MIMIC-IV dataset on Google Cloud
- 🔒 **Secure**: Read-only queries with SQL injection protection

## 🚀 Quick Start

> 💡 **Need more options?** Run `m3 --help` to see all available commands and options.

### Prerequisites

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### Option 1: Local Demo (Recommended for Beginners)

**Perfect for learning and development - completely free!**

1. **Install M3**:
   ```bash
   pip install -e .
   ```

2. **Download demo database**:
   ```bash
   m3 init mimic-iv-demo
   ```

3. **Setup MCP Client**:
   ```bash
   m3 config
   ```

   *Alternative: For Claude Desktop specifically:*
   ```bash
   m3 config claude
   ```

4. **Restart your MCP client** and ask:

   - "What tools do you have for MIMIC-IV data?"
   - "Show me patient demographics from the ICU"

### Option 2: BigQuery (Full Dataset)

**For researchers needing complete MIMIC-IV data**

#### Prerequisites
- Google Cloud account and project with billing enabled
- Access to MIMIC-IV on BigQuery (requires PhysioNet credentialing)

#### Setup Steps

1. **Install Google Cloud CLI**:
   ```bash
   # macOS (with Homebrew)
   brew install google-cloud-sdk

   # Windows: Download from https://cloud.google.com/sdk/docs/install
   # Linux
   curl https://sdk.cloud.google.com | bash
   ```

2. **Authenticate**:
   ```bash
   gcloud auth application-default login
   ```

3. **Install M3**:
   ```bash
   pip install -e .
   ```

4. **Setup MCP Client for BigQuery**:
   ```bash
   m3 config
   ```

   *Alternative: For Claude Desktop specifically:*
   ```bash
   m3 config claude --backend bigquery --project-id YOUR_PROJECT_ID
   ```

5. **Test BigQuery Access** - Restart your MCP client and ask:
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

## 🧪 Example Queries

Try asking your MCP client these questions:

**Demographics & Statistics:**

- "What is the race distribution in MIMIC-IV admissions?"
- "Show me patient demographics for ICU stays"
- "How many total admissions are in the database?"

**Clinical Data:**

- "Find lab results for patient X"
- "What lab tests are most commonly ordered?"
- "Show me recent ICU admissions"

**Data Exploration:**

- "What tables are available in the database?"
- "What tools do you have for MIMIC-IV data?"

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

```bash
git clone https://github.com/rafiattrach/m3 # HTTPS as an example
cd m3
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

### Testing

```bash
pytest  # All tests (uses mocks for BigQuery)
pytest tests/test_mcp_server.py -v  # Detailed test output
```

### Test BigQuery Locally

```bash
# Set environment variables
export M3_BACKEND=bigquery
export M3_PROJECT_ID=your-project-id
export GOOGLE_CLOUD_PROJECT=your-project-id

# Test MCP server
m3-mcp-server
```

## 🔮 Roadmap

- 🏠 **Local Full Dataset**: Complete MIMIC-IV locally (no cloud costs)
- 🔧 **Advanced Tools**: More specialized medical data functions
- 📊 **Visualization**: Built-in plotting and charting tools

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

*Built with ❤️ for the medical AI community*

**Need help?** Open an issue on GitHub or check our troubleshooting guide above.
