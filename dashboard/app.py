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
import os
import sys
import time

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passport import ledger, memory  # noqa: E402

# Stable-ish color per agent.
_PALETTE = ["#8ecae6", "#ffb703", "#90be6d", "#f28482", "#cdb4db", "#94d2bd", "#e9c46a"]


def color_for(agent: str) -> str:
    return _PALETTE[hash(agent) % len(_PALETTE)]


def run_async(coro):
    """Run a Cognee coroutine from Streamlit on a fresh loop (reconnect each call)."""
    async def _wrap():
        memory._connected = False
        try:
            return await coro
        finally:
            await memory.disconnect()
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

# ---- sidebar ----
tenants = ledger.list_tenants() or ["default"]
with st.sidebar:
    st.header("View")
    tenant = st.selectbox("Tenant (user / workspace)", tenants, index=0)
    tenant_mems = ledger.list_memories(tenant)
    projects = sorted({m["project"] for m in tenant_mems}) or ["fleet"]
    project = st.selectbox("Project", projects, index=0)
    if st.button("🔄 Refresh"):
        st.rerun()

    st.divider()
    st.subheader("Live demo controls")
    st.caption("These call Cognee Cloud.")
    q = st.text_input("Recall query", "")
    if st.button("Recall") and q:
        with st.spinner("Recalling…"):
            res = run_async(memory.recall(q, project=project, tenant=tenant))
        st.session_state["recall"] = [memory._text_of(x) for x in res] or ["(nothing found)"]
    if st.button("Detect conflicts"):
        with st.spinner("Asking Cognee's LLM…"):
            st.session_state["detect"] = run_async(memory.detect_conflicts(project=project, tenant=tenant))

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
            f"<span style='color:{color_for(a)};font-size:18px'>●</span> {a}" for a in agents
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
            f"color:#111;font-size:12px'>{m['agent']}</span> "
            f"<span style='color:#888;font-size:12px'>{ts}</span><br>{m['text']}",
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
