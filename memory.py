"""
Method Card store and search. ClickHouse only; fallback local JSON when ClickHouse unavailable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import getenv, get_logger, new_id

logger = get_logger(__name__)

# Method Card schema (strict). All cards must have these keys.
METHOD_CARD_KEYS = (
    "id", "timestamp", "task_intent", "context", "plan", "tool_calls",
    "mistakes", "fixes", "outcome_score", "tags",
)


def method_card(
    task_intent: str,
    context: str = "",
    plan: str = "",
    tool_calls: str | list = "",
    mistakes: str = "",
    fixes: str = "",
    outcome_score: float | int = 0.0,
    tags: list[str] | None = None,
    id_: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a Method Card dict with required schema. Does not write to store."""
    tags = tags or []
    tool_calls_str = json.dumps(tool_calls) if isinstance(tool_calls, list) else str(tool_calls)
    return {
        "id": id_ or new_id(),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "task_intent": task_intent,
        "context": context,
        "plan": plan,
        "tool_calls": tool_calls_str,
        "mistakes": mistakes,
        "fixes": fixes,
        "outcome_score": float(outcome_score),
        "tags": tags,
    }


def _json_path() -> Path:
    """Path to local Method Cards JSON file."""
    return Path(__file__).resolve().parent / "method_cards.json"


def _load_json_cards() -> list[dict[str, Any]]:
    """Load all cards from local JSON. Returns list; empty if file missing."""
    p = _json_path()
    if not p.exists():
        logger.debug("method_cards.json missing, returning []")
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        out = data if isinstance(data, list) else []
        logger.debug("Loaded %d cards from %s", len(out), p)
        return out
    except Exception as e:
        logger.warning("Failed to load JSON cards from %s: %s", p, e)
        return []


def _save_json_cards(cards: list[dict[str, Any]]) -> bool:
    """Write cards to local JSON. Returns True on success."""
    try:
        with open(_json_path(), "w", encoding="utf-8") as f:
            json.dump(cards, f, indent=2)
        logger.info("Saved %d cards to method_cards.json", len(cards))
        return True
    except Exception as e:
        logger.error("Failed to save JSON cards: %s", e)
        return False


def _parse_clickhouse_host(host: str) -> tuple[str, int]:
    """Extract hostname and port from CLICKHOUSE_HOST. Cloud expects hostname only + port 8443."""
    s = (host or "").strip()
    if not s:
        return "", 8443
    # Strip scheme
    for prefix in ("https://", "http://"):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    # Strip port if present (e.g. hostname:8443)
    if ":" in s:
        hostname, _, port_str = s.rpartition(":")
        try:
            return hostname.strip(), int(port_str)
        except ValueError:
            return s, 8443
    return s, 8443


def get_clickhouse_client():
    """Return ClickHouse client or None if unavailable. Does not create table."""
    raw_host = getenv("CLICKHOUSE_HOST")
    if not raw_host:
        return None
    hostname, port = _parse_clickhouse_host(raw_host)
    if not hostname:
        logger.warning("ClickHouse: CLICKHOUSE_HOST is empty after parsing")
        return None
    try:
        import clickhouse_connect
        port_env = getenv("CLICKHOUSE_PORT")
        if port_env is not None:
            try:
                port = int(port_env)
            except ValueError:
                pass
        client = clickhouse_connect.get_client(
            host=hostname,
            port=port,
            username=getenv("CLICKHOUSE_USER") or "default",
            password=getenv("CLICKHOUSE_PASSWORD") or "",
            secure=port == 8443,
        )
        return client
    except Exception as e:
        logger.warning("ClickHouse client failed: %s", e)
        return None


