"""Reusable UI atoms."""
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
                <div class="sub">Internal risk monitoring · {escape(run_label)}</div>
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
        <div class="uae-card subtle" style="border-top: 3px solid {accent};">
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
    return (f'<span class="uae-badge" '
            f'style="background:{tier.accent_bg};color:{tier.color};'
            f'border-color:{tier.color}40;">{escape(tier.label)}</span>')


def risk_badge(level: int) -> None:
    st.markdown(risk_badge_html(level), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Empty states
# ---------------------------------------------------------------------------
def empty_state(title: str, desc: str = "", icon: str = "📭") -> None:
    st.markdown(
        f"""
        <div class="uae-card" style="text-align:center; padding: 36px 20px;">
            <div style="font-size: 32px;">{icon}</div>
            <div style="font-size: 15px; font-weight: 700; margin-top: 8px;">
                {escape(title)}
            </div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
                {escape(desc)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def error_state(title: str, detail: str = "") -> None:
    st.markdown(
        f"""
        <div class="uae-card" style="border-color: rgba(214,60,84,0.35);">
            <div style="color:#D63C54; font-weight:700; font-size:13px;">
                ⚠ {escape(title)}
            </div>
            <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
                {escape(detail)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Entity card (used on Overview priority queue)
# ---------------------------------------------------------------------------
def entity_card(row: pd.Series, on_open_key: str) -> None:
    brand = escape(str(row.get(Col.BRAND, "—")))
    service = escape(str(row.get(Col.SERVICE, "—")))
    regulator = escape(str(row.get(Col.REGULATOR, "—")))
    level = int(row.get(Col.RISK_LEVEL, 1))
    rationale = escape(str(row.get(Col.RATIONALE, ""))[:180])

    st.markdown(
        f"""
        <div class="uae-card" style="margin-bottom: 8px;">
            <div style="display:flex; justify-content:space-between;
                        align-items:start; gap: 12px;">
                <div style="min-width: 0; flex:1;">
                    <div style="font-size: 15px; font-weight: 800;
                                color: var(--text); margin-bottom: 2px;">
                        {brand}
                    </div>
                    <div style="font-size: 12px; color: var(--dim);">
                        {service} · {regulator}
                    </div>
                </div>
                <div>{risk_badge_html(level)}</div>
            </div>
            {f'<div style="margin-top:10px;font-size:12px;color:var(--muted);">{rationale}</div>'
             if rationale else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Open details", key=on_open_key, use_container_width=True)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="margin: 8px 0 8px 0;">
            <div style="font-size: 16px; font-weight: 800; color: var(--text);">
                {escape(title)}
            </div>
            {f'<div style="font-size:12px;color:var(--muted);">{escape(subtitle)}</div>'
             if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def divider() -> None:
    st.markdown('<div style="height:1px;background:var(--border);'
                'margin: 10px 0;"></div>', unsafe_allow_html=True)


def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")
