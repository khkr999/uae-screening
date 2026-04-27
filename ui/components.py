"""Reusable UI atoms."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL


def top_bar(run_label: str, live: bool = True) -> None:
    """Top bar: title left, theme toggle + LIVE badge right. Always visible."""
    badge = ('<span class="uae-live"><span class="uae-live-dot"></span>LIVE</span>'
             if live else "")

    bar_col, btn_col = st.columns([7, 1])

    with bar_col:
        st.markdown(
            f'<div class="uae-topbar">'
            f'<div>'
            f'<h1>🛡️ UAE Regulatory Screening</h1>'
            f'<div class="sub">Internal Risk Monitoring &nbsp;·&nbsp; {escape(run_label)}</div>'
            f'</div>'
            f'<div>{badge}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with btn_col:
        is_dark = st.session_state.get("theme", "dark") == "dark"
        label   = "☀ Light" if is_dark else "☾ Dark"
        st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
        if st.button(label, key="topbar_theme_toggle", use_container_width=True):
            import state as _state
            _state.toggle_theme(st.session_state)
            st.rerun()


def kpi_card(label: str, value: str | int, hint: str = "",
             accent: str = "var(--accent)") -> None:
    st.markdown(
        f'<div class="uae-card subtle nohover" style="border-top:2px solid {accent};cursor:default;">'
        f'<div class="uae-kpi-label">{escape(label)}</div>'
        f'<div class="uae-kpi-value">{escape(str(value))}</div>'
        f'<div class="uae-kpi-hint">{escape(hint)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def risk_badge_html(level: int) -> str:
    tier = RISK_BY_LEVEL.get(int(level), RISK_BY_LEVEL[1])
    return (f'<span class="uae-badge" style="background:{tier.accent_bg};'
            f'color:{tier.color};border-color:{tier.color}33;">'
            f'{escape(tier.label)}</span>')


def risk_badge(level: int) -> None:
    st.markdown(risk_badge_html(level), unsafe_allow_html=True)


def empty_state(title: str, desc: str = "", icon: str = "📭") -> None:
    st.markdown(
        f'<div class="uae-empty">'
        f'<div class="uae-empty-icon">{icon}</div>'
        f'<div class="uae-empty-title">{escape(title)}</div>'
        f'<div class="uae-empty-desc">{escape(desc)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def error_state(title: str, detail: str = "") -> None:
    st.markdown(
        f'<div class="uae-card nohover" style="border-color:rgba(239,68,68,0.35);'
        f'border-left:3px solid #EF4444;">'
        f'<div style="color:#EF4444;font-weight:700;font-size:13px;">⚠ {escape(title)}</div>'
        f'<div style="color:var(--muted);font-size:12px;margin-top:6px;">{escape(detail)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def entity_card(row: pd.Series, on_open_key: str) -> None:
    brand     = escape(str(row.get(Col.BRAND,     "—")))
    service   = escape(str(row.get(Col.SERVICE,   "—")))
    regulator = escape(str(row.get(Col.REGULATOR, "—")))
    level     = int(row.get(Col.RISK_LEVEL, 1))
    rationale = escape(str(row.get(Col.RATIONALE, "") or "")[:200])
    action    = escape(str(row.get(Col.ACTION,    "") or ""))

    action_html = (
        f'<div class="uae-action-lbl" style="margin-top:8px;">{action}</div>'
        if action else ""
    )
    rat_html = (
        f'<div style="font-size:11px;color:var(--muted);margin-top:10px;'
        f'border-top:1px solid var(--border);padding-top:8px;line-height:1.55;">'
        f'{rationale}</div>'
    ) if rationale else ""

    st.markdown(
        f'<div class="uae-entity-card">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;gap:12px;">'
        f'<div style="min-width:0;flex:1;">'
        f'<div style="font-size:14px;font-weight:700;color:var(--text);">{brand}</div>'
        f'<div style="font-size:11px;color:var(--dim);margin-top:2px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'{service} &nbsp;·&nbsp; {regulator}</div>'
        f'{action_html}</div>'
        f'<div style="flex-shrink:0;">{risk_badge_html(level)}</div>'
        f'</div>{rat_html}</div>',
        unsafe_allow_html=True,
    )
    st.button("Open Details →", key=on_open_key, use_container_width=True)


def section_header(title: str, subtitle: str = "") -> None:
    sub = f'<div class="uae-sec-sub">{escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin:4px 0 12px 0;">'
        f'<div class="uae-sec-title">{escape(title)}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def divider() -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:12px 0;"></div>',
        unsafe_allow_html=True,
    )


def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")
