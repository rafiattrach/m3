import logging

from beartype.typing import Dict, Type

from m3.core.tool.backend.backends.bigquery import BigQueryBackend
from m3.core.tool.backend.backends.sqlite import SQLiteBackend
from m3.core.tool.backend.base import BackendBase

logger = logging.getLogger(__name__)

BACKEND_REGISTRY: Dict[str, Type[BackendBase]] = {
    "sqlite": SQLiteBackend,
    "bigquery": BigQueryBackend,
}
