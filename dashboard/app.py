"""Passport dashboard — the visual centerpiece.

Reads the provenance ledger (SQLite, no cloud/credit needed) and renders:
  * a live knowledge graph colored by which agent taught each memory
  * per-agent metrics
  * a chronological memory timeline
  * the conflict log (open / resolved)
  * optional live demo controls (recall / detect conflicts) that hit Cognee

Run:
    ./.venv/Scripts/python.exe -m streamlit run dashboard/app.py
"""
import asyncio
import html
import json
import os
import sys
import time

import streamlit as st

# On Streamlit Community Cloud, expose secrets as env vars so config.py picks them up.
try:
    for _k in ("COGNEE_API_KEY", "COGNEE_CLOUD_URL", "COGNEE_MODE", "PASSPORT_API_KEY"):
        if _k in st.secrets:
            os.environ.setdefault(_k, str(st.secrets[_k]))
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Light import only (Cognee is imported lazily inside live controls, so the
# visual dashboard deploys cleanly even without the full stack / credentials).
from passport import ledger  # noqa: E402


def text_of(item):
    if isinstance(item, dict):
        return item.get("text") or item.get("answer") or str(item)
    for a in ("text", "answer"):
        v = getattr(item, a, None)
        if v:
            return v
    return str(item)


def seed_demo_if_empty():
    """Populate the ledger from demo_seed.json on a fresh deploy so the dashboard is
    never empty. Pure ledger writes — no Cognee/credit needed."""
    if ledger.list_memories():
        return
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_seed.json")
    if not os.path.exists(path):
        return
    data = json.load(open(path, encoding="utf-8"))
    t, p = data["tenant"], data["project"]
    for m in data["memories"]:
        ledger.record_memory(tenant=t, agent=m["agent"], session="seed", project=p,
                             text=m["text"], importance=m.get("importance", 5))
    for c in data.get("conflicts", []):
        ledger.record_conflict(tenant=t, project=p, description=c["description"])
        if c.get("resolved"):
            ledger.mark_conflicts_resolved(t, p)

# Stable-ish color per agent.
_PALETTE = ["#8ecae6", "#ffb703", "#90be6d", "#f28482", "#cdb4db", "#94d2bd", "#e9c46a"]


def color_for(agent: str) -> str:
    return _PALETTE[hash(agent) % len(_PALETTE)]


def run_async(coro, mem):
    """Run a Cognee coroutine from Streamlit on a fresh loop (reconnect each call)."""
    async def _wrap():
        mem._connected = False
        try:
            return await coro
        finally:
            await mem.disconnect()
    return asyncio.run(_wrap())


def build_dot(memories: list[dict]) -> str:
    lines = [
        "digraph Passport {",
        '  rankdir=LR; bgcolor="transparent";',
        '  node [style=filled, fontname="Helvetica", fontsize=11];',
        '  edge [color="#888888"];',
    ]
    agents = sorted({m["agent"] for m in memories})
    for a in agents:
        c = color_for(a)
        lines.append(f'  "agent::{a}" [shape=box, fillcolor="{c}", label="🤖 {a}", fontsize=13];')
    for m in memories:
        c = color_for(m["agent"])
        label = (m["text"][:46] + "…") if len(m["text"]) > 46 else m["text"]
        label = label.replace('"', "'")
        lines.append(f'  "mem::{m["id"]}" [shape=note, fillcolor="{c}", label="{label}"];')
        lines.append(f'  "agent::{m["agent"]}" -> "mem::{m["id"]}";')
    lines.append("}")
    return "\n".join(lines)


st.set_page_config(page_title="Passport — Shared Agent Memory", page_icon="🧳", layout="wide")
st.title("🧳 Passport — Shared Memory for Your Agent Fleet")
st.caption("One brain for Claude Code, Cursor & Codex — and it remembers who taught it what.")

seed_demo_if_empty()

# ---- sidebar ----
tenants = ledger.list_tenants()
# Always offer "default" (agents' default tenant), but keep a data-bearing tenant
# selected first so a fresh deploy opens on populated data, not an empty page.
if "default" not in tenants:
    tenants = tenants + ["default"]
if not tenants:
    tenants = ["default"]
with st.sidebar:
    st.header("View")
    tenant = st.selectbox("Tenant (user / workspace)", tenants, index=0)
    tenant_mems = ledger.list_memories(tenant)
    projects = sorted({m["project"] for m in tenant_mems})
    # Always offer "fleet" (agents' default project), appended so a data-bearing
    # project stays selected first (populated deploy, not an empty page).
    if "fleet" not in projects:
        projects = projects + ["fleet"]
    if not projects:
        projects = ["fleet"]
    project = st.selectbox("Project", projects, index=0)
    if st.button("🔄 Refresh"):
        st.rerun()

    st.divider()
    st.subheader("Live demo controls")
    st.caption("These call Cognee Cloud.")
    q = st.text_input("Recall query", "")
    if st.button("Recall") and q:
        try:
            from passport import memory as _mem
            with st.spinner("Recalling…"):
                res = run_async(_mem.recall(q, project=project, tenant=tenant), _mem)
            st.session_state["recall"] = [text_of(x) for x in res] or ["(nothing found)"]
        except Exception as e:
            st.error(f"Live recall needs Cognee credentials in secrets. ({e})")
    if st.button("Detect conflicts"):
        try:
            from passport import memory as _mem
            with st.spinner("Asking Cognee's LLM…"):
                st.session_state["detect"] = run_async(
                    _mem.detect_conflicts(project=project, tenant=tenant), _mem)
        except Exception as e:
            st.error(f"Live conflict scan needs Cognee credentials in secrets. ({e})")

st.caption(f"Viewing tenant **{tenant}** · project **{project}** — isolated from other tenants.")

# ---- data for the selected tenant + project ----
mems = ledger.list_memories(tenant, project)
conflicts = ledger.list_conflicts(tenant, project)
agents = sorted({m["agent"] for m in mems})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Memories", len(mems))
c2.metric("Agents", len(agents))
c3.metric("Open conflicts", sum(1 for c in conflicts if not c["resolved"]))
c4.metric("Resolved", sum(1 for c in conflicts if c["resolved"]))

if st.session_state.get("recall"):
    st.info("**Recall result:**\n\n" + "\n\n".join(f"- {r}" for r in st.session_state["recall"]))
if st.session_state.get("detect"):
    d = st.session_state["detect"]
    st.warning("**Conflict scan:** " + (d["raw"] or "NO CONFLICTS"))

st.subheader("🕸️ Provenance graph — colored by source agent")
if mems:
    if agents:
        legend = " &nbsp;&nbsp; ".join(
            f"<span style='color:{color_for(a)};font-size:18px'>●</span> {html.escape(a)}"
            for a in agents
        )
        st.markdown(legend, unsafe_allow_html=True)
    st.graphviz_chart(build_dot(mems), use_container_width=True)
else:
    st.info("No memories yet for this project. Teach your agents something via the Passport tool.")

left, right = st.columns(2)
with left:
    st.subheader("🧾 Memory timeline")
    for m in reversed(mems):
        ts = time.strftime("%H:%M:%S", time.localtime(m["created_at"]))
        st.markdown(
            f"<span style='background:{color_for(m['agent'])};padding:2px 8px;border-radius:8px;"
            f"color:#111;font-size:12px'>{html.escape(m['agent'])}</span> "
            f"<span style='color:#888;font-size:12px'>{ts}</span><br>{html.escape(m['text'])}",
            unsafe_allow_html=True,
        )
        st.write("")

with right:
    st.subheader("⚔️ Conflict log")
    if not conflicts:
        st.caption("No conflicts detected yet.")
    for c in conflicts:
        badge = "✅ resolved" if c["resolved"] else "🔴 open"
        st.markdown(f"**{badge}**  \n{c['description']}")
        st.write("")
