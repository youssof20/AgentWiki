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
# LLM and run timeouts (seconds). Env: LLM_TIMEOUT, RUN_DEMO_TIMEOUT
LLM_TIMEOUT = max(15, int(os.getenv("LLM_TIMEOUT") or "45"))
RUN_DEMO_TIMEOUT = max(60, int(os.getenv("RUN_DEMO_TIMEOUT") or "120"))


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


def get_langfuse():
    """Return Langfuse client or None if not configured. Demo must not crash if keys missing."""
    _log = get_logger("utils")
    pk = getenv("LANGFUSE_PUBLIC_KEY")
    sk = getenv("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        _log.debug("Langfuse: missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")
        return None
    host = getenv("LANGFUSE_BASE_URL") or getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com"
    try:
        from langfuse import Langfuse
        client = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=host.rstrip("/"),
            debug=getenv("LANGFUSE_DEBUG", "").lower() in ("1", "true", "yes"),
        )
        _log.info("Langfuse: initialized, host=%s", host)
        if getenv("LANGFUSE_AUTH_CHECK", "").lower() in ("1", "true", "yes"):
            try:
                client.auth_check()
                _log.info("Langfuse: auth_check OK")
            except Exception as auth_err:
                _log.warning("Langfuse: auth_check failed: %s", auth_err)
        return client
    except Exception as e:
        _log.warning("Langfuse: init failed: %s", e)
        return None
