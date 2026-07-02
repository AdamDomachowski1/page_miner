"""Logging: concise console output plus a full-detail rotating log file."""

import logging
from logging.handlers import RotatingFileHandler

from page_miner.config import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOGS_DIR,
)

_CONSOLE_FORMAT = "%(levelname)s | %(message)s"
_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(verbose: bool = False) -> None:
    """Attach a console handler and a rotating file handler to the root logger.

    The console stays concise (INFO+, or DEBUG with verbose=True); the file
    always keeps full DEBUG detail for post-mortem debugging.
    Safe to call more than once — handlers are only attached on the first call.
    """
    root = logging.getLogger()
    if root.handlers:  # already configured
        return

    LOGS_DIR.mkdir(exist_ok=True)
    root.setLevel(logging.DEBUG)  # let each handler decide what to show

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else LOG_LEVEL)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers; we log requests ourselves.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
