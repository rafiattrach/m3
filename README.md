# M3: MIMIC-IV + MCP + Models 🏥🤖

> **MIMIC-IV querying (Local or Remote) with LLMs via Model Context Protocol (MCP)**

Query MIMIC-IV medical data using natural language through Claude Desktop or other MCP clients. Works with local SQLite databases or remote BigQuery.

## ✨ Features

- 🔍 **Natural Language Queries**: Ask questions about MIMIC-IV data in plain English
- 🏠 **Local SQLite**: Fast queries on local MIMIC-IV demo database
- ☁️ **BigQuery Support**: Scale to full MIMIC-IV dataset on Google Cloud
- 🤖 **Claude Desktop Integration**: Automated setup for seamless AI assistance
- 🔒 **Secure**: Read-only queries with SQL injection protection

## 🚀 Quick Start

### For Users

1. **Setup virtual environment** (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. **Install M3 with MCP support**:

   ```bash
   pip install -e ".[mcp]"
   ```
3. **Download MIMIC-IV demo database**:

   ```bash
   m3 init mimic-iv-demo
   ```
4. **Setup Claude Desktop** (automatically detects your environment):

   ```bash
   python mcp_client_configs/setup_claude_desktop.py
   ```
5. **Restart Claude Desktop** and start asking questions like:

   - "What tools do you have for MIMIC-IV data?"
   - "Show me patient demographics from the ICU"
   - "Find lab results for patient 10000032"

### For Developers

1. **Clone and install with dev dependencies**:

   ```bash
   git clone <repo-url>
   cd m3
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   pre-commit install  # Install git hooks
   ```
2. **For full MCP development** (includes BigQuery):

   ```bash
   pip install -e ".[mcp-full]"
   ```
3. **Run tests**:

   ```bash
   pytest
   ```

## 🔧 Configuration

### SQLite (Default) - Local Demo Dataset

- Uses MIMIC-IV demo database (subset of full data)
- **No cloud costs** - everything runs locally
- Perfect for development, testing, and learning
- Requires `m3 init mimic-iv-demo` to download the demo database first

### BigQuery - Full Dataset (Cloud)

For access to the complete MIMIC-IV dataset:

```bash
python mcp_client_configs/setup_claude_desktop.py --backend bigquery --project-id your-project-id
```

⚠️ **Note**: BigQuery usage incurs cloud costs

### 🔮 Coming Soon: Local Full Dataset

- Full MIMIC-IV dataset available locally (no cloud costs)
- Larger database for complete data access
- Stay tuned for integration instructions!

## 🛠️ Available Tools

- **execute_mimic_query**: Run custom SQL queries (SELECT only)
- **get_patient_demographics**: Patient info from ICU stays
- **get_lab_results**: Laboratory test results
- **get_database_schema**: Explore available tables

## 🔮 Roadmap

- 📱 More MCP clients
- 🏠 Local full MIMIC-IV dataset support

## 🤝 Contributing

We welcome contributions! Please see our development setup above and submit PRs.

*Built with ❤️ for the medical AI community*
