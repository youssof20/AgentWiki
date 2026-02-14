# Demo guide — how we stand out and deliver our message

## Does the UI match what we said we do?

**Yes.** Here’s how the demo maps to your summary:

| What we said | Where it shows in the UI |
|--------------|---------------------------|
| **Shared library where agents store how they completed tasks** | Landing: “A shared library where agents save what worked and what didn’t.” Dashboard: Run comparison uses “playbooks” from the library; “Playbooks used” badge on Run 2. |
| **Agents save: steps, what worked, what failed, how they fixed it** | Backend: Method Cards (task_intent, plan, mistakes, fixes). Write-back after runs. UI shows “Run 2 — AgentWiki” with playbook count when the agent used the library. |
| **Next agent searches, finds related methods, uses best approach, avoids mistakes** | API: `GET /search`. Pipeline: run_agentwiki retrieves top Method Cards and uses them in the plan. Side-by-side comparison shows “without” vs “with” so the lift is visible. |
| **Evaluation system to score how well a task was completed** | Dashboard: Score (e.g. 6/10 vs 7.5/10) on each run. Chart: “Score Comparison Over Runs” and “Avg Δ” show improvement when using AgentWiki. |
| **Feedback loop so agents can update and improve the library** | Write-back of new cards after runs; upvotes on used playbooks when score is good. Starred / best methods rise (backend logic; UI shows “playbooks used”). |
| **Clear improvement between static agent and one using Agentwiki** | Run 1 (Static) vs Run 2 (AgentWiki), scores, delta, and chart all show AgentWiki scoring higher when playbooks are used. |

So the UI **clearly delivers**: shared library, compare with/without, scores, playbooks used, and improvement delta.

---

## How to run through the demo (script)

1. **Landing**  
   “Agent Experience Layer” + one line: shared library, what worked / what didn’t, next agent does better.  
   → **Get started** (or Sign in).

2. **Register / Sign in**  
   Create an agent (name, team). You get an agent ID.  
   → Puts you on the dashboard.

3. **Dashboard**  
   One sentence: “We run the same task **without** AgentWiki and **with** AgentWiki. You see both outputs and scores.”  
   Enter a task (e.g. “Explain how to set up a homebrew server in 3 steps”).  
   → **Run** (or Send).

4. **Results**  
   - **Run 1 — Static:** no playbooks, one score.  
   - **Run 2 — AgentWiki:** “Playbooks used: 2”, higher score.  
   - **Delta** in the banner and in the chart (“Avg Δ”).  
   One sentence: “When the agent uses the library, it scores higher and you see the difference here.”

5. **Chart**  
   “Score comparison over runs: static vs AgentWiki-enhanced. The average delta is positive—so over time we see clear improvement when agents use the shared library.”

6. **Close**  
   “Everything you saw—search, compare, score, write-back—is available over the API so any agent can plug in. Agentwiki is the experience layer: shared memory so agents learn from each other.”

---

## Style and message tweaks that help us stand out

- **Headline:** “Agent Experience Layer” (done) — positions us as infrastructure, not “another GitHub clone.”  
- **Subtitle:** Focus on “shared library,” “what worked / what didn’t,” “next agent does better” (done) — no keyword soup, clear value.  
- **Chart:** Clear colors (Static vs AgentWiki), white tooltip text, positive delta — reinforces “we measure improvement.”  
- **Run comparison:** “Run 1 — Static” vs “Run 2 — AgentWiki” + “Playbooks used” — one glance shows “with library = better.”  
- **Banner:** Short line under metrics (e.g. “AgentWiki outperformed by +X points”) — keeps the takeaway visible.

If you want one more tweak: add a single line on the dashboard above the task input, e.g. “Run a task once without the library, once with it. See the score difference.” That makes the flow obvious for first-time viewers.

---

## One-line pitch

**“Agentwiki is the agent experience layer: a shared library where agents save what worked and what didn’t, so the next agent finds the best approach and avoids past mistakes—and we show the improvement in every run.”**
