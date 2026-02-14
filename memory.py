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
    "mistakes", "fixes", "outcome_score", "upvotes", "tags",
)


def method_card(
    task_intent: str,
    context: str = "",
    plan: str = "",
    tool_calls: str | list = "",
    mistakes: str = "",
    fixes: str = "",
    outcome_score: float | int = 0.0,
    upvotes: int = 0,
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
        "upvotes": int(upvotes),
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


# SQL to create method_cards table. upvotes = success count (Reddit/ELO-like).
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
    upvotes Int64 DEFAULT 0,
    tags String
) ENGINE = MergeTree()
ORDER BY (timestamp, id)
"""


def ensure_method_cards_table(client) -> bool:
    """Create method_cards table if it does not exist; add upvotes column if missing. Returns True on success."""
    try:
        client.command(CLICKHOUSE_CREATE_TABLE_SQL.strip())
        logger.info("ClickHouse: method_cards table ensured")
        try:
            client.command("ALTER TABLE method_cards ADD COLUMN IF NOT EXISTS upvotes Int64 DEFAULT 0")
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error("ClickHouse: failed to ensure method_cards table: %s", e)
        return False


def save_card(card: dict[str, Any]) -> bool:
    """Store one Method Card. ClickHouse if configured; else local JSON."""
    card_id = card.get("id", "")[:8]
    upvotes = int(card.get("upvotes", 0))
    client = get_clickhouse_client()
    if client:
        try:
            ensure_method_cards_table(client)
            tags_str = ",".join(card.get("tags") or [])
            client.insert("method_cards", [[
                card.get("id"), card.get("timestamp"), card.get("task_intent"),
                card.get("context"), card.get("plan"), str(card.get("tool_calls", "")),
                card.get("mistakes"), card.get("fixes"), card.get("outcome_score"),
                upvotes, tags_str,
            ]], column_names=[
                "id", "timestamp", "task_intent", "context", "plan", "tool_calls",
                "mistakes", "fixes", "outcome_score", "upvotes", "tags",
            ])
            logger.info("Saved Method Card %s to ClickHouse (upvotes=%d)", card_id, upvotes)
            return True
        except Exception as e:
            logger.warning("ClickHouse insert failed for card %s: %s", card_id, e)
    logger.info("Using local method_cards.json (ClickHouse unavailable)")
    cards = _load_json_cards()
    cards.append(card)
    if len(cards) > 100:
        cards = sorted(cards, key=lambda c: c.get("timestamp", ""), reverse=True)[:100]
    return _save_json_cards(cards)


def upvote_card(card_id: str) -> bool:
    """Increment upvotes for a Method Card (agent upvotes on success). Returns True if updated."""
    if not (card_id or str(card_id).strip()):
        logger.warning("upvote_card: empty card_id")
        return False
    client = get_clickhouse_client()
    if client:
        try:
            ensure_method_cards_table(client)
            safe_id = str(card_id).replace("'", "''")
            client.command(f"ALTER TABLE method_cards UPDATE upvotes = upvotes + 1 WHERE id = '{safe_id}'")
            logger.info("upvote_card: incremented upvotes for card %s (ClickHouse)", card_id[:8])
            return True
        except Exception as e:
            logger.warning("upvote_card ClickHouse failed for %s: %s", card_id[:8], e)
    cards = _load_json_cards()
    for c in cards:
        if c.get("id") == card_id:
            c["upvotes"] = int(c.get("upvotes", 0)) + 1
            _save_json_cards(cards)
            logger.info("upvote_card: incremented upvotes for card %s (JSON)", card_id[:8])
            return True
    logger.warning("upvote_card: card %s not found", card_id[:8])
    return False


def _clickhouse_select_with_upvotes_fallback(client, order_by: str, limit: int) -> list[dict[str, Any]]:
    """Query method_cards; if upvotes column missing (e.g. old table), retry without it and default upvotes=0."""
    cols_with = "id, timestamp, task_intent, context, plan, tool_calls, mistakes, fixes, outcome_score, upvotes, tags"
    cols_without = "id, timestamp, task_intent, context, plan, tool_calls, mistakes, fixes, outcome_score, tags"
    order_without = "outcome_score DESC, timestamp DESC"
    for cols, order in [(cols_with, order_by), (cols_without, order_without)]:
        try:
            r = client.query(f"SELECT {cols} FROM method_cards ORDER BY {order} LIMIT {limit}")
            rows = r.result_rows
            col_names = [c[0] for c in r.column_names] if hasattr(r, "column_names") else []
            if not col_names and rows:
                col_names = [x.strip() for x in cols.split(",")]
            out = []
            for row in rows:
                d = dict(zip(col_names, row)) if col_names else {}
                d.setdefault("upvotes", 0)
                if isinstance(d.get("tags"), str):
                    d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]
                out.append(d)
            return out
        except Exception as e:
            if "upvotes" in str(e) or "47" in str(e) or "UNKNOWN_IDENTIFIER" in str(e):
                logger.info("ClickHouse: retrying without upvotes column")
                continue
            raise
    return []


def search_cards(query: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Search Method Cards by task_intent/plan/tags; return top N by relevance (score + recency)."""
    query_lower = (query or "").strip().lower()
    if not query_lower:
        return []

    client = get_clickhouse_client()
    if client:
        try:
            rows = _clickhouse_select_with_upvotes_fallback(
                client, "upvotes DESC, outcome_score DESC, timestamp DESC", 50,
            )
            out = []
            for d in rows:
                text = " ".join([str(d.get("task_intent", "")), str(d.get("plan", "")), ",".join(d.get("tags") or [])]).lower()
                if query_lower in text:
                    out.append(d)
            out = out[:top_n]
            logger.info("search_cards ClickHouse: query=%r, found=%d", query[:50], len(out))
            return out
        except Exception as e:
            logger.warning("search_cards ClickHouse failed: %s", e)
    # Local JSON: keyword match; sort by upvotes then outcome_score
    cards = _load_json_cards()
    scored = []
    for c in cards:
        text = " ".join([
            str(c.get("task_intent", "")),
            str(c.get("plan", "")),
            ",".join(c.get("tags") or []),
        ]).lower()
        if query_lower in text:
            up = int(c.get("upvotes", 0))
            score = float(c.get("outcome_score", 0))
            ts = c.get("timestamp", "")
            scored.append((up, score, ts, c))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    out = [c for _, _, _, c in scored[:top_n]]
    logger.info("search_cards JSON: query=%r, found=%d", query[:50], len(out))
    return out


