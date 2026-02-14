"""
Score runs (LLM-as-judge critic). Write back improved Method Cards.
Critic: OpenAI primary, then OpenRouter, then Mistral — separate from agent LLM for unbiased ratings.
"""
from __future__ import annotations

from typing import Any

from memory import method_card as build_card, save_card
from moderator import moderate_card
from utils import get_langfuse, get_logger, getenv, LLM_TIMEOUT

logger = get_logger(__name__)


def _trace_critic(model: str, messages: list, output: str) -> None:
    """Record critic LLM call in Langfuse if configured."""
    lf = get_langfuse()
    if not lf:
        return
    try:
        with lf.start_as_current_observation(as_type="generation", name="critic", model=model) as gen:
            gen.update(input=messages, output=output)
    except Exception:
        pass


def critic_completion(system_prompt: str, user_input: str) -> str:
    """
    Critic LLM: OpenAI first, then OpenRouter, then Mistral.
    Used only for scoring (not for agent responses) so ratings are unbiased.
    Returns empty string on failure.
    """
    messages = [
        {"role": "system", "content": system_prompt or "You are a strict judge. Output only a number 0-10."},
        {"role": "user", "content": user_input or ""},
    ]
    api_key = getenv("OPENAI_API_KEY") or getenv("OPENAI_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=LLM_TIMEOUT)
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            _trace_critic("gpt-4o-mini", messages, out)
            logger.info("Critic: OpenAI OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("Critic: OpenAI failed: %s", e)
    api_key = getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=LLM_TIMEOUT)
            r = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            _trace_critic("openai/gpt-4o-mini", messages, out)
            logger.info("Critic: OpenRouter OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("Critic: OpenRouter failed: %s", e)
    api_key = getenv("MISTRAL_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1", timeout=LLM_TIMEOUT)
            r = client.chat.completions.create(
                model="mistral-small",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            _trace_critic("mistral-small", messages, out)
            logger.info("Critic: Mistral OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("Critic: Mistral failed: %s", e)
    logger.warning("Critic: no provider available, falling back to agent LLM")
    try:
        from agent import llm_completion
        return llm_completion(system_prompt=system_prompt, user_input=user_input)
    except Exception:
        return ""


def score_outcome(task_intent: str, plan: str, output: str, retry_count: int = 0, used_playbooks: bool = False) -> float:
    """
    Score outcome 0–10 using critic LLM (OpenAI → OpenRouter → Mistral).
    Stricter prompt so we get real spread (not always 9). If used_playbooks=True, critic rewards use of library playbooks. Returns 0 on failure.
    """
    playbook_note = ""
    if used_playbooks:
        playbook_note = "\n\nThis run used Agentwiki playbooks from the shared library. If the plan is structured and the output is at least as good as a run without playbooks, you may add up to 1.0 for effective use of shared playbooks (max 10)."
    prompt = f"""You are a strict critic. Score this agent run from 0 to 10. Be discriminating: 5 = adequate, 7 = good, 9–10 only for exceptional, complete, correct answers. Do not default to high scores.

Task: {task_intent[:500]}
Plan used: {plan[:500]}
Agent output: {output[:800]}
Retries: {retry_count} (fewer is better)
{playbook_note}

Criteria: Does the output fully address the task? Is it complete and correct? Any hallucinations or vagueness? Fewer retries = better.
Reply with ONLY a single number between 0 and 10 (e.g. 6 or 7.5)."""
    try:
        reply = critic_completion(
            system_prompt="You are a strict judge. Output only one number 0–10. No explanation. Be discriminating.",
            user_input=prompt,
        )
        if not reply:
            logger.warning("score_outcome: empty critic reply")
            return 0.0
        for part in reply.strip().replace(",", ".").split():
            try:
                v = float(part)
                if 0 <= v <= 10:
                    logger.info("score_outcome: critic reply=%r -> score=%.1f", reply.strip()[:50], v)
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
    if not moderate_card(card):
        logger.warning("write_back_card: card rejected by moderator")
        return False
    ok = save_card(card)
    logger.info("write_back_card: saved=%s, score=%.1f", ok, outcome_score)
    return ok
