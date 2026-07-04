# Passport — a shared memory layer for coding agents

Teach one AI coding agent (Claude Code) something, and your other agents
(Cursor, Codex) know it too — with full provenance (which agent learned what,
and when) and automatic conflict reconciliation. One self-hosted-capable brain
for your whole agent fleet, powered by [Cognee](https://github.com/topoteretes/cognee).

Built for **The Hangover Part AI** hackathon (WeMakeDevs x Cognee).

## Why it's different

Every published agent-memory system (MemGPT, Mem0, Zep, A-MEM) is **single-agent**.
Passport is a **shared memory substrate for a heterogeneous fleet of agents**, adding
what none of them combine: per-agent provenance + trust weighting, cross-agent conflict
reconciliation, and bi-temporal recall.

## Architecture (short)

```
Claude Code / Codex / Cursor  --MCP-->  Passport Server (FastAPI)  --SDK-->  Cognee
                                              |                                  |
                                        Streamlit dashboard  <-------------------+
```

- **Passport Server** — wraps Cognee; tags every memory with source agent/session
  (via Cognee `node_set`); detects + reconciles conflicts; serves recall.
- **MCP server** — exposes `remember` / `recall` / `forget` so any MCP client plugs in.
- **Dashboard** — live knowledge graph colored by source agent + conflict log.

## Setup

1. `pip install -r requirements.txt`
2. `cp .env.template .env` and fill in your Cognee Cloud key + tenant URL
   (from platform.cognee.ai -> API Keys). Redeem code `COGNEE-35` for the free Developer plan.
3. (build steps land here as we go)

## Cognee lifecycle used

`remember` (ingest + provenance) · `recall` (hybrid graph+vector) ·
`improve`/memify (conflict reconciliation) · `forget` (surgical delete).

## Status

Scaffolding. See PRD for the full spec and 48h plan.
