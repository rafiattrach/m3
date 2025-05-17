import os
import json
from typing import Any, Dict, List, Literal, Optional
from google.cloud import bigquery
import pandas as pd

# Assuming FastMCP is installed and available
# pip install fastmcp google-cloud-bigquery pandas db-dtypes
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP library not found. Please install it: pip install fastmcp")
    exit(1)

# --- Configuration ---
# Public PhysioNet project and specific MIMIC-IV dataset names
# Adjust dataset names if using a different version or if names differ
PHYSIONET_PROJECT = "physionet-data"
MIMIC_HOSP_DATASET = "mimiciv_3_1_hosp"  # Common name for MIMIC-IV hosp data
MIMIC_ICU_DATASET = "mimiciv_3_1_icu"      # Common name for MIMIC-IV icu data
MIMIC_ED_DATASET = "mimiciv_ed"        # MIMIC-IV ED data

# 1. IMPORTANT: Use YOUR Google Cloud project ID for billing and authentication.
#    Ensure this project has the BigQuery API enabled.
#    The service account/user running this code needs appropriate IAM roles:
#    - On YOUR project: 'BigQuery User', 'BigQuery Job User'
#    - On physionet-data project: 'BigQuery Data Viewer' (or viewer on specific datasets)
BILLING_PROJECT_ID = "level-strategy-383218" # <<<--- REPLACE WITH YOUR BILLING PROJECT ID

# 2. Initialize BigQuery client
bq_client = None # Initialize as None
try:
    # Check if the placeholder ID is still present
    if not BILLING_PROJECT_ID or BILLING_PROJECT_ID == "your-billing-project-id-here":
         raise ValueError("BILLING_PROJECT_ID is not set. Please replace it with your actual Google Cloud project ID.")

    # The client needs your project ID to know where to bill jobs and manage quotas
    bq_client = bigquery.Client(project=BILLING_PROJECT_ID)
    print(f"BigQuery client initialized successfully. Billing project: {BILLING_PROJECT_ID}")

    # Optional: Test access to a public dataset (uncomment to run)
    # try:
    #     test_dataset = f"{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}"
    #     bq_client.get_dataset(test_dataset)
    #     print(f"Successfully accessed dataset: {test_dataset}")
    # except Exception as e:
    #     print(f"Warning: Could not directly confirm access to {test_dataset}. Ensure permissions are set. Error: {e}")

except Exception as e:
    print(f"Error initializing BigQuery client for project {BILLING_PROJECT_ID}: {e}")
    print("Please check:")
    print("1. Google Cloud SDK Authentication (`gcloud auth application-default login` or service account key)")
    print(f"2. The BILLING_PROJECT_ID ('{BILLING_PROJECT_ID}') is correct and exists.")
    print(f"3. Necessary IAM roles are granted on project '{BILLING_PROJECT_ID}' and '{PHYSIONET_PROJECT}'.")
    print("4. The BigQuery API is enabled in your Google Cloud project.")
    # bq_client remains None, the script will exit later if it's needed

# --- Initialize FastMCP server ---
mcp = FastMCP("mimic_criteria_query_server")

