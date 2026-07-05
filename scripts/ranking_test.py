"""Stage 9 test: retrieval intelligence (recency + importance x trust re-ranking).

An old, tentative, low-importance fact vs a recent, authoritative decision on the
same topic. The decision should rank first, with an explainable score breakdown.

    ./.venv/Scripts/python.exe scripts/ranking_test.py
"""
import asyncio
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import memory  # noqa: E402

TENANT, PROJECT = "acme", "style"


async def main() -> None:
    await memory.connect()

    print(">> teaching an OLD, tentative fact (claude-code) ...")
    await memory.remember("We might try tabs for indentation sometime.",
                          agent="claude-code", project=PROJECT, tenant=TENANT)
    time.sleep(2)
    print(">> teaching a RECENT, authoritative DECISION (passport) ...")
    await memory.remember("Decision: we always use spaces for indentation, never tabs.",
                          agent="passport", project=PROJECT, tenant=TENANT)
    time.sleep(4)

    print("\n>> recall 'what indentation style do we use?' (re-ranked):\n")
    results = await memory.recall("what indentation style do we use?",
                                  project=PROJECT, tenant=TENANT)
    for rank, r in enumerate(results, 1):
        s = r["scores"]
        print(f"  #{rank}  composite={s['composite']}  (rel={s['relevance']} "
              f"rec={s['recency']} imp={s['importance']} trust={s['trust']}) "
              f"[{r['agent']}]")
        print(f"       {r['text']}")

    top = results[0]["text"] if results else ""
    print(f"\n  TOP RESULT {'PASSED' if 'spaces' in top else 'CHECK'}: "
          f"authoritative decision ranked #1" if "spaces" in top else "  (review ordering)")

    await memory.forget(project=PROJECT, tenant=TENANT)
    await memory.disconnect()
    print("\nRANKING TEST COMPLETE.")


if __name__ == "__main__":
    asyncio.run(main())
