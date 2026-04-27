"""Reusable UI atoms — redesigned for professional dark dashboard."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL


# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------
def top_bar(run_label: str, live: bool = True) -> None:
    badge = ('<span class="uae-live"><span class="uae-live-dot"></span>LIVE</span>'
             if live else "")
    st.markdown(
        f"""
        <div class="uae-topbar">
            <div>
                <h1>🛡️ UAE Regulatory Screening</h1>
                <div class="sub">Internal Risk Monitoring &nbsp;·&nbsp; {escape(run_label)}</div>
            </div>
            <div>{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI card
# ---------------------------------------------------------------------------
def kpi_card(label: str,
             value: str | int,
             hint: str = "",
             accent: str = "var(--accent)") -> None:
    st.markdown(
        f"""
        <div class="uae-card subtle nohover" style="border-top: 2px solid {accent}; cursor: default;">
            <div class="uae-kpi-label">{escape(label)}</div>
            <div class="uae-kpi-value">{escape(str(value))}</div>
            <div class="uae-kpi-hint">{escape(hint)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Risk badge
# ---------------------------------------------------------------------------
def risk_badge_html(level: int) -> str:
    tier = RISK_BY_LEVEL.get(int(level), RISK_BY_LEVEL[1])
    return (
        f'<span class="uae-badge" '
        f'style="background:{tier.accent_bg};color:{tier.color};'
        f'border-color:{tier.color}33;">'
        f'{escape(tier.label)}</span>'
    )


def risk_badge(level: int) -> None:
    st.markdown(risk_badge_html(level), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Empty / Error states
# ---------------------------------------------------------------------------
def empty_state(title: str, desc: str = "", icon: str = "📭") -> None:
    st.markdown(
        f"""
        <div class="uae-empty">
            <div class="uae-empty-icon">{icon}</div>
            <div class="uae-empty-title">{escape(title)}</div>
            <div class="uae-empty-desc">{escape(desc)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def error_state(title: str, detail: str = "") -> None:
    st.markdown(
        f"""
        <div class="uae-card nohover" style="border-color: rgba(239,68,68,0.35); border-left: 3px solid #EF4444;">
            <div style="color:#EF4444; font-weight:700; font-size:13px; font-family:'IBM Plex Mono',monospace;">
                ⚠ {escape(title)}
            </div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 6px;">
                {escape(detail)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entity card (priority queue)
# ---------------------------------------------------------------------------
def entity_card(row: pd.Series, on_open_key: str) -> None:
    brand    = escape(str(row.get(Col.BRAND,     "—")))
    service  = escape(str(row.get(Col.SERVICE,   "—")))
    regulator = escape(str(row.get(Col.REGULATOR,"—")))
    level    = int(row.get(Col.RISK_LEVEL, 1))
    rationale = escape(str(row.get(Col.RATIONALE, ""))[:200])
    action   = escape(str(row.get(Col.ACTION, "")  or ""))

    action_html = (
        f'<div class="uae-action-label">{action}</div>'
        if action else ""
    )
    rationale_html = (
        f'<div class="uae-entity-rationale">{rationale}</div>'
        if rationale else ""
    )

    st.markdown(
        f"""
        <div class="uae-entity-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                <div style="min-width:0; flex:1;">
                    <div class="uae-entity-brand">{brand}</div>
                    <div class="uae-entity-meta">{service} &nbsp;·&nbsp; {regulator}</div>
                    {action_html}
                </div>
                <div style="flex-shrink:0;">{risk_badge_html(level)}</div>
            </div>
            {rationale_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Open Details →", key=on_open_key, use_container_width=True)


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section_header(title: str, subtitle: str = "") -> None:
    sub_html = (
        f'<div class="uae-sec-sub">{escape(subtitle)}</div>'
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style="margin: 4px 0 12px 0;">
            <div class="uae-sec-title">{escape(title)}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Divider
# ---------------------------------------------------------------------------
def divider() -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:12px 0;"></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")
