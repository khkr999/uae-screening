"""Reusable UI atoms — Bloomberg terminal aesthetic."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL


# ── Risk colors ───────────────────────────────────────────────────────────────
_RISK_CLASSES = {
    0: ("licensed", "Licensed"),
    1: ("low",      "Low"),
    2: ("monitor",  "Monitor"),
    3: ("medium",   "Medium"),
    4: ("high",     "High"),
    5: ("critical", "Critical"),
}


def risk_pill_html(level: int) -> str:
    cls, label = _RISK_CLASSES.get(int(level), ("low", "Low"))
    return (
        f'<span class="uae-risk-badge uae-pill {cls}">'
        f'<span class="uae-risk-dot" style="background:currentColor;"></span>'
        f'{escape(label.upper())}</span>'
    )


# ── Compatibility aliases for older modules ──────────────────────────────────
# review_queue.py and insights.py still import these names
risk_badge_html = risk_pill_html


def risk_badge(level: int) -> None:
    """Legacy helper — renders the risk pill via st.markdown."""
    st.markdown(risk_pill_html(level), unsafe_allow_html=True)


# ── Regulator colors ─────────────────────────────────────────────────────────
_REG_CLASSES = {
    "cbuae":      "cbuae",
    "vara":       "vara",
    "adgm":       "adgm",
    "fsra":       "fsra",
    "dfsa":       "dfsa",
    "government": "gov",
}


def regulator_pill_html(reg: str) -> str:
    if not reg or pd.isna(reg):
        return '<span class="uae-reg other">N/A</span>'
    reg_str = str(reg).strip()
    reg_low = reg_str.lower()
    cls = "other"
    label = reg_str.split("_")[0].upper() if "_" in reg_str else reg_str.upper()
    for key, c in _REG_CLASSES.items():
        if key in reg_low:
            cls = c
            label = key.upper()
            break
    return f'<span class="uae-reg {cls}">{escape(label[:8])}</span>'


# ── Status pills ──────────────────────────────────────────────────────────────
def risk_up_pill() -> str:
    return '<span class="uae-pill risk-up">↑ RISK UP</span>'


def new_pill() -> str:
    return '<span class="uae-pill new">+ NEW</span>'


def trend_arrow(value: int, kind: str = "up") -> str:
    """Returns a small ↑N badge or empty if 0."""
    if value <= 0:
        return ""
    cls = "new" if kind == "new" else "up"
    return f'<span class="uae-kpi-trend {cls}">↑{value}</span>'


# ── Required action label ────────────────────────────────────────────────────
def action_label(action: str) -> str:
    """Convert action string into a short readable label."""
    if not action or pd.isna(action):
        return "—"
    a = str(action).strip().lower()
    if "investigate" in a:    return "Immediate enhanced due diligence required"
    if "review this month" in a: return "Annual compliance review"
    if "review" in a:         return "Compliance review"
    if "monitor" in a:        return "Routine monitoring"
    if "no action" in a:      return "No action needed"
    return str(action)[:40]


# ── Empty / error ─────────────────────────────────────────────────────────────
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
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-left:3px solid var(--critical);border-radius:12px;'
        f'padding:16px 20px;">'
        f'<div style="color:var(--critical);font-weight:700;font-size:13px;">'
        f'⚠ {escape(title)}</div>'
        f'<div style="color:var(--muted);font-size:12px;margin-top:6px;">'
        f'{escape(detail)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Section header ────────────────────────────────────────────────────────────
def section_header(title: str, badge: str = "") -> None:
    badge_html = f'<span class="uae-section-badge">{escape(badge)}</span>' if badge else ''
    st.markdown(
        f'<div class="uae-section">'
        f'<div class="uae-section-title">{escape(title)}</div>'
        f'{badge_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Top bar ───────────────────────────────────────────────────────────────────
def top_bar(run_label: str, live: bool = True) -> None:
    badge = ('<span class="uae-live"><span class="uae-live-dot"></span>LIVE</span>'
             if live else "")
    bar_col, theme_col, signout_col = st.columns([7, 1, 1])

    with bar_col:
        st.markdown(
            f'<div class="uae-topbar">'
            f'<div><h1>🛡️ UAE Regulatory Screening</h1>'
            f'<div class="sub">Internal Risk Monitoring &nbsp;·&nbsp; {escape(run_label)}</div></div>'
            f'<div>{badge}</div></div>',
            unsafe_allow_html=True,
        )

    with theme_col:
        is_dark = st.session_state.get("theme", "dark") == "dark"
        st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
        if st.button("☀ Light" if is_dark else "☾ Dark",
                     key="topbar_theme_toggle", use_container_width=True):
            import state as _state
            _state.toggle_theme(st.session_state)
            st.rerun()

    with signout_col:
        st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
        if st.button("⏻ Sign out", key="topbar_signout", use_container_width=True):
            st.session_state["current_user"] = ""
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


def short_brand(name: str, max_len: int = 28) -> str:
    name = str(name or "").strip()
    return name if len(name) <= max_len else name[:max_len - 1] + "…"
