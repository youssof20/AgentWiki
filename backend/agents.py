"""
Agent sign-up: register agents so they can use the library. Stored in ClickHouse or local JSON.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import get_logger, new_id

logger = get_logger(__name__)

AGENT_REGISTRATIONS_JSON = Path(__file__).resolve().parent / "agent_registrations.json"

CLICKHOUSE_AGENT_REGISTRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS agent_registrations (
    id String,
    agent_name String,
    team_name String,
    email String,
    created_at String
) ENGINE = MergeTree()
ORDER BY (created_at, id)
"""


def _get_client():
    """ClickHouse client or None."""
    from memory import get_clickhouse_client
    return get_clickhouse_client()


def _ensure_agent_registrations_table(client) -> bool:
    """Create agent_registrations table if not exists."""
    try:
        client.command(CLICKHOUSE_AGENT_REGISTRATIONS_SQL.strip())
        logger.info("ClickHouse: agent_registrations table ensured")
        return True
    except Exception as e:
        logger.error("ClickHouse: ensure agent_registrations failed: %s", e)
        return False


def save_agent_registration(agent_name: str, team_name: str, email: str = "") -> str | None:
    """
    Register an agent. Returns agent_id (uuid) on success, None on failure.
    Stores in ClickHouse if configured; else local JSON.
    """
    agent_name = (agent_name or "").strip()
    team_name = (team_name or "").strip()
    email = (email or "").strip()
    if not agent_name:
        logger.warning("save_agent_registration: agent_name empty")
        return None
    agent_id = new_id()
    created_at = datetime.now(timezone.utc).isoformat()
    client = _get_client()
    if client:
        try:
            _ensure_agent_registrations_table(client)
            client.insert("agent_registrations", [[
                agent_id, agent_name, team_name, email, created_at,
            ]], column_names=["id", "agent_name", "team_name", "email", "created_at"])
            logger.info("Agent registered: %s (%s)", agent_name, agent_id[:8])
            return agent_id
        except Exception as e:
            logger.warning("ClickHouse agent_registrations insert failed: %s", e)
    # Local JSON fallback
    try:
        path = AGENT_REGISTRATIONS_JSON
        data = _load_json_registrations()
        data.append({
            "id": agent_id,
            "agent_name": agent_name,
            "team_name": team_name,
            "email": email,
            "created_at": created_at,
        })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Agent registered (JSON): %s (%s)", agent_name, agent_id[:8])
        return agent_id
    except Exception as e:
        logger.warning("agent_registrations JSON save failed: %s", e)
        return None


def _load_json_registrations() -> list[dict[str, Any]]:
    """Load agent registrations from local JSON."""
    if not AGENT_REGISTRATIONS_JSON.exists():
        return []
    try:
        with open(AGENT_REGISTRATIONS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_registered_agents(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent agent registrations (id, agent_name, team_name, email, created_at)."""
    client = _get_client()
    if client:
        try:
            r = client.query(
                f"SELECT id, agent_name, team_name, email, created_at FROM agent_registrations ORDER BY created_at DESC LIMIT {max(1, limit)}",
            )
            rows = r.result_rows
            names = [c[0] for c in r.column_names] if hasattr(r, "column_names") else ["id", "agent_name", "team_name", "email", "created_at"]
            return [dict(zip(names, row)) for row in rows]
        except Exception as e:
            logger.warning("get_registered_agents ClickHouse failed: %s", e)
    data = _load_json_registrations()
    data.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return data[:limit]


def get_agent_count() -> int:
    """Return total number of registered agents."""
    client = _get_client()
    if client:
        try:
            r = client.query("SELECT count() FROM agent_registrations")
            return int(r.result_rows[0][0]) if r.result_rows else 0
        except Exception:
            pass
    return len(_load_json_registrations())
