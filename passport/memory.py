"""Passport memory engine — a thin, provenance-aware wrapper over Cognee.

Design goals:
  * Every write is tagged with a `node_set` that encodes provenance
    (which agent / session / project produced the memory). node_set is
    Cognee's native grouping + access-control primitive, so we get
    provenance filtering and scoped recall for free.
  * Cloud vs local is a single switch (config.COGNEE_MODE). In cloud mode
    we call `cognee.serve()` once, which routes all subsequent
    remember/recall/improve/forget calls to the Cognee Cloud tenant.

All public functions are async (Cognee's V2 API is async).
"""
from __future__ import annotations

import math
import os
import time
from typing import Any

# Disable Cognee's session memory/cache BEFORE importing cognee, so recall reflects
# the actual per-tenant dataset (not stale cross-session context). Critical for
# tenant isolation. (Cognee 1.0 enables session memory by default.)
os.environ.setdefault("CACHING", "false")

import cognee

from . import config, ledger

_connected = False

# System prompt that turns a normal recall into a contradiction detector,
# using Cognee's own (cloud) LLM — no extra provider key needed.
_CONFLICT_SYSTEM_PROMPT = (
    "You are a memory conflict detector for a team's shared knowledge base. "
    "From the provided context of stored memories, identify pairs of statements that "
    "DIRECTLY CONTRADICT each other (same subject, incompatible values — for example "
    "'the database is Postgres' vs 'the database is MySQL'). "
    "For EACH conflict output exactly one line in the form: "
    "CONFLICT: <subject> - '<statement A>' vs '<statement B>'. "
    "If there are no contradictions, output exactly: NO CONFLICTS."
)


def _text_of(item: Any) -> str:
    for attr in ("text", "answer"):
        v = getattr(item, attr, None)
        if v:
            return v
    if isinstance(item, dict):
        return item.get("text") or item.get("answer") or str(item)
    return str(item)


# --------------------------------------------------------------------------
# Retrieval intelligence (Stage 9): score recalled facts by
# relevance + recency + importance, boosted by source trust.
# (Generative Agents, arXiv:2304.03442.)
# --------------------------------------------------------------------------
_RECENCY_TAU_DAYS = 14.0          # exponential recency decay constant
_RANK_WEIGHTS = {"relevance": 0.5, "recency": 0.25, "importance": 0.25}
_TRUST = {"passport": 1.3}        # reconciliation/decision facts are authoritative


def score_importance(text: str) -> int:
    """Heuristic 1-10 importance: durable/decisive statements score higher."""
    t = text.lower()
    score = 3
    for kw, pts in (("always", 3), ("never", 3), ("decision", 3), ("must", 2),
                    ("convention", 2), ("prefer", 2), ("standard", 2), ("policy", 2),
                    ("we use", 1), ("our ", 1), ("rule", 2)):
        if kw in t:
            score += pts
    return max(1, min(10, score))


def _trust_for(agent: str | None) -> float:
    return _TRUST.get(agent or "", 1.0)


def _rerank(candidates: list[Any], tenant: str, project: str) -> list[dict]:
    """Re-rank raw recall candidates using ledger metadata. Returns enriched dicts
    with an explainable score breakdown, sorted best-first."""
    mems = {m["text"].strip(): m for m in ledger.list_memories(tenant, project)}
    now = time.time()
    n = max(1, len(candidates))
    out: list[dict] = []
    for i, cand in enumerate(candidates):
        text = _text_of(cand).strip()
        relevance = 1.0 - i / n  # Cognee returns candidates in relevance order
        m = mems.get(text)
        if m:
            age_days = max(0.0, (now - (m.get("created_at") or now)) / 86400.0)
            recency = math.exp(-age_days / _RECENCY_TAU_DAYS)
            importance = (m.get("importance") or 3) / 10.0
            agent = m.get("agent")
        else:
            recency, importance, agent = 0.5, 0.3, None
        trust = _trust_for(agent)
        base = (_RANK_WEIGHTS["relevance"] * relevance
                + _RANK_WEIGHTS["recency"] * recency
                + _RANK_WEIGHTS["importance"] * importance)
        composite = base * trust
        out.append({
            "text": text,
            "agent": agent,
            "created_at": m.get("created_at") if m else None,
            "scores": {
                "relevance": round(relevance, 3),
                "recency": round(recency, 3),
                "importance": round(importance, 3),
                "trust": round(trust, 3),
                "composite": round(composite, 4),
            },
        })
    out.sort(key=lambda d: d["scores"]["composite"], reverse=True)
    return out


# --------------------------------------------------------------------------
# Provenance helpers
# --------------------------------------------------------------------------
def provenance_tags(agent: str, session: str, project: str, tenant: str) -> list[str]:
    """Stable provenance tags used as the Cognee node_set for a memory.

    Filtering recall by any of these (via node_name) answers questions like
    "what did the claude-code agent teach us about this project?".
    """
    tags = [f"tenant:{tenant}", f"agent:{agent}", f"project:{project}"]
    if session:
        tags.append(f"session:{session}")
    return tags


def _clean(s: str) -> str:
    return s.strip().replace(" ", "_").lower()


def dataset_for(tenant: str, project: str) -> str:
    """One Cognee dataset per (tenant, project). Tenant-namespacing isolates users:
    recall only searches the caller's tenant dataset, so users can't see each
    other's memory."""
    return f"passport_{_clean(tenant)}_{_clean(project)}"


