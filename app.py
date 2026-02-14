"""
Agentwiki — Streamlit UI only. Side-by-side demo: Run 1 (static) vs Run 2 (Agentwiki).
"""
from dotenv import load_dotenv

load_dotenv()

from utils import setup_logging

setup_logging()

import streamlit as st
from utils import get_logger

logger = get_logger(__name__)

# Page config first
st.set_page_config(
    page_title="Agentwiki",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme + distinctive typography (Bricolage Grotesque, accent teal/amber)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&display=swap');
    .main { background: linear-gradient(180deg, #0c0f14 0%, #131820 50%, #0c0f14 100%); }
    .stTextArea textarea { background: #1a1f2e; color: #e6edf3; border: 1px solid #2d3748; border-radius: 10px; }
    .stButton button { background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); color: white; border: none; border-radius: 10px; font-weight: 600; font-family: 'Bricolage Grotesque', sans-serif; transition: transform 0.2s, box-shadow 0.2s; }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(13, 148, 136, 0.4); }
    .metric-card { background: #1a1f2e; border-radius: 12px; padding: 16px; border: 1px solid #2d3748; margin: 8px 0; }
    .run-card { background: #161b26; border-radius: 12px; padding: 20px; border: 1px solid #2d3748; margin-bottom: 16px; }
    h1, h2, h3 { font-family: 'Bricolage Grotesque', sans-serif; }
    h1 { background: linear-gradient(90deg, #0d9488, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-weight: 700; }
    .stSidebar { background: #0f131a; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }
    .badge-static { background: #374151; color: #9ca3af; }
    .badge-wiki { background: rgba(13, 148, 136, 0.25); color: #5eead4; }
    .improve { color: #34d399; }
    .same { color: #fbbf24; }
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


def run_demo() -> None:
    """Run both static and Agentwiki, then evaluate and optionally write back."""
    task = (st.session_state.get("task") or "").strip()
    if not task:
        st.error("Enter a task first.")
        return
    logger.info("run_demo: starting, task_len=%d", len(task))
    try:
        from agent import run_static, run_agentwiki
        from evaluator import score_outcome, write_back_card
    except Exception as e:
        logger.exception("run_demo: failed to load agent/evaluator")
        st.error(f"Could not load agent or evaluator: {e}")
        return
    # Run 1: static
    with st.spinner("Run 1 — Static agent..."):
        r1 = run_static(task)
    st.session_state.run_static = r1
    # Run 2: Agentwiki
    with st.spinner("Run 2 — Agentwiki (with playbooks)..."):
        r2 = run_agentwiki(task, top_n=3)
    st.session_state.run_agentwiki = r2
    # Score both
    with st.spinner("Evaluating outcomes..."):
        s1 = score_outcome(task, r1["plan"], r1["output"], r1["retry_count"])
        s2 = score_outcome(task, r2["plan"], r2["output"], r2["retry_count"])
    st.session_state.run_static["score"] = s1
    st.session_state.run_agentwiki["score"] = s2
    st.session_state.scores = {"static": s1, "agentwiki": s2}
    # Write back Method Card for Agentwiki run (so next time we have a playbook)
    write_back_card(
        task_intent=task,
        context="Side-by-side demo run.",
        plan=r2["plan"],
        tool_calls="LLM completion",
        mistakes="None recorded",
        fixes="Use retrieved playbooks.",
        outcome_score=s2,
        tags=["demo", "agentwiki"],
    )
    logger.info("run_demo: done, scores static=%.1f agentwiki=%.1f", s1, s2)
    st.rerun()


def main() -> None:
    st.title("Agentwiki")
    st.caption("StackOverflow + Wikipedia for agents — same task, with and without shared playbooks.")

    task = st.text_area(
        "Task",
        value=st.session_state.get("task", ""),
        key="task",
        placeholder="e.g. Explain recursion in 3 sentences for a beginner.",
        height=100,
    )
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("Run both (Static vs Agentwiki)", type="primary"):
            run_demo()

    r1 = st.session_state.get("run_static")
    r2 = st.session_state.get("run_agentwiki")

    if r1 is None and r2 is None:
        st.info("Enter a task and click **Run both** to compare a static agent vs one that uses Agentwiki playbooks.")
        return

    # Side-by-side
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Run 1 — Static agent")
        st.markdown('<span class="badge badge-static">no playbooks</span>', unsafe_allow_html=True)
        if r1:
            st.metric("Time", f"{r1.get('time_seconds', 0)} s")
            st.metric("Retries", r1.get("retry_count", 0))
            st.metric("Score", f"{r1.get('score', '—')}/10" if r1.get("score") is not None else "—")
            st.markdown("**Output**")
            st.markdown(f'<div class="run-card"><pre style="white-space: pre-wrap; margin:0; color: #e6edf3;">{r1.get("output", "")[:2000]}</pre></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### Run 2 — Agentwiki")
        st.markdown('<span class="badge badge-wiki">playbooks used</span>', unsafe_allow_html=True)
        if r2:
            st.metric("Time", f"{r2.get('time_seconds', 0)} s")
            st.metric("Retries", r2.get("retry_count", 0))
            st.metric("Playbooks used", r2.get("cards_used", 0))
            st.metric("Score", f"{r2.get('score', '—')}/10" if r2.get("score") is not None else "—")
            st.markdown("**Output**")
            st.markdown(f'<div class="run-card"><pre style="white-space: pre-wrap; margin:0; color: #e6edf3;">{r2.get("output", "")[:2000]}</pre></div>', unsafe_allow_html=True)

    # Improvement indicator
    if r1 and r2 and r1.get("score") is not None and r2.get("score") is not None:
        s1, s2 = r1["score"], r2["score"]
        if s2 > s1:
            st.success(f"Agentwiki run scored higher: {s2} vs {s1} — improvement from shared playbooks.")
        elif s2 == s1:
            st.warning("Same score this run. Try a task that matches existing playbooks for a clearer boost.")
        else:
            st.info("Static run scored higher this time. More playbooks will improve Agentwiki over time.")

    # Sidebar: recent playbooks count
    with st.sidebar:
        st.markdown("### Library")
        try:
            from memory import get_recent_cards
            recent = get_recent_cards(top_n=5)
            st.metric("Method Cards (recent)", len(recent))
            if recent:
                for c in recent[:3]:
                    st.caption(f"• { (c.get('task_intent') or '')[:40]}... (score {c.get('outcome_score', 0)})")
        except Exception:
            st.caption("Method Cards: load memory to see count.")
        st.markdown("---")
        st.caption("📚 Agentwiki — Ruya AI Hackathon 2026")


if __name__ == "__main__":
    main()
