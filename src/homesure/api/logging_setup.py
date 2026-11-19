"""Configure application logging."""

import logging

from homesure.config import Settings, get_settings


def setup_logging(settings: Settings | None = None) -> None:
    """Set the logging level and format."""
    settings = settings or get_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
