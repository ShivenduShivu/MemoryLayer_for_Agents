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
| D10 | 2026-07-04 | **Multi-tenancy** via tenant-namespaced datasets (`passport_{tenant}_{project}`) + `tenant:` node_set tag + ledger `tenant` column | Logical isolation within one Cognee tenant; per-user Cognee tenants = production path |
| D11 | 2026-07-04 | **recall uses CHUNKS (dataset-scoped), not GRAPH/RAG completion** | Finding: completion recall leaks across datasets in a shared tenant; CHUNKS is provably isolated. Passport returns faithful facts, the agent synthesizes. Conflict detection still uses graph completion. |
| D12 | 2026-07-04 | Disable Cognee session cache (`CACHING=false`) before import | Session memory returned stale cross-session context; off = recall reflects the actual dataset |
| D13 | 2026-07-05 | **LLM-based importance scoring** via Cognee's cloud LLM (recall + system prompt), heuristic fallback; deliberate writes use LLM, background auto-capture uses heuristic for speed | Makes importance genuinely intelligent (not keywords). Verified: rated a policy 9/10, chatter 2/10. Cloud LLM reachable without a local key. |

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

### Stage 6 — Depth (SHOULD items)  ✅ (marquee done)
- [x] **Auto-capture hook** (`hooks/capture_hook.py`): UserPromptSubmit -> POST /remember.
      Verified: durable facts captured in ~950ms (background ingest), questions filtered.
- [x] **Importance filter** (`looks_durable`): only durable facts/prefs/decisions are
      kept (research: importance-scored retention). Avoids memory noise.
- [x] Background ingestion path (`remember(background=True)`) so capture never blocks a turn.
- [~] Full recency/importance re-ranking of recall: recall already uses Cognee's hybrid
      auto-routing; deeper re-ranking left as stretch.
- [M] Enable hook in Claude Code (config below) + run the API server for it to post to.

Enable auto-capture (add to a Claude Code settings.json; needs the API server running):
```
{"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
  "command": "C:\\Users\\shive\\AppData\\Local\\Programs\\passport\\.venv\\Scripts\\python.exe C:\\Users\\shive\\AppData\\Local\\Programs\\passport\\hooks\\capture_hook.py"}]}]}}
```

### Stage 7 — Polish & Submit
- [x] README final: pitch, prior-art table, mermaid architecture, Cognee scorecard,
      research citations, setup, AI-disclosure
- [x] LICENSE (MIT), DEMO.md runbook (2-min demo script)
- [M] Record 2-minute demo video (you) — script in DEMO.md
- [M] Deploy public URL (you; I can help wire Railway/Render for the API + Vercel/Streamlit Cloud)
- [M] Submit hackathon form + declare AI assistance (you)

### Stage 8 — Multi-tenancy & isolation  ✅ DONE
- [x] `tenant` threaded through memory, ledger, server, MCP (`--tenant`), hook, dashboard
- [x] Tenant-namespaced Cognee datasets + `tenant:` node_set tag + ledger `tenant` column (with migration)
- [x] **Isolation verified** (`scripts/tenant_test.py`): alice sees only her data, bob only his — no leak
- [x] Recall switched to dataset-scoped **CHUNKS** (provably isolated); `CACHING=false`
- [x] `forget()` now also clears the ledger (Stage-10 consistency, done early)
- [x] Dashboard has a **tenant selector** to view each user's isolated brain
- Key finding logged (D11): completion-mode recall leaks across datasets in a shared tenant.

### Stage 9 — Retrieval Intelligence  ✅ DONE
- [x] `score_importance()` heuristic (1-10) stored per memory in the ledger
- [x] Recency (exponential decay, tau=14d) + per-agent trust weights (`passport`=1.3)
- [x] `recall()` re-ranks candidates: **composite = (0.5·relevance + 0.25·recency +
      0.25·importance) × trust**, with an explainable per-result score breakdown
- [x] Verified (`scripts/ranking_test.py`): authoritative recent decision outranks old
      tentative fact. Grounded in Generative Agents (arXiv:2304.03442).

### Stage 9.5 — LLM importance (make it genuinely intelligent)  ✅ DONE
- [x] `score_importance_llm()`: real LLM rating 1-10 via Cognee's cloud LLM (no extra key)
- [x] Heuristic fallback; deliberate writes use LLM, background auto-capture uses heuristic
- [x] Verified: policy statement -> 9/10, trivial chatter -> 2/10 (calibrated, not keyword)
- Note (honesty): recall semantics + conflict detection + importance are now real AI;
  trust weights remain an explicit admin policy (normal for production systems).

### Stage 12 — Evaluation harness  ✅ DONE
- [x] `scripts/eval_harness.py`: measures cross-agent recall@1, tenant isolation, ranking
- [x] Live results: recall@1 **4/4 (100%)**, isolation **2/2 (100% non-leak)**, ranking **PASS**
- [x] Metrics table added to README ("Evaluation — measured, not claimed")

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
  Dashboard visually confirmed by user (screenshot): 3 agents, resolved conflict.
- 2026-07-04 — Stage 6 done: auto-capture hook (UserPromptSubmit -> /remember) with
  importance filter; ~950ms via background ingestion; questions filtered. API server
  is now the live hub. remember(background=True) added.
- 2026-07-04 — Stage 7 docs: README (diagram+citations), LICENSE, DEMO.md. Deep-dive PDF
  generated locally (gitignored, user reference only).
- 2026-07-04 — Stage 8 done: MULTI-TENANCY. tenant end-to-end; isolation test passed.
  Critical finding: graph/RAG completion recall leaks across datasets in a shared Cognee
  tenant -> switched recall to dataset-scoped CHUNKS (isolated). CACHING=false. forget syncs ledger.
- 2026-07-05 — Stage 9 done: RETRIEVAL INTELLIGENCE. recall re-ranks by
  relevance+recency+importance x trust (Generative Agents scoring); importance stored in
  ledger. Verified authoritative/recent facts outrank stale ones.
- 2026-07-05 — Stage 9.5: LLM-based importance scoring via Cognee cloud LLM (policy 9/10,
  chatter 2/10). Adversarial proof: semantic recall with zero keyword overlap works.
- 2026-07-05 — Stage 12 done: eval harness. recall@1 4/4 (100%), isolation 2/2 (100%),
  ranking PASS. Metrics in README.
