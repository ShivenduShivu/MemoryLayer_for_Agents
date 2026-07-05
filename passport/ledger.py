"""Provenance ledger — a local SQLite record of every memory Passport stores.

Why this exists: Cognee's built-in provenance graph reads a local system DB that
is empty in cloud mode, so we keep our OWN lightweight ledger of who-taught-what.
It's the source of truth for the dashboard (Stage 5) and the conflict log.

Stage 8: every row is scoped to a `tenant` (a user/workspace) so multiple users
share the one file without seeing each other's memory.

All Passport processes (each IDE's MCP server, the API, the dashboard) share this
one file, so provenance aggregates across every agent.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_DB = Path(__file__).resolve().parent.parent / "ledger.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB, timeout=15)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _ensure_column(c: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT DEFAULT 'default',
                agent TEXT, session TEXT, project TEXT, text TEXT, created_at REAL,
                importance INTEGER DEFAULT 3)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS conflicts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT DEFAULT 'default',
                project TEXT, description TEXT, created_at REAL, resolved INTEGER DEFAULT 0)"""
        )
        # Migrate older databases that lack newer columns.
        _ensure_column(c, "memories", "tenant", "TEXT DEFAULT 'default'")
        _ensure_column(c, "memories", "importance", "INTEGER DEFAULT 3")
        _ensure_column(c, "conflicts", "tenant", "TEXT DEFAULT 'default'")


def record_memory(tenant: str, agent: str, session: str, project: str, text: str,
                  importance: int = 3, ts: float | None = None) -> None:
    init()
    with _conn() as c:
        c.execute(
            "INSERT INTO memories(tenant,agent,session,project,text,created_at,importance)"
            " VALUES(?,?,?,?,?,?,?)",
            (tenant, agent, session, project, text,
             ts if ts is not None else time.time(), importance),
        )


def list_memories(tenant: str | None = None, project: str | None = None) -> list[dict]:
    init()
    clauses, args = [], []
    if tenant:
        clauses.append("tenant=?"); args.append(tenant)
    if project:
        clauses.append("project=?"); args.append(project)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _conn() as c:
        rows = c.execute(
            f"SELECT id,tenant,agent,session,project,text,created_at,importance"
            f" FROM memories{where} ORDER BY created_at",
            args,
        ).fetchall()
    return [
        {"id": r[0], "tenant": r[1], "agent": r[2], "session": r[3],
         "project": r[4], "text": r[5], "created_at": r[6], "importance": r[7]}
        for r in rows
    ]


def record_conflict(tenant: str, project: str, description: str, ts: float | None = None) -> None:
    init()
    with _conn() as c:
        c.execute(
            "INSERT INTO conflicts(tenant,project,description,created_at) VALUES(?,?,?,?)",
            (tenant, project, description, ts if ts is not None else time.time()),
        )


def list_conflicts(tenant: str | None = None, project: str | None = None) -> list[dict]:
    init()
    clauses, args = [], []
    if tenant:
        clauses.append("tenant=?"); args.append(tenant)
    if project:
        clauses.append("project=?"); args.append(project)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _conn() as c:
        rows = c.execute(
            f"SELECT id,tenant,project,description,created_at,resolved FROM conflicts{where} ORDER BY created_at DESC",
            args,
        ).fetchall()
    return [
        {"id": r[0], "tenant": r[1], "project": r[2], "description": r[3],
         "created_at": r[4], "resolved": bool(r[5])}
        for r in rows
    ]


def mark_conflicts_resolved(tenant: str, project: str) -> None:
    init()
    with _conn() as c:
        c.execute("UPDATE conflicts SET resolved=1 WHERE tenant=? AND project=?", (tenant, project))


def delete_project(tenant: str, project: str) -> None:
    """Remove ledger rows for a project (keeps ledger in sync with forget())."""
    init()
    with _conn() as c:
        c.execute("DELETE FROM memories WHERE tenant=? AND project=?", (tenant, project))
        c.execute("DELETE FROM conflicts WHERE tenant=? AND project=?", (tenant, project))


def list_tenants() -> list[str]:
    init()
    with _conn() as c:
        rows = c.execute("SELECT DISTINCT tenant FROM memories ORDER BY tenant").fetchall()
    return [r[0] for r in rows]
