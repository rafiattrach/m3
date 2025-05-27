"""
M3 MCP Server - MIMIC-IV + MCP + Models
Provides MCP tools for querying MIMIC-IV data via SQLite or BigQuery.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import sqlparse
from fastmcp import FastMCP

from m3.config import get_default_database_path

# Create FastMCP server instance
mcp = FastMCP("m3")

# Global variables for backend configuration
_backend = None
_db_path = None
_bq_client = None
_project_id = None


def is_safe_query(sql_query: str) -> tuple[bool, str]:
    """More robust SQL safety check."""
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed or parsed[0].get_type() != "SELECT":
            return False, "Only SELECT queries are allowed"

        # Block dangerous patterns: ';', '--', 'UNION', etc.
        # Use word boundaries for patterns that could be part of table names
        dangerous_patterns = [";", "--", "/*", "*/"]
        dangerous_words = ["UNION", "EXEC"]  # These need word boundaries

        sql_upper = sql_query.upper()

        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in sql_upper:
                return False, f"Dangerous pattern detected: {pattern}"

        # Check for dangerous words with word boundaries
        import re

        for word in dangerous_words:
            if re.search(r"\b" + word + r"\b", sql_upper):
                return False, f"Dangerous pattern detected: {word}"

        return True, "Safe"
    except Exception as e:
        # If parsing fails, let it through to get proper SQL error from database
        return True, f"SQL parsing warning: {e}"


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

    This tool provides direct SQL access to MIMIC-IV database. Use this for complex queries
    or when the specialized tools don't meet your needs.

    IMPORTANT DATABASE SCHEMA INFORMATION:

    SQLite Tables (use these table names for SQLite backend):
    - icu_icustays: ICU stay information (subject_id, hadm_id, stay_id, intime, outtime, los)
    - hosp_labevents: Laboratory test results (subject_id, hadm_id, itemid, charttime, value, valuenum, valueuom)
    - hosp_admissions: Hospital admissions (subject_id, hadm_id, admittime, dischtime, race, insurance, language)

    BigQuery Tables (use these fully qualified names for BigQuery backend):
    - `physionet-data.mimiciv_3_1_icu.icustays`: ICU stay information
    - `physionet-data.mimiciv_3_1_hosp.labevents`: Laboratory test results
    - `physionet-data.mimiciv_3_1_hosp.admissions`: Hospital admissions

    COMMON QUERY PATTERNS (based on existing specialized tools):

    1. Patient Demographics from ICU stays:
       SQLite: "SELECT * FROM icu_icustays WHERE subject_id = 12345"
       BigQuery: "SELECT * FROM `physionet-data.mimiciv_3_1_icu.icustays` WHERE subject_id = 12345"

    2. Laboratory Results:
       SQLite: "SELECT * FROM hosp_labevents WHERE subject_id = 12345 AND value LIKE '%glucose%' LIMIT 20"
       BigQuery: "SELECT * FROM `physionet-data.mimiciv_3_1_hosp.labevents` WHERE subject_id = 12345 LIMIT 20"

    3. Race Distribution:
       SQLite: "SELECT race, COUNT(*) as count FROM hosp_admissions GROUP BY race ORDER BY count DESC LIMIT 10"
       BigQuery: "SELECT race, COUNT(*) as count FROM `physionet-data.mimiciv_3_1_hosp.admissions` GROUP BY race ORDER BY count DESC"

    4. Database Schema Discovery:
       SQLite: "SELECT name FROM sqlite_master WHERE type='table'"
       BigQuery: "SELECT table_name FROM `physionet-data.mimiciv_3_1_hosp.INFORMATION_SCHEMA.TABLES`"

    5. Advanced Patient Analysis with Joins:
       SQLite: "SELECT i.subject_id, i.los, a.race, a.insurance FROM icu_icustays i JOIN hosp_admissions a ON i.subject_id = a.subject_id AND i.hadm_id = a.hadm_id LIMIT 20"
       BigQuery: "SELECT i.subject_id, i.los, a.race FROM `physionet-data.mimiciv_3_1_icu.icustays` i JOIN `physionet-data.mimiciv_3_1_hosp.admissions` a ON i.subject_id = a.subject_id LIMIT 20"

    KEY COLUMNS TO KNOW:
    - subject_id: Patient identifier (links across all tables)
    - hadm_id: Hospital admission identifier
    - stay_id: ICU stay identifier
    - charttime: Timestamp for events/measurements
    - itemid: Identifier for specific lab tests, medications, etc.
    - value/valuenum: Test results (value=text, valuenum=numeric)
    - intime/outtime: ICU admission/discharge times
    - admittime/dischtime: Hospital admission/discharge times
    - los: Length of stay in days
    - race, insurance, language: Patient demographics

    QUERY CONSTRUCTION TIPS:
    - Always use LIMIT to prevent overwhelming results (recommended: 10-50 rows)
    - Use subject_id to filter for specific patients
    - Use LIKE '%pattern%' for text searching in values
    - Use ORDER BY with COUNT(*) for distributions and rankings
    - Join tables on subject_id and hadm_id when combining data
    - Filter by time ranges using charttime, intime, admittime for temporal analysis
    - Use GROUP BY for aggregations and statistical analysis
    - Consider using DISTINCT to avoid duplicate records

    COMMON USE CASES:
    - Patient-specific analysis: Filter by subject_id
    - Temporal analysis: Use time-based columns with WHERE clauses
    - Statistical summaries: Use COUNT(), AVG(), MIN(), MAX() with GROUP BY
    - Data exploration: Start with simple SELECT * queries with LIMIT
    - Cross-table analysis: JOIN tables on subject_id and hadm_id

    SECURITY: Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, or DDL operations.

    Args:
        sql_query: SQL query to execute (SELECT only)

    Returns:
        Query results as formatted text
    """
    # Enhanced security check using SQL parsing
    is_safe, message = is_safe_query(sql_query)
    if not is_safe:
        return f"Error: {message}"

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
