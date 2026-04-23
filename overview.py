from __future__ import annotations
import pandas as pd
import streamlit as st
from config import Col
import services
import state
from models import RunMetrics
from ui.components import empty_state, entity_card, kpi_card, section_header

def render(df: pd.DataFrame, metrics: RunMetrics, session) -> None:
    _render_kpis(metrics)
    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        _render_priority_queue(df, session)
    with right:
        _render_summary(metrics, df)
        st.write("")
        _render_risk_distribution(df)

def _render_kpis(m: RunMetrics) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi_card("Entities Screened", f"{m.total:,}", "This run", accent="var(--accent)")
    with c2: kpi_card("Critical / High", m.critical_high, f"{round((m.critical_high/max(m.total,1))*100)}% of total", accent="#D63C54")
    with c3: kpi_card("Needs Review", m.needs_review, "Risk levels 2–3", accent="#C9A84C")
    with c4: kpi_card("Licensed / Clear", m.licensed, "On official register", accent="#50C88A")
    with c5: kpi_card("New Alerts", m.new_entities, f"+{m.risk_increased} risk up" if m.risk_increased else "Surfaced this run", accent="#3DA5E0")

def _render_priority_queue(df: pd.DataFrame, session) -> None:
    section_header("Priority Review Queue", "Top entities by risk — focus here first")
    priority = services.get_insights(df)["priority"]
    if priority.empty:
        empty_state("No high-risk entities this run", "All clear — keep monitoring weekly.", icon="✅")
        return
    cols = st.columns(2, gap="medium")
    for idx, (_, row) in enumerate(priority.iterrows()):
        with cols[idx % 2]:
            key = f"open_priority_{row.get('id', idx)}"
            entity_card(row, on_open_key=key)
            if st.session_state.get(key):
                state.set_selected(session, str(row.get("id", "")))

def _render_summary(m: RunMetrics, df: pd.DataFrame) -> None:
    section_header("Run Summary")
    rows = [("Top regulator", m.top_regulator), ("Top service", m.top_service), ("Total rows", f"{m.total:,}"), ("Distinct brands", f"{df[Col.BRAND].nunique():,}")]
    body = "".join(f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);"><span style="color:var(--muted);font-size:12px;">{l}</span><span style="color:var(--text);font-size:12.5px;font-weight:700;">{v}</span></div>' for l, v in rows)
    st.markdown(f'<div class="uae-card">{body}</div>', unsafe_allow_html=True)

def _render_risk_distribution(df: pd.DataFrame) -> None:
    section_header("Risk Distribution")
    dist = services.get_insights(df)["risk_distribution"]
    max_count = max(dist["count"].max(), 1)
    bars = []
    for _, r in dist.iterrows():
        width = (r["count"] / max_count) * 100
        bars.append(f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0;"><span style="width:90px;font-size:10px;font-weight:700;text-transform:uppercase;color:var(--muted);">{r["label"]}</span><div style="flex:1;height:8px;border-radius:999px;background:rgba(128,128,128,0.12);overflow:hidden;"><div style="height:100%;width:{width:.1f}%;background:{r["color"]};border-radius:999px;"></div></div><span style="width:30px;text-align:right;font-size:12px;font-weight:700;color:var(--text);">{r["count"]}</span></div>')
    st.markdown(f'<div class="uae-card">{"".join(bars)}</div>', unsafe_allow_html=True)
