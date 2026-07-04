"""Stage 2 test: exercise the Passport API end-to-end (in-process TestClient).

Uses a single persistent event loop (context-managed TestClient) so the
Cognee cloud session stays valid across requests. Does real cloud calls.

    ./.venv/Scripts/python.exe scripts/api_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from passport import config  # noqa: E402
from passport.server import app  # noqa: E402

KEY = {"X-Passport-Key": config.PASSPORT_API_KEY}
PROJECT = "apitest"


def show(label, resp):
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    print(f"[{resp.status_code}] {label}: {body}")


with TestClient(app) as client:
    show("health (no auth)", client.get("/health"))

    # auth must be enforced
    show("remember WITHOUT key -> expect 401",
         client.post("/remember", json={"text": "x", "agent": "a"}))

    show("remember (claude-code)", client.post("/remember", headers=KEY, json={
        "text": "We deploy on Fridays and our primary language is Rust.",
        "agent": "claude-code", "session": "s1", "project": PROJECT,
    }))

    show("recall", client.post("/recall", headers=KEY, json={
        "query": "When do we deploy and what language do we use?",
        "project": PROJECT,
    }))

    show("graph", client.get("/graph", headers=KEY))

    show("forget (cleanup)", client.post("/forget", headers=KEY, json={"project": PROJECT}))

print("\nAPI TEST COMPLETE.")
