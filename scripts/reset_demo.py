"""Reset a workspace (Cognee + ledger) so the dashboard starts empty on camera.

    ./.venv/Scripts/python.exe scripts/reset_demo.py [tenant] [project]
    (defaults: tenant=default  project=fleet)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import ledger, memory  # noqa: E402

TENANT = sys.argv[1] if len(sys.argv) > 1 else "default"
PROJECT = sys.argv[2] if len(sys.argv) > 2 else "fleet"


async def main() -> None:
    await memory.connect()
    try:
        await memory.forget(project=PROJECT, tenant=TENANT)
    except Exception as e:
        print("cognee forget note:", e)
    await memory.disconnect()
    try:
        ledger.delete_project(TENANT, PROJECT)
    except Exception:
        pass
    print(f"Reset {TENANT}/{PROJECT}: Cognee + ledger cleared. Graph is now empty.")


if __name__ == "__main__":
    asyncio.run(main())
