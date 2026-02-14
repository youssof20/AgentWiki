"""
Score runs (LLM-as-judge or rubric). Write back improved Method Cards.
"""
from __future__ import annotations

from typing import Any

from memory import method_card as build_card, save_card
from utils import get_logger

logger = get_logger(__name__)


def score_outcome(task_intent: str, plan: str, output: str, retry_count: int = 0) -> float:
    """
    Score outcome 0–10 using LLM-as-judge. Returns 0 on failure.
    Criteria: relevance, completeness, correctness, fewer retries = better.
    """
    try:
        from agent import llm_completion
    except Exception:
        return 0.0
    prompt = f"""You are a judge. Score this agent run from 0 to 10 (one number only).

Task: {task_intent[:500]}
Plan used: {plan[:500]}
Agent output: {output[:800]}
Retries: {retry_count} (fewer is better)

Consider: Did the output address the task? Is it complete and correct? Fewer retries = better.
Reply with ONLY a single number between 0 and 10, e.g. 7"""
    try:
        reply = llm_completion(
            system_prompt="You output only a number 0-10. No explanation.",
            user_input=prompt,
        )
        if not reply:
            logger.warning("score_outcome: empty LLM reply")
            return 0.0
        # Parse first number
        for part in reply.strip().replace(",", ".").split():
            try:
                v = float(part)
                if 0 <= v <= 10:
                    logger.info("score_outcome: score=%.1f", v)
                    return round(v, 1)
            except ValueError:
                continue
        logger.warning("score_outcome: could not parse number from %r", reply[:80])
        return 0.0
    except Exception as e:
        logger.warning("score_outcome failed: %s", e)
        return 0.0


def write_back_card(
    task_intent: str,
    context: str,
    plan: str,
    tool_calls: str | list,
    mistakes: str,
    fixes: str,
    outcome_score: float,
    tags: list[str] | None = None,
) -> bool:
    """Build and save a Method Card from a completed run."""
    card = build_card(
        task_intent=task_intent,
        context=context,
        plan=plan,
        tool_calls=tool_calls,
        mistakes=mistakes,
        fixes=fixes,
        outcome_score=outcome_score,
        tags=tags or [],
    )
    ok = save_card(card)
    logger.info("write_back_card: saved=%s, score=%.1f", ok, outcome_score)
    return ok
