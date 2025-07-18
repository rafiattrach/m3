import logging
import os

from beartype import beartype

from m3.core.utils.exceptions import M3ValidationError
from m3.core.utils.logging import setup_logging
from m3.m3 import M3

logger = logging.getLogger(__name__)


@beartype
def main() -> None:
    setup_logging(level=os.getenv("M3_LOG_LEVEL", "INFO"))
    logger.info("Starting M3 MCP server...")

    config_path = os.getenv("M3_CONFIG_PATH")
    if not config_path:
        raise M3ValidationError(
            "M3_CONFIG_PATH env var not set. Generate a config via CLI (e.g., 'm3 build --config-path m3_pipeline.json') and set it."
        )

    try:
        m3 = M3.load(config_path)
        logger.info(f"Loaded pipeline from config: {config_path}")
    except (FileNotFoundError, M3ValidationError) as e:
        logger.error(f"Failed to load config: {e}")
        raise

    m3.build()
    m3.run()


if __name__ == "__main__":
    try:
        main()
    except M3ValidationError as e:
        logger.error(
            f"Validation failed: {e}. Generate and set M3_CONFIG_PATH via CLI."
        )
        raise
    except Exception as e:
        logger.error(f"Failed to start M3 server: {e}")
        raise
