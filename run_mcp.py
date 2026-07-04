"""Standalone launcher for the Passport MCP server.

Registering this by ABSOLUTE path means IDEs (Claude Code, Cursor, Codex) can
launch it from any working directory — it adds its own folder to sys.path and
config.py loads .env by absolute path.

    <venv-python> C:\\...\\passport\\run_mcp.py --agent claude-code

IMPORTANT (Windows): MCP stdio uses STDOUT for its JSON-RPC protocol. Verbose
library logs on STDERR can fill an MCP client's unread stderr pipe and crash
tool calls with "[Errno 22] Invalid argument". So we quiet Cognee and redirect
STDERR to a log file BEFORE importing Cognee, so its logger binds to the file
(not the client's pipe). STDOUT is left untouched for the MCP protocol.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

os.environ.setdefault("LOG_LEVEL", "ERROR")
try:
    sys.stderr = open(os.path.join(ROOT, "mcp_server.log"), "a", buffering=1, encoding="utf-8")
except Exception:
    pass

from passport.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
