"""Overview tab — KPIs + priority queue + run summary."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL
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
    with c1:
        kpi_card("Entities Screened", f"{m.total:,}", "This run", accent="#3DA5E0")
    with c2:
        share = f"{round((m.critical_high / max(m.total, 1)) * 100)}% of total"
        kpi_card("Critical / High", m.critical_high, share, accent="#EF4444")
    with c3:
        kpi_card("Needs Review", m.needs_review, "Risk levels 2–3", accent="#FBBF24")
    with c4:
        kpi_card("Licensed / Clear", m.licensed, "On official register", accent="#34D399")
    with c5:
        hint = f"+{m.risk_increased} risk up" if m.risk_increased else "Surfaced this run"
        kpi_card("New Alerts", m.new_entities, hint, accent="#C9A84C")


def _render_priority_queue(df: pd.DataFrame, session) -> None:
    section_header("Priority Review Queue", "Top entities by risk — focus here first")
    priority = services.get_insights(df)["priority"]

    if priority.empty:
        empty_state("No high-risk entities this run",
                    "All clear — keep monitoring weekly.", icon="✅")
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
    rows = [
        ("Top regulator",   m.top_regulator),
        ("Top service",     m.top_service),
        ("Total entities",  f"{m.total:,}"),
        ("Distinct brands", f"{df[Col.BRAND].nunique():,}"),
    ]
    rows_html = "".join(
        f'<div class="uae-sum-row">'
        f'<span class="uae-sum-label">{label}</span>'
        f'<span class="uae-sum-value">{value}</span>'
        f'</div>'
        for label, value in rows
    )
    st.markdown(f'<div class="uae-card nohover">{rows_html}</div>',
                unsafe_allow_html=True)


def _render_risk_distribution(df: pd.DataFrame) -> None:
    section_header("Risk Distribution")
    dist = services.get_insights(df)["risk_distribution"]
    max_count = max(dist["count"].max(), 1)

    bars = []
    for _, r in dist.iterrows():
        width = (r["count"] / max_count) * 100
        short = r["label"].split("/")[0].strip()
        bars.append(
            f'<div class="uae-bar-row">'
            f'<span class="uae-bar-label">{short}</span>'
            f'<div class="uae-bar-track">'
            f'<div class="uae-bar-fill" style="width:{width:.1f}%;background:{r["color"]};"></div>'
            f'</div>'
            f'<span class="uae-bar-count">{r["count"]}</span>'
            f'</div>'
        )
    st.markdown(f'<div class="uae-card nohover">{"".join(bars)}</div>',
                unsafe_allow_html=True)
