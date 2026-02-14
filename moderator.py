"""
Moderator for inputs (Method Cards) before they are written to the database.
Validates schema, length, and basic quality so we don't store junk or abuse.
"""
from __future__ import annotations

from typing import Any

from utils import get_logger

logger = get_logger(__name__)

# Limits
MAX_TASK_INTENT = 2000
MAX_PLAN = 5000
MAX_CONTEXT = 1000
MIN_TASK_INTENT_LEN = 1


def moderate_card(card: dict[str, Any]) -> bool:
    """
    Return True if the Method Card is OK to save to the database.
    Checks: non-empty task_intent, length limits, no obvious spam (repeated chars).
    """
    if not card:
        logger.warning("moderate_card: empty card rejected")
        return False
    task = (card.get("task_intent") or "").strip()
    if len(task) < MIN_TASK_INTENT_LEN:
        logger.warning("moderate_card: task_intent empty or too short")
        return False
    if len(task) > MAX_TASK_INTENT:
        logger.warning("moderate_card: task_intent too long (%d)", len(task))
        return False
    plan = str(card.get("plan") or "")
    if len(plan) > MAX_PLAN:
        logger.warning("moderate_card: plan too long (%d)", len(plan))
        return False
    context = str(card.get("context") or "")
    if len(context) > MAX_CONTEXT:
        logger.warning("moderate_card: context too long (%d)", len(context))
        return False
    # Reject obvious spam: same char repeated for most of task
    if len(task) >= 10 and task.count(task[0]) >= len(task) * 0.9:
        logger.warning("moderate_card: task_intent looks like spam (repeated char)")
        return False
    logger.debug("moderate_card: passed")
    return True
