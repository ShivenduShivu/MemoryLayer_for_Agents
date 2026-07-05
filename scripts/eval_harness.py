"""Stage 12 — evaluation harness. Turns Passport's claims into measured numbers.

Measures three things against the live Cognee backend:
  1. Cross-agent recall accuracy  — facts taught by one agent, retrieved by a
     tenant-level query (recall@1: does the top result contain the answer?).
  2. Tenant isolation             — two tenants with contradictory facts; neither
     may see the other's (leakage rate must be 0).
  3. Ranking correctness          — an authoritative recent decision must outrank
     an old tentative note on the same topic.

    ./.venv/Scripts/python.exe scripts/eval_harness.py
"""
import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import memory  # noqa: E402


async def _seed(tenant, project, facts, agent="claude-code"):
    for text in facts:
        await memory.remember(text, agent=agent, project=project, tenant=tenant)


async def suite_cross_agent_recall():
    tenant, project = "eval_xagent", "proj"
    cases = [
        ("Our CI runs on GitHub Actions.", "Where does our CI pipeline execute?", "GitHub Actions"),
        ("The payment service is written in Go.", "Which language powers the payments backend?", "Go"),
        ("We cache user sessions in Redis.", "What stores our session cache?", "Redis"),
        ("The design system is built with Tailwind CSS.", "What styling framework does the UI use?", "Tailwind"),
    ]
    await _seed(tenant, project, [t for t, _, _ in cases], agent="claude-code")
    await asyncio.sleep(5)
    hits = 0
    for _, query, expect in cases:  # recalled tenant-wide (i.e. by any other agent)
        res = await memory.recall(query, project=project, tenant=tenant)
        top = (res[0]["text"] if res else "").lower()
        if expect.lower() in top:
            hits += 1
    await memory.forget(project=project, tenant=tenant)
    return hits, len(cases)


async def suite_isolation():
    proj = "policy"
    await _seed("eval_tenantA", proj, ["Our admin password rotation is every 30 days."])
    await _seed("eval_tenantB", proj, ["Our admin password rotation is every 90 days."])
    await asyncio.sleep(5)
    leaks = 0
    ra = " ".join(r["text"] for r in await memory.recall("How often do we rotate the admin password?", project=proj, tenant="eval_tenantA"))
    rb = " ".join(r["text"] for r in await memory.recall("How often do we rotate the admin password?", project=proj, tenant="eval_tenantB"))
    if "90" in ra:  # tenant A must not see B's 90-day value
        leaks += 1
    if "30" in rb:  # tenant B must not see A's 30-day value
        leaks += 1
    await memory.forget(project=proj, tenant="eval_tenantA")
    await memory.forget(project=proj, tenant="eval_tenantB")
    return (2 - leaks), 2


async def suite_ranking():
    tenant, project = "eval_rank", "style"
    await memory.remember("We might try tabs for indentation sometime.",
                          agent="claude-code", project=project, tenant=tenant)
    await asyncio.sleep(2)
    await memory.remember("Decision: we always use spaces for indentation, never tabs.",
                          agent="passport", project=project, tenant=tenant)
    await asyncio.sleep(4)
    res = await memory.recall("what indentation style do we use?", project=project, tenant=tenant)
    top = (res[0]["text"] if res else "").lower()
    await memory.forget(project=project, tenant=tenant)
    return "spaces" in top


async def main():
    await memory.connect()
    print("Running Passport evaluation harness (live)...\n")

    xa_hits, xa_total = await suite_cross_agent_recall()
    iso_ok, iso_total = await suite_isolation()
    rank_ok = await suite_ranking()

    await memory.disconnect()

    xa_pct = round(100 * xa_hits / xa_total)
    iso_pct = round(100 * iso_ok / iso_total)
    print("\n==================== RESULTS ====================")
    print(f"  Cross-agent recall @1 : {xa_hits}/{xa_total}  ({xa_pct}%)")
    print(f"  Tenant isolation      : {iso_ok}/{iso_total}  ({iso_pct}% non-leak)")
    print(f"  Ranking correctness   : {'PASS' if rank_ok else 'FAIL'}")
    print("================================================")
    print("\nMarkdown:")
    print("| Metric | Result |")
    print("|---|---|")
    print(f"| Cross-agent recall@1 | {xa_hits}/{xa_total} ({xa_pct}%) |")
    print(f"| Tenant isolation (non-leak) | {iso_ok}/{iso_total} ({iso_pct}%) |")
    print(f"| Ranking correctness | {'PASS' if rank_ok else 'FAIL'} |")


if __name__ == "__main__":
    asyncio.run(main())
