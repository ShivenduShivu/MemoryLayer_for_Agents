"""Passport API server — FastAPI wrapping the Cognee memory engine.

Exposes the memory lifecycle over HTTP with a simple API-key header so any
client (the MCP server, the dashboard, curl) can remember / recall / improve /
forget and read the provenance graph.

Run locally:
    ./.venv/Scripts/python.exe -m uvicorn passport.server:app --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

import cognee
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import config, ledger, memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect once, on the server's event loop, so the Cognee (cloud) client
    # session lives for the whole process.
    await memory.connect()
    yield
    await memory.disconnect()


app = FastAPI(
    title="Passport",
    version="0.1.0",
    description="A shared memory layer for coding agents, powered by Cognee.",
    lifespan=lifespan,
)


async def require_key(x_passport_key: str = Header(default="")) -> None:
    if x_passport_key != config.PASSPORT_API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-Passport-Key")


def _serialize(obj: Any) -> Any:
    """Best-effort JSON-safe conversion for Cognee result objects."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------
class RememberBody(BaseModel):
    text: str
    agent: str
    session: str = ""
    project: str = "default"


class RecallBody(BaseModel):
    query: str
    agent: Optional[str] = None
    project: str = "default"
    top_k: int = 10


class ImproveBody(BaseModel):
    project: str = "default"
    node_name: Optional[list[str]] = None


class ForgetBody(BaseModel):
    project: Optional[str] = None
    everything: bool = False


class ConflictBody(BaseModel):
    project: str = "default"


class ReconcileBody(BaseModel):
    project: str = "default"
    resolution: Optional[str] = None
    agent: str = "passport"


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "passport", "mode": config.COGNEE_MODE}


@app.post("/remember", dependencies=[Depends(require_key)])
async def remember_endpoint(body: RememberBody) -> dict:
    result = await memory.remember(
        body.text, agent=body.agent, session=body.session, project=body.project
    )
    return {
        "ok": True,
        "provenance": memory.provenance_tags(body.agent, body.session, body.project),
        "result": _serialize(result),
    }


@app.post("/recall", dependencies=[Depends(require_key)])
async def recall_endpoint(body: RecallBody) -> dict:
    results = await memory.recall(
        body.query, agent=body.agent, project=body.project, top_k=body.top_k
    )
    return {"ok": True, "count": len(results), "results": _serialize(results)}


@app.post("/improve", dependencies=[Depends(require_key)])
async def improve_endpoint(body: ImproveBody) -> dict:
    # memify is not exposed on Cognee Cloud (404); degrade gracefully.
    try:
        result = await memory.improve(project=body.project, node_name=body.node_name)
        return {"ok": True, "result": _serialize(result)}
    except Exception as e:
        return {"ok": False, "error": f"memify not available on this backend: {e}"}


@app.post("/forget", dependencies=[Depends(require_key)])
async def forget_endpoint(body: ForgetBody) -> dict:
    result = await memory.forget(project=body.project, everything=body.everything)
    return {"ok": True, "result": _serialize(result)}


@app.post("/conflicts", dependencies=[Depends(require_key)])
async def conflicts_endpoint(body: ConflictBody) -> dict:
    result = await memory.detect_conflicts(project=body.project)
    return {"ok": True, **result}


@app.post("/reconcile", dependencies=[Depends(require_key)])
async def reconcile_endpoint(body: ReconcileBody) -> dict:
    result = await memory.reconcile(
        project=body.project, resolution=body.resolution, agent=body.agent
    )
    return result


@app.get("/ledger", dependencies=[Depends(require_key)])
async def ledger_endpoint(project: Optional[str] = None) -> dict:
    """Provenance ledger: who taught what, plus the conflict log (dashboard source)."""
    return {
        "ok": True,
        "memories": ledger.list_memories(project),
        "conflicts": ledger.list_conflicts(project),
    }


@app.get("/graph", dependencies=[Depends(require_key)])
async def graph_endpoint(include_memory: bool = True) -> dict:
    """Provenance graph: nodes + edges showing which agent taught what."""
    await memory.connect()
    try:
        nodes, edges = await cognee.get_memory_provenance_graph(include_memory=include_memory)
        return {"ok": True, "nodes": _serialize(nodes), "edges": _serialize(edges)}
    except Exception as e:  # graph backend may differ in cloud; don't 500 the demo
        return {"ok": False, "error": str(e), "nodes": [], "edges": []}
