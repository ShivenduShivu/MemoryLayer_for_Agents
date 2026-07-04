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
| D7 | 2026-07-04 | **Cognee Cloud credit = ~$37 (ample).** Use freely when genuinely needed for verification; just avoid wasteful/repeated calls. `local` OSS mode remains a fallback if ever needed | User confirmed ample credit |
| D8 | 2026-07-04 | **Codex is a 3rd fleet agent.** Demo = Claude Code + Cursor + Codex, all MCP clients sharing one brain (stronger cross-agent story). May also use Codex to assist implementation | User has Codex; more heterogeneous agents = better demo |
| D9 | 2026-07-04 | Dev-prompt reduction: `.claude/settings.local.json` in **both** roots (codeforces session root + passport), gitignored, allowlists safe commands; `git push`/`rm`/`reset --hard` still prompt | Works whether Claude Code is launched from either folder |

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

### Stage 1 — Memory Engine Core (the foundation of the kill test)  ✅ DONE
- [x] `memory.py`: connect to Cognee Cloud via SDK (`serve()`)
- [x] `remember(text, agent, session, project)` with `node_set` provenance tags
- [x] `recall(query, scope)` hybrid graph+vector — **confirmed graph traversal (source: 'graph')**
- [~] `improve()` / memify wrapper (written; verified in Stage 4)
- [x] `forget(dataset)` wrapper
- [x] `scripts/smoke_test.py`: remember -> recall round-trip proves it works
- [x] Smoke test passed against live Cloud tenant (2026-07-04)

Known minor: aiohttp "Unclosed client session" warning on disconnect (cosmetic; Cognee CloudClient session cleanup — revisit if noisy).

### Stage 2 — Passport API Server  ✅ DONE
- [x] `server.py`: FastAPI with `/health /remember /recall /improve /forget /graph`
- [x] API-key auth via `X-Passport-Key` (401 verified when missing)
- [x] Provenance tags returned on every write (agent/project/session)
- [x] Tested end-to-end (`scripts/api_test.py`, in-process TestClient) on live Cloud
- [!] `/graph` (cognee.get_memory_provenance_graph) reads LOCAL sqlite -> empty in cloud
      mode. Degrades gracefully. **Stage 5 will build our own provenance ledger instead.**

### Stage 3 — MCP Server + Agent Integration (THE KILL TEST)
- [x] `mcp_server.py`: `passport_remember / passport_recall / passport_forget`
      (verified via a real MCP client in `scripts/mcp_test.py`)
- [x] `run_mcp.py` launcher + absolute `.env` load -> cwd-independent (verified from home dir)
- [x] All agents share project "fleet"; provenance via per-client `--agent` flag
- [M] Register with Claude Code (command provided)
- [M] Register with Cursor (config provided)
- [M] Register with Codex (config provided)
- [x] **CROSS-AGENT LOOP PROVEN (2026-07-04):** Claude Code taught JWT+React;
      **Codex (OpenAI GPT-5.5) recalled them** from the shared brain. Kill test PASSED. 🎯

Caveat: avoid rapid create/delete of the SAME dataset name in one burst — the
cloud tenant can 409/500 on churn. Use fresh dataset/project names in tests.

Fix (2026-07-04): Codex `passport_recall` hit `[Errno 22]` on Windows — verbose
Cognee stderr filled the client's unread pipe (recall is chatty; remember wasn't).
`run_mcp.py` now sets LOG_LEVEL=ERROR and redirects stderr to `mcp_server.log`
BEFORE importing Cognee, keeping the client's stdio pipes clean.

### Stage 4 — Conflict Detection & Reconciliation  ✅ DONE
- [x] **Conflict detection via Cognee's own LLM** (custom-prompted `recall`) — no extra key.
      Verified: caught Postgres(claude-code) vs MySQL(cursor).
- [x] Provenance ledger (`ledger.py`, SQLite) records who-taught-what + conflict log
- [x] `reconcile()`: authoritative resolution fact + mark resolved; recall now returns
      the resolved answer ("primary database is MySQL")
- [!] `improve()`/memify returns 404 on Cognee Cloud — runs only in self-hosted/OSS.
      Reconciliation works without it; memify is a bonus we can show in OSS mode.
- [x] Endpoints: `/conflicts`, `/reconcile`, `/ledger` (+ graceful `/improve`)

### Stage 5 — Dashboard
- [x] **Passport provenance ledger** (`ledger.py`, SQLite) — built in Stage 4; the
      source for the dashboard graph + conflict log. `/ledger` endpoint serves it.
- [x] Streamlit app (`dashboard/app.py`): provenance graph via graphviz (no extra deps)
- [x] Nodes colored by source agent (provenance) + legend + metrics
- [x] Conflict log panel (open/resolved)
- [x] Timeline / recent memories view + live demo controls (recall / detect conflicts)
- [x] Boots headless with no errors; renders the 3 ledger memories + 1 conflict
- [M] Visually confirm in browser (you): `streamlit run dashboard/app.py`

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
- 2026-07-04 — Scaffolding + PROJECT_LOG created. Stage 0 committed & pushed (c8830aa).
- 2026-07-04 — Stage 1 memory engine done. Verified real API: `remember(node_set=...)`,
  `recall(node_name=..., auto_route=True)`, `improve`, `forget`, `serve` (all async).
  Smoke test round-trip green on Cognee Cloud; recall answered via graph traversal.
- 2026-07-04 — Stage 2 API server done. 5 endpoints + auth (401 enforced). E2E test green.
  Finding: cognee provenance graph is local-sqlite-only -> Stage 5 uses own ledger.
  Decisions D7 (ample credit ~$37), D8 (Codex 3rd agent), D9 (permission allowlist) logged.
- 2026-07-04 — Stage 3 MCP server done + KILL TEST PASSED: Claude Code taught JWT+React,
  Codex (OpenAI) recalled from shared brain. Fixed Windows [Errno 22] stderr pipe issue.
  Cross-agent, cross-vendor shared memory works end-to-end.
- 2026-07-04 — Stage 4 done: conflict detection via Cognee LLM (caught Postgres vs MySQL),
  provenance ledger (SQLite), reconcile() with authoritative resolution. Finding: memify
  404 on Cloud (OSS-only). Endpoints /conflicts /reconcile /ledger added.
- 2026-07-04 — Stage 5 done: Streamlit dashboard — provenance graph colored by agent,
  timeline, conflict log, metrics, live recall/detect controls. Boots clean headless.
