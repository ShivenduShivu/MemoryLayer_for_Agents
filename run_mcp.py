"""Standalone launcher for the Passport MCP server.

Registering this by ABSOLUTE path means IDEs (Claude Code, Cursor, Codex) can
launch it from any working directory — it adds its own folder to sys.path and
config.py loads .env by absolute path.

    <venv-python> C:\\...\\passport\\run_mcp.py --agent claude-code
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from passport.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
