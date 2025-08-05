import logging

import pandas as pd
from beartype import beartype
from beartype.typing import Any, Dict

from m3.core.tool.backend.base import BackendBase
from m3.core.utils.exceptions import M3InitializationError, M3ValidationError

logger = logging.getLogger(__name__)


@beartype
class BigQueryBackend(BackendBase):
    def __init__(self, project: str) -> None:
        self.project = project
        self.client = None

    def to_dict(self) -> Dict[str, Any]:
        return {"project": self.project}

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> "BigQueryBackend":
        try:
            return cls(project=params["project"])
        except KeyError as e:
            raise ValueError(f"Missing required param: {e}") from e

    def initialize(self) -> None:
        logger.debug(f"Initializing BigQuery backend for project: {self.project}")
        try:
            from google.cloud import bigquery

            self.client = bigquery.Client(project=self.project)
        except ImportError as e:
            raise M3InitializationError(
                "google-cloud-bigquery package not installed", details=str(e)
            ) from e
        except Exception as e:
            raise M3InitializationError(
                "BigQuery client initialization failed", details=str(e)
            ) from e

    def execute(self, operation: str) -> str:
        if not self.client:
            raise M3ValidationError("BigQuery backend not initialized")
        try:
            from google.cloud import bigquery

            job_config = bigquery.QueryJobConfig()
            query_job = self.client.query(operation, job_config=job_config)
            dataframe = query_job.to_dataframe()
            return self._format_result(dataframe)
        except Exception as e:
            raise M3ValidationError(f"BigQuery execution failed: {e}") from e

    def _format_result(self, dataframe: pd.DataFrame) -> str:
        if dataframe.empty:
            return "No results found"
        if len(dataframe) > 50:
            result = dataframe.head(50).to_string(index=False)
            result += f"\n... ({len(dataframe)} total rows, showing first 50)"
        else:
            result = dataframe.to_string(index=False)
        return result

    def teardown(self) -> None:
        self.client = None

    def __getstate__(self) -> dict:
        state = super().__getstate__()
        state["client"] = None
        return state

    def __setstate__(self, state: dict) -> None:
        super().__setstate__(state)
        self.client = None
