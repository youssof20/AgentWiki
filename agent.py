"""
LLM logic, prompt building, planning using retrieved Method Cards. Static vs Agentwiki run.
"""
from __future__ import annotations

import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from memory import get_recent_cards, search_cards
from utils import getenv, get_logger

logger = get_logger(__name__)


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
            client = Groq(api_key=api_key)
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            logger.info("LLM: Groq OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: Groq failed: %s", e)
    # 2. OpenRouter
    api_key = getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            r = client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
            logger.info("LLM: OpenRouter OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: OpenRouter failed: %s", e)
    # 3. Mistral
    api_key = getenv("MISTRAL_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
            r = client.chat.completions.create(
                model="mistral-small",
                messages=messages,
            )
            out = (r.choices[0].message.content or "").strip()
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
            logger.info("LLM: Gemini OK, response length=%d", len(out))
            return out
        except Exception as e:
            logger.warning("LLM: Gemini failed: %s", e)
    logger.error("LLM: all providers failed, returning empty")
    return ""


def build_system_prompt(use_agentwiki: bool, task_intent: str) -> str:
    """Build system prompt; if use_agentwiki, include retrieved Method Cards (plan + avoid mistakes)."""
    base = "You are a precise assistant. Answer the user's task clearly and completely. Be concise."
    if not use_agentwiki:
        return base
    # Retrieve top playbooks
    cards = search_cards(task_intent, top_n=3)
    if not cards:
        cards = get_recent_cards(top_n=2)
    if not cards:
        logger.debug("No playbooks found for task, using base prompt")
        return base
    logger.info("Using %d playbooks for Agentwiki prompt", len(cards))
    parts = [base, "\n\n## Relevant playbooks from Agentwiki (use best methodology, avoid listed mistakes):"]
    for i, c in enumerate(cards, 1):
        intent = (c.get("task_intent") or "")[:200]
        plan = (c.get("plan") or "")[:300]
        mistakes = (c.get("mistakes") or "")[:200]
        fixes = (c.get("fixes") or "")[:200]
        score = c.get("outcome_score", 0)
        parts.append(f"\n--- Playbook {i} (score {score}) ---\nTask: {intent}\nPlan: {plan}\nMistakes to avoid: {mistakes}\nFixes: {fixes}")
    parts.append("\nCompose your plan using the best of the above; avoid the mistakes mentioned.")
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
    Run agent with Agentwiki: retrieve top N Method Cards, build plan, execute, return result.
    Does not evaluate or write back (app/evaluator does that).
    Returns dict: output, plan, retry_count, time_seconds, score (None), cards_used.
    """
    logger.info("run_agentwiki: task_len=%d, top_n=%d", len(task or ""), top_n)
    start = time.perf_counter()
    system_prompt = build_system_prompt(use_agentwiki=True, task_intent=task)
    output = llm_completion(system_prompt=system_prompt, user_input=task)
    elapsed = time.perf_counter() - start
    cards = search_cards(task, top_n=top_n)
    if not cards:
        cards = get_recent_cards(top_n=top_n)
    logger.info("run_agentwiki: done in %.2fs, cards_used=%d, output_len=%d", elapsed, len(cards), len(output or ""))
    return {
        "output": output or "(No response)",
        "plan": "Plan composed from Agentwiki playbooks." if cards else "No playbooks found; direct response.",
        "retry_count": 0,
        "time_seconds": round(elapsed, 2),
        "score": None,
        "cards_used": len(cards),
    }
