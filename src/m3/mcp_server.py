"""
M3 MCP Server - MIMIC-IV + MCP + Models
Provides MCP tools for querying MIMIC-IV data via SQLite or BigQuery.
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import sqlparse
from fastmcp import FastMCP

from m3.auth import init_oauth2, require_oauth2
from m3.config import get_default_database_path, logger

# Create FastMCP server instance
mcp = FastMCP("m3")

# Global variables for backend configuration
_backend = None
_db_path = None
_bq_client = None
_project_id = None


def validate_patient_id(patient_id: Optional[int]) -> bool:
    """Validate patient_id parameter."""
    if patient_id is None:
        return True
    return isinstance(patient_id, int) and 0 < patient_id < 999999999


def validate_limit(limit: int) -> bool:
    """Validate limit parameter."""
    return isinstance(limit, int) and 0 < limit <= 1000


def sanitize_lab_item(lab_item: Optional[str]) -> Optional[str]:
    """Sanitize lab_item parameter to prevent injection."""
    if lab_item is None:
        return None
    # Remove any dangerous characters, keep only alphanumeric, spaces, hyphens, underscores
    sanitized = re.sub(r'[^\w\s\-_]', '', lab_item)
    # Limit length to prevent abuse
    return sanitized[:100] if sanitized else None


def is_safe_query(sql_query: str, internal_tool: bool = False) -> tuple[bool, str]:
    """Secure SQL validation - blocks injection attacks, allows legitimate queries."""
    try:
        if not sql_query or not sql_query.strip():
            return False, "Empty query"

        # Parse SQL to validate structure
        parsed = sqlparse.parse(sql_query.strip())
        if not parsed:
            return False, "Invalid SQL syntax"

        # Block multiple statements (main injection vector)
        if len(parsed) > 1:
            return False, "Multiple statements not allowed"

        statement = parsed[0]
        statement_type = statement.get_type()

        # Allow SELECT and PRAGMA (PRAGMA is needed for schema exploration)
        if statement_type not in (
            "SELECT",
            "UNKNOWN",
        ):  # PRAGMA shows as UNKNOWN in sqlparse
            return False, "Only SELECT and PRAGMA queries allowed"

        # Check if it's a PRAGMA statement (these are safe for schema exploration)
        sql_upper = sql_query.strip().upper()
        if sql_upper.startswith("PRAGMA"):
            return True, "Safe PRAGMA statement"

        # For SELECT statements, block dangerous injection patterns
        if statement_type == "SELECT":
            # Block dangerous write operations within SELECT
            dangerous_keywords = {
                "INSERT",
                "UPDATE",
                "DELETE",
                "DROP",
                "CREATE",
                "ALTER",
                "TRUNCATE",
                "REPLACE",
                "MERGE",
                "EXEC",
                "EXECUTE",
            }

            for keyword in dangerous_keywords:
                if f" {keyword} " in f" {sql_upper} ":
                    return False, f"Write operation not allowed: {keyword}"

            # Block common injection patterns that are rarely used in legitimate analytics
            injection_patterns = [
                # Classic SQL injection patterns
                ("1=1", "Classic injection pattern"),
                ("OR 1=1", "Boolean injection pattern"),
                ("AND 1=1", "Boolean injection pattern"),
                ("OR '1'='1'", "String injection pattern"),
                ("AND '1'='1'", "String injection pattern"),
                ("WAITFOR", "Time-based injection"),
                ("SLEEP(", "Time-based injection"),
                ("BENCHMARK(", "Time-based injection"),
                ("LOAD_FILE(", "File access injection"),
                ("INTO OUTFILE", "File write injection"),
                ("INTO DUMPFILE", "File write injection"),
            ]

            for pattern, description in injection_patterns:
                if pattern in sql_upper:
                    return False, f"Injection pattern detected: {description}"

            # Context-aware protection: Block suspicious table/column names not in medical databases
            suspicious_names = [
                "PASSWORD",
                "ADMIN",
                "USER",
                "LOGIN",
                "AUTH",
                "TOKEN",
                "CREDENTIAL",
                "SECRET",
                "KEY",
                "HASH",
                "SALT",
                "SESSION",
                "COOKIE",
            ]

            for name in suspicious_names:
                if name in sql_upper:
                    return (
                        False,
                        f"Suspicious identifier detected: {name} (not medical data)",
                    )

        return True, "Safe"

    except Exception as e:
        return False, f"Validation error: {e}"


def _init_backend():
    """Initialize the backend based on environment variables."""
    global _backend, _db_path, _bq_client, _project_id

    # Initialize OAuth2 authentication
    init_oauth2()
    
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

        # User's GCP project ID for authentication and billing
        # MIMIC-IV data resides in the public 'physionet-data' project
        _project_id = os.getenv("M3_PROJECT_ID", "physionet-data")
        try:
            _bq_client = bigquery.Client(project=_project_id)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BigQuery client: {e}")

    else:
        raise ValueError(f"Unsupported backend: {_backend}")


# Initialize backend when module is imported
_init_backend()


def _get_backend_info() -> str:
    """Get current backend information for display in responses."""
    if _backend == "sqlite":
        return f"🔧 **Current Backend:** SQLite (local database)\n📁 **Database Path:** {_db_path}\n"
    else:
        return f"🔧 **Current Backend:** BigQuery (cloud database)\n☁️ **Project ID:** {_project_id}\n"


@mcp.tool()
@require_oauth2
def get_database_schema(**kwargs) -> str:
    """🔍 Discover what data is available in the MIMIC-IV database.

    **When to use:** Start here when you need to understand what tables exist, or when someone asks about data that might be in multiple tables.

    **What you'll get:** A list of all available tables with their structure, so you can choose the right one for your query.

    **Next steps:** Use `get_table_info()` to explore specific tables, then `execute_mimic_query()` for complex analyses.
    """
    backend_info = _get_backend_info()

    if _backend == "sqlite":
        # Get tables using PRAGMA (safe for schema exploration)
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        safe, reason = is_safe_query(tables_query, internal_tool=True)
        if not safe:
            return f"Query validation failed: {reason}"

        result = _execute_sqlite_query(tables_query)
        return f"{backend_info}📋 **Available Tables:**\n{result}\n\n💡 **Tip:** Use `get_table_info('table_name')` to explore a specific table's structure and see sample data."

    else:  # bigquery
        # For BigQuery, we'll show tables from the standard MIMIC-IV datasets
        return f"""{backend_info}📋 **Available MIMIC-IV Tables:**

