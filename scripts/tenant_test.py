"""Stage 8 test: tenant isolation.

Two users (alice, bob) store DIFFERENT facts in the SAME project name.
Each must recall only their own — no cross-tenant leakage.

    ./.venv/Scripts/python.exe scripts/tenant_test.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows console safety
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from passport import config  # noqa: E402
from passport.server import app  # noqa: E402

import time  # noqa: E402

KEY = {"X-Passport-Key": config.PASSPORT_API_KEY}
PROJ = "orgteam4"


def recall_text(resp) -> str:
    return " ".join(r.get("text", "") for r in resp.json().get("results", []))


with TestClient(app) as client:
    print(">> alice and bob store DIFFERENT mascots in the same project 'teaminfo' ...")
    client.post("/remember", headers=KEY, json={
        "text": "Our team mascot is a falcon named Skye.", "agent": "claude-code",
        "project": PROJ, "tenant": "alice"})
    client.post("/remember", headers=KEY, json={
        "text": "Our team mascot is a panda named Bao.", "agent": "claude-code",
        "project": PROJ, "tenant": "bob"})

    time.sleep(4)  # let cloud indexing settle
    a = recall_text(client.post("/recall", headers=KEY, json={
        "query": "What is our team mascot and its name?", "project": PROJ, "tenant": "alice"}))
    b = recall_text(client.post("/recall", headers=KEY, json={
        "query": "What is our team mascot and its name?", "project": PROJ, "tenant": "bob"}))

    print(f"\n  alice recalls: {a}")
    print(f"  bob   recalls: {b}")

    ok = ("Skye" in a and "Bao" not in a) and ("Bao" in b and "Skye" not in b)
    print(f"\n  ISOLATION {'PASSED' if ok else 'FAILED'} "
          f"(alice sees only Skye/falcon, bob sees only Bao/panda)")

    la = client.get("/ledger", headers=KEY, params={"tenant": "alice", "project": PROJ}).json()
    print(f"  alice ledger memories: {[m['text'] for m in la['memories']]}")

    client.post("/forget", headers=KEY, json={"project": PROJ, "tenant": "alice"})
    client.post("/forget", headers=KEY, json={"project": PROJ, "tenant": "bob"})
    print("  cleanup done.")

print("\nTENANT TEST COMPLETE.")
