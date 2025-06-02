"""
M3 MCP Server - MIMIC-IV + MCP + Models
Provides MCP tools for querying MIMIC-IV data via SQLite or BigQuery.
"""

import os
import sqlite3
from pathlib import Path

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
def get_database_schema() -> str:
    """🔍 Discover what data is available in the MIMIC-IV database.

    **When to use:** Start here when you need to understand what tables exist, or when someone asks about data that might be in multiple tables.

    **What this does:** Shows all available tables so you can identify which ones contain the data you need.

    **Next steps after using this:**
    - If you see relevant tables, use `get_table_info(table_name)` to explore their structure
    - Common tables: `patients` (demographics), `admissions` (hospital stays), `icustays` (ICU data), `labevents` (lab results)

    Returns:
        List of all available tables in the database with current backend info
    """
    if _backend == "sqlite":
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = execute_mimic_query(query)
        return f"{_get_backend_info()}\n📋 **Available Tables:**\n{result}"
    else:  # bigquery
        # Show fully qualified table names that are ready to copy-paste into queries
        query = """
        SELECT CONCAT('`physionet-data.mimiciv_3_1_hosp.', table_name, '`') as query_ready_table_name
        FROM `physionet-data.mimiciv_3_1_hosp.INFORMATION_SCHEMA.TABLES`
        UNION ALL
        SELECT CONCAT('`physionet-data.mimiciv_3_1_icu.', table_name, '`') as query_ready_table_name
        FROM `physionet-data.mimiciv_3_1_icu.INFORMATION_SCHEMA.TABLES`
        ORDER BY query_ready_table_name
        """
        result = execute_mimic_query(query)
        return f"{_get_backend_info()}\n📋 **Available Tables (query-ready names):**\n{result}\n\n💡 **Copy-paste ready:** These table names can be used directly in your SQL queries!"


