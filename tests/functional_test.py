import pytest
from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

PROJECT_ID = "level-strategy-383218"


def test_bigquery_connection():
    """
    Test if a connection to BigQuery can be established with the provided project ID.
    This test will pass if the client can be created and a simple query runs
    successfully.
    """
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        query_job = bq_client.query("SELECT 1 AS test")
        results = list(query_job.result())
        assert results[0].test == 1
    except GoogleAPIError as e:
        pytest.fail(f"BigQuery API error occurred: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error occurred: {e}")
