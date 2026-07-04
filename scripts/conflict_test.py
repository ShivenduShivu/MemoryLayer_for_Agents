"""Stage 4 test: conflict detection + reconciliation via the API.

Two agents teach contradictory facts -> Cognee's LLM flags the conflict ->
ledger records who-taught-what + the conflict -> reconcile() resolves it.

    ./.venv/Scripts/python.exe scripts/conflict_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from passport import config  # noqa: E402
from passport.server import app  # noqa: E402

KEY = {"X-Passport-Key": config.PASSPORT_API_KEY}
P = "conflictdemo"


def show(label, resp):
    print(f"\n=== {label} [{resp.status_code}] ===")
    print(resp.json())


with TestClient(app) as client:
    print(">> Two different agents teach contradictory facts ...")
    client.post("/remember", headers=KEY, json={
        "text": "Our primary database is PostgreSQL.", "agent": "claude-code", "project": P})
    client.post("/remember", headers=KEY, json={
        "text": "We have migrated our primary database to MySQL.", "agent": "cursor", "project": P})

    show("DETECT CONFLICTS (Cognee LLM)", client.post("/conflicts", headers=KEY, json={"project": P}))
    show("LEDGER (provenance + conflict log)", client.get("/ledger", headers=KEY, params={"project": P}))
    show("RECONCILE (improve + resolution)", client.post("/reconcile", headers=KEY, json={
        "project": P,
        "resolution": "Decision: the primary database is now MySQL (supersedes PostgreSQL).",
        "agent": "passport"}))

    client.post("/forget", headers=KEY, json={"project": P})

print("\nCONFLICT TEST COMPLETE.")