def get_recent_cards(top_n: int = 5) -> list[dict[str, Any]]:
    """Return top Method Cards by upvotes then recency. Falls back to query without upvotes if column missing."""
    client = get_clickhouse_client()
    if client:
        try:
            n = max(1, int(top_n))
            out = _clickhouse_select_with_upvotes_fallback(
                client, "upvotes DESC, timestamp DESC", n,
            )
            logger.info("get_recent_cards ClickHouse: top_n=%d, found=%d", top_n, len(out))
            return out[:top_n]
        except Exception as e:
            logger.warning("get_recent_cards ClickHouse failed: %s", e)
    cards = _load_json_cards()
    for c in cards:
        c.setdefault("upvotes", 0)
    cards.sort(key=lambda c: (int(c.get("upvotes", 0)), c.get("timestamp", "")), reverse=True)
    out = cards[:top_n]
    logger.info("get_recent_cards JSON: top_n=%d, found=%d", top_n, len(out))
    return out


# Demo templates: always ensure these exist (for hackathon demo)
DEMO_TEMPLATES = [
        {
            "task_intent": "Explain recursion in 3 sentences for a beginner",
            "plan": "Output exactly 3 sentences. Sentence 1: Define recursion (a function that calls itself). Sentence 2: One simple example (e.g. factorial or countdown). Sentence 3: One real-world analogy (e.g. Russian dolls or folders). Use plain language; no jargon like 'base case' or 'stack'.",
            "mistakes": "More than 3 sentences; technical jargon; vague or abstract.",
            "fixes": "Exactly 3 sentences. Use 'calls itself'. Give a concrete example and a clear analogy.",
            "outcome_score": 8.5,
            "upvotes": 3,
            "tags": ["explanation", "recursion", "beginner", "sentences"],
        },
        {
            "task_intent": "Summarize a paragraph in 2 or 3 sentences",
            "plan": "Identify the main idea in one sentence. Add 1–2 supporting points in the next sentence(s). Use your own words. Do not copy phrases. Total: 2–3 sentences only.",
            "mistakes": "Copy-pasting; adding new ideas not in the text; writing more than 3 sentences.",
            "fixes": "Paraphrase. Only what is in the paragraph. Keep it short.",
            "outcome_score": 8.0,
            "upvotes": 2,
            "tags": ["summary", "writing", "paragraph"],
        },
        {
            "task_intent": "Write a hello-world program",
            "plan": "One minimal file. One print or echo statement. One line saying how to run it (e.g. 'Run: python file.py'). No extra setup or comments unless one line.",
            "mistakes": "Multiple files; complex setup; no run instruction.",
            "fixes": "Single file, one command to run, minimal code.",
            "outcome_score": 8.0,
            "upvotes": 2,
            "tags": ["code", "hello-world", "beginner"],
        },
        {
            "task_intent": "Explain a concept in simple terms",
            "plan": "Start with a one-sentence definition. Then one short example. Then one everyday analogy. Use simple words. Avoid jargon; if you use a term, explain it.",
            "mistakes": "Assuming prior knowledge; long paragraphs; no example or analogy.",
            "fixes": "Define, example, analogy. Short sentences. Plain language.",
            "outcome_score": 7.5,
            "upvotes": 1,
            "tags": ["explanation", "simple", "beginner"],
        },
        {
            "task_intent": "Give step-by-step instructions",
            "plan": "Number the steps. One action per step. Start with what you need. End with how to verify. Keep each step to one short sentence.",
            "mistakes": "Combining steps; skipping prerequisites; vague verbs.",
            "fixes": "Numbered list. One clear action per step. Include 'you need' and 'to verify'.",
            "outcome_score": 7.5,
            "upvotes": 1,
            "tags": ["instructions", "steps", "howto"],
        },
    ]


