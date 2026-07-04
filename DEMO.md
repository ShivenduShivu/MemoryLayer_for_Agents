# Passport — demo runbook (for the video / judging)

Target: a tight ~2-minute demo that shows cross-agent shared memory, provenance,
conflict reconciliation, and forget — every Cognee lifecycle API, live.

## Setup (before recording)
1. `python -m uvicorn passport.server:app --port 8000`  (API + auto-capture hub)
2. `python -m streamlit run dashboard/app.py`  (dashboard at http://localhost:8501)
3. Ensure Claude Code + Codex have the `passport` MCP server registered.
4. (Optional) delete `ledger.db*` for a clean slate, and pick a fresh project so the
   graph starts empty on camera.
5. (Optional) enable the auto-capture hook in Claude Code for the "it captured itself" beat.

## The 6 beats
1. **Empty graph** on the dashboard. "This is one shared brain for all my AI agents."
2. **Claude Code:** *"Remember we use pytest, never unittest, and our database is Postgres."*
   → dashboard: a purple `claude-code` node blooms.
3. **Codex** (different vendor, fresh chat): *"What testing framework and database do we use?"*
   → answers **pytest + Postgres**, unprompted. → dashboard: a second-colored `codex` node.
   **← the jaw-drop: cross-vendor shared memory.**
4. **Provenance:** point at the graph — "every fact is colored by which agent taught it."
5. **Conflict:** tell Codex *"Actually we migrated the database to MySQL."* → click
   **Detect conflicts** on the dashboard → Cognee's LLM flags Postgres-vs-MySQL →
   reconcile → recall now returns **MySQL**. Conflict log shows ✅ resolved.
6. **Forget:** `forget()` the project → nodes vanish. "Your memory, self-hosted-capable, yours."

## The one-liner to close
"Every published memory system is single-agent. Passport is a shared brain for your whole
agent fleet — and it remembers who taught it what."
