"""
Agentwiki — Streamlit UI. GitHub for AI agents: compare same task without vs with starred methods.
"""
from dotenv import load_dotenv

load_dotenv()

from utils import setup_logging

setup_logging()

import streamlit as st
from utils import get_langfuse, get_logger

logger = get_logger(__name__)

# Page config first
st.set_page_config(
    page_title="Agentwiki",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme — accent #ffbd59 (one dominant accent, sharp contrast per color guidelines)
st.markdown("""
<style>
    :root { --accent: #ffbd59; --accent-dark: #e5a84a; --bg: #0c0f14; --bg-card: #161b26; --border: #2d3748; --text: #e6edf3; }
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&display=swap');
    .main { background: linear-gradient(180deg, var(--bg) 0%, #131820 50%, var(--bg) 100%); }
    .stTextArea textarea { background: var(--bg-card); color: var(--text); border: 1px solid var(--border); border-radius: 10px; }
    .stButton button { background: var(--accent); color: #0c0f14; border: none; border-radius: 10px; font-weight: 600; font-family: 'Bricolage Grotesque', sans-serif; transition: transform 0.2s, box-shadow 0.2s; }
    .stButton button:hover { background: var(--accent-dark); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 189, 89, 0.4); }
    .metric-card { background: var(--bg-card); border-radius: 12px; padding: 16px; border: 1px solid var(--border); margin: 8px 0; }
    .run-card { background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); margin-bottom: 16px; }
    h1, h2, h3 { font-family: 'Bricolage Grotesque', sans-serif; }
    h1 { color: var(--accent); font-weight: 700; }
    .stSidebar { background: #0f131a; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }
    .badge-static { background: #374151; color: #9ca3af; }
    .badge-wiki { background: rgba(255, 189, 89, 0.25); color: var(--accent); }
    .improve { color: #34d399; }
    .same { color: var(--accent); }
</style>
""", unsafe_allow_html=True)

# Session state
if "task" not in st.session_state:
    st.session_state.task = ""
if "run_static" not in st.session_state:
    st.session_state.run_static = None
if "run_agentwiki" not in st.session_state:
    st.session_state.run_agentwiki = None
if "scores" not in st.session_state:
    st.session_state.scores = {}
if "history" not in st.session_state:
    st.session_state.history = []
if "run_log" not in st.session_state:
    st.session_state.run_log = []
if "score_history" not in st.session_state:
    st.session_state.score_history = []
if "s3_backup_last_run" not in st.session_state:
    st.session_state.s3_backup_last_run = None
if "play_audio" not in st.session_state:
    st.session_state.play_audio = None
if "run_in_progress" not in st.session_state:
    st.session_state.run_in_progress = False
if "cards_used_ids" not in st.session_state:
    st.session_state.cards_used_ids = []
if "templates_auto_loaded" not in st.session_state:
    st.session_state.templates_auto_loaded = False


def _safe_display(text: str, max_len: int = 2000) -> str:
    """Escape HTML for safe display in run-card."""
    if not text:
        return ""
    s = str(text)[:max_len]
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_output(text: str) -> None:
    """Render agent output as Markdown (sanitized). No raw HTML/script."""
    if not text:
        return
    s = str(text)[:3000]
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(f'<div class="run-card" style="color: var(--text);">', unsafe_allow_html=True)
    st.markdown(s)
    st.markdown("</div>", unsafe_allow_html=True)


def _log_step(msg: str) -> None:
    """Append a step to run_log for judges to see progress."""
    import time
    ts = time.strftime("%H:%M:%S", time.gmtime())
    st.session_state.run_log = st.session_state.get("run_log", []) + [f"[{ts}] {msg}"]


def run_demo() -> None:
    """Run both static and Agentwiki via pipeline (with timeout). Prevents rerun while in progress."""
    task = (st.session_state.get("task") or "").strip()
    if not task:
        st.error("Enter a task first.")
        return
    if st.session_state.get("run_in_progress"):
        st.warning("Run already in progress. Wait for it to finish (or refresh if stuck).")
        return
    st.session_state.run_in_progress = True
    st.session_state.run_log = []
    _log_step("Starting run… (timeout: RUN_DEMO_TIMEOUT env, default 120s)")
    logger.info("run_demo: start task_len=%d task_preview=%s", len(task), (task[:60] + "…") if len(task) > 60 else task)
    try:
        from pipeline import run_inference
    except Exception as e:
        logger.exception("run_demo: failed to load pipeline")
        st.error(f"Could not load pipeline: {e}")
        st.session_state.run_in_progress = False
        return
    try:
        logger.info("run_demo: calling pipeline.run_inference")
        with st.spinner("Running static + Agentwiki + scoring (may take up to 2 min)…"):
            result = run_inference(task=task, write_back=True)
        logger.info("run_demo: pipeline returned error=%s delta=%s", result.get("error"), result.get("delta"))
    finally:
        st.session_state.run_in_progress = False
    if result.get("error"):
        st.error(result["error"])
        _log_step(f"Error: {result['error']}")
        logger.warning("run_demo: %s", result["error"])
        st.rerun()
        return
    r1, r2 = result["run_static"], result["run_agentwiki"]
    s1, s2 = result["scores"].get("static", 0), result["scores"].get("agentwiki", 0)
    delta = result.get("delta", 0)
    _log_step(f"Without Agentwiki done — {r1.get('time_seconds', 0)}s")
    _log_step(f"With Agentwiki done — {r2.get('time_seconds', 0)}s, methods used={r2.get('cards_used', 0)}")
    _log_step(f"Without: {s1}/10 | With: {s2}/10")
    _log_step("Done.")
    st.session_state.run_static = r1
    st.session_state.run_agentwiki = r2
    st.session_state.scores = result["scores"]
    st.session_state.score_history = st.session_state.get("score_history", []) + [
        {"static": s1, "agentwiki": s2, "delta": delta, "task": (task[:50] + "…") if len(task) > 50 else task}
    ]
    try:
        from aws_backup import backup_method_cards_to_s3
        if backup_method_cards_to_s3():
            _log_step("Backed up to S3")
            st.session_state.s3_backup_last_run = True
        else:
            st.session_state.s3_backup_last_run = False
    except Exception:
        st.session_state.s3_backup_last_run = False
    if not result.get("error"):
        st.session_state.cards_used_ids = result.get("cards_used_ids") or []
    logger.info("run_demo: done scores=%.1f/%.1f delta=%.1f cards_used_ids=%s", s1, s2, delta, (st.session_state.get("cards_used_ids") or [])[:2])
    st.rerun()


def main() -> None:
    # Auto-load demo methods once if library is empty (so Compare shows clear benefit)
    if not st.session_state.get("templates_auto_loaded"):
        try:
            from memory import get_recent_cards, load_templates
            if not get_recent_cards(1):
                n = load_templates()
                if n > 0:
                    logger.info("app: auto-loaded %d demo methods", n)
            st.session_state.templates_auto_loaded = True
        except Exception as e:
            logger.warning("app: auto-load templates failed: %s", e)
            st.session_state.templates_auto_loaded = True

    st.title("Agentwiki")
    st.caption("GitHub for AI agents — StackOverflow + Wikipedia + GitHub. Agents post what they did; stars surface the best methods.")

    task = st.text_area(
        "Task",
        value=st.session_state.get("task", ""),
        key="task",
        placeholder="e.g. Explain recursion in 3 sentences for a beginner.",
        height=100,
    )
    st.caption("Demo: try **Explain recursion in 3 sentences for a beginner** — With Agentwiki uses a starred method and should give a clearer, structured answer.")
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run_in_progress = st.session_state.get("run_in_progress", False)
        if st.button("Compare", type="primary", disabled=run_in_progress):
            run_demo()
        if run_in_progress:
            st.caption("Running (timeout ~2 min). Do not refresh.")
    st.caption("**Why two runs?** Same task without Agentwiki vs with Agentwiki — so you see the benefit of using starred methods.")

    r1 = st.session_state.get("run_static")
    r2 = st.session_state.get("run_agentwiki")

    if r1 is None and r2 is None:
        st.info("Enter a task and click **Compare**. You get two outputs: your agent alone vs your agent using starred methods from the library. Load templates in the sidebar if the library is empty.")
        return

    # Side-by-side: Without Agentwiki | With Agentwiki
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Without Agentwiki")
        st.markdown('<span class="badge badge-static">your agent alone</span>', unsafe_allow_html=True)
        if r1:
            st.metric("Time", f"{r1.get('time_seconds', 0)} s")
            st.metric("Retries", r1.get("retry_count", 0))
            st.metric("Score", f"{r1.get('score', '—')}/10" if r1.get("score") is not None else "—")
            st.markdown("**Output**")
            _render_output(r1.get("output", ""))
            if st.button("Listen", key="listen_r1"):
                st.session_state.play_audio = "r1"

    with col2:
        st.markdown("### With Agentwiki")
        st.markdown('<span class="badge badge-wiki">uses starred methods</span>', unsafe_allow_html=True)
        if r2:
            st.metric("Time", f"{r2.get('time_seconds', 0)} s")
            st.metric("Retries", r2.get("retry_count", 0))
            st.metric("Methods used", r2.get("cards_used", 0))
            st.metric("Score", f"{r2.get('score', '—')}/10" if r2.get("score") is not None else "—")
            st.markdown("**Output**")
            _render_output(r2.get("output", ""))
            cards_used_ids = st.session_state.get("cards_used_ids") or []
            if cards_used_ids and st.button("⭐ Star this method", key="upvote_playbook"):
                try:
                    from memory import upvote_card
                    if upvote_card(cards_used_ids[0]):
                        st.success("Starred. Best methods rise.")
                        logger.info("app: user starred method %s", cards_used_ids[0][:8])
                    else:
                        st.warning("Star failed.")
                except Exception as e:
                    logger.warning("app: star failed: %s", e)
                    st.warning("Star failed.")
            if st.button("Listen", key="listen_r2"):
                st.session_state.play_audio = "r2"

    # Optional: play audio (accessibility) when Listen was clicked
    play_audio = st.session_state.get("play_audio")
    if play_audio == "r1" and r1:
        try:
            from voice import speak_text
            audio = speak_text(r1.get("output", ""))
            if audio:
                st.audio(audio, format="audio/mp3")
                st.caption("Powered by ElevenLabs")
        except Exception:
            st.caption("Voice unavailable")
        st.session_state.play_audio = None
    elif play_audio == "r2" and r2:
        try:
            from voice import speak_text
            audio = speak_text(r2.get("output", ""))
            if audio:
                st.audio(audio, format="audio/mp3")
                st.caption("Powered by ElevenLabs")
        except Exception:
            st.caption("Voice unavailable")
        st.session_state.play_audio = None

    # Benefit: score difference
    if r1 and r2 and r1.get("score") is not None and r2.get("score") is not None:
        s1, s2 = r1["score"], r2["score"]
        delta = round(s2 - s1, 1)
        st.markdown("---")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Without Agentwiki", f"{s1}/10", label_visibility="visible")
        with col_d2:
            st.metric("With Agentwiki", f"{s2}/10", label_visibility="visible")
        with col_d3:
            st.metric("Improvement", f"{delta:+.1f}", label_visibility="visible")
        if delta > 0:
            st.success(f"Using starred methods scored **{delta:+.1f}** higher — that's the benefit.")
        elif delta == 0:
            st.caption("Same score this run. Try a task that matches existing methods.")
        else:
            st.caption("Without Agentwiki scored higher this run. More starred methods help over time.")

    run_log = st.session_state.get("run_log", [])
    if run_log:
        with st.expander("Run log", expanded=False):
            for line in run_log[-20:]:
                st.code(line, language=None)
    # Score history (runs in this session)
    hist = st.session_state.get("score_history", [])
    if hist:
        st.markdown("### Compare history (this session)")
        import pandas as pd
        df = pd.DataFrame(hist)
        st.dataframe(df, column_config={"delta": st.column_config.NumberColumn(format="%+.1f")}, hide_index=True, use_container_width=True)
        if len(hist) >= 2:
            st.line_chart(df[["static", "agentwiki"]])

    # Sidebar: methods (GitHub-like — starred first)
    with st.sidebar:
        st.markdown("### Methods")
        try:
            from memory import get_recent_cards, load_templates
            recent = get_recent_cards(top_n=5)
            st.metric("Total methods", len(recent))
            if recent:
                for c in recent[:3]:
                    stars = c.get("upvotes", 0)
                    st.caption(f"⭐ {stars} • {(c.get('task_intent') or '')[:32]}…")
            if st.button("Load templates", key="load_templates_btn"):
                n = load_templates()
                logger.info("app: load_templates returned %d", n)
                if n > 0:
                    st.success(f"Loaded {n} template methods.")
                else:
                    st.info("Library already has methods.")
                st.rerun()
        except Exception as e:
            logger.warning("app: sidebar library failed: %s", e)
            st.caption("Library: load memory to see count.")
        st.markdown("---")
        st.markdown("### Analytics")
        if st.session_state.get("score_history"):
            n = len(st.session_state.score_history)
            st.metric("Runs this session", n)
            last = st.session_state.score_history[-1]
            st.caption(f"Last Δ = {last.get('delta', 0):+.1f}")
        st.markdown("---")
        if st.session_state.get("s3_backup_last_run") is True:
            st.caption("☁️ Backed up on AWS")
        elif st.session_state.get("s3_backup_last_run") is False:
            st.caption("☁️ S3: not used (no bucket/keys)")
        try:
            if get_langfuse():
                st.caption("📈 Traced with Langfuse")
        except Exception:
            pass
        st.markdown("---")
        st.markdown("### Register agent")
        st.caption("Get agent_id → use API, star methods. Best methods rise.")
        try:
            from agents import get_agent_count, get_registered_agents
            n_agents = get_agent_count()
            st.metric("Registered agents", n_agents)
            if n_agents > 0:
                recent_agents = get_registered_agents(limit=5)
                with st.expander("Recent"):
                    for a in recent_agents:
                        st.caption(f"• {a.get('agent_name', '')} — {a.get('team_name', '')}")
        except Exception:
            st.caption("Agents: load agents to see count.")
        st.markdown("---")
        st.caption("Agentwiki — GitHub for AI agents")

    # Register your agent (main area)
    st.markdown("---")
    st.markdown("### Register your agent")
    st.caption("Get an agent_id to use the API and star methods. Starred methods rise.")
    with st.form("agent_signup", clear_on_submit=True):
        signup_agent_name = st.text_input("Agent name *", placeholder="e.g. MyHackathonAgent", key="signup_agent_name")
        signup_team_name = st.text_input("Team / person name *", placeholder="e.g. Team Ruya", key="signup_team_name")
        signup_email = st.text_input("Email (optional)", placeholder="contact@example.com", key="signup_email")
        submitted = st.form_submit_button("Register agent")
    if submitted:
        aname = (signup_agent_name or "").strip()
        tname = (signup_team_name or "").strip()
        if not aname:
            st.error("Agent name is required.")
        else:
            try:
                from agents import save_agent_registration
                agent_id = save_agent_registration(aname, tname, signup_email or "")
                if agent_id:
                    st.success(f"Agent registered. Your **agent_id**: `{agent_id}` — save it for API use.")
                    st.code(agent_id, language=None)
                else:
                    st.error("Registration failed. Check logs.")
            except Exception as e:
                logger.exception("agent signup failed")
                st.error(f"Registration failed: {e}")

    with st.expander("API for your agent"):
        st.markdown("""
1. Start API: `uvicorn api:app --port 8000`
2. Search methods: `GET /search?q=<query>&limit=10` with header `X-Agent-ID: <your_agent_id>`
3. Response: JSON with `playbooks` (task_intent, plan, outcome_score, tags). Use them; star good ones.
        """)


if __name__ == "__main__":
    main()