def _get_existing_task_intents() -> set[str]:
    """Return set of task_intent strings in the store (for ensure_demo_templates)."""
    out = set()
    client = get_clickhouse_client()
    if client:
        try:
            r = client.query("SELECT task_intent FROM method_cards")
            for row in (r.result_rows or []):
                if row and row[0]:
                    out.add(str(row[0]).strip())
        except Exception:
            pass
    for c in _load_json_cards():
        ti = (c.get("task_intent") or "").strip()
        if ti:
            out.add(ti)
    return out


def ensure_demo_templates() -> int:
    """Ensure all 5 demo methods exist (add any missing). Call on app load. Returns number added."""
    existing = _get_existing_task_intents()
    added = 0
    for t in DEMO_TEMPLATES:
        if (t["task_intent"] or "").strip() in existing:
            continue
        card = method_card(
            task_intent=t["task_intent"],
            plan=t["plan"],
            mistakes=t["mistakes"],
            fixes=t["fixes"],
            outcome_score=t["outcome_score"],
            upvotes=int(t.get("upvotes", 0)),
            tags=t.get("tags", []),
        )
        if save_card(card):
            added += 1
            existing.add((t["task_intent"] or "").strip())
    if added:
        logger.info("ensure_demo_templates: added %d missing demo methods", added)
    return added


def load_templates() -> int:
    """Seed or ensure demo methods. If store is empty, add all; else ensure_demo_templates (add missing only)."""
    existing = _get_existing_task_intents()
    if not existing:
        for t in DEMO_TEMPLATES:
            card = method_card(
                task_intent=t["task_intent"],
                plan=t["plan"],
                mistakes=t["mistakes"],
                fixes=t["fixes"],
                outcome_score=t["outcome_score"],
                upvotes=int(t.get("upvotes", 0)),
                tags=t.get("tags", []),
            )
            save_card(card)
        logger.info("load_templates: seeded %d demo methods", len(DEMO_TEMPLATES))
        return len(DEMO_TEMPLATES)
    return ensure_demo_templates()
