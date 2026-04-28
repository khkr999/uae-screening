"""Reusable UI atoms — enriched with avatars, pills, meters."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL

# ── Regulator color map ───────────────────────────────────────────────────────
_REG_COLORS: dict[str, tuple[str, str]] = {
    "CBUAE":  ("#3DA5E0", "rgba(61,165,224,0.15)"),
    "VARA":   ("#C9A84C", "rgba(201,168,76,0.15)"),
    "DFSA":   ("#A78BFA", "rgba(167,139,250,0.15)"),
    "FSRA":   ("#34D399", "rgba(52,211,153,0.15)"),
    "ADGM":   ("#34D399", "rgba(52,211,153,0.15)"),
    "SCA":    ("#F87171", "rgba(248,113,113,0.15)"),
    "GOV":    ("#6B7280", "rgba(107,114,128,0.15)"),
}

def _reg_color(reg: str) -> tuple[str, str]:
    """Return (text_color, bg_color) for a regulator string."""
    reg_upper = reg.upper()
    for key, colors in _REG_COLORS.items():
        if key in reg_upper:
            return colors
    return ("#9CA3AF", "rgba(156,163,175,0.12)")


# ── Avatar ────────────────────────────────────────────────────────────────────
def avatar_html(brand: str, reg: str, size: int = 36) -> str:
    letter  = (brand.strip()[0].upper()) if brand.strip() else "?"
    color, bg = _reg_color(reg)
    return (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:999px;background:{bg};'
        f'border:1.5px solid {color}40;font-size:{size//2-2}px;font-weight:800;'
        f'color:{color};flex-shrink:0;font-family:\'IBM Plex Sans\',sans-serif;">'
        f'{escape(letter)}</span>'
    )


# ── Service pill ──────────────────────────────────────────────────────────────
_SVC_COLORS: dict[str, tuple[str, str]] = {
    "wallet":    ("#3DA5E0", "rgba(61,165,224,0.12)"),
    "bnpl":      ("#F87171", "rgba(248,113,113,0.12)"),
    "payment":   ("#C9A84C", "rgba(201,168,76,0.12)"),
    "exchange":  ("#A78BFA", "rgba(167,139,250,0.12)"),
    "va":        ("#A78BFA", "rgba(167,139,250,0.12)"),
    "crypto":    ("#A78BFA", "rgba(167,139,250,0.12)"),
    "remittance":("#34D399", "rgba(52,211,153,0.12)"),
    "hawala":    ("#34D399", "rgba(52,211,153,0.12)"),
    "finance":   ("#FBBF24", "rgba(251,191,36,0.12)"),
    "gateway":   ("#6B7280", "rgba(107,114,128,0.12)"),
}

def service_pill_html(svc: str) -> str:
    svc_lower = svc.lower()
    color, bg = "#9CA3AF", "rgba(156,163,175,0.10)"
    for key, (c, b) in _SVC_COLORS.items():
        if key in svc_lower:
            color, bg = c, b
            break
    short = svc[:30] + ("…" if len(svc) > 30 else "")
    return (
        f'<span style="display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.06em;text-transform:uppercase;color:{color};'
        f'background:{bg};border-radius:4px;padding:2px 7px;'
        f'font-family:\'IBM Plex Mono\',monospace;white-space:nowrap;">'
        f'{escape(short)}</span>'
    )


# ── Classification badge ──────────────────────────────────────────────────────
_CLF_RULES = [
    ("unlicensed", "POSSIBLE UNLICENSED", "#EF4444", "rgba(239,68,68,0.12)"),
    ("critical",   "CRITICAL",            "#EF4444", "rgba(239,68,68,0.12)"),
    ("not found",  "NOT FOUND",           "#F87171", "rgba(248,113,113,0.10)"),
    ("likely licensed", "LIKELY LICENSED","#34D399", "rgba(52,211,153,0.10)"),
    ("licensed",   "LICENSED",            "#34D399", "rgba(52,211,153,0.10)"),
    ("government", "GOVERNMENT",          "#3DA5E0", "rgba(61,165,224,0.10)"),
    ("verification","NEEDS VERIFICATION", "#FBBF24", "rgba(251,191,36,0.10)"),
    ("needs",      "NEEDS REVIEW",        "#FBBF24", "rgba(251,191,36,0.10)"),
]

def classification_badge_html(clf: str) -> str:
    clf_lower = clf.lower()
    # Strip emoji prefixes
    import re
    clean = re.sub(r'^[\U0001F300-\U0001FFFE\U00002702-\U000027B0\s🔴🟡🟠🟢✅⚠]+', '', clf).strip()
    color, bg, label = "#9CA3AF", "rgba(156,163,175,0.10)", clean[:35]
    for key, lbl, c, b in _CLF_RULES:
        if key in clf_lower:
            color, bg, label = c, b, lbl
            break
    return (
        f'<span style="display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.06em;text-transform:uppercase;color:{color};'
        f'background:{bg};border:1px solid {color}30;border-radius:4px;'
        f'padding:2px 8px;font-family:\'IBM Plex Mono\',monospace;white-space:nowrap;">'
        f'{escape(label)}</span>'
    )


# ── Priority dot meter ────────────────────────────────────────────────────────
def priority_dots_html(level: int, max_dots: int = 3) -> str:
    tier   = RISK_BY_LEVEL.get(int(level), RISK_BY_LEVEL[1])
    filled = min(int(level), max_dots)
    dots   = ""
    for i in range(max_dots):
        c = tier.color if i < filled else "rgba(128,128,128,0.2)"
        dots += f'<span style="color:{c};font-size:10px;">●</span>'
    return f'<span title="Risk level {level}" style="letter-spacing:2px;">{dots}</span>'


# ── Confidence meter ──────────────────────────────────────────────────────────
_CONF_MAP = {
    "high":   (3, "#34D399", "3 signals confirmed — source URL + license check + register match"),
    "medium": (2, "#FBBF24", "2 signals confirmed — partial evidence, needs manual review"),
    "low":    (1, "#EF4444", "1 signal only — limited evidence, treat with caution"),
}

def confidence_meter_html(conf: str) -> str:
    key        = conf.lower().strip()
    dots, color, tip = _CONF_MAP.get(key, (1, "#6B7280", "Unknown confidence level"))
    filled_dots = "".join(
        f'<span style="color:{"" if i < dots else "rgba(128,128,128,0.2)"};color:{color if i < dots else "rgba(128,128,128,0.2)"};">●</span>'
        for i in range(3)
    )
    return (
        f'<span title="{escape(tip)}" style="letter-spacing:2px;cursor:help;">'
        f'{filled_dots}</span>'
        f'<span style="font-size:9px;color:var(--muted);margin-left:4px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{escape(conf)}</span>'
    )


# ── Regulator badge ───────────────────────────────────────────────────────────
def regulator_badge_html(reg: str) -> str:
    color, bg = _reg_color(reg)
    short = reg.split("_")[0] if "_" in reg else reg
    return (
        f'<span style="display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.06em;color:{color};background:{bg};'
        f'border-radius:4px;padding:2px 7px;font-family:\'IBM Plex Mono\',monospace;">'
        f'{escape(short)}</span>'
    )


# ── Action icon map ───────────────────────────────────────────────────────────
_ACTION_ICONS = {
    "investigate": "🔍",
    "review":      "📋",
    "monitor":     "👁",
    "no action":   "✓",
    "escalate":    "⚑",
}

def action_icon(action: str) -> str:
    a = action.lower()
    for key, icon in _ACTION_ICONS.items():
        if key in a:
            return icon
    return "›"


# ── Top bar ───────────────────────────────────────────────────────────────────
def top_bar(run_label: str, live: bool = True) -> None:
    badge = ('<span class="uae-live"><span class="uae-live-dot"></span>LIVE</span>'
             if live else "")
    bar_col, btn_col = st.columns([7, 1])
    with bar_col:
        st.markdown(
            f'<div class="uae-topbar">'
            f'<div><h1>🛡️ UAE Regulatory Screening</h1>'
            f'<div class="sub">Internal Risk Monitoring &nbsp;·&nbsp; {escape(run_label)}</div></div>'
            f'<div>{badge}</div></div>',
            unsafe_allow_html=True,
        )
    with btn_col:
        is_dark = st.session_state.get("theme", "dark") == "dark"
        st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
        if st.button("☀ Light" if is_dark else "☾ Dark",
                     key="topbar_theme_toggle", use_container_width=True):
            import state as _state
            _state.toggle_theme(st.session_state)
            st.rerun()


# ── KPI card ──────────────────────────────────────────────────────────────────
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


# ── Risk badge ────────────────────────────────────────────────────────────────
def risk_badge_html(level: int) -> str:
    tier = RISK_BY_LEVEL.get(int(level), RISK_BY_LEVEL[1])
    return (
        f'<span class="uae-badge" style="background:{tier.accent_bg};'
        f'color:{tier.color};border-color:{tier.color}33;">'
        f'{escape(tier.label)}</span>'
    )


def risk_badge(level: int) -> None:
    st.markdown(risk_badge_html(level), unsafe_allow_html=True)


# ── Empty / error ─────────────────────────────────────────────────────────────
def empty_state(title: str, desc: str = "", icon: str = "📭") -> None:
    st.markdown(
        f'<div class="uae-empty"><div class="uae-empty-icon">{icon}</div>'
        f'<div class="uae-empty-title">{escape(title)}</div>'
        f'<div class="uae-empty-desc">{escape(desc)}</div></div>',
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


# ── Entity card (overview priority queue) ─────────────────────────────────────
def entity_card(row: pd.Series, on_open_key: str) -> None:
    brand     = str(row.get(Col.BRAND,     "—") or "—")
    service   = str(row.get(Col.SERVICE,   "—") or "—")
    regulator = str(row.get(Col.REGULATOR, "—") or "—")
    level     = int(row.get(Col.RISK_LEVEL, 1))
    rationale = str(row.get(Col.RATIONALE, "") or "")[:180]
    action    = str(row.get(Col.ACTION,    "") or "")
    conf      = str(row.get(Col.CONFIDENCE,"") or "")

    icon_html = f'<span style="margin-right:6px;">{action_icon(action)}</span>' if action else ""
    act_html  = (
        f'<div style="margin-top:8px;display:flex;align-items:center;gap:6px;">'
        f'<span class="uae-action-lbl">{icon_html}{escape(action)}</span>'
        f'</div>'
    ) if action else ""
    rat_html = (
        f'<div style="font-size:11px;color:var(--muted);margin-top:10px;'
        f'border-top:1px solid var(--border);padding-top:8px;line-height:1.55;">'
        f'{escape(rationale)}{"…" if len(str(row.get(Col.RATIONALE,""))) > 180 else ""}</div>'
    ) if rationale else ""

    st.markdown(
        f'<div class="uae-entity-card">'
        # Header row: avatar + name + dots + badge
        f'<div style="display:flex;align-items:flex-start;gap:10px;">'
        f'{avatar_html(brand, regulator, 36)}'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
        f'<span style="font-size:14px;font-weight:700;color:var(--text);">{escape(brand)}</span>'
        f'{priority_dots_html(level)}'
        f'</div>'
        # Service pill + regulator badge
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:5px;flex-wrap:wrap;">'
        f'{service_pill_html(service)}'
        f'{regulator_badge_html(regulator)}'
        f'</div>'
        # Confidence
        + (f'<div style="margin-top:4px;">{confidence_meter_html(conf)}</div>' if conf else "")
        + f'{act_html}</div>'
        f'<div style="flex-shrink:0;">{risk_badge_html(level)}</div>'
        f'</div>'
        f'{rat_html}</div>',
        unsafe_allow_html=True,
    )
    st.button("Open Details →", key=on_open_key, use_container_width=True)


# ── Section header ────────────────────────────────────────────────────────────
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
