"""Lightweight logging utilities for ColtraDataAi.

Wraps the standard library ``logging`` module so the rest of the codebase
can call ``get_logger(__name__)`` and get a consistently configured logger
without repeating boilerplate.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_configured = False


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger.  The root logger is configured once on first call.

    *level* overrides the LOG_LEVEL environment variable if provided.
    """
    _ensure_root_configured(level)
    return logging.getLogger(name)


def _ensure_root_configured(level: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return

    effective_level = level or os.getenv("LOG_LEVEL", "INFO")
    numeric = getattr(logging, effective_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(numeric)
    if not root.handlers:
        root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "botocore", "boto3", "streamlit"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