# --- Helper Function for BigQuery ---
async def execute_bq_query(sql_query: str, query_params: list = None) -> pd.DataFrame | str:
    """
    Executes a BigQuery query using the global client and returns a DataFrame or error string.

    Args:
        sql_query: The SQL query string to execute.
        query_params: Optional list of bigquery.ScalarQueryParameter for parameterized queries.

    Returns:
        A pandas DataFrame with the query results, or a string containing an error message.
    """
    if not bq_client:
        return "Error: BigQuery client is not initialized. Check configuration and authentication."
    try:
        # Configure the job. Use parameters if provided.
        job_config = bigquery.QueryJobConfig(query_parameters=query_params) if query_params else bigquery.QueryJobConfig()

        # Log the query being executed
        print(f"Executing BigQuery Query (Billing Project: {BILLING_PROJECT_ID}):\n---\n{sql_query}\n---")
        if query_params:
             print(f"With parameters: {[(p.name, p.value) for p in query_params]}")

        # Execute the query, ensuring it runs under the billing project context
        query_job = bq_client.query(sql_query, job_config=job_config, project=BILLING_PROJECT_ID)

        # Wait for the job to complete and fetch results into a pandas DataFrame
        # Requires 'db-dtypes' package for full compatibility with newer BQ types
        results_df = query_job.to_dataframe()
        print(f"Query successful. Fetched {len(results_df)} rows.")
        return results_df

    except Exception as e:
        # Attempt to provide a detailed error message
        error_message = f"Error executing BigQuery query: {str(e)}"
        print(error_message)
        # Extract more specific BQ error details if available
        if hasattr(e, 'errors') and e.errors:
            try:
                error_detail = e.errors[0].get('message', 'No specific error message found.')
                reason_detail = e.errors[0].get('reason', 'No specific reason found.')
                location_detail = e.errors[0].get('location', 'No specific location found.')
                error_message += (f"\nBigQuery Error Details:\n  Reason: {reason_detail}\n"
                                  f"  Location: {location_detail}\n  Message: {error_detail}")
            except Exception as inner_e:
                error_message += f"\n(Could not parse detailed BigQuery error: {inner_e})"
        # Check if the error message specifically mentions db-dtypes
        if 'db-dtypes' in str(e):
            error_message += "\n\nHint: Try installing the required package: pip install db-dtypes google-cloud-bigquery[pandas]"
        return error_message

# --- Tool Definitions ---

@mcp.tool()
async def execute_arbitrary_mimic_query(sql_query: str) -> str:
    """
    Executes an arbitrary SQL SELECT query against the MIMIC datasets hosted on BigQuery.

    Args:
        sql_query: A valid BigQuery SQL SELECT query string. The query *must* explicitly reference
                   tables using the full path, e.g.,
                   `physionet-data.mimiciv_3_1_hosp.admissions`.

    Returns:
        A string containing the query results (formatted as a string table, max 50 rows)
        or an error message if the query fails or is disallowed.
    """
    # Basic security checks (should primarily rely on IAM)
    disallowed_keywords = ["UPDATE ", "DELETE ", "INSERT ", "DROP ", "CREATE ", "ALTER ", "GRANT ", "TRUNCATE "]
    query_upper = sql_query.upper()

    for keyword in disallowed_keywords:
        if keyword in query_upper:
            return f"Error: Query contains disallowed keyword ('{keyword.strip()}'). Only SELECT queries are permitted."

    # Enforce explicit project reference for clarity and safety
    required_project_prefix = f"`{PHYSIONET_PROJECT}`." # Check for backticks too
    required_project_prefix_no_ticks = f"{PHYSIONET_PROJECT}."
    sql_query_lower = sql_query.lower()
    if required_project_prefix not in sql_query_lower and required_project_prefix_no_ticks not in sql_query_lower:
         return (f"Error: Query must explicitly reference tables within the '{PHYSIONET_PROJECT}' project "
                 f"(e.g., `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.patients`).")

    # Execute the query using the helper function
    result = await execute_bq_query(sql_query)

    # Format the result
    if isinstance(result, str): # An error message string was returned
        return result
    elif isinstance(result, pd.DataFrame):
        if result.empty:
            return "Query executed successfully, but returned no results."
        else:
            # Format the DataFrame to a string for the client
            # Add max_rows/cols to prevent overly large outputs flooding the client
            try:
                return result.to_string(index=False, max_rows=50, max_cols=20)
            except Exception as e:
                return f"Error formatting query results: {e}"
    else:
        # Should not happen with current helper function logic
        return "Error: Unexpected return type from query execution."


