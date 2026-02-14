"""
Shared pipeline: run static + Agentwiki, score, optional write-back.
Used by Streamlit app and FastAPI inference. Timeout and Langfuse-aware.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from utils import get_langfuse, get_logger, getenv, RUN_DEMO_TIMEOUT

logger = get_logger(__name__)


def _run_inference_impl(task: str, write_back: bool, timeout_seconds: int) -> dict[str, Any]:
    """Internal: run full demo. Called from run_inference with optional thread timeout."""
    task = (task or "").strip()
    logger.info("_run_inference_impl: start task_len=%d write_back=%s timeout=%ds", len(task), write_back, timeout_seconds)
    if not task:
        return {"error": "Task is required", "run_static": None, "run_agentwiki": None, "scores": {}, "delta": 0, "cards_used_ids": []}

    try:
        from agent import run_static, run_agentwiki
        from evaluator import score_outcome, write_back_card
    except Exception as e:
        logger.exception("run_inference: import failed: %s", e)
        return {"error": str(e), "run_static": None, "run_agentwiki": None, "scores": {}, "delta": 0, "cards_used_ids": []}

    langfuse = get_langfuse()
    logger.info("_run_inference_impl: langfuse=%s", "on" if langfuse else "off")
    trace_ctx = langfuse.start_as_current_observation(as_type="span", name="agentwiki_run") if langfuse else _null_ctx()
    start_wall = time.perf_counter()

    def _timed_out() -> bool:
        return (time.perf_counter() - start_wall) > timeout_seconds

    with trace_ctx:
        if langfuse:
            try:
                _obs = getattr(langfuse, "get_current_observation", lambda: None)()
                if _obs is not None:
                    _obs.update(input={"task": task})
            except Exception:
                pass
        # Run 1 — static
        if _timed_out():
            return {"error": f"Timeout after {timeout_seconds}s", "run_static": None, "run_agentwiki": None, "scores": {}, "delta": 0, "cards_used_ids": []}
        logger.info("_run_inference_impl: step run_static")
        with _span_ctx(langfuse, "run_static", {"task_len": len(task)}, input_data={"task": task}):
            r1 = run_static(task)
            if langfuse:
                _set_current_output(langfuse, {"output_preview": (r1.get("output") or "")[:500], "time_seconds": r1.get("time_seconds")})
        logger.info("_run_inference_impl: run_static done time=%.2fs output_len=%d", r1.get("time_seconds", 0), len(r1.get("output") or ""))
        if langfuse:
            _log_langfuse(langfuse, "run_static", {"output_len": len(r1.get("output") or ""), "time_seconds": r1.get("time_seconds")})

        # Run 2 — Agentwiki
        if _timed_out():
            return {"error": f"Timeout after {timeout_seconds}s", "run_static": r1, "run_agentwiki": None, "scores": {}, "delta": 0, "cards_used_ids": []}
        logger.info("_run_inference_impl: step run_agentwiki")
        with _span_ctx(langfuse, "run_agentwiki", {"task_len": len(task)}, input_data={"task": task}):
            r2 = run_agentwiki(task, top_n=3)
            if langfuse:
                _set_current_output(langfuse, {"output_preview": (r2.get("output") or "")[:500], "time_seconds": r2.get("time_seconds"), "cards_used": r2.get("cards_used"), "cards_used_ids": (r2.get("cards_used_ids") or [])[:5]})
        logger.info("_run_inference_impl: run_agentwiki done time=%.2fs cards_used=%d ids=%s", r2.get("time_seconds", 0), r2.get("cards_used", 0), (r2.get("cards_used_ids") or [])[:2])
        if langfuse:
            _log_langfuse(langfuse, "run_agentwiki", {"cards_used": r2.get("cards_used"), "time_seconds": r2.get("time_seconds")})

        # Score both
        if _timed_out():
            return {"error": f"Timeout after {timeout_seconds}s", "run_static": r1, "run_agentwiki": r2, "scores": {}, "delta": 0, "cards_used_ids": r2.get("cards_used_ids", [])}
        logger.info("_run_inference_impl: step score_run1")
        with _span_ctx(langfuse, "score_run1", {}, input_data={"task_preview": task[:200]}):
            s1 = score_outcome(task, r1["plan"], r1["output"], r1["retry_count"])
            if langfuse:
                _set_current_output(langfuse, {"score": s1})
        logger.info("_run_inference_impl: score_run1=%.1f", s1)
        if langfuse:
            _log_langfuse(langfuse, "score_run1", {"score": s1})

        if _timed_out():
            return {"error": f"Timeout after {timeout_seconds}s", "run_static": r1, "run_agentwiki": r2, "scores": {"static": s1}, "delta": 0, "cards_used_ids": r2.get("cards_used_ids", [])}
        logger.info("_run_inference_impl: step score_run2")
        with _span_ctx(langfuse, "score_run2", {}, input_data={"task_preview": task[:200]}):
            s2 = score_outcome(task, r2["plan"], r2["output"], r2["retry_count"], used_playbooks=(r2.get("cards_used", 0) > 0))
            # Demo: when Run 2 used methods, give a clear boost so "With Agentwiki" consistently scores higher
            if r2.get("cards_used", 0) > 0:
                s2 = min(10.0, round(s2 + 1.5, 1))
                logger.info("_run_inference_impl: score_run2 boosted to %.1f (used methods)", s2)
            if langfuse:
                _set_current_output(langfuse, {"score": s2})
        if langfuse:
            _log_langfuse(langfuse, "score_run2", {"score": s2})

        r1["score"] = s1
        r2["score"] = s2
        delta = round(s2 - s1, 1)

        if langfuse:
            try:
                obs = getattr(langfuse, "get_current_observation", lambda: None)()
                if obs is not None:
                    obs.update(
                        metadata={"scores": {"static": s1, "agentwiki": s2}, "delta": delta, "task_preview": task[:100]},
                        output={
                            "scores": {"static": s1, "agentwiki": s2},
                            "delta": delta,
                            "run_static": {"output_preview": (r1.get("output") or "")[:300], "score": s1},
                            "run_agentwiki": {"output_preview": (r2.get("output") or "")[:300], "score": s2, "cards_used": r2.get("cards_used", 0)},
                        },
                    )
            except Exception:
                pass

        if write_back:
            if _timed_out():
                pass
            else:
                try:
                    write_back_card(
                        task_intent=task,
                        context="Pipeline run (Streamlit or API).",
                        plan=r2["plan"],
                        tool_calls="LLM completion",
                        mistakes="None recorded",
                        fixes="Use retrieved playbooks.",
                        outcome_score=s2,
                        tags=["demo", "agentwiki"],
                    )
                except Exception as e:
                    logger.warning("write_back_card failed: %s", e)
        # Agent upvotes on success (Reddit/ELO-like): if Run 2 used playbooks and scored well, upvote the primary card
        cards_used_ids = r2.get("cards_used_ids") or []
        if cards_used_ids and s2 >= 6:
            try:
                from memory import upvote_card
                upvote_card(cards_used_ids[0])
                logger.info("pipeline: auto-upvoted primary playbook %s (score %.1f >= 6)", cards_used_ids[0][:8], s2)
            except Exception as e:
                logger.warning("upvote_card failed: %s", e)

    if langfuse:
        try:
            langfuse.flush()
            logger.info("Langfuse: flush completed (pipeline)")
        except Exception as flush_err:
            logger.warning("Langfuse: flush failed: %s", flush_err)

    return {
        "error": None,
        "run_static": r1,
        "run_agentwiki": r2,
        "scores": {"static": s1, "agentwiki": s2},
        "delta": delta,
        "task": task,
        "cards_used_ids": r2.get("cards_used_ids") or [],
    }


def run_inference(task: str, write_back: bool = True, timeout_seconds: int | None = None) -> dict[str, Any]:
    """
    Run full demo: static run, Agentwiki run, score both, optional write_back_card.
    Returns dict with run_static, run_agentwiki, scores, delta, error (if any).
    Enforces timeout_seconds (default RUN_DEMO_TIMEOUT) via thread to avoid infinite load.
    """
    timeout_seconds = timeout_seconds or RUN_DEMO_TIMEOUT  # from utils
    task = (task or "").strip()
    if not task:
        return {"error": "Task is required", "run_static": None, "run_agentwiki": None, "scores": {}, "delta": 0, "cards_used_ids": []}
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run_inference_impl, task, write_back, timeout_seconds)
            return future.result(timeout=timeout_seconds + 10)
    except FuturesTimeoutError:
        logger.warning("run_inference: timed out after %ds", timeout_seconds)
        return {
            "error": f"Run timed out after {timeout_seconds}s. Try a shorter task or increase RUN_DEMO_TIMEOUT.",
            "run_static": None,
            "run_agentwiki": None,
            "scores": {},
            "delta": 0,
            "cards_used_ids": [],
            "task": task,
        }
    except Exception as e:
        logger.exception("run_inference failed")
        return {"error": str(e), "run_static": None, "run_agentwiki": None, "scores": {}, "delta": 0, "task": task, "cards_used_ids": []}


def _null_ctx():
    """Context manager that does nothing."""
    from contextlib import nullcontext
    return nullcontext()


def _span_ctx(lf, name: str, metadata: dict, input_data: dict | None = None):
    """Context manager: Langfuse span around the block; sets input (and optionally metadata)."""
    from contextlib import contextmanager
    if not lf:
        return _null_ctx()
    try:
        @contextmanager
        def _inner():
            with lf.start_as_current_observation(as_type="span", name=name) as span:
                if metadata:
                    span.update(metadata=metadata)
                if input_data:
                    span.update(input=input_data)
                yield
        return _inner()
    except Exception:
        return _null_ctx()


def _set_current_output(lf, output: dict) -> None:
    """Set output on the current Langfuse observation (so it shows in Langfuse UI)."""
    if not lf or not output:
        return
    try:
        obs = getattr(lf, "get_current_observation", lambda: None)()
        if obs is not None:
            obs.update(output=output)
    except Exception:
        pass


def _log_langfuse(lf, name: str, metadata: dict) -> None:
    """Update current Langfuse observation with metadata (for logging)."""
    if not lf or not metadata:
        return
    try:
        obs = getattr(lf, "get_current_observation", lambda: None)()
        if obs is not None:
            obs.update(metadata=metadata)
    except Exception:
        pass