**ICU Data:**
- `physionet-data.mimiciv_3_1_icu.icustays` - ICU stay information
- `physionet-data.mimiciv_3_1_icu.chartevents` - Charted events (vitals, etc.)
- `physionet-data.mimiciv_3_1_icu.inputevents` - Fluid/medication inputs

**Hospital Data:**
- `physionet-data.mimiciv_3_1_hosp.admissions` - Hospital admissions
- `physionet-data.mimiciv_3_1_hosp.patients` - Patient demographics
- `physionet-data.mimiciv_3_1_hosp.labevents` - Laboratory results
- `physionet-data.mimiciv_3_1_hosp.prescriptions` - Medications

💡 **Tip:** Use `get_table_info('table_name')` to explore structure, or `execute_mimic_query()` for custom analysis."""


@mcp.tool()
@require_oauth2
def get_table_info(table_name: str, show_sample: bool = True, **kwargs) -> str:
    """🔍 Get detailed information about a specific table.

    **When to use:** After `get_database_schema()` showed you available tables, use this to understand a table's structure before writing queries.

    **What you'll get:** Column names, data types, and sample rows to understand the data format.

    Args:
        table_name: Name of the table to inspect
        show_sample: Whether to include sample data (default: True)

    Returns:
        Table structure and sample data
    """
    backend_info = _get_backend_info()

    if _backend == "sqlite":
        # First check if table exists
        check_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        safe, reason = is_safe_query(check_query, internal_tool=True)
        if not safe:
            return f"Query validation failed: {reason}"

        table_check = _execute_sqlite_query(check_query)
        if "No results found" in table_check:
            return f"{backend_info}❌ **Table '{table_name}' not found.**\n\nUse `get_database_schema()` to see available tables."

        # Get column information using PRAGMA
        columns_query = f"PRAGMA table_info({table_name})"
        safe, reason = is_safe_query(columns_query, internal_tool=True)
        if not safe:
            return f"Query validation failed: {reason}"

        columns_result = _execute_sqlite_query(columns_query)

        if show_sample:
            # Get sample data
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"
            safe, reason = is_safe_query(sample_query, internal_tool=True)
            if not safe:
                return f"Query validation failed: {reason}"

            sample_result = _execute_sqlite_query(sample_query)
            return f"""{backend_info}📋 **Table: {table_name}**

**Column Structure:**
{columns_result}

**Sample Data (first 3 rows):**
{sample_result}

💡 **Next steps:** Use `execute_mimic_query()` with this table for custom analysis."""
        else:
            return f"""{backend_info}📋 **Table: {table_name}**

**Column Structure:**
{columns_result}