@mcp.tool()
async def get_mimic_aggregation(
    metric: Literal["patient_count", "average_age"]
) -> str:
    """
    Performs simple overall dataset aggregation queries on MIMIC-IV hosp data.

    Args:
        metric: The aggregation metric ('patient_count', 'average_age').

    Returns:
        A string containing the aggregation result or an error message.
    """
    sql_query = ""
    query_params = [] # No parameters needed for these simple aggregations

    if metric == "patient_count":
        # Count all unique patients in the dataset
        sql_query = f"""
        SELECT COUNT(DISTINCT subject_id) as total_patients
        FROM `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.patients`
        """
    elif metric == "average_age":
        # Calculate overall average age at admission across all admissions
        sql_query = f"""
        SELECT
            AVG(CAST( (p.anchor_age + EXTRACT(YEAR FROM a.admittime) - p.anchor_year) AS NUMERIC )) as overall_average_admission_age
        FROM
            `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.patients` p
        JOIN
             `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.admissions` a ON p.subject_id = a.subject_id
        -- Add basic filters for valid age calculation
        WHERE p.anchor_age IS NOT NULL
          AND p.anchor_year IS NOT NULL
          AND a.admittime IS NOT NULL
          AND EXTRACT(YEAR FROM a.admittime) >= p.anchor_year -- Ensure admission is not before anchor year
        """
    else:
        return f"Error: Unsupported metric '{metric}'. Only 'patient_count' and 'average_age' are supported."

    # --- Execute Query ---
    result = await execute_bq_query(sql_query, query_params)

    # --- Format Output ---
    if isinstance(result, str):
        return result
    elif isinstance(result, pd.DataFrame):
        if result.empty or result.iloc[0,0] is None: # Check for empty or NULL result
            return f"Aggregation query for '{metric}' executed successfully, but returned no results (or zero count/null average)."
        try:
            # Return simple result, usually one row
            return result.to_string(index=False)
        except Exception as e:
            return f"Error formatting aggregation results for metric '{metric}': {e}"
    else:
        return "Error: Unexpected return type from query execution."


@mcp.tool()
async def list_common_lab_items(search_term: Optional[str] = None, limit: int = 50) -> str:
    """
    Lists common lab item labels available in MIMIC-IV (from d_labitems).
    Optionally filters the list based on a search term (case-insensitive contains).

    Args:
        search_term (Optional[str]): A term to search for within lab labels. Defaults to None (no filter).
        limit (int): Maximum number of lab labels to return. Defaults to 50.

    Returns:
        A JSON string containing a list of matching lab item labels, or an error message.
        Example output: '["Glucose", "Potassium", "Sodium", ...]'
    """
    if limit <= 0:
        return "Error: limit must be positive."

    # Construct the query to select distinct labels from d_labitems
    sql_query = f"""
    SELECT DISTINCT label
    FROM `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.d_labitems`
    """
    query_params = []
    param_counter = 0

    # Add WHERE clause if search term is provided
    if search_term:
        # Use LOWER for case-insensitive search with LIKE
        param_name = f"p{param_counter}"; param_counter+=1
        sql_query += f" WHERE LOWER(label) LIKE LOWER(@{param_name})"
        # Add wildcards for 'contains' search
        query_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", f"%{search_term}%"))

    # Add ordering and limit
    sql_query += f"\nORDER BY label\nLIMIT {limit}"

    # Execute the query
    result = await execute_bq_query(sql_query, query_params)

    # Format the result
    if isinstance(result, str): # Error occurred
        return result
    elif isinstance(result, pd.DataFrame):
        if result.empty:
            search_str = f" matching search term '{search_term}'" if search_term else ""
            return f"No lab item labels found{search_str}."
        else:
            # Convert the DataFrame column to a list and return as JSON string
            labels = result['label'].tolist()
            return json.dumps(labels)
    else:
        return "Error: Unexpected return type."


