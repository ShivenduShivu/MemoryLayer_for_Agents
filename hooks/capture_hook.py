"""Claude Code UserPromptSubmit hook: auto-capture durable facts into Passport.

Reads the hook JSON on stdin. If the user's message looks like a durable fact,
preference, or decision (not a question/command/small talk), it POSTs it to the
running Passport API's /remember. This makes memory capture AUTOMATIC — the model
doesn't have to decide to call a tool.

Design notes:
  * Lightweight: imports only passport.config (no Cognee) and POSTs over HTTP to
    the already-running Passport API server, which holds the warm Cognee session.
  * An "importance" filter avoids flooding memory with noise (research: importance-
    scored retention, Generative Agents / MemGPT).
  * Fails silently and always exits 0, so it can never block your turn.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from passport import config  # noqa: E402  (config-only; does NOT import Cognee)

_SKIP_PREFIXES = (
    "write ", "create ", "fix ", "run ", "show ", "list ", "explain ", "add ",
    "how ", "what ", "why ", "when ", "where ", "who ", "can you", "could you",
    "please ", "help ", "debug ", "refactor ", "implement ", "generate ", "make ",
)
_KEEP_HINTS = (
    "we use", "we prefer", "i prefer", "our ", "always", "never", "remember",
    "the project", "convention", "decision", "we deploy", "database", "stack",
    "we're using", "we are using", "standard is", "rule:", "note:", "policy",
)


def looks_durable(text: str) -> bool:
    t = text.strip()
    if len(t) < 15 or t.endswith("?"):
        return False
    low = t.lower()
    if low.startswith(_SKIP_PREFIXES):
        return False
    return any(h in low for h in _KEEP_HINTS)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt = (data.get("prompt") or "").strip()
    if not looks_durable(prompt):
        return

    payload = json.dumps({
        "text": prompt,
        "agent": os.getenv("PASSPORT_AGENT", "claude-code"),
        "project": os.getenv("PASSPORT_PROJECT", "fleet"),
        "tenant": os.getenv("PASSPORT_TENANT", "default"),
        "session": "auto-capture",
        "background": True,  # queue Cognee ingestion; server returns fast
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{config.PASSPORT_PORT}/remember",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "X-Passport-Key": config.PASSPORT_API_KEY},
    )
    try:
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass  # never block the user's turn


if __name__ == "__main__":
    main()