@mcp.tool()
def get_table_info(table_name: str, show_sample: bool = True) -> str:
    """📋 Explore a specific table's structure and see sample data.

    **When to use:** After you know which table you need (from `get_database_schema()`), use this to understand the columns and data format.

    **What this does:**
    - Shows column names, types, and constraints
    - Displays sample rows so you understand the actual data format
    - Helps you write accurate SQL queries

    **Pro tip:** Always look at sample data! It shows you the actual values, date formats, and data patterns.

    Args:
        table_name: Exact table name from the schema (case-sensitive). Can be simple name or fully qualified BigQuery name.
        show_sample: Whether to include sample rows (default: True, recommended)

    Returns:
        Complete table structure with sample data to help you write queries
    """
    backend_info = _get_backend_info()

    if _backend == "sqlite":
        # Get column information
        pragma_query = f"PRAGMA table_info({table_name})"
        try:
            result = _execute_sqlite_query(pragma_query)
            if "error" in result.lower():
                return f"{backend_info}❌ Table '{table_name}' not found. Use get_database_schema() to see available tables."

            info_result = f"{backend_info}📋 **Table:** {table_name}\n\n**Column Information:**\n{result}"

            if show_sample:
                sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                sample_result = _execute_sqlite_query(sample_query)
                info_result += (
                    f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"
                )

            return info_result
        except Exception as e:
            return f"{backend_info}❌ Error examining table '{table_name}': {e}\n\n💡 Use get_database_schema() to see available tables."

    else:  # bigquery
        # Handle both simple names (patients) and fully qualified names (`physionet-data.mimiciv_3_1_hosp.patients`)
        if table_name.startswith("`") and table_name.endswith("`"):
            # Fully qualified name - use it directly
            full_table_name = table_name
            # Extract simple table name for INFORMATION_SCHEMA query
            parts = table_name.strip("`").split(".")
            simple_table_name = parts[-1] if len(parts) >= 3 else table_name
            dataset = ".".join(parts[:-1]) if len(parts) >= 3 else None
        else:
            # Simple name - try both datasets to find the table
            simple_table_name = table_name
            full_table_name = None
            dataset = None

        # If we have a fully qualified name, try that first
        if full_table_name:
            try:
                # Get column information using the dataset from the full name
                dataset_parts = dataset.split(".")
                if len(dataset_parts) >= 2:
                    project_dataset = f"`{dataset_parts[0]}.{dataset_parts[1]}`"
                    info_query = f"""
                    SELECT column_name, data_type, is_nullable
                    FROM {project_dataset}.INFORMATION_SCHEMA.COLUMNS
                    WHERE table_name = '{simple_table_name}'
                    ORDER BY ordinal_position
                    """

                    info_result = _execute_bigquery_query(info_query)
                    if "No results found" not in info_result:
                        result = f"{backend_info}📋 **Table:** {full_table_name}\n\n**Column Information:**\n{info_result}"

                        if show_sample:
                            sample_query = f"SELECT * FROM {full_table_name} LIMIT 3"
                            sample_result = _execute_bigquery_query(sample_query)
                            result += f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"

                        return result
            except Exception:
                pass  # Fall through to try simple name approach

        # Try both datasets with simple name (fallback or original approach)
        for dataset in ["mimiciv_3_1_hosp", "mimiciv_3_1_icu"]:
            try:
                full_table_name = f"`physionet-data.{dataset}.{simple_table_name}`"

                # Get column information
                info_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM `physionet-data.{dataset}.INFORMATION_SCHEMA.COLUMNS`
                WHERE table_name = '{simple_table_name}'
                ORDER BY ordinal_position
                """

                info_result = _execute_bigquery_query(info_query)
                if "No results found" not in info_result:
                    result = f"{backend_info}📋 **Table:** {full_table_name}\n\n**Column Information:**\n{info_result}"

                    if show_sample:
                        sample_query = f"SELECT * FROM {full_table_name} LIMIT 3"
                        sample_result = _execute_bigquery_query(sample_query)
                        result += (
                            f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"
                        )

                    return result
            except Exception:
                continue

        return f"{backend_info}❌ Table '{table_name}' not found in any dataset. Use get_database_schema() to see available tables."


@mcp.tool()
def execute_mimic_query(sql_query: str) -> str:
    """🚀 Execute SQL queries to analyze MIMIC-IV data.

    **💡 Pro tip:** For best results, explore the database structure first!

    **Recommended workflow (especially for smaller models):**
    1. **See available tables:** Use `get_database_schema()` to list all tables
    2. **Examine table structure:** Use `get_table_info('table_name')` to see columns and sample data
    3. **Write your SQL query:** Use exact table/column names from exploration

    **Why exploration helps:**
    - Table names vary between backends (SQLite vs BigQuery)
    - Column names may be unexpected (e.g., age might be 'anchor_age')
    - Sample data shows actual formats and constraints

    Args:
        sql_query: Your SQL SELECT query (must be SELECT only)

    Returns:
        Query results or helpful error messages with next steps
    """
    # Enhanced security check
    is_safe, message = is_safe_query(sql_query)
    if not is_safe:
        if "describe" in sql_query.lower() or "show" in sql_query.lower():
            return f"""❌ **Security Error:** {message}

🔍 **For table structure:** Use `get_table_info('table_name')` instead of DESCRIBE
📋 **Why this is better:** Shows columns, types, AND sample data to understand the actual data

