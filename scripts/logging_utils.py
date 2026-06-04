"""Shared console logging setup for StuArchive scripts."""

from __future__ import annotations

import logging
import sys
import time


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class UtcFormatter(logging.Formatter):
    converter = time.gmtime


def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(UtcFormatter(LOG_FORMAT, DATE_FORMAT))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
