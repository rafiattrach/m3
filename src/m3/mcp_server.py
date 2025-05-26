"""
M3 MCP Server - MIMIC-IV + MCP + Models
Provides MCP tools for querying MIMIC-IV data via SQLite or BigQuery.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from fastmcp import FastMCP

from m3.config import get_default_database_path

# Create FastMCP server instance
mcp = FastMCP("m3")

# Global variables for backend configuration
_backend = None
_db_path = None
_bq_client = None
_project_id = None


def _init_backend():
    """Initialize the backend based on environment variables."""
    global _backend, _db_path, _bq_client, _project_id

    _backend = os.getenv("M3_BACKEND", "sqlite")

    if _backend == "sqlite":
        _db_path = os.getenv("M3_DB_PATH")
        if not _db_path:
            # Use default database path
            _db_path = get_default_database_path("mimic-iv-demo")

        # Ensure the database exists
        if not Path(_db_path).exists():
            raise FileNotFoundError(f"SQLite database not found: {_db_path}")

    elif _backend == "bigquery":
        try:
            from google.cloud import bigquery
        except ImportError:
            raise ImportError(
                "BigQuery dependencies not found. Install with: pip install google-cloud-bigquery"
            )

        _project_id = os.getenv("M3_PROJECT_ID", "physionet-data")
        try:
            _bq_client = bigquery.Client(project=_project_id)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BigQuery client: {e}")

    else:
        raise ValueError(f"Unsupported backend: {_backend}")


@mcp.tool()
def execute_mimic_query(sql_query: str) -> str:
    """Execute SQL query against MIMIC-IV data.

    Args:
        sql_query: SQL query to execute (SELECT only)

    Returns:
        Query results as formatted text
    """
    # Security check - only allow SELECT queries
    if any(
        keyword in sql_query.upper()
        for keyword in ["UPDATE", "DELETE", "INSERT", "DROP", "CREATE", "ALTER"]
    ):
        return "Error: Only SELECT queries are allowed"

    try:
        if _backend == "sqlite":
            return _execute_sqlite_query(sql_query)
        else:  # bigquery
            return _execute_bigquery_query(sql_query)
    except Exception as e:
        return f"Query execution failed: {e!s}"


@mcp.tool()
def get_patient_demographics(patient_id: Optional[int] = None, limit: int = 10) -> str:
    """Get patient demographic information from ICU stays.

    Args:
        patient_id: Specific patient ID to query (optional)
        limit: Maximum number of records to return

    Returns:
        Patient demographics as formatted text
    """
    if _backend == "sqlite":
        if patient_id:
            query = f"SELECT * FROM icu_icustays WHERE subject_id = {patient_id}"
        else:
            query = f"SELECT * FROM icu_icustays LIMIT {limit}"
    else:  # bigquery
        table = "`physionet-data.mimiciv_3_1_icu.icustays`"
        if patient_id:
            query = f"SELECT * FROM {table} WHERE subject_id = {patient_id}"
        else:
            query = f"SELECT * FROM {table} LIMIT {limit}"

    return execute_mimic_query(query)


@mcp.tool()
def get_lab_results(
    patient_id: Optional[int] = None, lab_item: Optional[str] = None, limit: int = 20
) -> str:
    """Get laboratory test results.

    Args:
        patient_id: Specific patient ID to query (optional)
        lab_item: Lab item to search for (optional)
        limit: Maximum number of records to return

    Returns:
        Lab results as formatted text
    """
    if _backend == "sqlite":
        query = "SELECT * FROM hosp_labevents"
        conditions = []
        if patient_id:
            conditions.append(f"subject_id = {patient_id}")
        if lab_item:
            conditions.append(f"value LIKE '%{lab_item}%'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" LIMIT {limit}"
    else:  # bigquery
        table = "`physionet-data.mimiciv_3_1_hosp.labevents`"
        query = f"SELECT * FROM {table}"
        conditions = []
        if patient_id:
            conditions.append(f"subject_id = {patient_id}")
        if lab_item:
            conditions.append(f"value LIKE '%{lab_item}%'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" LIMIT {limit}"

    return execute_mimic_query(query)


@mcp.tool()
def get_database_schema() -> str:
    """Get database schema information.

    Returns:
        Database schema as formatted text
    """
    if _backend == "sqlite":
        query = "SELECT name FROM sqlite_master WHERE type='table'"
    else:  # bigquery
        query = """
        SELECT table_name
        FROM `physionet-data.mimiciv_3_1_hosp.INFORMATION_SCHEMA.TABLES`
        UNION ALL
        SELECT table_name
        FROM `physionet-data.mimiciv_3_1_icu.INFORMATION_SCHEMA.TABLES`
        """

    return execute_mimic_query(query)


@mcp.tool()
def get_race_distribution(limit: int = 10) -> str:
    """Get race distribution from hospital admissions.

    Args:
        limit: Maximum number of race categories to return

    Returns:
        Race distribution as formatted text
    """
    if _backend == "sqlite":
        query = f"SELECT race, COUNT(*) as count FROM hosp_admissions GROUP BY race ORDER BY count DESC LIMIT {limit}"
    else:  # bigquery
        query = f"SELECT race, COUNT(*) as count FROM `physionet-data.mimiciv_3_1_hosp.admissions` GROUP BY race ORDER BY count DESC LIMIT {limit}"

    return execute_mimic_query(query)


def _execute_sqlite_query(sql_query: str) -> str:
    """Execute SQLite query."""
    try:
        conn = sqlite3.connect(_db_path)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()

        if df.empty:
            return "No results found"

        # Limit output size
        if len(df) > 50:
            result = df.head(50).to_string(index=False)
            result += f"\n... ({len(df)} total rows, showing first 50)"
        else:
            result = df.to_string(index=False)

        return result

    except Exception as e:
        return f"SQLite query error: {e!s}"


def _execute_bigquery_query(sql_query: str) -> str:
    """Execute BigQuery query."""
    try:
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig()
        query_job = _bq_client.query(sql_query, job_config=job_config)
        df = query_job.to_dataframe()

        if df.empty:
            return "No results found"

        # Limit output size
        if len(df) > 50:
            result = df.head(50).to_string(index=False)
            result += f"\n... ({len(df)} total rows, showing first 50)"
        else:
            result = df.to_string(index=False)

        return result

    except Exception as e:
        return f"BigQuery query error: {e!s}"


def main():
    """Main entry point for MCP server."""
    # Initialize backend
    _init_backend()

    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
