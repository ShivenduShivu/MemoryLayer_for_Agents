"""Passport MCP server — exposes the shared memory to any MCP client
(Claude Code, Cursor, Codex).

Each client launches this with its OWN --agent identity, so every memory is
tagged with which agent wrote it (provenance). All agents point at the same
Cognee tenant + project, so they share one brain.

Register (stdio). Example for Claude Code:
    claude mcp add passport -- <venv-python> -m passport.mcp_server --agent claude-code

MCP stdio uses STDOUT for its JSON-RPC protocol, so we defensively redirect any
stray library stdout to stderr inside each tool. (Cognee already logs to stderr.)
"""
from __future__ import annotations

import argparse
import contextlib
import os
import sys

from mcp.server.fastmcp import FastMCP

from . import memory


def _identity() -> tuple[str, str, str]:
    p = argparse.ArgumentParser(description="Passport MCP server")
    p.add_argument("--agent", default=os.getenv("PASSPORT_AGENT", "unknown-agent"))
    p.add_argument("--project", default=os.getenv("PASSPORT_PROJECT", "fleet"))
    p.add_argument("--tenant", default=os.getenv("PASSPORT_TENANT", "default"))
    args, _ = p.parse_known_args()
    return args.agent, args.project, args.tenant


AGENT, PROJECT, TENANT = _identity()
mcp = FastMCP("passport")


def _text_of(item) -> str:
    for attr in ("text", "answer"):
        v = getattr(item, attr, None)
        if v:
            return v
    if isinstance(item, dict):
        return item.get("text") or item.get("answer") or str(item)
    return str(item)


@mcp.tool()
async def passport_remember(text: str, session: str = "") -> str:
    """Save a durable fact, preference, decision, or convention into the shared
    team memory so every agent (Claude Code, Cursor, Codex) can recall it later.
    Use whenever the user states something worth remembering across sessions/tools."""
    with contextlib.redirect_stdout(sys.stderr):
        await memory.remember(text, agent=AGENT, session=session, project=PROJECT, tenant=TENANT)
    return f"Remembered (by {AGENT}): {text}"


@mcp.tool()
async def passport_recall(query: str) -> str:
    """Recall relevant facts from the shared team memory written by ANY agent.
    Use before answering when past preferences, decisions, or context may exist."""
    with contextlib.redirect_stdout(sys.stderr):
        results = await memory.recall(query, project=PROJECT, tenant=TENANT)
    if not results:
        return "No relevant memory found in the Passport."
    return "\n".join(f"- {_text_of(r)}" for r in results)


@mcp.tool()
async def passport_forget(project: str) -> str:
    """Delete all shared memories for a given project/workspace."""
    with contextlib.redirect_stdout(sys.stderr):
        await memory.forget(project=project, tenant=TENANT)
    return f"Forgot all memories for project: {project}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