💡 **Recommended workflow:**
1. `get_database_schema()` ← See available tables
2. `get_table_info('table_name')` ← Explore structure
3. `execute_mimic_query('SELECT ...')` ← Run your analysis"""

        return f"❌ **Security Error:** {message}\n\n💡 **Tip:** Only SELECT statements are allowed for data analysis."

    try:
        if _backend == "sqlite":
            return _execute_sqlite_query(sql_query)
        else:  # bigquery
            return _execute_bigquery_query(sql_query)
    except Exception as e:
        error_msg = str(e).lower()

        # Provide specific, actionable error guidance
        suggestions = []

        if "no such table" in error_msg or "table not found" in error_msg:
            suggestions.append(
                "🔍 **Table name issue:** Use `get_database_schema()` to see exact table names"
            )
            suggestions.append(
                f"📋 **Backend-specific naming:** {_backend} has specific table naming conventions"
            )
            suggestions.append(
                "💡 **Quick fix:** Check if the table name matches exactly (case-sensitive)"
            )

        if "no such column" in error_msg or "column not found" in error_msg:
            suggestions.append(
                "🔍 **Column name issue:** Use `get_table_info('table_name')` to see available columns"
            )
            suggestions.append(
                "📝 **Common issue:** Column might be named differently (e.g., 'anchor_age' not 'age')"
            )
            suggestions.append(
                "👀 **Check sample data:** `get_table_info()` shows actual column names and sample values"
            )

        if "syntax error" in error_msg:
            suggestions.append(
                "📝 **SQL syntax issue:** Check quotes, commas, and parentheses"
            )
            suggestions.append(
                f"🎯 **Backend syntax:** Verify your SQL works with {_backend}"
            )
            suggestions.append(
                "💭 **Try simpler:** Start with `SELECT * FROM table_name LIMIT 5`"
            )

        if "describe" in error_msg.lower() or "show" in error_msg.lower():
            suggestions.append(
                "🔍 **Schema exploration:** Use `get_table_info('table_name')` instead of DESCRIBE"
            )
            suggestions.append(
                "📋 **Better approach:** `get_table_info()` shows columns AND sample data"
            )

        if not suggestions:
            suggestions.append(
                "🔍 **Start exploration:** Use `get_database_schema()` to see available tables"
            )
            suggestions.append(
                "📋 **Check structure:** Use `get_table_info('table_name')` to understand the data"
            )

        suggestion_text = "\n".join(f"   {s}" for s in suggestions)

        return f"""❌ **Query Failed:** {e}

🛠️ **How to fix this:**
{suggestion_text}

🎯 **Quick Recovery Steps:**
1. `get_database_schema()` ← See what tables exist
2. `get_table_info('your_table')` ← Check exact column names
3. Retry your query with correct names

📚 **Current Backend:** {_backend} - table names and syntax are backend-specific"""


@mcp.tool()
def get_icu_stays(patient_id: int | None = None, limit: int = 10) -> str:
    """🏥 Get ICU stay information and length of stay data.

    **⚠️ Note:** This is a convenience function that assumes standard MIMIC-IV table structure.
    **For reliable queries:** Use `get_database_schema()` → `get_table_info()` → `execute_mimic_query()` workflow.

    **What you'll get:** Patient IDs, admission times, length of stay, and ICU details.

    Args:
        patient_id: Specific patient ID to query (optional)
        limit: Maximum number of records to return (default: 10)

    Returns:
        ICU stay data as formatted text or guidance if table not found
    """
    # Try common ICU table names based on backend
    if _backend == "sqlite":
        icustays_table = "icu_icustays"
    else:  # bigquery
        icustays_table = "`physionet-data.mimiciv_3_1_icu.icustays`"

    if patient_id:
        query = f"SELECT * FROM {icustays_table} WHERE subject_id = {patient_id}"
    else:
        query = f"SELECT * FROM {icustays_table} LIMIT {limit}"

    # Execute with error handling that suggests proper workflow
    result = execute_mimic_query(query)
    if "error" in result.lower() or "not found" in result.lower():
        return f"""❌ **Convenience function failed:** {result}

💡 **For reliable results, use the proper workflow:**
1. `get_database_schema()` ← See actual table names
2. `get_table_info('table_name')` ← Understand structure
3. `execute_mimic_query('your_sql')` ← Use exact names

