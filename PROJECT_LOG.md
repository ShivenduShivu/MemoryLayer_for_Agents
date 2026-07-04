# Passport — Project Log & Roadmap

Single source of truth for **major decisions** and **staged progress**.
Update this file as decisions change or stages complete.

- **Project:** Passport — a shared memory layer for coding agents (Cognee-powered)
- **Hackathon:** The Hangover Part AI (WeMakeDevs x Cognee)
- **Submission deadline:** 2026-07-06, 05:29 AM IST
- **Repo:** https://github.com/ShivenduShivu/MemoryLayer_for_Agents
- **Prize target:** Best Use of Cognee Cloud (iPhone 17). OSS/self-host = stretch.

---

## 1. Decision Log

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| D1 | 2026-07-03 | Build **Passport** (shared memory across coding agents) — not the Trading Analyst / other ideas | Real gap (all published memory systems are single-agent); hits judges (Cognee) dead-center; jaw-drop cross-tool demo |
| D2 | 2026-07-03 | **Option B: MCP-only** across Claude Code / Cursor / Codex — no browser extension | Higher floor; nothing fragile to break live; still fully proves cross-agent shared memory |
| D3 | 2026-07-04 | **Primary backend = Cognee Cloud** → target the **iPhone 17 (Cloud)** track | Credit claimed (COGNEE-35); removes LLM-key + Docker friction; fastest path in 48h. Architecture stays swap-ready for OSS. |
| D4 | 2026-07-04 | Stack: Python 3.11+, FastAPI, **cognee 1.2.2**, MCP SDK 1.28.1, Streamlit | Matches Cognee ecosystem; fast to ship |
| D5 | 2026-07-04 | Commits authored **solely by ShivenduShivu** — no Claude co-author, no other contributors | User requirement |
| D6 | 2026-07-04 | Secrets only in `.env` (gitignored); `.env.template` removed after key leaked into it | Public repo — no secrets committed |

**Open decisions / to revisit:**
- Rotate the exposed Cognee API key before/after submission (flagged, user's call).
- Whether to also self-host for the OSS/MacBook track if time allows (stretch).

---

## 2. Staged Roadmap

Legend: `[ ]` todo · `[x]` done · `[~]` in progress · `[M]` needs your manual verification

### Stage 0 — Project Setup & Scaffolding
- [x] Repo folder + package layout
- [x] `config.py` (Cloud/local swap via env)
- [x] `requirements.txt` installed (cognee 1.2.2 confirmed)
- [x] `.gitignore` protects `.env`
- [x] `.env` created with Cloud key + tenant URL (local only)
- [x] `.env.template` deleted
- [x] This PROJECT_LOG.md created
- [ ] `git init`, remote added, first commit + push
- [M] Confirm GitHub email attribution = ShivenduShivu

### Stage 1 — Memory Engine Core (the foundation of the kill test)
- [ ] `memory.py`: connect to Cognee Cloud via SDK
- [ ] `remember(text, agent, session, project)` with `node_set` provenance tags
- [ ] `recall(query, scope)` hybrid graph+vector
- [ ] `improve()` / memify wrapper
- [ ] `forget(dataset)` wrapper
- [ ] `scripts/smoke_test.py`: remember -> recall round-trip proves it works
- [M] Run smoke test against live Cloud instance (you run it, confirm output)

### Stage 2 — Passport API Server
- [ ] `server.py`: FastAPI with `/remember /recall /improve /forget /graph`
- [ ] API-key auth (single passport key)
- [ ] Provenance tagging enforced on every write
- [ ] Manual test via curl / docs page

### Stage 3 — MCP Server + Agent Integration (THE KILL TEST)
- [ ] `mcp_server.py`: expose `passport_remember / passport_recall / passport_forget`
- [ ] Register with Claude Code
- [ ] Register with Cursor (or Codex)
- [ ] **Cross-agent loop: teach in Agent A -> recall in Agent B**
- [M] Install + wire Claude Code and Cursor (you do the client-side registration)

### Stage 4 — Conflict Detection & Reconciliation
- [ ] Detect contradictory facts on write (embedding threshold + same entity)
- [ ] `improve()` reconciles / deprecates stale node
- [ ] Conflict log persisted for the dashboard

### Stage 5 — Dashboard
- [ ] Streamlit app: live knowledge graph
- [ ] Nodes colored by source agent (provenance)
- [ ] Conflict log panel
- [ ] Timeline / recent memories view

### Stage 6 — Depth (SHOULD items)
- [ ] Provenance/recency/importance retrieval scoring
- [ ] Auto-capture hook for Claude Code (Stop hook -> /remember)

### Stage 7 — Polish & Submit
- [ ] README final + architecture diagram
- [ ] 2-minute demo video
- [ ] Deploy public URL
- [ ] Submission form + AI-tool disclosure

### Stretch (only if ahead)
- [ ] Bi-temporal "what did we believe at time T"
- [ ] LLM importance auto-scoring
- [ ] Third agent surface
- [ ] Mini eval table (cross-agent recall %)

---

## 3. Manual-Verification Items (things outside my scope)
Tracked here so nothing slips. I'll tag each with `[M]` in the stages above.
- Confirm GitHub email attribution.
- Run smoke test / server locally and report output.
- Register MCP server inside Claude Code and Cursor.
- Record the demo video; submit the form.
- Rotate the Cognee API key (security).

---

## 4. Changelog
- 2026-07-04 — Scaffolding + PROJECT_LOG created. Stage 0 near complete.
