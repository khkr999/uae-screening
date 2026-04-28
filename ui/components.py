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


# ── Helpers ───────────────────────────────────────────────────────────────────
def now_label() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


def short_brand(name: str, max_len: int = 28) -> str:
    name = str(name or "").strip()
    return name if len(name) <= max_len else name[:max_len - 1] + "…"
