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

from typing import Any

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
# Provenance helpers
# --------------------------------------------------------------------------
def provenance_tags(agent: str, session: str, project: str) -> list[str]:
    """Stable provenance tags used as the Cognee node_set for a memory.

    Filtering recall by any of these (via node_name) answers questions like
    "what did the claude-code agent teach us about this project?".
    """
    tags = [f"agent:{agent}", f"project:{project}"]
    if session:
        tags.append(f"session:{session}")
    return tags


def dataset_for(project: str) -> str:
    """One Cognee dataset per project, so forget()/improve() scope cleanly."""
    return "passport_" + project.strip().replace(" ", "_").lower()


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
    background: bool = False,
) -> Any:
    """Ingest a memory, tagged with provenance. Also recorded in the local ledger.

    background=True queues Cognee ingestion and returns fast (used by auto-capture
    so it never blocks a turn); the ledger is updated immediately either way.
    """
    await connect()
    result = await cognee.remember(
        text,
        dataset_name=dataset_for(project),
        node_set=provenance_tags(agent, session, project),
        run_in_background=background,
    )
    # Mirror into the provenance ledger (who taught what) for the dashboard + conflicts.
    try:
        ledger.record_memory(agent=agent, session=session, project=project, text=text)
    except Exception:
        pass
    return result


async def recall(
    query: str,
    *,
    agent: str | None = None,
    project: str = "default",
    top_k: int = 10,
) -> list[Any]:
    """Hybrid (vector + graph) recall. Optionally scope to one agent's memories."""
    await connect()
    node_name = [f"agent:{agent}"] if agent else None
    return await cognee.recall(
        query,
        datasets=[dataset_for(project)],
        node_name=node_name,
        top_k=top_k,
        auto_route=True,
    )


async def improve(*, project: str = "default", node_name: list[str] | None = None) -> Any:
    """Post-ingestion enrichment / conflict reconciliation (memify)."""
    await connect()
    return await cognee.improve(dataset=dataset_for(project), node_name=node_name)


async def forget(*, project: str | None = None, everything: bool = False) -> dict:
    """Surgically delete a project's memory, or wipe everything."""
    await connect()
    if everything:
        return await cognee.forget(everything=True)
    if not project:
        raise ValueError("forget() needs a project, or everything=True")
    return await cognee.forget(dataset=dataset_for(project))


# --------------------------------------------------------------------------
# Conflict detection + reconciliation (the "Best Use of Cognee" differentiator)
# --------------------------------------------------------------------------
async def detect_conflicts(*, project: str = "default") -> dict:
    """Ask Cognee's LLM to surface contradictory memories in a project.

    Returns {"has_conflicts": bool, "conflicts": [str], "raw": str} and records
    any found conflicts in the ledger for the dashboard.
    """
    await connect()
    results = await cognee.recall(
        "Find any contradictory or conflicting facts among the stored memories about "
        "databases, languages, tools, settings, conventions, and decisions.",
        datasets=[dataset_for(project)],
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
            ledger.record_conflict(project=project, description=desc)
        except Exception:
            pass
    return {"has_conflicts": bool(conflicts), "conflicts": conflicts, "raw": raw}


async def reconcile(*, project: str = "default", resolution: str | None = None,
                    agent: str = "passport") -> dict:
    """Reconcile a project's memory: record an authoritative resolution fact, mark
    ledger conflicts resolved, and run improve()/memify if the backend supports it.

    Note: memify is not exposed on Cognee Cloud (404), so it runs only in
    self-hosted/OSS mode; reconciliation still works via the resolution fact.
    """
    await connect()
    memify = {"ran": False, "detail": None}
    try:
        improved = await cognee.improve(dataset=dataset_for(project))
        memify = {"ran": True, "detail": _text_of(improved) if improved else None}
    except Exception as e:
        memify = {"ran": False, "detail": f"memify not available on this backend ({e})"}

    if resolution:
        await remember(resolution, agent=agent, session="reconcile", project=project)
    try:
        ledger.mark_conflicts_resolved(project)
    except Exception:
        pass
    return {"ok": True, "resolution": resolution, "memify": memify}
