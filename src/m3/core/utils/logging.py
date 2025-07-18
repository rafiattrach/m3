import logging

from beartype import beartype
from beartype.typing import Optional


@beartype
def setup_logging(
    level: str = "INFO",
    force: bool = False,
    format_str: Optional[str] = None,
    datefmt: Optional[str] = None,
) -> None:  # pragma: no cover
    root = logging.getLogger()
    effective_format = (
        format_str or "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    )
    effective_datefmt = datefmt or "%Y-%m-%d %H:%M:%S"

    if force or not root.handlers:
        logging.basicConfig(
            level=level,
            format=effective_format,
            datefmt=effective_datefmt,
        )
    else:
        root.setLevel(level)
