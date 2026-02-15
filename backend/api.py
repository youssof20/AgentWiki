"""
REST API for Agentwiki: inference (Lovable frontend) + search for registered agents.
Run: uvicorn api:app --reload --port 8000. API docs: http://localhost:8000/docs
Optional auth: set AGENTWIKI_API_KEY in env; then send header X-API-Key on /inference and /search.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from utils import setup_logging, get_logger, getenv

setup_logging()
logger = get_logger(__name__)

API_KEY = getenv("AGENTWIKI_API_KEY")


def _require_api_key(x_api_key: str | None = None) -> None:
    """If API_KEY is set, require X-API-Key header to match. Raises 401 otherwise."""
    if not API_KEY:
        return
    if not x_api_key or x_api_key.strip() != API_KEY.strip():
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup: ensure demo Method Cards exist. Shutdown: no-op."""
    try:
        from memory import ensure_demo_templates
        n = ensure_demo_templates()
        logger.info("ensure_demo_templates: %d methods", n)
    except Exception as e:
        logger.warning("ensure_demo_templates failed: %s", e)
    yield


app = FastAPI(
    title="Agentwiki API",
    description="Inference and search. Docs: /docs. Optional: set AGENTWIKI_API_KEY and send X-API-Key header.",
    lifespan=_lifespan,
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


class RegisterRequest(BaseModel):
    """Request body for POST /auth/register."""
    agent_name: str = Field(..., min_length=1, description="Display name for the agent")
    team_name: str = Field("", description="Team or person name")
    email: str = Field("", description="Optional contact email")


class InferenceResponse(BaseModel):
    """Response from POST /inference."""
    run_static: dict | None
    run_agentwiki: dict | None
    scores: dict
    delta: float
    error: str | None
    task: str | None


class RegisterResponse(BaseModel):
    """Response from POST /auth/register."""
    agent_id: str


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


@app.post("/auth/register", response_model=RegisterResponse)
def register(
    req: RegisterRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Register an agent. Returns agent_id for use in X-Agent-ID header."""
    _require_api_key(x_api_key)
    try:
        from agents import save_agent_registration
    except Exception as e:
        logger.warning("register: import failed: %s", e)
        raise HTTPException(status_code=500, detail="Service unavailable")
    agent_name = (req.agent_name or "").strip()
    if not agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")
    agent_id = save_agent_registration(
        agent_name=agent_name,
        team_name=(req.team_name or "").strip(),
        email=(req.email or "").strip(),
    )
    if not agent_id:
        raise HTTPException(status_code=500, detail="Registration failed")
    return RegisterResponse(agent_id=agent_id)


@app.post("/inference", response_model=InferenceResponse)
def inference(
    req: InferenceRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Run Compare: without vs with Agentwiki. POST {"task": "..."}. Returns run_static, run_agentwiki, scores, delta."""
    _require_api_key(x_api_key)
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
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Search methods by keyword. Header X-Agent-ID required. Returns playbooks (task_intent, plan, outcome_score, tags)."""
    _require_api_key(x_api_key)
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


@app.post("/cards/{card_id}/upvote")
def upvote_card(
    card_id: str = Path(..., description="Method Card ID to upvote (star)"),
    x_agent_id: str | None = Header(default=None, alias="X-Agent-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Star (upvote) a Method Card. Header X-Agent-ID required."""
    _require_api_key(x_api_key)
    if not x_agent_id:
        raise HTTPException(status_code=401, detail="Missing X-Agent-ID header. Register your agent in the app to get an agent_id.")
    try:
        from agents import get_registered_agents
        from memory import upvote_card as memory_upvote_card
    except Exception as e:
        logger.warning("API upvote: import failed: %s", e)
        raise HTTPException(status_code=500, detail="Service unavailable")
    try:
        registered = get_registered_agents(limit=1000)
        ids = {r.get("id") for r in registered if r.get("id")}
        if ids and x_agent_id not in ids:
            raise HTTPException(status_code=403, detail="Invalid or unregistered agent_id.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("API: agent lookup failed: %s", e)
    ok = memory_upvote_card(card_id.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="Card not found or upvote failed")
    return {"ok": True, "card_id": card_id}
