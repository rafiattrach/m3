import logging
from collections.abc import Callable

import sqlparse
from beartype import beartype
from beartype.typing import Any, Dict, List, Optional, Tuple

from m3.core.config import M3Config
from m3.core.tool.backend.base import BackendBase
from m3.core.tool.backend.registry import BACKEND_REGISTRY
from m3.core.tool.base import BaseTool
from m3.core.utils.exceptions import M3ValidationError
from m3.tools.mimic.components.auth import Auth
from m3.tools.mimic.components.data_io import DataIO
from m3.tools.mimic.components.utils import (
    load_env_vars_config,
    load_security_config,
    validate_limit,
)

logger = logging.getLogger(__name__)


@beartype
class MIMIC(BaseTool):
    @beartype
    def __init__(
        self,
        backends: List[BackendBase],
        config: Optional[M3Config] = None,
        data_io: Optional[DataIO] = None,
        backend_key: str = "sqlite",
    ) -> None:
        super().__init__()
        self.config = config or M3Config()
        self.env_config = load_env_vars_config()
        self._set_required_env_vars(backend_key)
        self._set_backends(backends)
        self.data_io = data_io or DataIO(self.config)
        self.backend_key = backend_key
        self._set_auth()
        self._validate_backend_key(backend_key)
        self.security_config = {}
        self.table_names = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend_key": self.backend_key,
            "backends": [
                {"type": k, "params": v.to_dict()} for k, v in self.backends.items()
            ],
        }

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> "MIMIC":
        try:
            backends_list = []
            for bd in params["backends"]:
                backend_type = bd["type"]
                if backend_type not in BACKEND_REGISTRY:
                    raise ValueError(f"Unknown backend type: {backend_type}")
                backend_cls = BACKEND_REGISTRY[backend_type]
                backends_list.append(backend_cls.from_dict(bd["params"]))
            return cls(
                backends=backends_list,
                backend_key=params["backend_key"],
            )
        except KeyError as e:
            raise ValueError(f"Missing required param: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to reconstruct MIMIC: {e}") from e

    def actions(self) -> List[Callable]:
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
            backend_info = self._get_backend_info()
            if "sqlite" in self.backend_key.lower():
                query = (
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                result = self.backends[self.backend_key].execute(query)
                return f"{backend_info}\n📋 **Available Tables:**\n{result}"
            else:
                hosp_dataset = self.config.get_env_var(
                    "M3_BIGQUERY_HOSP_DATASET", "mimiciv_3_1_hosp"
                )
                icu_dataset = self.config.get_env_var(
                    "M3_BIGQUERY_ICU_DATASET", "mimiciv_3_1_icu"
                )
                project = self.config.get_env_var(
                    "M3_BIGQUERY_PROJECT", "physionet-data"
                )
                query = f"""
                   SELECT CONCAT('`{project}.{hosp_dataset}.', table_name, '`') as query_ready_table_name
                   FROM `{project}.{hosp_dataset}.INFORMATION_SCHEMA.TABLES`
                   UNION ALL
                   SELECT CONCAT('`{project}.{icu_dataset}.', table_name, '`') as query_ready_table_name
                   FROM `{project}.{icu_dataset}.INFORMATION_SCHEMA.TABLES`
                   ORDER BY query_ready_table_name
                   """
                result = self.backends[self.backend_key].execute(query)
                return f"{backend_info}\n📋 **Available Tables (query-ready names):**\n{result}\n\n💡 **Copy-paste ready:** These table names can be used directly in your SQL queries!"

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
            backend_info = self._get_backend_info()
            if "sqlite" in self.backend_key.lower():
                pragma_query = f"PRAGMA table_info({table_name})"
                try:
                    result = self.backends[self.backend_key].execute(pragma_query)
                    info_result = f"{backend_info}📋 **Table:** {table_name}\n\n**Column Information:**\n{result}"
                    if show_sample:
                        sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                        sample_result = self.backends[self.backend_key].execute(
                            sample_query
                        )
                        info_result += (
                            f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"
                        )
                    return info_result
                except Exception as e:
                    return f"{backend_info}❌ Error examining table '{table_name}': {e}\n\n💡 Use get_database_schema() to see available tables."
            else:
                if "." in table_name and "physionet-data" in table_name:
                    clean_name = table_name.strip("`")
                    full_table_name = f"`{clean_name}`"
                    parts = clean_name.split(".")
                    if len(parts) != 3:
                        return f"{backend_info}❌ **Invalid qualified table name:** `{table_name}`\n\n**Expected format:** `project.dataset.table`\n**Example:** `physionet-data.mimiciv_3_1_hosp.diagnoses_icd`\n\n**Available MIMIC-IV datasets:**\n- `physionet-data.mimiciv_3_1_hosp.*` (hospital module)\n- `physionet-data.mimiciv_3_1_icu.*` (ICU module)"
                    simple_table_name = parts[2]
                    dataset = f"{parts[0]}.{parts[1]}"
                else:
                    simple_table_name = table_name
                    full_table_name = None
                    dataset = None

                if full_table_name:
                    try:
                        info_query = f"""
                           SELECT column_name, data_type, is_nullable
                           FROM {dataset}.INFORMATION_SCHEMA.COLUMNS
                           WHERE table_name = '{simple_table_name}'
                           ORDER BY ordinal_position
                           """
                        info_result = self.backends[self.backend_key].execute(
                            info_query
                        )
                        if "No results found" not in info_result:
                            result = f"{backend_info}📋 **Table:** {full_table_name}\n\n**Column Information:**\n{info_result}"
                            if show_sample:
                                sample_query = (
                                    f"SELECT * FROM {full_table_name} LIMIT 3"
                                )
                                sample_result = self.backends[self.backend_key].execute(
                                    sample_query
                                )
                                result += f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"
                            return result
                    except Exception:
                        pass

                for ds in [
                    self.config.get_env_var(
                        "M3_BIGQUERY_HOSP_DATASET", "mimiciv_3_1_hosp"
                    ),
                    self.config.get_env_var(
                        "M3_BIGQUERY_ICU_DATASET", "mimiciv_3_1_icu"
                    ),
                ]:
                    try:
                        full_table_name = f"`{self.config.get_env_var('M3_BIGQUERY_PROJECT', 'physionet-data')}.{ds}.{simple_table_name}`"
                        info_query = f"""
                           SELECT column_name, data_type, is_nullable
                           FROM `{self.config.get_env_var("M3_BIGQUERY_PROJECT", "physionet-data")}.{ds}.INFORMATION_SCHEMA.COLUMNS`
                           WHERE table_name = '{simple_table_name}'
                           ORDER BY ordinal_position
                           """
                        info_result = self.backends[self.backend_key].execute(
                            info_query
                        )
                        if "No results found" not in info_result:
                            result = f"{backend_info}📋 **Table:** {full_table_name}\n\n**Column Information:**\n{info_result}"
                            if show_sample:
                                sample_query = (
                                    f"SELECT * FROM {full_table_name} LIMIT 3"
                                )
                                sample_result = self.backends[self.backend_key].execute(
                                    sample_query
                                )
                                result += f"\n\n📊 **Sample Data (first 3 rows):**\n{sample_result}"
                            return result
                    except Exception:
                        continue
                return f"{backend_info}❌ Table '{table_name}' not found in any dataset. Use get_database_schema() to see available tables."

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
            is_safe, message = self._is_safe_query(sql_query)
            if not is_safe:
                if "describe" in sql_query.lower() or "show" in sql_query.lower():
                    return f"❌ **Security Error:** {message}\n\n🔍 **For table structure:** Use `get_table_info('table_name')` instead of DESCRIBE\n📋 **Why this is better:** Shows columns, types, AND sample data to understand the actual data\n\n💡 **Recommended workflow:**\n1. `get_database_schema()` ← See available tables\n2. `get_table_info('table_name')` ← Explore structure\n3. `execute_mimic_query('SELECT ...')` ← Run your analysis"
                return f"❌ **Security Error:** {message}\n\n💡 **Tip:** Only SELECT statements are allowed for data analysis."
            try:
                result = self.backends[self.backend_key].execute(sql_query)
                return result
            except Exception as e:
                error_msg = str(e).lower()
                suggestions = []
                if "no such table" in error_msg or "table not found" in error_msg:
                    suggestions.append(
                        "🔍 **Table name issue:** Use `get_database_schema()` to see exact table names"
                    )
                    suggestions.append(
                        f"📋 **Backend-specific naming:** {self.backend_key} has specific table naming conventions"
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
                        f"🎯 **Backend syntax:** Verify your SQL works with {self.backend_key}"
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
                return f"❌ **Query Failed:** {e}\n\n🛠️ **How to fix this:**\n{suggestion_text}\n\n🎯 **Quick Recovery Steps:**\n1. `get_database_schema()` ← See what tables exist\n2. `get_table_info('your_table')` ← Check exact column names\n3. Retry your query with correct names\n\n📚 **Current Backend:** {self.backend_key} - table names and syntax are backend-specific"

        def get_icu_stays(patient_id: Optional[int] = None, limit: int = 10) -> str:
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
            if not validate_limit(limit):
                return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
            icustays_table = self.table_names["icustays"]
            if patient_id:
                query = (
                    f"SELECT * FROM {icustays_table} WHERE subject_id = {patient_id}"
                )
            else:
                query = f"SELECT * FROM {icustays_table} LIMIT {limit}"
            result = self.backends[self.backend_key].execute(query)
            if "error" in result.lower() or "not found" in result.lower():
                return f"❌ **Convenience function failed:** {result}\n\n💡 **For reliable results, use the proper workflow:**\n1. `get_database_schema()` ← See actual table names\n2. `get_table_info('table_name')` ← Understand structure\n3. `execute_mimic_query('your_sql')` ← Use exact names\n\nThis ensures compatibility across different MIMIC-IV setups."
            return result

        def get_lab_results(
            patient_id: Optional[int] = None,
            lab_item: Optional[str] = None,
            limit: int = 20,
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
            if not validate_limit(limit):
                return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
            labevents_table = self.table_names["labevents"]
            conditions = []
            if patient_id:
                conditions.append(f"subject_id = {patient_id}")
            if lab_item:
                escaped_lab_item = lab_item.replace("'", "''")
                conditions.append(f"value LIKE '%{escaped_lab_item}%'")
            base_query = f"SELECT * FROM {labevents_table}"
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            base_query += f" LIMIT {limit}"
            result = self.backends[self.backend_key].execute(base_query)
            if "error" in result.lower() or "not found" in result.lower():
                return f"❌ **Convenience function failed:** {result}\n\n💡 **For reliable results, use the proper workflow:**\n1. `get_database_schema()` ← See actual table names\n2. `get_table_info('table_name')` ← Understand structure\n3. `execute_mimic_query('your_sql')` ← Use exact names\n\nThis ensures compatibility across different MIMIC-IV setups."
            return result

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
            if not validate_limit(limit):
                return "Error: Invalid limit. Must be a positive integer between 1 and 1000."
            admissions_table = self.table_names["admissions"]
            query = f"SELECT race, COUNT(*) as count FROM {admissions_table} GROUP BY race ORDER BY count DESC LIMIT {limit}"
            result = self.backends[self.backend_key].execute(query)
            if "error" in result.lower() or "not found" in result.lower():
                return f"❌ **Convenience function failed:** {result}\n\n💡 **For reliable results, use the proper workflow:**\n1. `get_database_schema()` ← See actual table names\n2. `get_table_info('table_name')` ← Understand structure\n3. `execute_mimic_query('your_sql')` ← Use exact names\n\nThis ensures compatibility across different MIMIC-IV setups."
            return result

        actions_list = [
            get_database_schema,
            get_table_info,
            execute_mimic_query,
            get_icu_stays,
            get_lab_results,
            get_race_distribution,
        ]
        if self.auth:
            actions_list = [self.auth.decorator(action) for action in actions_list]
        return actions_list

    def _set_required_env_vars(self, backend_key: str) -> None:
        self.required_env_vars = {}

        def add_required_vars(section_vars: List[Dict[str, Any]]) -> None:
            for var in section_vars:
                if var.get("required", False):
                    key = var["key"]
                    default = var.get("default", None)
                    self.required_env_vars[key] = default

        add_required_vars(self.env_config.get("core", []))

        backend_section = self.env_config.get("backends", {}).get(backend_key, [])
        add_required_vars(backend_section)

        enabled = (
            self.config.get_env_var("M3_OAUTH2_ENABLED", "false").lower() == "true"
        )
        if enabled:
            add_required_vars(self.env_config.get("oauth2", []))

        logger.debug(
            f"Set {len(self.required_env_vars)} required env vars for backend '{backend_key}', oauth enabled: {enabled}"
        )

    def _set_backends(self, backends: List[BackendBase]) -> None:
        self.backends = {
            b.__class__.__name__.lower().replace("backend", ""): b for b in backends
        }

    def _set_auth(self) -> None:
        enabled = (
            self.config.get_env_var("M3_OAUTH2_ENABLED", "false").lower() == "true"
        )
        self.auth = Auth(self.config) if enabled else None

    def _validate_backend_key(self, backend_key: str) -> None:
        if backend_key not in self.backends:
            raise M3ValidationError(f"Invalid backend key: {backend_key}")

    def _initialize(self) -> None:
        self.table_names = {}
        if self.backend_key == "sqlite":
            env_vars = {
                "icustays": ("M3_ICUSTAYS_TABLE", "icu_icustays"),
                "labevents": ("M3_LABEVENTS_TABLE", "hosp_labevents"),
                "admissions": ("M3_ADMISSIONS_TABLE", "hosp_admissions"),
            }
            self.table_names = {
                key: self.config.get_env_var(*env) for key, env in env_vars.items()
            }
        else:
            prefix = self.config.get_env_var(
                "M3_BIGQUERY_PREFIX", "`physionet-data.mimiciv_3_1_"
            )
            self.table_names = {
                "icustays": f"{prefix}icu.icustays`",
                "labevents": f"{prefix}hosp.labevents`",
                "admissions": f"{prefix}hosp.admissions`",
            }

    def _get_backend_info(self) -> str:
        if "sqlite" in self.backend_key.lower():
            return f"🔧 **Current Backend:** SQLite (local database)\n📁 **Database Path:** {self.backends[self.backend_key].path}\n"
        else:
            return f"🔧 **Current Backend:** BigQuery (cloud database)\n☁️ **Project ID:** {self.backends[self.backend_key].project}\n"

    def _is_safe_query(self, sql_query: str) -> Tuple[bool, str]:
        if not sql_query or not sql_query.strip():
            return False, "Empty query"
        parsed = sqlparse.parse(sql_query.strip())
        if not parsed:
            return False, "Invalid SQL syntax"
        if len(parsed) > 1:
            return False, "Multiple statements not allowed"
        statement = parsed[0]
        statement_type = statement.get_type()
        if statement_type not in ("SELECT", "UNKNOWN"):
            return False, "Only SELECT and PRAGMA queries allowed"
        sql_upper = sql_query.strip().upper()
        if sql_upper.startswith("PRAGMA"):
            return True, "Safe PRAGMA statement"
        if not self.security_config:
            self.security_config = load_security_config()
        dangerous_keywords = set(self.security_config.get("dangerous_keywords", []))
        for keyword in dangerous_keywords:
            if f" {keyword} " in f" {sql_upper} ":
                return False, f"Write operation not allowed: {keyword}"
        injection_patterns = self.security_config.get("injection_patterns", [])
        for pattern, description in injection_patterns:
            if pattern.upper() in sql_upper:
                return False, f"Injection pattern detected: {description}"
        suspicious_names = set(self.security_config.get("suspicious_names", []))
        for name in suspicious_names:
            if name.upper() in sql_upper:
                return (
                    False,
                    f"Suspicious identifier detected: {name} (not medical data)",
                )
        return True, "Safe"

    def _post_load(self) -> None:
        self.data_io = DataIO(self.config)
        enabled = (
            self.config.get_env_var("M3_OAUTH2_ENABLED", "false").lower() == "true"
        )
        self.auth = Auth(self.config) if enabled else None
