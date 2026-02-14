"""
LLM logic, prompt building, planning using retrieved Method Cards. Static vs Agentwiki run.
"""
from __future__ import annotations

import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from memory import get_recent_cards, search_cards
from utils import get_langfuse, getenv, get_logger, LLM_TIMEOUT

logger = get_logger(__name__)


def _trace_generation(name: str, model: str, messages: list, output: str) -> None:
    """Record one LLM call in Langfuse if configured."""
    lf = get_langfuse()
    if not lf:
        return
    try:
        with lf.start_as_current_observation(as_type="generation", name=name, model=model) as gen:
            gen.update(input=messages, output=output)
    except Exception:
        pass


def llm_completion(system_prompt: str, user_input: str) -> str:
    """
    Single LLM call. Groq primary; fallback OpenRouter, Mistral, Gemini.
    Returns empty string on failure. Never raises.
    """
    messages = [
        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
        {"role": "user", "content": user_input or ""},
    ]
    # 1. Groq
    api_key = getenv("GROQ_API_KEY")
    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key, timeout=LLM_TIMEOUT)
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            _trace_generation("agent", "llama-3.3-70b-versatile", messages, out)
            logger.info("LLM: Groq OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: Groq failed: %s", e)
    # 2. OpenRouter
    api_key = getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=LLM_TIMEOUT)
            r = client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            _trace_generation("agent", "meta-llama/llama-3.3-70b-instruct", messages, out)
            logger.info("LLM: OpenRouter OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: OpenRouter failed: %s", e)
    # 3. Mistral
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
            _trace_generation("agent", "mistral-small", messages, out)
            logger.info("LLM: Mistral OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: Mistral failed: %s", e)
    # 4. Gemini
    api_key = getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=messages[0]["content"])
            r = model.generate_content(messages[1]["content"])
            out = (r.text or "").strip()
            _trace_generation("agent", "gemini-2.0-flash", messages, out)
            logger.info("LLM: Gemini OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: Gemini failed: %s", e)
    logger.error("LLM: all providers failed, returning empty")
    return ""


def _get_cards_for_task(task_intent: str, top_n: int = 3) -> list[dict]:
    """Retrieve best-rated playbooks for task (upvotes + score). Capped to avoid prompt overflow."""
    cards = search_cards(task_intent, top_n=top_n)
    if not cards:
        cards = get_recent_cards(top_n=min(2, top_n))
    return cards


def build_system_prompt(use_agentwiki: bool, task_intent: str, cards_out: list | None = None) -> str:
    """Build system prompt; if use_agentwiki, include best-rated playbooks. Sum up do's and don'ts (capped)."""
    base = "You are a precise assistant. Answer the user's task clearly and completely. Be concise."
    if not use_agentwiki:
        return base
    cards = _get_cards_for_task(task_intent, top_n=3)
    if cards_out is not None:
        cards_out.clear()
        cards_out.extend(cards)
    if not cards:
        logger.info("build_system_prompt: no playbooks found, using base prompt")
        return base
    logger.info("build_system_prompt: using %d best-rated playbooks (upvotes+score)", len(cards))
    parts = [base, "\n\n## Best-rated playbooks from Agentwiki (what to do / what not to do):"]
    for i, c in enumerate(cards, 1):
        intent = (c.get("task_intent") or "")[:200]
        plan = (c.get("plan") or "")[:300]
        mistakes = (c.get("mistakes") or "")[:200]
        fixes = (c.get("fixes") or "")[:200]
        score = c.get("outcome_score", 0)
        up = c.get("upvotes", 0)
        parts.append(f"\n--- Playbook {i} (score {score}, ↑{up}) ---\nTask: {intent}\nPlan: {plan}\nAvoid: {mistakes}\nDo: {fixes}")
    parts.append("\nUse the best of the above; avoid the mistakes. Keep your plan within these guidelines.")
    return "\n".join(parts)


def run_static(task: str) -> dict[str, Any]:
    """
    Run agent without Agentwiki: one LLM call, no retrieval.
    Returns dict: output, plan, retry_count, time_seconds, score (0 until evaluated).
    """
    logger.info("run_static: task_len=%d", len(task or ""))
    start = time.perf_counter()
    system_prompt = build_system_prompt(use_agentwiki=False, task_intent=task)
    output = llm_completion(system_prompt=system_prompt, user_input=task)
    elapsed = time.perf_counter() - start
    logger.info("run_static: done in %.2fs, output_len=%d", elapsed, len(output or ""))
    return {
        "output": output or "(No response)",
        "plan": "Single direct response (no playbooks).",
        "retry_count": 0,
        "time_seconds": round(elapsed, 2),
        "score": None,
        "cards_used": 0,
    }


def run_agentwiki(task: str, top_n: int = 3) -> dict[str, Any]:
    """
    Run agent with Agentwiki: find best-rated playbooks, sum do's/don'ts, execute. Returns card IDs used for upvote.
    """
    logger.info("run_agentwiki: start task_len=%d top_n=%d", len(task or ""), top_n)
    start = time.perf_counter()
    cards_used: list[dict] = []
    system_prompt = build_system_prompt(use_agentwiki=True, task_intent=task, cards_out=cards_used)
    output = llm_completion(system_prompt=system_prompt, user_input=task)
    elapsed = time.perf_counter() - start
    cards_used_ids = [c.get("id") for c in cards_used if c.get("id")]
    logger.info("run_agentwiki: done in %.2fs cards_used=%d output_len=%d ids=%s", elapsed, len(cards_used), len(output or ""), cards_used_ids[:3] if cards_used_ids else [])
    return {
        "output": output or "(No response)",
        "plan": "Plan from best-rated playbooks." if cards_used else "No playbooks; direct response.",
        "retry_count": 0,
        "time_seconds": round(elapsed, 2),
        "score": None,
        "cards_used": len(cards_used),
        "cards_used_ids": cards_used_ids,
    }