💡 **Next steps:** Use `execute_mimic_query()` with this table for custom analysis."""

    else:  # bigquery
        # For BigQuery, we'll construct the table name and get schema info
        if not table_name.startswith("`physionet-data."):
            # Add the full path if not provided
            table_name = f"`physionet-data.mimiciv_3_1_hosp.{table_name.replace('`', '')}`"

        # Get column information
        schema_query = f"SELECT column_name, data_type, is_nullable FROM `{table_name.strip('`')}`.INFORMATION_SCHEMA.COLUMNS WHERE table_name = '{table_name.split('.')[-1].strip('`')}'"

        try:
            schema_result = _execute_bigquery_query(schema_query)

            if show_sample:
                # Get sample data
                sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                safe, reason = is_safe_query(sample_query, internal_tool=True)
                if not safe:
                    return f"Query validation failed: {reason}"

                sample_result = _execute_bigquery_query(sample_query)
                return f"""{backend_info}📋 **Table: {table_name}**

**Column Structure:**
{schema_result}

**Sample Data (first 3 rows):**
{sample_result}

💡 **Next steps:** Use `execute_mimic_query()` with this table for custom analysis."""
            else:
                return f"""{backend_info}📋 **Table: {table_name}**

**Column Structure:**
{schema_result}

💡 **Next steps:** Use `execute_mimic_query()` with this table for custom analysis."""

        except Exception as e:
            return f"{backend_info}❌ **Error accessing table '{table_name}':** {e}\n\nUse `get_database_schema()` to see available tables."


@mcp.tool()
@require_oauth2
def execute_mimic_query(sql_query: str, **kwargs) -> str:
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
    backend_info = _get_backend_info()

    # Validate the SQL query for security
    safe, reason = is_safe_query(sql_query)
    if not safe:
        return f"❌ **Query Rejected:** {reason}\n\n{backend_info}💡 **Tip:** Only SELECT queries are allowed. Avoid SQL injection patterns and ensure you're querying medical data tables."

    try:
        if _backend == "sqlite":
            result = _execute_sqlite_query(sql_query)
        else:  # bigquery
            result = _execute_bigquery_query(sql_query)

        return f"{backend_info}✅ **Query Results:**\n\n{result}"

    except Exception as e:
        return f"{backend_info}❌ **Query Error:** {e}\n\n💡 **Suggestions:**\n- Check table names with `get_database_schema()`\n- Verify column names with `get_table_info('table_name')`\n- Ensure proper SQL syntax"


@mcp.tool()
@require_oauth2
def get_patient_demographics(patient_id: Optional[int] = None, limit: int = 10, **kwargs) -> str:
    """Get patient demographic information from ICU stays.

    Args:
        patient_id: Specific patient ID to query (optional)
        limit: Maximum number of records to return (default: 10)

    Returns:
        ICU stay data as formatted text or guidance if table not found
    """
    # Input validation
    if not validate_patient_id(patient_id):
        return "Error: Invalid patient_id. Must be a positive integer less than 999999999."
    
    if not validate_limit(limit):
        return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
    
    if _backend == "sqlite":
        if patient_id:
            # Use parameterized query for SQLite
            return _execute_sqlite_query_with_params(
                "SELECT * FROM icu_icustays WHERE subject_id = ?", 
                [patient_id]
            )
        else:
            return _execute_sqlite_query_with_params(
                "SELECT * FROM icu_icustays LIMIT ?", 
                [limit]
            )
    else:  # bigquery
        if patient_id:
            # Use parameterized query for BigQuery
            return _execute_bigquery_query_with_params(
                "SELECT * FROM `physionet-data.mimiciv_3_1_icu.icustays` WHERE subject_id = @patient_id",
                {"patient_id": patient_id}
            )
        else:
            return _execute_bigquery_query_with_params(
                "SELECT * FROM `physionet-data.mimiciv_3_1_icu.icustays` LIMIT @limit",
                {"limit": limit}
            )


@mcp.tool()
@require_oauth2
def get_lab_results(
    patient_id: Optional[int] = None, lab_item: Optional[str] = None, limit: int = 20, **kwargs
) -> str:
    """🧪 Get laboratory test results quickly.

    **When to use:** When you need lab values for analysis, either for specific patients or general lab patterns.

    **For reliable queries:** Use `get_database_schema()` → `get_table_info()` → `execute_mimic_query()` workflow.

    **What you'll get:** Lab test results with values, timestamps, and patient IDs.

    Args:
        patient_id: Specific patient ID to query (optional)
        lab_item: Search for specific lab test by name/value (optional)
        limit: Maximum number of results to return (default: 20)

    Returns:
        Lab results as formatted text or guidance if table not found
    """
    # Input validation
    if not validate_patient_id(patient_id):
        return "Error: Invalid patient_id. Must be a positive integer less than 999999999."
    
    if not validate_limit(limit):
        return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
    
    # Sanitize lab_item to prevent injection
    sanitized_lab_item = sanitize_lab_item(lab_item)
    
    if _backend == "sqlite":
        params = []
        conditions = []
        base_query = "SELECT * FROM hosp_labevents"
        
        if patient_id:
            conditions.append("subject_id = ?")
            params.append(patient_id)
            
        if sanitized_lab_item:
            conditions.append("value LIKE ?")
            params.append(f"%{sanitized_lab_item}%")
            
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " LIMIT ?"
        params.append(limit)
        
        return _execute_sqlite_query_with_params(query, params)
    else:  # bigquery
        params = {"limit": limit}
        conditions = []
        base_query = "SELECT * FROM `physionet-data.mimiciv_3_1_hosp.labevents`"
        
        if patient_id:
            conditions.append("subject_id = @patient_id")
            params["patient_id"] = patient_id
            
        if sanitized_lab_item:
            conditions.append("value LIKE @lab_item")
            params["lab_item"] = f"%{sanitized_lab_item}%"
            
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " LIMIT @limit"
        
        return _execute_bigquery_query_with_params(query, params)


@mcp.tool()
@require_oauth2
def get_race_distribution(limit: int = 10, **kwargs) -> str:
    """Get race distribution from hospital admissions.

    Args:
        limit: Maximum number of race categories to return (default: 10)

    Returns:
        Race distribution as formatted text or guidance if table not found
    """
    # Input validation
    if not validate_limit(limit):
        return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
    
    if _backend == "sqlite":
        return _execute_sqlite_query_with_params(
            "SELECT race, COUNT(*) as count FROM hosp_admissions GROUP BY race ORDER BY count DESC LIMIT ?",
            [limit]
        )
    else:  # bigquery
        return _execute_bigquery_query_with_params(
            "SELECT race, COUNT(*) as count FROM `physionet-data.mimiciv_3_1_hosp.admissions` GROUP BY race ORDER BY count DESC LIMIT @limit",
            {"limit": limit}
        )


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


def _execute_sqlite_query_safe(sql_query: str, params: Optional[dict] = None) -> str:
    """Execute SQLite query with optional parameters (internal use)."""
    try:
        # Safety check - this is an internal function but we still validate
        safe, reason = is_safe_query(sql_query, internal_tool=True)
        if not safe:
            raise Exception(f"Internal query safety check failed: {reason}")

        conn = sqlite3.connect(_db_path)
        if params:
            df = pd.read_sql_query(sql_query, conn, params=params)
        else:
            df = pd.read_sql_query(sql_query, conn)
        conn.close()

        if df.empty:
            return "No results found"

        # Limit output size for safety
        if len(df) > 50:
            result = df.head(50).to_string(index=False)
            result += f"\n... ({len(df)} total rows, showing first 50)"
        else:
            result = df.to_string(index=False)

        return result

    except Exception as e:
        # Re-raise for debugging but don't expose internal details to users
        raise e


def _execute_sqlite_query_with_params(sql_query: str, params: list) -> str:
    """Execute SQLite query with parameterized inputs."""
    try:
        conn = sqlite3.connect(_db_path)
        df = pd.read_sql_query(sql_query, conn, params=params)
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
        query_job = _bq_client.query(sql_query)
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


def _execute_bigquery_query_safe(sql_query: str, params: Optional[dict] = None) -> str:
    """Execute BigQuery query with optional parameters (internal use)."""
    try:
        from google.cloud import bigquery

        # Safety check - this is an internal function but we still validate
        safe, reason = is_safe_query(sql_query, internal_tool=True)
        if not safe:
            raise Exception(f"Internal query safety check failed: {reason}")

        job_config = bigquery.QueryJobConfig()
        if params:
            # Convert parameters to BigQuery format
            query_parameters = []
            for name, value in params.items():
                if isinstance(value, int):
                    param_type = "INT64"
                elif isinstance(value, str):
                    param_type = "STRING"
                else:
                    param_type = "STRING"  # Default for safety

                query_parameters.append(
                    bigquery.ScalarQueryParameter(name, param_type, value)
                )
            job_config.query_parameters = query_parameters

        query_job = _bq_client.query(sql_query, job_config=job_config)
        df = query_job.to_dataframe()

        if df.empty:
            return "No results found"

        # Limit output size for safety
        if len(df) > 50:
            result = df.head(50).to_string(index=False)
            result += f"\n... ({len(df)} total rows, showing first 50)"
        else:
            result = df.to_string(index=False)

        return result

    except Exception as e:
        # Re-raise for debugging but don't expose internal details to users
        raise e


def _execute_bigquery_query_with_params(sql_query: str, params: dict) -> str:
    """Execute BigQuery query with parameterized inputs."""
    try:
        from google.cloud import bigquery

        # Convert parameters to BigQuery format
        query_parameters = []
        for name, value in params.items():
            if isinstance(value, int):
                param_type = "INT64"
            elif isinstance(value, str):
                param_type = "STRING"
            else:
                param_type = "STRING"  # Default to string for safety
            
            query_parameters.append(
                bigquery.ScalarQueryParameter(name, param_type, value)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
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
    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
