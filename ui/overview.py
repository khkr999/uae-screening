"""Overview tab — KPIs + priority queue + run summary."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, HIGH_RISK_THRESHOLD, REVIEW_MIN, REVIEW_MAX, RISK_BY_LEVEL
import services
import state
from models import RunMetrics
from ui.components import (
    empty_state, entity_card, kpi_card, section_header,
)


def render(df: pd.DataFrame, metrics: RunMetrics, session) -> None:
    _render_kpis(df, metrics)
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    left, right = st.columns([2, 1], gap="large")
    with left:
        _render_priority_queue(df, session)
    with right:
        st.markdown('<div style="margin-top:-24px;"></div>', unsafe_allow_html=True)
        _render_risk_distribution(df)


# ── KPI CARDS ─────────────────────────────────────────────────────────────────
def _render_kpis(df: pd.DataFrame, m: RunMetrics) -> None:
    """Count KPIs directly from data — not just risk level mapping."""
    total = len(df)

    # Licensed = Risk Level 0 OR classification contains LICENSED
    clf = df[Col.CLASSIFICATION].fillna("").astype(str) if Col.CLASSIFICATION in df.columns else pd.Series([""] * total)
    rl  = df[Col.RISK_LEVEL].fillna(99).astype(int)     if Col.RISK_LEVEL    in df.columns else pd.Series([99]  * total)

    licensed_mask   = (rl == 0) | clf.str.contains("LICENSED", case=False, na=False)
    high_risk_mask  = rl >= HIGH_RISK_THRESHOLD
    review_mask     = rl.between(REVIEW_MIN, REVIEW_MAX - 1)  # level 2 only (monitor)

    licensed_count  = int(licensed_mask.sum())
    high_risk_count = int(high_risk_mask.sum())
    review_count    = int(review_mask.sum())

    share = f"{round((high_risk_count / max(total, 1)) * 100)}% of total"
    hint  = f"+{m.risk_increased} risk up" if m.risk_increased else "Surfaced this run"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Entities Screened",   f"{total:,}",        "This run",            accent="#3DA5E0")
    with c2:
        kpi_card("Critical / High",     high_risk_count,     share,                 accent="#EF4444")
    with c3:
        kpi_card("Needs Review",        review_count,        "Risk level 2",        accent="#FBBF24")
    with c4:
        kpi_card("Licensed / Clear",    licensed_count,      "On official register", accent="#059669")
    with c5:
        kpi_card("New Alerts",          m.new_entities,      hint,                  accent="#C9A84C")


# ── PRIORITY QUEUE ────────────────────────────────────────────────────────────
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


# ── RUN SUMMARY ───────────────────────────────────────────────────────────────
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
        f'<span class="uae-sum-value">{escape(str(value))}</span>'
        f'</div>'
        for label, value in rows
    )
    st.markdown(f'<div class="uae-card nohover">{rows_html}</div>',
                unsafe_allow_html=True)


# ── RISK DISTRIBUTION ─────────────────────────────────────────────────────────
def _render_risk_distribution(df: pd.DataFrame) -> None:
    section_header("Risk Distribution")

    # Build counts directly so Licensed (0) is always correct
    rl = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL in df.columns else pd.Series(dtype=int)

    rows = []
    for tier in sorted(RISK_BY_LEVEL.values(), key=lambda t: t.level, reverse=True):
        count = int((rl == tier.level).sum())
        rows.append({"label": tier.label, "count": count, "color": tier.color})

    # Add "Licensed" row explicitly using classification if risk level 0 count is off
    clf = df[Col.CLASSIFICATION].fillna("").astype(str) if Col.CLASSIFICATION in df.columns else pd.Series([""] * len(df))
    licensed_by_clf = int(clf.str.contains("LICENSED", case=False, na=False).sum())
    # Use the higher of the two counts for the Licensed row
    for r in rows:
        if r["label"] == "Licensed / Clear":
            r["count"] = max(r["count"], licensed_by_clf)

    max_count = max((r["count"] for r in rows), default=1)
    bars = []
    for r in rows:
        if r["count"] == 0:
            continue  # skip empty tiers for cleanliness
        width = (r["count"] / max_count) * 100
        short = r["label"].split("/")[0].strip()
        bars.append(
            f'<div class="uae-bar-row">'
            f'<span class="uae-bar-label">{escape(short)}</span>'
            f'<div class="uae-bar-track">'
            f'<div class="uae-bar-fill" style="width:{width:.1f}%;background:{r["color"]};"></div>'
            f'</div>'
            f'<span class="uae-bar-count">{r["count"]}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="uae-card nohover">{"".join(bars)}</div>',
        unsafe_allow_html=True,
    )
