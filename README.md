# M3: MIMIC-IV + MCP + Models

## Development Setup

To contribute to M3:

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate    # On Windows
    ```

2.  **Install editable mode with development dependencies:**
    This installs the project itself, plus tools like Ruff, pre-commit, and pytest.
    ```bash
    pip install -e ".[dev]"
    ```

3.  **Install Git hooks (for auto-formatting/linting on commit):**
    ```bash
    pre-commit install
    ```

4.  **Run tests:**
    ```bash
    pytest
    ```

You're now set up for development!

## Idea Draft

**M3** brings the power of MIMIC-IV to your local machine, enhanced with a Model Context Protocol (MCP) server and natural language querying via Large Language Models (LLMs).

## Vision

1.  **Easy Setup:** `pip install m3`
2.  **Secure Login:** `m3 login` (for PhysioNet)
3.  **Local Ingestion:** `m3 init --dataset mimic-iv-demo --db-path ./mimic_demo.db` (downloads & prepares data)
4.  **Private Data Server:** `m3 serve` (starts a local MCP server)
5.  **Intuitive Querying:** `m3 ui` (opens a web UI to chat with your data via LLMs)

## Core Components

*   **Data Pipeline:** Downloads MIMIC-IV (could be expanded in the future) into a local SQL database (SQLite/Postgres).
*   **MCP Server:** Exposes the local database via an MCP-compliant API.
*   **LLM Integration:** Allows users to query the data using natural language, translated to SQL/MCP queries by LLMs.
*   **Local UI:** A simple web interface for interacting with the system.

## Current Status

Pre-alpha. Initial development focused on the data pipeline.

## Getting Started (Target)

```bash
pip install m3
m3 login # PhysioNet credentials
m3 init --dataset mimic-iv-demo --db-path ./mimic_demo.db # ~200MB
m3 serve &
m3 ui
```

(In the UI, select an LLM, type "How many patients died during their hospital admission?")
