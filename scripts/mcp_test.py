"""Stage 3 test: spawn the Passport MCP server as a real MCP client and
exercise its tools. Verifies the server works before wiring it into IDEs.

    ./.venv/Scripts/python.exe scripts/mcp_test.py
"""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


async def main() -> None:
    # Launch via the absolute-path launcher from a DIFFERENT working directory
    # (home dir) to prove the server is cwd-independent, like an IDE would.
    params = StdioServerParameters(
        command=sys.executable,  # the venv python running this test
        args=[os.path.join(ROOT, "run_mcp.py"), "--agent", "test-agent", "--project", "stage3check"],
        cwd=os.path.expanduser("~"),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])

            r = await session.call_tool(
                "passport_remember",
                {"text": "Passport MCP test fact: the project mascot is a wolf named Doug."},
            )
            print("REMEMBER:", r.content[0].text)

            r = await session.call_tool("passport_recall", {"query": "what is the mascot and its name?"})
            print("RECALL:", r.content[0].text)

            r = await session.call_tool("passport_forget", {"project": "stage3check"})
            print("FORGET:", r.content[0].text)

    print("\nMCP TEST COMPLETE.")


if __name__ == "__main__":
    asyncio.run(main())