This ensures compatibility across different MIMIC-IV setups."""

    return result


@mcp.tool()
def get_lab_results(
    patient_id: int | None = None, lab_item: str | None = None, limit: int = 20
) -> str:
    """🧪 Get laboratory test results quickly.

    **⚠️ Note:** This is a convenience function that assumes standard MIMIC-IV table structure.
    **For reliable queries:** Use `get_database_schema()` → `get_table_info()` → `execute_mimic_query()` workflow.

    **What you'll get:** Lab values, timestamps, patient IDs, and test details.

    Args:
        patient_id: Specific patient ID to query (optional)
        lab_item: Lab item to search for in the value field (optional)
        limit: Maximum number of records to return (default: 20)

    Returns:
        Lab results as formatted text or guidance if table not found
    """
    # Try common lab table names based on backend
    if _backend == "sqlite":
        labevents_table = "hosp_labevents"
    else:  # bigquery
        labevents_table = "`physionet-data.mimiciv_3_1_hosp.labevents`"

    # Build safe parameterized query
    conditions = []
    params = {}

    if patient_id:
        conditions.append("subject_id = :patient_id")
        params["patient_id"] = patient_id

    if lab_item:
        conditions.append("value LIKE :lab_item")
        params["lab_item"] = f"%{lab_item}%"

    base_query = f"SELECT * FROM {labevents_table}"
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    base_query += f" LIMIT {limit}"

    # Execute with safe parameter substitution
    try:
        if _backend == "sqlite":
            return _execute_sqlite_query_safe(base_query, params)
        else:
            return _execute_bigquery_query_safe(base_query, params)
    except Exception as e:
        return f"""❌ **Convenience function failed:** {e}

💡 **For reliable results, use the proper workflow:**
1. `get_database_schema()` ← See actual table names
2. `get_table_info('table_name')` ← Understand structure
3. `execute_mimic_query('your_sql')` ← Use exact names

This ensures compatibility across different MIMIC-IV setups."""


@mcp.tool()
def get_race_distribution(limit: int = 10) -> str:
    """📊 Get race distribution from hospital admissions.

    **⚠️ Note:** This is a convenience function that assumes standard MIMIC-IV table structure.
    **For reliable queries:** Use `get_database_schema()` → `get_table_info()` → `execute_mimic_query()` workflow.

    **What you'll get:** Count of patients by race category, ordered by frequency.

    Args:
        limit: Maximum number of race categories to return (default: 10)

    Returns:
        Race distribution as formatted text or guidance if table not found
    """
    # Try common admissions table names based on backend
    if _backend == "sqlite":
        admissions_table = "hosp_admissions"
    else:  # bigquery
        admissions_table = "`physionet-data.mimiciv_3_1_hosp.admissions`"

    query = f"SELECT race, COUNT(*) as count FROM {admissions_table} GROUP BY race ORDER BY count DESC LIMIT {limit}"

    # Execute with error handling that suggests proper workflow
    result = execute_mimic_query(query)
    if "error" in result.lower() or "not found" in result.lower():
        return f"""❌ **Convenience function failed:** {result}

💡 **For reliable results, use the proper workflow:**
1. `get_database_schema()` ← See actual table names
2. `get_table_info('table_name')` ← Understand structure
3. `execute_mimic_query('your_sql')` ← Use exact names

This ensures compatibility across different MIMIC-IV setups."""

    return result


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
        # Re-raise the exception so execute_mimic_query can handle it with enhanced guidance
        raise e


def _execute_sqlite_query_safe(sql_query: str, params: dict | None = None) -> str:
    """Execute SQLite query with safe parameter substitution."""
    try:
        conn = sqlite3.connect(_db_path)

        if params:
            # Convert named parameters to SQLite format
            safe_query = sql_query
            safe_params = {}
            for key, value in params.items():
                safe_query = safe_query.replace(f":{key}", f":{key}")
                safe_params[key] = value
            df = pd.read_sql_query(safe_query, conn, params=safe_params)
        else:
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
        raise e


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
        # Re-raise the exception so execute_mimic_query can handle it with enhanced guidance
        raise e


def _execute_bigquery_query_safe(sql_query: str, params: dict | None = None) -> str:
    """Execute BigQuery query with safe parameter substitution."""
    try:
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig()

        if params:
            # Convert to BigQuery parameters
            query_params = []
            safe_query = sql_query
            for key, value in params.items():
                safe_query = safe_query.replace(f":{key}", f"@{key}")
                query_params.append(
                    bigquery.ScalarQueryParameter(
                        key, "STRING" if isinstance(value, str) else "INT64", value
                    )
                )
            job_config.query_parameters = query_params
            query_job = _bq_client.query(safe_query, job_config=job_config)
        else:
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
        raise e


def main():
    """Main entry point for MCP server."""
    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