# --------------------------------------------------------------------------
# Connection lifecycle
# --------------------------------------------------------------------------
async def connect() -> None:
    """Idempotently connect to the backend. No-op in local/OSS mode."""
    global _connected
    if _connected:
        return
    config.validate()
    if config.is_cloud():
        await cognee.serve(url=config.COGNEE_CLOUD_URL, api_key=config.COGNEE_API_KEY)
    _connected = True


async def disconnect() -> None:
    global _connected
    if _connected and config.is_cloud():
        await cognee.disconnect()
    _connected = False


# --------------------------------------------------------------------------
# Core lifecycle: remember / recall / improve / forget
# --------------------------------------------------------------------------
async def remember(
    text: str,
    *,
    agent: str,
    session: str = "",
    project: str = "default",
    tenant: str = "default",
    background: bool = False,
) -> Any:
    """Ingest a memory, tagged with provenance. Also recorded in the local ledger.

    background=True queues Cognee ingestion and returns fast (used by auto-capture
    so it never blocks a turn); the ledger is updated immediately either way.
    """
    await connect()
    result = await cognee.remember(
        text,
        dataset_name=dataset_for(tenant, project),
        node_set=provenance_tags(agent, session, project, tenant),
        run_in_background=background,
    )
    # Mirror into the provenance ledger (who taught what) for the dashboard + conflicts.
    try:
        ledger.record_memory(tenant=tenant, agent=agent, session=session, project=project,
                             text=text, importance=score_importance(text))
    except Exception:
        pass
    return result


async def recall(
    query: str,
    *,
    agent: str | None = None,
    project: str = "default",
    tenant: str = "default",
    top_k: int = 10,
) -> list[Any]:
    """Recall the caller's own stored facts, HARD-scoped to their tenant dataset.

    We use dataset-scoped CHUNKS retrieval (not graph/RAG completion) because it is
    provably isolated per dataset — completion modes can surface cross-dataset
    associations from a shared Cognee tenant. Passport returns the tenant's faithful
    facts; the calling agent synthesizes. Optionally further scope to one agent.
    """
    await connect()
    node_name = [f"agent:{agent}"] if agent else None
    candidates = await cognee.recall(
        query,
        datasets=[dataset_for(tenant, project)],
        query_type=cognee.SearchType.CHUNKS,
        auto_route=False,
        node_name=node_name,
        top_k=top_k,
    )
    # Re-rank by relevance + recency + importance x trust (Stage 9).
    return _rerank(candidates, tenant, project)


async def improve(*, project: str = "default", tenant: str = "default",
                  node_name: list[str] | None = None) -> Any:
    """Post-ingestion enrichment / conflict reconciliation (memify)."""
    await connect()
    return await cognee.improve(dataset=dataset_for(tenant, project), node_name=node_name)


async def forget(*, project: str | None = None, tenant: str = "default",
                 everything: bool = False) -> dict:
    """Surgically delete a project's memory (Cognee + ledger), or wipe everything."""
    await connect()
    if everything:
        return await cognee.forget(everything=True)
    if not project:
        raise ValueError("forget() needs a project, or everything=True")
    res = await cognee.forget(dataset=dataset_for(tenant, project))
    try:
        ledger.delete_project(tenant, project)  # keep ledger in sync (Stage 10 consistency)
    except Exception:
        pass
    return res


# --------------------------------------------------------------------------
# Conflict detection + reconciliation (the "Best Use of Cognee" differentiator)
# --------------------------------------------------------------------------
async def detect_conflicts(*, project: str = "default", tenant: str = "default") -> dict:
    """Ask Cognee's LLM to surface contradictory memories in a project.

    Returns {"has_conflicts": bool, "conflicts": [str], "raw": str} and records
    any found conflicts in the ledger for the dashboard.
    """
    await connect()
    results = await cognee.recall(
        "Find any contradictory or conflicting facts among the stored memories about "
        "databases, languages, tools, settings, conventions, and decisions.",
        datasets=[dataset_for(tenant, project)],
        system_prompt=_CONFLICT_SYSTEM_PROMPT,
        top_k=50,
        auto_route=True,
    )
    raw = "\n".join(_text_of(r) for r in results).strip()
    conflicts = [
        line.strip()
        for line in raw.splitlines()
        if line.strip().upper().startswith("CONFLICT:")
    ]
    for desc in conflicts:
        try:
            ledger.record_conflict(tenant=tenant, project=project, description=desc)
        except Exception:
            pass
    return {"has_conflicts": bool(conflicts), "conflicts": conflicts, "raw": raw}


async def reconcile(*, project: str = "default", tenant: str = "default",
                    resolution: str | None = None, agent: str = "passport") -> dict:
    """Reconcile a project's memory: record an authoritative resolution fact, mark
    ledger conflicts resolved, and run improve()/memify if the backend supports it.

    Note: memify is not exposed on Cognee Cloud (404), so it runs only in
    self-hosted/OSS mode; reconciliation still works via the resolution fact.
    """
    await connect()
    memify = {"ran": False, "detail": None}
    try:
        improved = await cognee.improve(dataset=dataset_for(tenant, project))
        memify = {"ran": True, "detail": _text_of(improved) if improved else None}
    except Exception as e:
        memify = {"ran": False, "detail": f"memify not available on this backend ({e})"}

    if resolution:
        await remember(resolution, agent=agent, session="reconcile", project=project, tenant=tenant)
    try:
        ledger.mark_conflicts_resolved(tenant, project)
    except Exception:
        pass
    return {"ok": True, "resolution": resolution, "memify": memify}
