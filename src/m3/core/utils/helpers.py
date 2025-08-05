import logging
import os

from beartype import beartype

from m3.core.config import M3Config

logger = logging.getLogger(__name__)


@beartype
def get_config(env_override: bool = True) -> M3Config:
    env_vars = os.environ.copy() if env_override else {}
    config = M3Config(env_vars=env_vars)
    return config
