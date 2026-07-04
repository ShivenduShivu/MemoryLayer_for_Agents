"""Stage 1 smoke test: prove remember -> recall works against the backend.

Run from the project root with the venv active:
    ./.venv/Scripts/python.exe scripts/smoke_test.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import memory  # noqa: E402

PROJECT = "smoketest"


async def main() -> None:
    print(">> connecting to Cognee backend ...")
    await memory.connect()
    print("   connected.\n")

    print(">> remember() — teaching a fact as agent 'claude-code' ...")
    await memory.remember(
        "We use pytest for testing, never unittest. Our database is Postgres.",
        agent="claude-code",
        session="s1",
        project=PROJECT,
    )
    print("   ingested.\n")

    print(">> recall() — asking a different question that needs that memory ...")
    results = await memory.recall(
        "What testing framework and which database does this project use?",
        project=PROJECT,
    )
    print(f"   got {len(results)} result(s):")
    for i, item in enumerate(results, 1):
        text = getattr(item, "text", None) or getattr(item, "answer", None) or str(item)
        print(f"   [{i}] {text}")

    print("\n>> cleaning up (forget smoketest project) ...")
    await memory.forget(project=PROJECT)
    print("   done.")

    await memory.disconnect()
    print("\nSMOKE TEST COMPLETE.")


if __name__ == "__main__":
    asyncio.run(main())