# SQL to create method_cards table. Timestamp as String for simple ISO storage.
CLICKHOUSE_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS method_cards (
    id String,
    timestamp String,
    task_intent String,
    context String,
    plan String,
    tool_calls String,
    mistakes String,
    fixes String,
    outcome_score Float64,
    tags String
) ENGINE = MergeTree()
ORDER BY (timestamp, id)
"""


def ensure_method_cards_table(client) -> bool:
    """Create method_cards table if it does not exist. Returns True on success."""
    try:
        client.command(CLICKHOUSE_CREATE_TABLE_SQL.strip())
        logger.info("ClickHouse: method_cards table ensured")
        return True
    except Exception as e:
        logger.error("ClickHouse: failed to ensure method_cards table: %s", e)
        return False


def save_card(card: dict[str, Any]) -> bool:
    """Store one Method Card. ClickHouse if configured; else local JSON."""
    card_id = card.get("id", "")[:8]
    client = get_clickhouse_client()
    if client:
        try:
            ensure_method_cards_table(client)
            tags_str = ",".join(card.get("tags") or [])
            client.insert("method_cards", [[
                card.get("id"), card.get("timestamp"), card.get("task_intent"),
                card.get("context"), card.get("plan"), str(card.get("tool_calls", "")),
                card.get("mistakes"), card.get("fixes"), card.get("outcome_score"),
                tags_str,
            ]], column_names=[
                "id", "timestamp", "task_intent", "context", "plan", "tool_calls",
                "mistakes", "fixes", "outcome_score", "tags",
            ])
            logger.info("Saved Method Card %s to ClickHouse", card_id)
            return True
        except Exception as e:
            logger.warning("ClickHouse insert failed for card %s: %s", card_id, e)
    logger.info("Using local method_cards.json (ClickHouse unavailable)")
    cards = _load_json_cards()
    cards.append(card)
    if len(cards) > 100:
        cards = sorted(cards, key=lambda c: c.get("timestamp", ""), reverse=True)[:100]
    return _save_json_cards(cards)


def search_cards(query: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Search Method Cards by task_intent/plan/tags; return top N by relevance (score + recency)."""
    query_lower = (query or "").strip().lower()
    if not query_lower:
        return []

    # ClickHouse: fetch recent, filter by query in Python (avoids dialect issues)
    client = get_clickhouse_client()
    if client:
        try:
            r = client.query(
                "SELECT id, timestamp, task_intent, context, plan, tool_calls, mistakes, fixes, outcome_score, tags "
                "FROM method_cards ORDER BY outcome_score DESC, timestamp DESC LIMIT 50",
            )
            rows = r.result_rows
            col_names = [c[0] for c in r.column_names] if hasattr(r, "column_names") else []
            if not col_names and rows:
                col_names = ["id", "timestamp", "task_intent", "context", "plan", "tool_calls", "mistakes", "fixes", "outcome_score", "tags"]
            out = []
            for row in rows:
                d = dict(zip(col_names, row)) if col_names else {}
                if isinstance(d.get("tags"), str):
                    d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
                text = " ".join([str(d.get("task_intent", "")), str(d.get("plan", "")), ",".join(d.get("tags") or [])]).lower()
                if query_lower in text:
                    out.append(d)
            out = out[:top_n]
            logger.debug("search_cards ClickHouse: query=%r, found=%d", query[:50], len(out))
            return out
        except Exception as e:
            logger.warning("search_cards ClickHouse failed: %s", e)
    # Local JSON: keyword match in task_intent, plan, tags
    cards = _load_json_cards()
    scored = []
    for c in cards:
        text = " ".join([
            str(c.get("task_intent", "")),
            str(c.get("plan", "")),
            ",".join(c.get("tags") or []),
        ]).lower()
        if query_lower in text:
            score = float(c.get("outcome_score", 0))
            ts = c.get("timestamp", "")
            scored.append((score, ts, c))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = [c for _, _, c in scored[:top_n]]
    logger.debug("search_cards JSON: query=%r, found=%d", query[:50], len(out))
    return out


def get_recent_cards(top_n: int = 5) -> list[dict[str, Any]]:
    """Return most recent Method Cards (when no search query). Used for cold start."""
    client = get_clickhouse_client()
    if client:
        try:
            n = max(1, int(top_n))
            r = client.query(
                f"SELECT id, timestamp, task_intent, context, plan, tool_calls, mistakes, fixes, outcome_score, tags "
                f"FROM method_cards ORDER BY timestamp DESC LIMIT {n}",
            )
            rows = r.result_rows
            col_names = getattr(r, "column_names", None)
            names = [c[0] for c in col_names] if col_names else ["id", "timestamp", "task_intent", "context", "plan", "tool_calls", "mistakes", "fixes", "outcome_score", "tags"]
            out = []
            for row in rows:
                d = dict(zip(names, row))
                if isinstance(d.get("tags"), str):
                    d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
                out.append(d)
            logger.debug("get_recent_cards ClickHouse: top_n=%d, found=%d", top_n, len(out))
            return out[:top_n]
        except Exception as e:
            logger.warning("get_recent_cards ClickHouse failed: %s", e)
    cards = _load_json_cards()
    cards.sort(key=lambda c: c.get("timestamp", ""), reverse=True)
    out = cards[:top_n]
    logger.debug("get_recent_cards JSON: top_n=%d, found=%d", top_n, len(out))
    return out
