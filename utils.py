"""
Shared helpers for Agentwiki. Load env, safe getenv, IDs, logging.
"""
from dotenv import load_dotenv

load_dotenv()

import logging
import os
import sys
import uuid
from typing import Optional

# Default log level from env (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(level: Optional[str] = None) -> None:
    """Configure root logger for Agentwiki. Call once at app start."""
    lvl = (level or LOG_LEVEL).upper()
    numeric = getattr(logging, lvl, logging.INFO)
    logging.basicConfig(
        level=numeric,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for module name (e.g. __name__)."""
    return logging.getLogger(name)


def getenv(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return env var value or default. Never raises."""
    return os.getenv(key) or default


def new_id() -> str:
    """Return a new UUID string for Method Card id."""
    return str(uuid.uuid4())
