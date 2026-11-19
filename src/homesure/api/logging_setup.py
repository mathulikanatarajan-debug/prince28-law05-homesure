"""Configure application logging."""

import logging

from homesure.config import get_settings


def setup_logging() -> None:
    """Set the logging level and format."""
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