@mcp.tool()
async def find_admissions_with_criteria(
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    gender: Optional[Literal["M", "F"]] = None,
    lab_criteria: Optional[List[Dict[str, Any]]] = None, # Accepts List[Dict]
    match_all_labs: bool = True,
    max_results: int = 100
) -> str:
    """
    Finds hospital admission IDs (hadm_id) based on demographics (age, gender)
    and/or specific lab value criteria. Corrected for JOIN order dependency.

    Args:
        min_age (Optional[int]): Minimum admission age.
        max_age (Optional[int]): Maximum admission age.
        gender (Optional[Literal["M", "F"]]): Patient gender.
        lab_criteria (Optional[List[Dict[str, Any]]]): A list of lab criteria dictionaries.
            Each dictionary should have:
            - "label": str (Lab item label from d_labitems, e.g., "Creatinine")
            - "value_min": Optional[float] (Minimum value for labevents.valuenum)
            - "value_max": Optional[float] (Maximum value for labevents.valuenum)
            - "time_window_hours": Optional[int] (Max hours after admission time for the lab event)
            Example: [{"label": "Troponin T", "value_min": 0.1}, {"label": "Creatinine", "value_max": 1.5, "time_window_hours": 24}]
        match_all_labs (bool): If True (default), admissions must meet ALL specified lab criteria.
                               If False, meeting ANY specified lab criterion is sufficient.
        max_results (int): Max number of hadm_ids to return. Defaults to 100.

    Returns:
        A string containing a comma-separated list of matching hadm_ids (up to max_results),
        a count message, or an error message.
    """
    # --- Input Validation ---
    if max_results <= 0: return "Error: max_results must be positive."
    if min_age is not None and max_age is not None and min_age > max_age: return "Error: min_age > max_age."
    if gender not in [None, "M", "F"]: return "Error: gender must be 'M', 'F', or None."

    parsed_lab_criteria: List[Dict[str, Any]] = lab_criteria if lab_criteria else []

    # Validate the structure of the received lab_criteria list
    try:
        if parsed_lab_criteria:
             if not isinstance(parsed_lab_criteria, list):
                  raise ValueError("lab_criteria must be a list of objects.")
             for item in parsed_lab_criteria:
                  if not isinstance(item, dict) or "label" not in item:
                       raise ValueError("Each item in lab_criteria list must be an object with at least a 'label' key.")
                  # Check numeric types for min/max
                  if "value_min" in item and item["value_min"] is not None and not isinstance(item["value_min"], (int, float)):
                     raise ValueError(f"value_min for label '{item['label']}' must be a number or null.")
                  if "value_max" in item and item["value_max"] is not None and not isinstance(item["value_max"], (int, float)):
                     raise ValueError(f"value_max for label '{item['label']}' must be a number or null.")
                  # Check integer type for time window
                  if "time_window_hours" in item and item["time_window_hours"] is not None:
                      if not isinstance(item["time_window_hours"], int):
                          raise ValueError(f"time_window_hours for label '{item['label']}' must be an integer or null.")
                      if item["time_window_hours"] < 0:
                           raise ValueError(f"time_window_hours for label '{item['label']}' cannot be negative.")

    except ValueError as e:
         return f"Error in lab_criteria format: {e}"

    num_required_labs = len(parsed_lab_criteria)

    # Check if any criteria were provided
    if min_age is None and max_age is None and gender is None and not parsed_lab_criteria:
         return "Error: Please provide at least one filter criterion (age, gender, or lab_criteria)."

    # --- Query Construction ---
    select_clause = "" # Will be set later based on logic
    from_clause = f"FROM `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.admissions` a"
    demographic_joins = set() # Use set for independent joins (like patients)
    lab_join_clause = ""      # Store ordered lab joins as a single string block
    where_conditions = []     # Conditions from demographics
    lab_where_conditions = [] # Conditions specifically derived from lab_criteria logic
    query_params = []
    param_counter = 0
    final_query_assembled = False # Flag to indicate if query was built by match_all logic
    group_by_clause = ""
    having_clause = ""

    # Add demographic joins and filters
    if min_age is not None or max_age is not None or gender is not None:
        # Add patient join to the demographic set
        demographic_joins.add(f"JOIN `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.patients` p ON a.subject_id = p.subject_id")
        age_calc = "(p.anchor_age + EXTRACT(YEAR FROM a.admittime) - p.anchor_year)" # Calculate age at admission
        if min_age is not None:
             param_name = f"p{param_counter}"; param_counter+=1
             where_conditions.append(f"{age_calc} >= @{param_name}")
             query_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", min_age))
        if max_age is not None:
             param_name = f"p{param_counter}"; param_counter+=1
             where_conditions.append(f"{age_calc} <= @{param_name}")
             query_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", max_age))
        if gender is not None:
             param_name = f"p{param_counter}"; param_counter+=1
             where_conditions.append(f"p.gender = @{param_name}")
             query_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", gender))

    # Define lab joins (if needed) and build lab filters
    lab_sub_clauses = [] # Stores conditions for each individual lab criterion: (cond1 AND cond2)
    required_labels = set() # Track unique labels required if match_all_labs=True
    if parsed_lab_criteria:
        # Define the lab join block in the CORRECT ORDER to avoid alias errors
        # 'le' must be defined before it's used in the 'dli' join condition.
        lab_join_clause = f"""
JOIN `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.labevents` le ON a.hadm_id = le.hadm_id
JOIN `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.d_labitems` dli ON le.itemid = dli.itemid"""

        # Build WHERE clauses for each lab criterion provided
        for i, criterion in enumerate(parsed_lab_criteria):
            label = criterion["label"]
            required_labels.add(label)
            value_min = criterion.get("value_min")
            value_max = criterion.get("value_max")
            time_window = criterion.get("time_window_hours")

            criterion_clause_parts = [] # Stores AND conditions for *this* criterion

            # Label match
            param_name = f"p{param_counter}"; param_counter+=1
            criterion_clause_parts.append(f"dli.label = @{param_name}")
            query_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", label))

            # Value min match (only add if specified)
            if value_min is not None:
                 param_name = f"p{param_counter}"; param_counter+=1
                 criterion_clause_parts.append(f"le.valuenum >= @{param_name}")
                 query_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", float(value_min)))

            # Value max match (only add if specified)
            if value_max is not None:
                 param_name = f"p{param_counter}"; param_counter+=1
                 criterion_clause_parts.append(f"le.valuenum <= @{param_name}")
                 query_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", float(value_max)))

            # Time window match (only add if specified)
            if time_window is not None:
                param_name = f"p{param_counter}"; param_counter+=1
                # Ensure charttime is within X hours AFTER admittime
                criterion_clause_parts.append(f"le.charttime >= a.admittime") # Lab must be after admission start
                criterion_clause_parts.append(f"TIMESTAMP_DIFF(le.charttime, a.admittime, HOUR) <= @{param_name}")
                query_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", time_window))

            # Combine parts for this single lab criterion with AND
            if criterion_clause_parts: # Avoid adding empty clauses
                lab_sub_clauses.append(f"({' AND '.join(criterion_clause_parts)})")

    # Determine overall query structure based on match_all_labs
    # Case 1: Match ALL labs (requires aggregation)
    if parsed_lab_criteria and match_all_labs and num_required_labs > 1:
        select_clause = "SELECT a.hadm_id" # Select hadm_id for grouping
        group_by_clause = " GROUP BY a.hadm_id"
        num_distinct_labels = len(required_labels) # Count unique labels required
        param_name = f"p{param_counter}"; param_counter+=1
        having_clause = f" HAVING COUNT(DISTINCT dli.label) >= @{param_name}"
        query_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", num_distinct_labels))

        # The main WHERE clause needs the OR of individual lab conditions
        # to filter the rows *before* they are grouped.
        if lab_sub_clauses:
            lab_where_conditions.append(f"({' OR '.join(lab_sub_clauses)})")

        # --- Assemble the final query (match_all_labs case) ---
        sql_query = f"{select_clause}\n{from_clause}\n"
        # Add demographic joins (if any), sorted is fine here as they are independent
        if demographic_joins:
             sql_query += "\n".join(sorted(list(demographic_joins))) + "\n"
        # Add the ORDERED lab joins (essential fix)
        sql_query += lab_join_clause + "\n"

        # Combine all WHERE conditions (Demographics AND Lab OR-Group)
        all_where_conditions = where_conditions + lab_where_conditions
        if all_where_conditions:
            sql_query += "WHERE " + "\n  AND ".join(all_where_conditions) + "\n"

        # Add grouping, having, ordering, limit
        sql_query += group_by_clause + "\n" + having_clause + "\n"
        sql_query += f"ORDER BY a.hadm_id\nLIMIT {max_results}"
        final_query_assembled = True # Mark query as assembled for this specific case

    # Case 2: Default - Match ANY lab, or only one lab specified, or no labs specified
    if not final_query_assembled:
         select_clause = "SELECT DISTINCT a.hadm_id" # Use DISTINCT if not grouping
         sql_query = f"{select_clause}\n{from_clause}\n"
         # Add demographic joins (if any)
         if demographic_joins:
             sql_query += "\n".join(sorted(list(demographic_joins))) + "\n"
         # Add the ORDERED lab joins if labs were specified
         if lab_join_clause: # Only add if parsed_lab_criteria was true
             sql_query += lab_join_clause + "\n"

         # Combine WHERE conditions
         # For match_any or single lab, the OR group goes directly in WHERE
         if lab_sub_clauses: # Only add if lab criteria were processed
              lab_where_conditions.append(f"({' OR '.join(lab_sub_clauses)})")

         all_where_conditions = where_conditions + lab_where_conditions
         if all_where_conditions:
             sql_query += "WHERE " + "\n  AND ".join(all_where_conditions) + "\n"

         sql_query += f"ORDER BY a.hadm_id\nLIMIT {max_results}" # Add ordering and limit

    # --- Execute Query ---
    # Optional: Add logging here to verify the generated query and parameters
    # print(f"DEBUG SQL:\n{sql_query}")
    # print(f"DEBUG PARAMS: {[(p.name, p.parameter_type.type_, p.value) for p in query_params]}")

    result = await execute_bq_query(sql_query, query_params)

    # --- Format Output ---
    if isinstance(result, str): # An error message string was returned
        return result
    elif isinstance(result, pd.DataFrame):
        if result.empty:
            return f"Query executed successfully, but found no admissions matching the specified criteria."
        else:
            # Extract hadm_ids, convert to string, join with comma
            hadm_ids_list = result['hadm_id'].astype(str).tolist()
            count = len(hadm_ids_list)
            # Limit the number of IDs actually returned in the string if needed,
            # although the SQL query already applied LIMIT max_results
            ids_to_return = ",".join(hadm_ids_list)
            # Provide summary message
            return f"Found {count} admissions matching criteria. Returning hadm_ids: {ids_to_return}"
    else:
        # Should not happen with current execute_bq_query logic, but good practice
        return "Error: Unexpected return type from query execution."

