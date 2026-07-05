"""Seed the public demo workspace (tenant=demo, project=webapp) into Cognee, so the
deployed dashboard's live Recall / Detect-conflicts buttons return real results.

Reads the SAME facts the dashboard shows (dashboard/demo_seed.json). Run once.

    ./.venv/Scripts/python.exe scripts/seed_demo_cloud.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import memory  # noqa: E402

SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "dashboard", "demo_seed.json")


async def main() -> None:
    data = json.load(open(SEED, encoding="utf-8"))
    t, p = data["tenant"], data["project"]
    await memory.connect()
    print(f">> seeding {len(data['memories'])} facts into Cognee ({t}/{p}) ...")
    for m in data["memories"]:
        await memory.remember(m["text"], agent=m["agent"], project=p, tenant=t)
        print(f"   + [{m['agent']}] {m['text']}")
    await memory.disconnect()
    print("\nDONE. The deployed dashboard's live Recall/Detect now work on demo/webapp.")


if __name__ == "__main__":
    asyncio.run(main())
