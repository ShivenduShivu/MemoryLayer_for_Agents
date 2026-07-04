"""Provenance ledger — a local SQLite record of every memory Passport stores.

Why this exists: Cognee's built-in provenance graph reads a local system DB that
is empty in cloud mode, so we keep our OWN lightweight ledger of who-taught-what.
It's the source of truth for the dashboard (Stage 5) and the conflict log.

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


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT, session TEXT, project TEXT, text TEXT, created_at REAL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS conflicts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT, description TEXT, created_at REAL, resolved INTEGER DEFAULT 0)"""
        )


def record_memory(agent: str, session: str, project: str, text: str, ts: float | None = None) -> None:
    init()
    with _conn() as c:
        c.execute(
            "INSERT INTO memories(agent,session,project,text,created_at) VALUES(?,?,?,?,?)",
            (agent, session, project, text, ts if ts is not None else time.time()),
        )


def list_memories(project: str | None = None) -> list[dict]:
    init()
    with _conn() as c:
        if project:
            rows = c.execute(
                "SELECT id,agent,session,project,text,created_at FROM memories WHERE project=? ORDER BY created_at",
                (project,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id,agent,session,project,text,created_at FROM memories ORDER BY created_at"
            ).fetchall()
    return [
        {"id": r[0], "agent": r[1], "session": r[2], "project": r[3], "text": r[4], "created_at": r[5]}
        for r in rows
    ]


def record_conflict(project: str, description: str, ts: float | None = None) -> None:
    init()
    with _conn() as c:
        c.execute(
            "INSERT INTO conflicts(project,description,created_at) VALUES(?,?,?)",
            (project, description, ts if ts is not None else time.time()),
        )


def list_conflicts(project: str | None = None) -> list[dict]:
    init()
    with _conn() as c:
        if project:
            rows = c.execute(
                "SELECT id,project,description,created_at,resolved FROM conflicts WHERE project=? ORDER BY created_at DESC",
                (project,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id,project,description,created_at,resolved FROM conflicts ORDER BY created_at DESC"
            ).fetchall()
    return [
        {"id": r[0], "project": r[1], "description": r[2], "created_at": r[3], "resolved": bool(r[4])}
        for r in rows
    ]


def mark_conflicts_resolved(project: str) -> None:
    init()
    with _conn() as c:
        c.execute("UPDATE conflicts SET resolved=1 WHERE project=?", (project,))
