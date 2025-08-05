import logging
import sqlite3

import pandas as pd
from beartype import beartype
from beartype.typing import Any, Dict

from m3.core.tool.backend.base import BackendBase
from m3.core.utils.exceptions import M3InitializationError, M3ValidationError

logger = logging.getLogger(__name__)


@beartype
class SQLiteBackend(BackendBase):
    def __init__(self, path: str) -> None:
        self.path = path
        self.connection: sqlite3.Connection | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path}

    @classmethod
    def from_dict(cls, params: Dict[str, Any]) -> "SQLiteBackend":
        try:
            return cls(path=params["path"])
        except KeyError as e:
            raise ValueError(f"Missing required param: {e}") from e

    def initialize(self) -> None:
        logger.debug(f"Initializing SQLite backend at path: {self.path}")
        try:
            self.connection = sqlite3.connect(self.path)
        except sqlite3.Error as e:
            raise M3InitializationError(
                f"SQLite connection failed for path {self.path}", details=str(e)
            ) from e

    def execute(self, operation: str) -> str:
        if not self.connection:
            raise M3ValidationError("SQLite backend not initialized")
        try:
            dataframe = pd.read_sql_query(operation, self.connection)
            return self._format_result(dataframe)
        except sqlite3.Error as e:
            raise M3ValidationError(f"SQLite execution failed: {e}") from e

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
        if self.connection:
            self.connection.close()
            self.connection = None

    def __getstate__(self) -> dict:
        state = super().__getstate__()
        state["connection"] = None
        return state

    def __setstate__(self, state: dict) -> None:
        super().__setstate__(state)
        self.connection = None