# --- Main Execution Block ---
if __name__ == "__main__":
    # Check if BigQuery client initialized correctly before starting the server
    if not bq_client:
         print("\n--- CRITICAL ERROR: BigQuery Client Initialization FAILED ---")
         print("The server cannot execute BigQuery queries. Please check the error messages above.")
         print("Ensure configuration, authentication, IAM roles, and API enablement are correct.")
         print("Exiting.")
         exit(1) # Exit if BQ client is not available
    else:
        # Display server configuration and available tools on startup
        print("\n--- Server Configuration ---")
        print(f"Billing Project ID: {BILLING_PROJECT_ID}")
        print(f"Querying Project: {PHYSIONET_PROJECT}")
        print(f"Target MIMIC Hosp Dataset: {MIMIC_HOSP_DATASET}")
        print(f"Target MIMIC ICU Dataset: {MIMIC_ICU_DATASET}")
        print(f"Target MIMIC ED Dataset: {MIMIC_ED_DATASET}")

        print("\n--- Available Tools ---")
        print("1. execute_arbitrary_mimic_query(sql_query: str)")
        print("   - Executes arbitrary SELECT queries. **HIGH RISK**. Use cautiously.")
        print(f"   - Requires full table paths (e.g., `{PHYSIONET_PROJECT}.{MIMIC_HOSP_DATASET}.patients`).")
        print("2. get_mimic_aggregation(metric: Literal['patient_count', 'average_age'])")
        print("   - Simple overall aggregations (total patient count or average admission age).")
        print("3. list_common_lab_items(search_term: Optional[str], limit: int = 50)")
        print("   - Lists available lab item labels, optionally filtered by search term.")
        # Updated description for find_admissions_with_criteria
        print("4. find_admissions_with_criteria(min_age: Optional[int], max_age: Optional[int], gender: Optional[Literal['M', 'F']], lab_criteria: Optional[List[Dict[str, Any]]], match_all_labs: bool = True, max_results: int = 100)")
        print("   - Finds admission IDs (hadm_id) matching demographics and/or lab criteria.")
        print("   - lab_criteria expects a list of dicts, e.g., [{'label': 'Glucose', 'value_max': 100}]")

        # Start the FastMCP server
        print("\nStarting FastMCP server for MIMIC queries...")
        print("Server ready to accept connections (e.g., via stdio). Send JSON RPC requests.")
        try:
            # Run the server using stdio transport by default
            # Other transports like 'websocket' might be configured if needed
            mcp.run(transport='stdio')
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
        except Exception as e:
            print(f"\nAn error occurred while running the server: {e}")

