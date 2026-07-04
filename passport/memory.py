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

from . import config

_connected = False


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
) -> Any:
    """Ingest a memory, tagged with provenance."""
    await connect()
    return await cognee.remember(
        text,
        dataset_name=dataset_for(project),
        node_set=provenance_tags(agent, session, project),
    )


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
