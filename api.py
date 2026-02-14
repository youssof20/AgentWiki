"""
REST API for Agentwiki: inference (Lovable frontend) + search for registered agents.
Run with: uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from utils import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Agentwiki API",
    description="Inference (run static vs Agentwiki) and search playbooks for registered agents. Connect your Lovable frontend to POST /inference.",
)

# CORS for Lovable and other frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InferenceRequest(BaseModel):
    """Request body for POST /inference."""
    task: str = Field(..., min_length=1, description="The task for the agent (e.g. 'Explain recursion in 3 sentences')")
    write_back: bool = Field(True, description="Whether to write back a Method Card after the run")


class InferenceResponse(BaseModel):
    """Response from POST /inference."""
    run_static: dict | None
    run_agentwiki: dict | None
    scores: dict
    delta: float
    error: str | None
    task: str | None


def _card_to_public(card: dict) -> dict:
    """Return a safe subset of a Method Card for API response."""
    return {
        "id": card.get("id"),
        "task_intent": card.get("task_intent"),
        "plan": card.get("plan"),
        "outcome_score": card.get("outcome_score"),
        "tags": card.get("tags") if isinstance(card.get("tags"), list) else [],
    }


@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok"}


@app.post("/inference", response_model=InferenceResponse)
def inference(req: InferenceRequest):
    """
    Run the full demo: static agent (Run 1) + Agentwiki agent (Run 2), score both, optional write-back.
    For Lovable frontend: POST JSON { "task": "your task here" }. Returns run_static, run_agentwiki, scores, delta.
    Timeout: RUN_DEMO_TIMEOUT env (default 120s).
    """
    try:
        from pipeline import run_inference as run_pipeline
    except Exception as e:
        logger.warning("inference: import failed: %s", e)
        raise HTTPException(status_code=500, detail="Service unavailable")
    result = run_pipeline(task=req.task.strip(), write_back=req.write_back)
    if result.get("error"):
        return JSONResponse(
            status_code=408 if "Timeout" in str(result["error"]) else 500,
            content={
                "run_static": result.get("run_static"),
                "run_agentwiki": result.get("run_agentwiki"),
                "scores": result.get("scores") or {},
                "delta": result.get("delta") or 0,
                "error": result["error"],
                "task": result.get("task"),
            },
        )
    return result


@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    x_agent_id: str | None = Header(default=None, alias="X-Agent-ID"),
):
    """
    Search playbooks by keyword. Registered agents should send their agent_id in header: X-Agent-ID.
    Returns list of playbooks (task_intent, plan, outcome_score, tags).
    """
    if not x_agent_id:
        raise HTTPException(status_code=401, detail="Missing X-Agent-ID header. Register your agent in the app to get an agent_id.")
    try:
        from agents import get_registered_agents
        from memory import search_cards
    except Exception as e:
        logger.warning("API search: import failed: %s", e)
        raise HTTPException(status_code=500, detail="Service unavailable")
    # Validate agent_id is registered (if we have any registrations)
    try:
        registered = get_registered_agents(limit=1000)
        ids = {r.get("id") for r in registered if r.get("id")}
        if ids and x_agent_id not in ids:
            raise HTTPException(status_code=403, detail="Invalid or unregistered agent_id.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("API: agent lookup failed: %s", e)
    try:
        cards = search_cards(q.strip(), top_n=limit)
        return JSONResponse(content={"query": q, "playbooks": [_card_to_public(c) for c in cards]})
    except Exception as e:
        logger.exception("API search failed")
        raise HTTPException(status_code=500, detail="Search failed")
