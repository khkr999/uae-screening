"""
UAE Regulatory Screening – Internal Search UI
Single-file, production-ready Streamlit app.
"""
from __future__ import annotations

import glob
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Optional fuzzy search
try:
    from rapidfuzz import fuzz, process as rf_process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Optional autocomplete searchbox
try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False


# ══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ══════════════════════════════════════════════════════════════════════════
WORKFLOW_STATES = ["OPEN", "INVESTIGATING", "REVIEWED", "CLOSED"]

WORKFLOW_STYLES = {
    "OPEN":          {"label": "Open",          "color": "#F87171", "bg": "rgba(239,68,68,0.10)", "border": "rgba(239,68,68,0.28)", "icon": "●"},
    "INVESTIGATING": {"label": "Investigating", "color": "#FBBF24", "bg": "rgba(251,191,36,0.10)","border": "rgba(251,191,36,0.28)","icon": "◐"},
    "REVIEWED":      {"label": "Reviewed",      "color": "#93C5FD", "bg": "rgba(37,99,235,0.12)", "border": "rgba(37,99,235,0.28)", "icon": "◑"},
    "CLOSED":        {"label": "Closed",        "color": "#34D399", "bg": "rgba(52,211,153,0.10)","border": "rgba(52,211,153,0.28)","icon": "✓"},
}


def default_workflow_state(risk_level, classification) -> str:
    cls = str(classification).upper()
    try:
        lvl = int(risk_level)
    except (ValueError, TypeError):
        lvl = 2
    if "LICENSED" in cls or "GOVERNMENT PLATFORM" in cls or lvl == 0:
        return "CLOSED"
    return "OPEN"


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════
WIDGET_KEYS = {
    "regulator_choice":  "All Regulators",
    "status_choice":     "All Statuses",
    "confidence_choice": "All Confidence",
    "sort_choice":       "Priority",
    "actionable_only":   False,
}

STATE_KEYS = {
    "theme":              "dark",
    "workflow":           {},      # {brand: {"state": str, "note": str|None, "ts": str}}
    "selected_brand":     None,
    "page":               1,
    "risk_filter":        None,
    "quick_filter":       None,
    "search_query":       "",
    "selected_rows":      [],
    "confirm_clear_brand": None,
    "clicked_risk_level": None,
    "reset_counter":      0,       # bump to force widget remount
}


def _init_state():
    for k, v in {**STATE_KEYS, **WIDGET_KEYS}.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()
dark = st.session_state.theme == "dark"


# ══════════════════════════════════════════════════════════════════════════
# THEME TOKENS
# ══════════════════════════════════════════════════════════════════════════
THEMES = {
    "dark": {
        "app_bg":     "#070b1a",
        "hero_bg":    "linear-gradient(135deg, #0b1428 0%, #0f172a 60%, #0b1428 100%)",
        "sidebar_bg": "#070b1a",
        "card_bg":    "#0f172a",
        "card_hi":    "#131e37",
        "raised_bg":  "#0b1426",
        "text":       "#f1f5f9",
        "text_dim":   "#cbd5e1",
        "text_muted": "#94a3b8",
        "accent":     "#818cf8",
        "accent_2":   "#a78bfa",
        "accent_dim": "rgba(129,140,248,0.12)",
        "accent_bd":  "rgba(129,140,248,0.32)",
        "border":     "rgba(148,163,184,0.12)",
        "border_hi":  "rgba(148,163,184,0.24)",
        "input_bg":   "#0b1426",
        "danger":     "#ef4444",
        "success":    "#10b981",
        "warning":    "#f59e0b",
    },
    "light": {
        "app_bg":     "#f8fafc",
        "hero_bg":    "linear-gradient(135deg, #ffffff 0%, #f1f5f9 60%, #ffffff 100%)",
        "sidebar_bg": "#ffffff",
        "card_bg":    "#ffffff",
        "card_hi":    "#f8fafc",
        "raised_bg":  "#f1f5f9",
        "text":       "#0f172a",
        "text_dim":   "#334155",
        "text_muted": "#64748b",
        "accent":     "#6366f1",
        "accent_2":   "#8b5cf6",
        "accent_dim": "rgba(99,102,241,0.08)",
        "accent_bd":  "rgba(99,102,241,0.28)",
        "border":     "rgba(15,23,42,0.08)",
        "border_hi":  "rgba(15,23,42,0.18)",
        "input_bg":   "#ffffff",
        "danger":     "#dc2626",
        "success":    "#059669",
        "warning":    "#d97706",
    },
}
c = THEMES[st.session_state.theme]


# ══════════════════════════════════════════════════════════════════════════
# RISK METADATA
# ══════════════════════════════════════════════════════════════════════════
RISK_META = {
    5: {"label": "Critical", "color": "#E11D48", "bg": "rgba(225,29,72,0.14)",  "border": "rgba(225,29,72,0.32)"},
    4: {"label": "High",     "color": "#F97316", "bg": "rgba(249,115,22,0.14)", "border": "rgba(249,115,22,0.32)"},
    3: {"label": "Medium",   "color": "#EAB308", "bg": "rgba(234,179,8,0.14)",  "border": "rgba(234,179,8,0.32)"},
    2: {"label": "Monitor",  "color": "#4A7FD4", "bg": "rgba(74,127,212,0.14)", "border": "rgba(74,127,212,0.32)"},
    1: {"label": "Low",      "color": "#4A7FD4", "bg": "rgba(74,127,212,0.08)", "border": "rgba(74,127,212,0.2)"},
    0: {"label": "Licensed", "color": "#10B981", "bg": "rgba(16,185,129,0.14)", "border": "rgba(16,185,129,0.32)"},
}

REGULATOR_LABELS = {
    "CBUAE_ONSHORE": "CBUAE Onshore",
    "DFSA_DIFC":     "DFSA / DIFC",
    "DFSA_DIFC_VA":  "DFSA / DIFC VA",
    "FSRA_ADGM_VA":  "FSRA / ADGM VA",
    "VARA_DUBAI_VA": "VARA / Dubai VA",
    "GOVERNMENT":    "Government",
}

CONFIDENCE_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════
def clean_text(value, fallback: str = "") -> str:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return fallback
        s = str(value).strip()
        if s.lower() in {"nan", "none", "nat", "<na>"}:
            return fallback
        return s
    except Exception:
        return fallback


def safe_int(value, default: int = 2) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def row_brand(row) -> str:
    try:
        return clean_text(row.get("Brand", ""), fallback="Unknown")
    except Exception:
        return "Unknown"


def normalize_regulator(scope) -> str:
    s = clean_text(scope, fallback="—")
    if s in REGULATOR_LABELS:
        return REGULATOR_LABELS[s]
    return s.replace("_", " ").title()


def confidence_rank(value) -> int:
    return CONFIDENCE_RANK.get(clean_text(value).upper(), 0)


def confidence_label(value) -> str:
    return clean_text(value).title() or "Unknown"


# ── Workflow ──────────────────────────────────────────────────────────────
def get_workflow(brand: str) -> dict:
    return st.session_state.workflow.get(brand, {"state": None, "note": None, "ts": None})


def get_effective_state(row) -> str:
    try:
        brand = row_brand(row)
        wf = st.session_state.workflow.get(brand)
        if wf and wf.get("state") in WORKFLOW_STATES:
            return wf["state"]
        return default_workflow_state(
            safe_int(row.get("Risk Level", 2)),
            clean_text(row.get("Classification", "")),
        )
    except Exception:
        return "OPEN"


def set_workflow_state(brand: str, state: str, note: str | None = None):
    if state not in WORKFLOW_STATES:
        return
    prev = st.session_state.workflow.get(brand, {})
    st.session_state.workflow[brand] = {
        "state": state,
        "note":  note if note is not None else prev.get("note"),
        "ts":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def clear_workflow(brand: str):
    st.session_state.workflow.pop(brand, None)


def next_primary_action(state: str):
    if state == "OPEN":          return ("Investigate", "INVESTIGATING")
    if state == "INVESTIGATING": return ("Mark Reviewed", "REVIEWED")
    if state == "REVIEWED":      return ("Close", "CLOSED")
    return None


def reset_all_filters():
    """Safely reset filter widgets by deleting widget-owned keys and bumping counter."""
    for key in list(WIDGET_KEYS.keys()):
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.risk_filter = None
    st.session_state.quick_filter = None
    st.session_state.search_query = ""
    st.session_state.page = 1
    st.session_state.selected_rows = []
    st.session_state.clicked_risk_level = None
    st.session_state.reset_counter += 1
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("row_sel_"):
            st.session_state[k] = False


# ══════════════════════════════════════════════════════════════════════════
# BADGE / CHIP HTML
# ══════════════════════════════════════════════════════════════════════════
def risk_badge_html(level: int) -> str:
    m = RISK_META.get(level, RISK_META[2])
    dot = f'<span style="width:6px;height:6px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:6px;box-shadow:0 0 8px {m["color"]};"></span>'
    return (
        f'<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;'
        f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;letter-spacing:0.04em;">{dot}{m["label"]} · {level}</span>'
    )


def state_badge_html(state: str) -> str:
    m = WORKFLOW_STYLES.get(state, WORKFLOW_STYLES["OPEN"])
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;'
        f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;letter-spacing:0.04em;">'
        f'<span style="opacity:0.8;">{m["icon"]}</span>{m["label"]}</span>'
    )


def alert_badge_html(status) -> str:
    s = clean_text(status).upper()
    if "NEW" in s:
        return ('<span style="display:inline-block;padding:3px 9px;border-radius:999px;'
                'background:rgba(34,197,94,0.14);color:#22C55E;border:1px solid rgba(34,197,94,0.32);'
                'font-size:9px;font-weight:800;letter-spacing:0.06em;">✨ NEW</span>')
    if "INCREASED" in s:
        return ('<span style="display:inline-block;padding:3px 9px;border-radius:999px;'
                'background:rgba(249,115,22,0.14);color:#F97316;border:1px solid rgba(249,115,22,0.32);'
                'font-size:9px;font-weight:800;letter-spacing:0.06em;">↑ RISK UP</span>')
    return ""


def chip_html(text: str) -> str:
    s = clean_text(text, fallback="—")
    return (
        f'<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:8px;'
        f'background:{c["accent_dim"]};border:1px solid {c["accent_bd"]};color:{c["accent"]};'
        f'font-size:11px;font-weight:700;max-width:100%;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;" title="{s}">{s}</span>'
    )


def confidence_bar_html(value) -> str:
    label = confidence_label(value)
    rank = confidence_rank(value)
    widths = {3: 100, 2: 66, 1: 33, 0: 15}
    colors = {3: "#34D399", 2: "#FBBF24", 1: "#F87171", 0: "#64748B"}
    return (
        f'<div style="display:flex;align-items:center;gap:6px;" title="Confidence: {label}">'
        f'<div style="width:48px;height:5px;background:{c["border"]};border-radius:999px;overflow:hidden;">'
        f'<div style="width:{widths[rank]}%;height:100%;background:{colors[rank]};border-radius:999px;'
        f'box-shadow:0 0 6px {colors[rank]}55;"></div></div>'
        f'<span style="font-size:10px;color:{c["text_muted"]};font-weight:700;">{label[:4]}</span>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: {c['app_bg']} !important;
    color: {c['text']} !important;
    letter-spacing: -0.01em;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {c['app_bg']} !important; }}
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1320px !important;
}}

[data-testid="stSidebar"] {{
    background: {c['sidebar_bg']} !important;
    border-right: 1px solid {c['border']} !important;
}}
[data-testid="stSidebar"] * {{ color: {c['text_dim']} !important; }}
[data-testid="stSidebar"] h3 {{ color: {c['text']} !important; }}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="input"] input,
.stTextInput input,
[data-testid="stSelectbox"] > div > div > div {{
    background: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
    min-height: 40px !important;
    box-shadow: none !important;
    font-weight: 500 !important;
}}
div[data-baseweb="select"]:hover > div {{ border-color: {c['border_hi']} !important; }}
ul[data-baseweb="menu"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['border_hi']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3) !important;
}}
[data-baseweb="option"] {{ color: {c['text']} !important; }}
[data-baseweb="option"]:hover {{ background: {c['raised_bg']} !important; }}
[data-baseweb="tag"] {{ background: {c['accent_dim']} !important; color: {c['text']} !important; }}

[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {c['card_bg']} !important;
    border-radius: 12px !important;
    padding: 5px !important;
    gap: 4px !important;
    border: 1px solid {c['border']} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    color: {c['text_muted']} !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 8px !important;
    transition: all 0.15s ease;
}}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
    background: {c['raised_bg']} !important;
    color: {c['text']} !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none !important; }}

div.stButton > button, .stDownloadButton button, .stLinkButton a {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    min-height: 38px !important;
    transition: all 0.15s ease !important;
}}
div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {c['accent']} 0%, {c['accent_2']} 100%) !important;
    border-color: transparent !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px {c['accent_dim']};
}}
div.stButton > button:hover:not(:disabled),
.stDownloadButton button:hover:not(:disabled),
.stLinkButton a:hover {{
    background: {c['card_hi']} !important;
    border-color: {c['border_hi']} !important;
    transform: translateY(-1px);
}}
div.stButton > button[kind="primary"]:hover:not(:disabled) {{
    box-shadow: 0 6px 20px {c['accent_dim']}, 0 0 0 1px {c['accent_bd']};
    filter: brightness(1.1);
}}
div.stButton > button:disabled {{ opacity: 0.35 !important; cursor: not-allowed !important; }}

[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    border: 1px solid {c['border']} !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] table {{ background: {c['card_bg']} !important; }}
[data-testid="stDataFrame"] th {{
    background: {c['raised_bg']} !important;
    color: {c['text_muted']} !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
[data-testid="stDataFrame"] td {{
    color: {c['text']} !important;
    font-size: 0.84rem !important;
    border-bottom: 1px solid {c['border']} !important;
}}
[data-testid="stDataFrame"] tr:hover td {{ background: {c['raised_bg']} !important; }}

::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {c['border_hi']}; border-radius: 99px; }}
::-webkit-scrollbar-thumb:hover {{ background: {c['accent_bd']}; }}

/* === Hero Top Bar === */
.hero-bar {{
    position: relative;
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 24px;
    margin-bottom: 20px;
    background: {c['hero_bg']};
    border: 1px solid {c['border']};
    border-radius: 16px;
    overflow: hidden;
}}
.hero-bar::before {{
    content: "";
    position: absolute;
    top: -50%; right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, {c['accent_dim']} 0%, transparent 70%);
    pointer-events: none;
}}
.hero-logo {{ display:flex; align-items:center; gap:14px; position: relative; z-index: 1; }}
.hero-icon {{
    width:44px; height:44px; border-radius:12px;
    background: linear-gradient(135deg, {c['accent']} 0%, {c['accent_2']} 100%);
    display:flex; align-items:center; justify-content:center;
    font-size:20px; flex-shrink:0;
    box-shadow: 0 8px 24px {c['accent_dim']}, 0 0 0 1px {c['accent_bd']};
}}
.hero-title {{
    color: {c['text']};
    font-size:18px;
    font-weight:800;
    line-height:1.15;
    letter-spacing:-0.02em;
}}
.hero-sub {{
    color: {c['text_muted']};
    font-size:10px;
    font-weight:600;
    letter-spacing:0.12em;
    text-transform:uppercase;
    margin-top:2px;
}}
.hero-meta {{ text-align:right; display:flex; align-items:center; gap:12px; position: relative; z-index: 1; }}
.hero-run {{
    padding: 8px 12px;
    background: {c['raised_bg']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    text-align: right;
}}
.hero-run .label {{ color: {c['text_muted']}; font-size:9px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; }}
.hero-run .value {{ color: {c['text']}; font-size:12px; font-weight:700; margin-top:2px; }}
.hero-run .src {{ color: {c['text_muted']}; font-size:9px; margin-top:2px; }}

.live-badge {{
    display:inline-flex; align-items:center; gap:6px;
    padding:8px 14px;
    border-radius:999px;
    background: rgba(16,185,129,0.12);
    border:1px solid rgba(16,185,129,0.32);
}}
.live-dot {{
    width:6px; height:6px;
    border-radius:50%;
    background:#10B981;
    display:inline-block;
    box-shadow: 0 0 10px #10B981;
    animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}
.live-txt {{ color:#10B981; font-size:10px; font-weight:800; letter-spacing:0.08em; }}

/* === KPI Cards === */
.kpi-card {{
    position: relative;
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 14px;
    padding: 18px 20px;
    min-height: 118px;
    overflow: hidden;
    transition: all 0.2s ease;
}}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent, {c['accent']});
    opacity: 0;
    transition: opacity 0.2s;
}}
.kpi-card:hover {{
    border-color: {c['border_hi']};
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.2);
}}
.kpi-card:hover::before {{ opacity: 1; }}
.kpi-label {{
    color: {c['text_muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.kpi-value {{
    color: {c['text']};
    font-size: 34px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 8px;
    letter-spacing: -0.02em;
    font-feature-settings: "tnum";
}}
.kpi-note {{ color: {c['text_dim']}; font-size: 11px; line-height: 1.45; }}
.kpi-trend {{
    display:inline-flex; align-items:center; gap:3px;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
}}

/* === Section Title === */
.section-title {{
    color: {c['text']};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0 0 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.section-title::before {{
    content: "";
    width: 3px;
    height: 14px;
    background: linear-gradient(180deg, {c['accent']}, {c['accent_2']});
    border-radius: 2px;
}}

/* === Entity Cards === */
.entity-card {{
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 8px;
    transition: all 0.15s ease;
    position: relative;
    overflow: hidden;
}}
.entity-card::before {{
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--risk-color, {c['accent']});
    opacity: 0.6;
}}
.entity-card:hover {{
    border-color: {c['border_hi']};
    background: {c['card_hi']};
    transform: translateX(2px);
}}
.entity-card h4 {{
    margin: 0 0 4px 0;
    color: {c['text']};
    font-size: 1rem;
    font-weight: 800;
    letter-spacing: -0.01em;
}}
.entity-card .meta {{
    color: {c['text_muted']};
    font-size: 0.78rem;
    margin-bottom: 0.5rem;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}}
.entity-card .rationale {{
    color: {c['text_dim']};
    font-size: 0.83rem;
    line-height: 1.55;
}}
.entity-card .rationale.empty {{
    color: {c['text_muted']};
    font-style: italic;
}}

/* === Empty / Error States === */
.empty-state {{
    text-align:center;
    padding:48px 20px;
    background: {c['card_bg']};
    border: 1px dashed {c['border_hi']};
    border-radius: 12px;
}}
.empty-state .icon {{ font-size:36px; margin-bottom:12px; opacity: 0.6; }}
.empty-state .title {{ color: {c['text']}; font-size: 14px; font-weight: 700; margin-bottom: 6px; }}
.empty-state .desc {{ color: {c['text_muted']}; font-size: 12px; }}

.error-state {{
    background: rgba(225,29,72,0.08);
    border: 1px solid rgba(225,29,72,0.3);
    border-radius: 12px;
    padding: 16px;
}}

.trust-bar {{
    display:flex; gap:20px; flex-wrap:wrap; align-items:center;
    padding:14px 18px;
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    color: {c['text_muted']};
    font-size:11px;
    margin-top: 20px;
}}
.trust-bar b {{ color: {c['text_dim']}; }}

/* === Table Row === */
.table-header-row {{
    background: {c['raised_bg']};
    border: 1px solid {c['border']};
    border-radius: 10px 10px 0 0;
    padding: 2px 0;
}}
.table-header-cell {{
    color: {c['text_muted']};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 12px 8px;
}}
.table-row {{
    border-bottom: 1px solid {c['border']};
    padding: 4px 0;
    transition: background 0.15s;
}}
.table-row:hover {{ background: {c['card_hi']}; }}

/* Utility */
hr {{ border-color: {c['border']} !important; }}
.muted {{ color: {c['text_muted']}; }}
.dim {{ color: {c['text_dim']}; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# NOISE FILTERING
# ══════════════════════════════════════════════════════════════════════════
NOISE_BRANDS = {
    "rulebook","the complete rulebook","licensing","centralbank",
    "globenewswire","globe newswire","cbuae rulebook",
    "insights for businesses","insights","businesses",
    "money transfers","gccbusinesswatch","financialit","visamiddleeast",
    "khaleejtimes","khaleej times","gulfnews","gulf news","thenational",
    "the national","arabianbusiness","arabian business","zawya","wam",
    "reuters","bloomberg","ft.com","cnbc","forbes","crunchbase",
    "techcrunch","wikipedia","medium","page","home","about","contact",
    "terms","privacy","fintech news","press release","media release",
    "news release","blog","white paper","whitepaper","report","research",
    "survey","study","conference","event","webinar","podcast","linkedin",
    "twitter","facebook","instagram","youtube","warning","vasps",
    "vasps licensing process","rules","guide","overview","trends","plan",
    "news","article","introduction","summary","conclusion","documentation",
    "docs","help","support","faq","faqs","sitemap","copyright",
}
NOISE_PATTERNS = re.compile(
    r"^(\s*[&'\"\-–—]|\s*\d+[\.\)\s]|top \d+|best \d+|leading \d+|"
    r"guide to|how to|what is|list of|complete list|overview|introduction|"
    r"insights for|transforming|mobile development|press release|whitepaper|"
    r"business plan|licensing process|warning|\d{4}\s|"
    r".*\.(com|ae|net|org|io|co)$|"
    r".*(news|times|watch|magazine|journal|newsletter|review|press|media|"
    r"blog|gazette|tribune|post|herald|daily|weekly)$)",
    re.I,
)
GENERIC_WORDS = {
    "bank","banks","banking","payment","payments","finance","financial",
    "wallet","wallets","exchange","exchanges","crypto","cryptocurrency",
    "trading","investment","investments","fintech","regulation","regulations",
    "regulatory","compliance","license","licenses","licensing","money",
    "transfer","transfers","remittance","remittances","loan","loans","lending",
    "credit","debit","card","cards","digital","mobile","online","virtual",
    "electronic","service","services","solution","solutions","platform",
    "technology","technologies","app","apps","application","company",
    "companies","corporation","corp","limited","ltd","uae","dubai","abu",
    "dhabi","emirates","gulf","middle","east","gcc","regional","international",
    "global","local",
}


def is_noise_brand(brand) -> bool:
    try:
        if not brand or not isinstance(brand, str): return True
        b = brand.strip().lower()
        if not b or len(b) < 3: return True
        if b in NOISE_BRANDS: return True
        if NOISE_PATTERNS.match(b): return True
        if re.match(r"^[\s&'\"\-–—_\.,;:]", brand): return True
        if b[0].isdigit(): return True
        if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", b): return True
        words = b.split()
        if all(w in GENERIC_WORDS for w in words): return True
        if len(words) > 5: return True
        letters = sum(ch.isalpha() for ch in brand)
        if letters < len(brand) * 0.5: return True
        return False
    except Exception:
        return True


# ══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════
DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data(show_spinner=False)
def list_screening_files() -> list[dict]:
    files = []
    try:
        for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
            p = Path(path)
            m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})", p.name)
            if m:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M")
                files.append({"path": path, "name": p.name,
                              "timestamp": ts, "size_kb": p.stat().st_size // 1024})
    except Exception:
        pass
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)


@st.cache_data(show_spinner=False)
def load_data(path: str):
    try:
        try:
            df = pd.read_excel(path, sheet_name="📋 All Results")
        except Exception:
            df = pd.read_excel(path, sheet_name=0)
    except Exception as e:
        return pd.DataFrame(), str(e)

    text_cols = [
        "Brand","Classification","Group","Service Type","Regulator Scope",
        "Alert Status","Rationale","Action Required","Top Source URL",
        "Matched Entity (Register)","Register Category","Key Snippet",
        "Source","Discovery Query","Confidence",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda v: clean_text(v))

    if "Risk Level" in df.columns:
        df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(2).astype(int)

    if "Brand" in df.columns:
        df = df[~df["Brand"].apply(is_noise_brand)].reset_index(drop=True)

    return df, None


def save_uploaded_run(uploaded_file) -> str:
    save_path = DATA_DIR / uploaded_file.name
    with open(save_path, "wb") as handle:
        handle.write(uploaded_file.getbuffer())
    st.cache_data.clear()
    return str(save_path)


# ══════════════════════════════════════════════════════════════════════════
# FUZZY SEARCH
# ══════════════════════════════════════════════════════════════════════════
def fuzzy_suggestions(query: str, choices, limit: int = 10):
    if not query or not choices: return []
    q = query.strip()
    if not q: return []
    try:
        if HAS_RAPIDFUZZ:
            return [item for item, score, _ in
                    rf_process.extract(q, list(choices), scorer=fuzz.WRatio, limit=limit)
                    if score >= 55]
        return [c for c in choices if q.lower() in str(c).lower()][:limit]
    except Exception:
        return []


def build_search_suggestions(query, brands, regulators, services):
    if not query: return []
    out = []
    for b in fuzzy_suggestions(query, list(brands), limit=8):
        out.append(f"Entity: {b}")
    for r in fuzzy_suggestions(query, [normalize_regulator(x) for x in regulators], limit=4):
        out.append(f"Regulator: {r}")
    for s in fuzzy_suggestions(query, list(services), limit=4):
        out.append(f"Service: {s}")
    return out[:12]


def fuzzy_filter_df(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or df.empty: return df
    if query.startswith("Entity: "):
        return df[df["Brand"] == query[len("Entity: "):]]
    if query.startswith("Regulator: "):
        label = query[len("Regulator: "):]
        if "Regulator Scope" in df.columns:
            return df[df["Regulator Scope"].astype(str).map(normalize_regulator) == label]
        return df
    if query.startswith("Service: "):
        return df[df["Service Type"] == query[len("Service: "):]] if "Service Type" in df.columns else df
    q = query.lower().strip()
    try:
        mask = pd.Series(False, index=df.index)
        for col in ["Brand", "Regulator Scope", "Service Type"]:
            if col in df.columns:
                if HAS_RAPIDFUZZ:
                    col_mask = df[col].astype(str).map(
                        lambda s: fuzz.partial_ratio(q, s.lower()) >= 70 if s else False
                    )
                else:
                    col_mask = df[col].astype(str).str.lower().str.contains(re.escape(q), na=False)
                mask = mask | col_mask
        return df[mask]
    except Exception:
        return df


# ══════════════════════════════════════════════════════════════════════════
# ENTITY DETAIL DIALOG
# ══════════════════════════════════════════════════════════════════════════
@st.dialog("Entity Detail", width="large")
def show_entity_detail(row: pd.Series):
    try:
        brand = row_brand(row)
        level = safe_int(row.get("Risk Level", 2))
        state = get_effective_state(row)
        wf = get_workflow(brand)
        rm = RISK_META.get(level, RISK_META[2])

        st.markdown(f"""
        <div style="background:{c['card_bg']};border:1px solid {c['border_hi']};border-radius:14px;
                    padding:18px 20px;margin-bottom:16px;position:relative;overflow:hidden;">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;
                      background: linear-gradient(90deg, {rm['color']}, {c['accent_2']});"></div>
          <div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            {risk_badge_html(level)}
            {state_badge_html(state)}
            {alert_badge_html(row.get("Alert Status", ""))}
          </div>
          <h3 style="color:{c['text']};font-size:22px;font-weight:800;margin:6px 0 6px 0;
                     letter-spacing:-0.02em;">{brand}</h3>
          <div style="color:{c['text_muted']};font-size:12px;">
            {clean_text(row.get('Classification',''), '—')}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Workflow
        st.markdown('<div class="section-title">Workflow</div>', unsafe_allow_html=True)
        nxt = next_primary_action(state)
        cols = st.columns(4)
        with cols[0]:
            if nxt is not None:
                label, target = nxt
                if st.button(label, key=f"wf_p_{brand}", type="primary", use_container_width=True):
                    set_workflow_state(brand, target); st.rerun()
            else:
                st.button("Done", key=f"wf_d_{brand}", disabled=True, use_container_width=True)
        with cols[1]:
            if st.button("↑ Escalate", key=f"wf_e_{brand}", use_container_width=True,
                         disabled=state == "INVESTIGATING"):
                set_workflow_state(brand, "INVESTIGATING"); st.rerun()
        with cols[2]:
            if st.button("✓ Mark Reviewed", key=f"wf_r_{brand}", use_container_width=True,
                         disabled=state == "REVIEWED"):
                set_workflow_state(brand, "REVIEWED"); st.rerun()
        with cols[3]:
            if st.session_state.confirm_clear_brand == brand:
                if st.button("⚠ Confirm", key=f"wf_cc_{brand}", use_container_width=True):
                    clear_workflow(brand)
                    st.session_state.confirm_clear_brand = None
                    st.rerun()
            else:
                if st.button("✕ Clear", key=f"wf_c_{brand}", use_container_width=True,
                             disabled=wf.get("state") is None):
                    st.session_state.confirm_clear_brand = brand; st.rerun()

        with st.expander("✎ Add / update note"):
            current_note = wf.get("note") or ""
            note = st.text_area("Note", value=current_note,
                                placeholder="Add context, link, or reason…",
                                key=f"note_{brand}", label_visibility="collapsed")
            nc = st.columns([1, 1, 4])
            with nc[0]:
                if st.button("Save note", key=f"sn_{brand}", use_container_width=True):
                    eff = wf.get("state") or default_workflow_state(level, row.get("Classification",""))
                    set_workflow_state(brand, eff, note=note.strip() or None); st.rerun()
            with nc[1]:
                if st.button("Clear note", key=f"cn_{brand}", use_container_width=True,
                             disabled=not current_note):
                    eff = wf.get("state") or default_workflow_state(level, row.get("Classification",""))
                    set_workflow_state(brand, eff, note=None); st.rerun()

        if wf.get("state"):
            note_txt = f' · Note: "{wf["note"]}"' if wf.get("note") else ""
            st.markdown(f"""
            <div style="background:{c['accent_dim']};border:1px solid {c['accent_bd']};
                        border-radius:8px;padding:10px 14px;margin-top:10px;
                        color:{c['text_dim']};font-size:11px;">
              Current state: <b style="color:{c['text']};">{WORKFLOW_STYLES[wf['state']]['label']}</b>
              · Updated at {wf.get('ts','—')}{note_txt}
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        mc1, mc2 = st.columns(2)
        with mc1:
            for label, key in [("Service Type","Service Type"),
                               ("Regulator Scope","Regulator Scope"),
                               ("Classification","Classification")]:
                raw = clean_text(row.get(key, ""), fallback="—")
                val = normalize_regulator(raw) if key == "Regulator Scope" else raw
                st.markdown(f"""
                <div style="margin-bottom:14px;">
                  <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                              letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px;">{label}</div>
                  <div style="color:{c['text']};font-size:13px;font-weight:500;">{val}</div>
                </div>
                """, unsafe_allow_html=True)

        with mc2:
            conf = clean_text(row.get("Confidence", ""))
            matched = clean_text(row.get("Matched Entity (Register)", ""), fallback="—")
            url = clean_text(row.get("Top Source URL", ""))
            st.markdown(f"""
            <div style="margin-bottom:14px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Confidence</div>
              {confidence_bar_html(conf)}
            </div>
            <div style="margin-bottom:14px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px;">Matched Entity</div>
              <div style="color:{c['text']};font-size:13px;font-weight:500;">{matched}</div>
            </div>
            """, unsafe_allow_html=True)
            if url.startswith("http"):
                st.link_button("↗ View Source", url, use_container_width=True)

        st.divider()

        rat = clean_text(row.get("Rationale", ""),
                         fallback="No description available — review source manually.")
        st.markdown(f"""
        <div style="margin-bottom:14px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                      letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px;">Rationale</div>
          <div style="color:{c['text_dim']};font-size:13px;line-height:1.7;">{rat}</div>
        </div>
        """, unsafe_allow_html=True)

        act = clean_text(row.get("Action Required", ""))
        if act:
            st.markdown(f"""
            <div style="background:{c['accent_dim']};border:1px solid {c['accent_bd']};
                        border-radius:10px;padding:12px 16px;">
              <div style="color:{c['accent']};font-size:9px;font-weight:800;letter-spacing:0.12em;
                          text-transform:uppercase;margin-bottom:6px;">Action Required</div>
              <div style="color:{c['text']};font-size:13px;line-height:1.6;">{act}</div>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Could not render details: {e}")


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:4px 0 16px 0;
                border-bottom:1px solid {c['border']};margin-bottom:16px;">
        <div class="hero-icon" style="width:36px;height:36px;font-size:16px;">🛡️</div>
        <div>
            <div style="color:{c['text']};font-size:14px;font-weight:800;">UAE Screening</div>
            <div style="color:{c['text_muted']};font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;">Risk Monitoring</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    theme_label = "☀  Light Mode" if dark else "☾  Dark Mode"
    if st.button(theme_label, use_container_width=True, key="sb_theme"):
        st.session_state.theme = "light" if dark else "dark"
        st.rerun()

    st.markdown("---")

    files = list_screening_files()
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;'
                f'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Screening Run</div>',
                unsafe_allow_html=True)

    selected_path = None
    if files:
        options = {
            f'{f["timestamp"].strftime("%d %b %Y, %H:%M")}  ·  {f["size_kb"]} KB': f["path"]
            for f in files
        }
        choice = st.selectbox("Run", list(options.keys()), index=0,
                              label_visibility="collapsed", key="sb_run")
        selected_path = options[choice]
    else:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">📭</div>
          <div class="title">No screening files</div>
          <div class="desc">Upload an xlsx below</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;'
                f'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Upload New Run</div>',
                unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload", type=["xlsx"],
                                label_visibility="collapsed", key="sb_upload")
    if uploaded:
        try:
            save_uploaded_run(uploaded)
            st.success(f"Saved: {uploaded.name}")
            st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")

    st.markdown("---")
    st.caption(f"Runs archived: **{len(files)}**")
    st.caption("Internal tool — not a legal determination.")


# ══════════════════════════════════════════════════════════════════════════
# HERO BAR
# ══════════════════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
st.markdown(f"""
<div class="hero-bar">
  <div class="hero-logo">
    <div class="hero-icon">🛡️</div>
    <div>
      <div class="hero-title">UAE Regulatory Screening</div>
      <div class="hero-sub">Internal Risk Monitoring Platform</div>
    </div>
  </div>
  <div class="hero-meta">
    <div class="hero-run">
      <div class="label">Current Run</div>
      <div class="value">{now_str}</div>
      <div class="src">VARA · CBUAE · DFSA · ADGM · SCA</div>
    </div>
    <div class="live-badge">
      <span class="live-dot"></span>
      <span class="live-txt">LIVE</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# EMPTY FILE STATE
# ══════════════════════════════════════════════════════════════════════════
if selected_path is None:
    st.markdown(f"""
    <div style="max-width:760px;margin:32px auto 0 auto;background:{c['card_bg']};
                border:1px solid {c['accent_bd']};border-radius:16px;padding:28px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
        <div style="width:44px;height:44px;border-radius:12px;background:{c['accent_dim']};
                    border:1px solid {c['accent_bd']};display:flex;align-items:center;
                    justify-content:center;font-size:20px;">📂</div>
        <div>
          <div style="color:{c['text']};font-size:20px;font-weight:800;">Upload a screening run</div>
          <div style="color:{c['text_muted']};font-size:12px;margin-top:4px;">
            Built for <code>UAE_Screening_*.xlsx</code> files.
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded_main = st.file_uploader("Upload", type=["xlsx"], key="main_upload")
    if uploaded_main:
        try:
            save_uploaded_run(uploaded_main)
            st.success(f"Uploaded: {uploaded_main.name}")
            st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════
with st.spinner("Loading screening data…"):
    df, load_error = load_data(selected_path)

if load_error:
    st.markdown(f"""
    <div class="error-state">
      <div style="color:#E11D48;font-size:13px;font-weight:700;margin-bottom:4px;">
        ⚠ Failed to load data
      </div>
      <div style="color:{c['text_muted']};font-size:11px;">{load_error}</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if df.empty:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">📭</div>
      <div class="title">Empty dataset</div>
      <div class="desc">The selected file contains no valid entities after filtering.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# Pre-compute derived columns once
df = df.copy()
df["__state"] = df.apply(get_effective_state, axis=1)
df["__conf_rank"] = df["Confidence"].map(confidence_rank) if "Confidence" in df.columns else 0
if "Risk Level" not in df.columns:
    df["Risk Level"] = 2
df["Risk Level"] = df["Risk Level"].fillna(2).astype(int)


# ══════════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════════
total     = len(df)
critical  = int((df["Risk Level"] >= 5).sum())
high      = int((df["Risk Level"] == 4).sum())
needs_rev = int(((df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)).sum())
licensed  = int((df["Risk Level"] == 0).sum())
new_ents  = int(df["Alert Status"].astype(str).str.contains("NEW", case=False, na=False).sum()) if "Alert Status" in df.columns else 0
risk_up   = int(df["Alert Status"].astype(str).str.contains("INCREASED", case=False, na=False).sum()) if "Alert Status" in df.columns else 0

kpi_cards = [
    ("👥  Entities Screened", f"{total:,}", "Total entities after noise filtering", c["accent"]),
    ("⚠️  Critical / High",   f"{critical + high:,}",
     f"{(critical + high) / total * 100:.0f}% of total" if total else "0%",
     RISK_META[4]["color"]),
    ("◐  Needs Review",       f"{needs_rev:,}", "Risk levels 2–3", RISK_META[3]["color"]),
    ("✓  Licensed / Clear",   f"{licensed:,}", "Risk level 0", RISK_META[0]["color"]),
    ("✨  New Entities",       f"{new_ents:,}",
     f"{risk_up} risk increased" if risk_up else "No risk increases this run",
     c["success"] if new_ents else c["text_muted"]),
]

k_cols = st.columns(5)
for col, (label, value, note, accent) in zip(k_cols, kpi_cards):
    col.markdown(f"""
    <div class="kpi-card" style="--accent:{accent};">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")


# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_home, tab_search, tab_insights = st.tabs(["🏠  Overview", "🔍  Search & Filter", "📊  Insights"])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
with tab_home:
    left_col, right_col = st.columns([1.7, 1])

    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.caption("High & Critical entities — review, escalate, or open full detail.")

        top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)

        if top_risk.empty:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.28);
                        border-radius:12px;padding:24px;text-align:center;">
              <div style="color:#10B981;font-size:14px;font-weight:700;">
                ✓ No high-risk entities this run
              </div>
              <div style="color:{c['text_muted']};font-size:11px;margin-top:4px;">
                All entities are below Critical/High thresholds.
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for _, row in top_risk.iterrows():
                try:
                    brand = row_brand(row)
                    level = safe_int(row.get("Risk Level", 2))
                    rm = RISK_META.get(level, RISK_META[2])
                    state = get_effective_state(row)
                    svc = clean_text(row.get("Service Type", ""), "—")
                    reg = normalize_regulator(row.get("Regulator Scope", ""))
                    rat_raw = clean_text(row.get("Rationale", ""))
                    rat = (rat_raw[:220] + "…") if len(rat_raw) > 220 else (rat_raw or "No description available.")

                    st.markdown(f"""
                    <div class="entity-card" style="--risk-color:{rm['color']};">
                      <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start;">
                        <div style="flex:1;min-width:0;">
                          <h4>{brand}</h4>
                          <div class="meta">
                            {chip_html(reg)} {chip_html(svc)}
                          </div>
                          <div class="rationale">{rat}</div>
                        </div>
                        <div style="text-align:right;min-width:140px;display:flex;flex-direction:column;gap:6px;align-items:flex-end;">
                          {risk_badge_html(level)}
                          {state_badge_html(state)}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    ctrl_cols = st.columns([1.3, 1.2, 1.1, 3.4])
                    nxt = next_primary_action(state)
                    with ctrl_cols[0]:
                        if nxt and st.button(nxt[0], key=f"ov_p_{row.name}",
                                             type="primary", use_container_width=True):
                            set_workflow_state(brand, nxt[1]); st.rerun()
                        elif not nxt:
                            st.button("Done", key=f"ov_d_{row.name}",
                                      disabled=True, use_container_width=True)
                    with ctrl_cols[1]:
                        if st.button("Detail", key=f"ov_det_{row.name}", use_container_width=True):
                            show_entity_detail(row)
                    with ctrl_cols[2]:
                        url = clean_text(row.get("Top Source URL", ""))
                        if url.startswith("http"):
                            st.link_button("Source", url, use_container_width=True)
                except Exception as e:
                    st.caption(f"Could not render row: {e}")

    with right_col:
        if new_ents > 0 or risk_up > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(249,115,22,0.08), rgba(249,115,22,0.02));
                        border:1px solid rgba(249,115,22,0.28);
                        border-radius:12px;padding:14px 16px;margin-bottom:16px;">
              <div style="color:#F97316;font-size:10px;font-weight:800;letter-spacing:0.1em;
                          margin-bottom:8px;text-transform:uppercase;">⚡ Alerts This Run</div>
              {"<div style='color:"+c["text_dim"]+";font-size:12px;margin-bottom:4px;'>"
                "<span style='color:#22C55E;font-weight:800;'>"+str(new_ents)+"</span> new entities added</div>"
                if new_ents else ""}
              {"<div style='color:"+c["text_dim"]+";font-size:12px;'>"
                "<span style='color:#F97316;font-weight:800;'>"+str(risk_up)+"</span> risk level increases</div>"
                if risk_up else ""}
            </div>
            """, unsafe_allow_html=True)

        try:
            import altair as alt
            st.markdown('<div class="section-title">Risk Distribution</div>', unsafe_allow_html=True)
            st.caption("Click a bar to filter the Search tab.")
            rc = df["Risk Level"].value_counts().reset_index()
            rc.columns = ["level", "count"]
            rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x), {}).get("label", "Unknown"))
            colors_map = {v["label"]: v["color"] for v in RISK_META.values()}

            selection = alt.selection_point(fields=["level"], name="sel")
            chart = (
                alt.Chart(rc)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, opacity=0.92)
                .encode(
                    x=alt.X("label:N",
                            sort=alt.EncodingSortField("level", order="descending"),
                            title=None,
                            axis=alt.Axis(labelColor=c["text_dim"], domainColor=c["border"],
                                          labelAngle=0, labelFontSize=11)),
                    y=alt.Y("count:Q",
                            axis=alt.Axis(labelColor=c["text_dim"], gridColor=c["border"],
                                          domainColor="transparent", title="Entities",
                                          titleColor=c["text_muted"])),
                    color=alt.Color("label:N",
                                    scale=alt.Scale(domain=list(colors_map.keys()),
                                                    range=list(colors_map.values())),
                                    legend=None),
                    opacity=alt.condition(selection, alt.value(1.0), alt.value(0.4)),
                    tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                )
                .add_params(selection)
                .properties(height=220)
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"])
            )
            event = st.altair_chart(chart, use_container_width=True,
                                    on_select="rerun", key="ov_chart")
            try:
                sel_points = event.selection.get("sel", []) if event and hasattr(event, "selection") else []
                if sel_points:
                    clicked = sel_points[0].get("level")
                    if clicked is not None and st.session_state.clicked_risk_level != clicked:
                        st.session_state.clicked_risk_level = int(clicked)
                        st.session_state.risk_filter = int(clicked)
                        st.session_state.page = 1
            except Exception:
                pass
        except Exception:
            pass

        # Recent workflow actions
        if st.session_state.workflow:
            st.markdown('<div class="section-title" style="margin-top:20px;">Recent Actions</div>',
                        unsafe_allow_html=True)
            recent = sorted(
                [(b, d) for b, d in st.session_state.workflow.items() if d.get("ts")],
                key=lambda x: x[1]["ts"], reverse=True
            )[:6]
            if not recent:
                st.caption("No workflow actions yet.")
            else:
                items_html = ""
                for brand_name, data in recent:
                    state = data.get("state", "OPEN")
                    ts = data.get("ts", "—").split(" ")[-1]  # HH:MM:SS
                    style = WORKFLOW_STYLES.get(state, WORKFLOW_STYLES["OPEN"])
                    items_html += f"""
                    <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
                                border-bottom:1px solid {c['border']};">
                      <span style="color:{style['color']};font-size:14px;">{style['icon']}</span>
                      <div style="flex:1;min-width:0;">
                        <div style="color:{c['text']};font-size:12px;font-weight:700;
                                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{brand_name}</div>
                        <div style="color:{c['text_muted']};font-size:10px;">
                          {style['label']} · {ts}
                        </div>
                      </div>
                    </div>
                    """
                st.markdown(f"""
                <div style="background:{c['card_bg']};border:1px solid {c['border']};
                            border-radius:12px;overflow:hidden;">
                  {items_html}
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — SEARCH & FILTER
# ══════════════════════════════════════════════════════════════════════════
with tab_search:
    all_brands     = sorted(df["Brand"].dropna().astype(str).tolist()) if "Brand" in df.columns else []
    all_regulators = sorted(df["Regulator Scope"].dropna().astype(str).unique().tolist()) if "Regulator Scope" in df.columns else []
    all_services   = sorted(df["Service Type"].dropna().astype(str).unique().tolist()) if "Service Type" in df.columns else []

    rc_version = st.session_state.reset_counter  # version suffix for widget keys

    # Search
    st.markdown('<div class="section-title">Search</div>', unsafe_allow_html=True)
    if HAS_SEARCHBOX:
        sbox_val = st_searchbox(
            lambda q: build_search_suggestions(q, all_brands, all_regulators, all_services),
            placeholder="Fuzzy search entity, regulator, or service…",
            key=f"search_autocomplete_{rc_version}",
            clear_on_submit=False,
        )
        search_query = (sbox_val or "").strip()
    else:
        search_query = st.text_input(
            "Search",
            value=st.session_state.get("search_query", ""),
            placeholder="Fuzzy search entity, regulator, or service…",
            key=f"search_text_{rc_version}",
            label_visibility="collapsed",
        ).strip()
        if search_query and not HAS_SEARCHBOX:
            sugg = build_search_suggestions(search_query, all_brands, all_regulators, all_services)
            if sugg:
                st.caption("Suggestions: " + " · ".join(sugg[:5]))
    st.session_state.search_query = search_query

    # Filters section
    st.markdown('<div class="section-title" style="margin-top:16px;">Filters</div>',
                unsafe_allow_html=True)

    # Risk chips
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:10px;font-weight:700;'
                f'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;">Risk Level</div>',
                unsafe_allow_html=True)
    risk_cols = st.columns(7)
    risk_defs = [("All", None), ("Critical", 5), ("High", 4), ("Medium", 3),
                 ("Monitor", 2), ("Low", 1), ("Licensed", 0)]
    for i, (label, level) in enumerate(risk_defs):
        active = st.session_state.risk_filter == level
        btn_label = f"● {label}" if active else label
        if risk_cols[i].button(btn_label, key=f"risk_{label}_{rc_version}",
                               use_container_width=True,
                               type="primary" if active else "secondary"):
            st.session_state.risk_filter = level
            st.session_state.page = 1
            st.rerun()

    # Dropdown row
    f_cols = st.columns([1.3, 1.3, 1.3, 1.1, 1.2])

    reg_counts = df["Regulator Scope"].fillna("—").astype(str).value_counts() if "Regulator Scope" in df.columns else pd.Series(dtype=int)
    reg_map = {"All Regulators": None}
    for r, cnt in reg_counts.items():
        reg_map[f"{normalize_regulator(r)} ({cnt})"] = r

    with f_cols[0]:
        reg_choice = st.selectbox(
            "Regulator", list(reg_map.keys()),
            key="regulator_choice",
            help="Filter by regulatory body",
        )
    with f_cols[1]:
        status_choice = st.selectbox(
            "Status (Workflow)",
            ["All Statuses"] + [WORKFLOW_STYLES[s]["label"] for s in WORKFLOW_STATES],
            key="status_choice",
            help="Workflow state: Open → Investigating → Reviewed → Closed",
        )
    with f_cols[2]:
        confidence_choice = st.selectbox(
            "Confidence",
            ["All Confidence", "High Only", "Medium Only", "Low Only"],
            key="confidence_choice",
            help="Model's confidence in the match",
        )
    with f_cols[3]:
        sort_choice = st.selectbox(
            "Sort",
            ["Priority", "Risk", "Status", "Confidence", "Regulator", "Brand"],
            key="sort_choice",
        )
    with f_cols[4]:
        actionable_only = st.toggle(
            "Actionable only",
            key="actionable_only",
            help="Only rows needing action (Open or Investigating).",
        )

    # Quick chips
    quick_defs = [("Critical/High", "high"), ("New Entities", "new"),
                  ("Risk Up", "riskup"), ("Licensed", "licensed"),
                  ("VASP/Crypto", "va")]
    qcols = st.columns(len(quick_defs) + 1)
    for i, (label, key) in enumerate(quick_defs):
        active = st.session_state.quick_filter == key
        btn_label = f"● {label}" if active else label
        if qcols[i].button(btn_label, key=f"quick_{key}_{rc_version}",
                           use_container_width=True,
                           type="primary" if active else "secondary"):
            st.session_state.quick_filter = None if active else key
            st.session_state.page = 1
            st.rerun()
    with qcols[-1]:
        if st.button("✕ Clear all", key=f"clear_all_{rc_version}", use_container_width=True):
            reset_all_filters()
            st.rerun()

    # Apply filters
    filtered = df.copy()
    try:
        if st.session_state.search_query:
            filtered = fuzzy_filter_df(filtered, st.session_state.search_query)

        sel_reg = reg_map.get(reg_choice)
        if sel_reg:
            filtered = filtered[filtered["Regulator Scope"] == sel_reg]

        if st.session_state.risk_filter is not None:
            filtered = filtered[filtered["Risk Level"] == st.session_state.risk_filter]

        label_to_state = {WORKFLOW_STYLES[s]["label"]: s for s in WORKFLOW_STATES}
        if status_choice != "All Statuses":
            want = label_to_state.get(status_choice)
            if want:
                filtered = filtered[filtered["__state"] == want]

        conf_map = {"High Only": 3, "Medium Only": 2, "Low Only": 1}
        if confidence_choice in conf_map:
            filtered = filtered[filtered["__conf_rank"] == conf_map[confidence_choice]]

        if actionable_only:
            filtered = filtered[filtered["__state"].isin(["OPEN", "INVESTIGATING"])]

        qf = st.session_state.quick_filter
        if qf == "high":
            filtered = filtered[filtered["Risk Level"] >= 4]
        elif qf == "new" and "Alert Status" in filtered.columns:
            filtered = filtered[filtered["Alert Status"].astype(str).str.contains("NEW", case=False, na=False)]
        elif qf == "riskup" and "Alert Status" in filtered.columns:
            filtered = filtered[filtered["Alert Status"].astype(str).str.contains("INCREASED", case=False, na=False)]
        elif qf == "licensed":
            filtered = filtered[filtered["Risk Level"] == 0]
        elif qf == "va":
            mask = pd.Series(False, index=filtered.index)
            if "Regulator Scope" in filtered.columns:
                mask = mask | filtered["Regulator Scope"].astype(str).str.contains("VA|VASP|CRYPTO", case=False, na=False)
            if "Service Type" in filtered.columns:
                mask = mask | filtered["Service Type"].astype(str).str.contains("crypto|virtual asset|token", case=False, na=False)
            filtered = filtered[mask]

        state_priority = {"OPEN": 3, "INVESTIGATING": 2, "REVIEWED": 1, "CLOSED": 0}
        filtered = filtered.copy()
        filtered["__state_pri"] = filtered["__state"].map(state_priority).fillna(0).astype(int)

        if sort_choice == "Priority":
            filtered = filtered.sort_values(["Risk Level", "__state_pri", "__conf_rank", "Brand"],
                                            ascending=[False, False, False, True])
        elif sort_choice == "Risk":
            filtered = filtered.sort_values(["Risk Level", "Brand"], ascending=[False, True])
        elif sort_choice == "Status":
            filtered = filtered.sort_values(["__state_pri", "Risk Level", "Brand"],
                                            ascending=[False, False, True])
        elif sort_choice == "Confidence":
            filtered = filtered.sort_values(["__conf_rank", "Risk Level", "Brand"],
                                            ascending=[False, False, True])
        elif sort_choice == "Regulator":
            filtered = filtered.sort_values(["Regulator Scope", "Risk Level", "Brand"],
                                            ascending=[True, False, True])
        else:
            filtered = filtered.sort_values(["Brand", "Risk Level"], ascending=[True, False])

    except Exception as e:
        st.error(f"Filter error: {e}")
        filtered = df.copy()

    # Count
    st.markdown(f"""
    <div style="color:{c['text_muted']};font-size:11px;margin:10px 0 12px 0;">
      <strong style="color:{c['text_dim']};font-weight:700;">{len(filtered):,}</strong>
      of <strong style="color:{c['text_dim']};font-weight:700;">{total:,}</strong> entities
    </div>
    """, unsafe_allow_html=True)

    selected_brands = set(st.session_state.selected_rows)

    if filtered.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🔍</div>
          <div class="title">No entities match these filters</div>
          <div class="desc">Clear one or two filters to repopulate the table.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        per_page = 10
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        if st.session_state.page > total_pages:
            st.session_state.page = 1
        start = (st.session_state.page - 1) * per_page
        page_df = filtered.iloc[start:start + per_page]

        # Header
        h_cols = st.columns([0.35, 2.3, 0.9, 1.2, 1.0, 0.85, 1.1, 1.5])
        sort_arrow = " ↓" if sort_choice in {"Priority", "Risk"} else ""
        status_arrow = " ↓" if sort_choice == "Status" else ""
        conf_arrow = " ↓" if sort_choice == "Confidence" else ""
        reg_arrow = " ↑" if sort_choice == "Regulator" else ""
        brand_arrow = " ↑" if sort_choice == "Brand" else ""
        headers = ["", f"Entity{brand_arrow}", f"Risk{sort_arrow}",
                   f"Regulator{reg_arrow}", "Service", f"Conf.{conf_arrow}",
                   f"Status{status_arrow}", "Actions"]
        for hcol, label in zip(h_cols, headers):
            hcol.markdown(
                f'<div class="table-header-cell">{label}</div>',
                unsafe_allow_html=True,
            )

        # Rows
        for _, row in page_df.iterrows():
            try:
                brand = row_brand(row)
                level = safe_int(row.get("Risk Level", 2))
                state = get_effective_state(row)
                service = clean_text(row.get("Service Type", ""), "—")
                regulator = normalize_regulator(row.get("Regulator Scope", "—"))

                brand_key = re.sub(r'[^a-z0-9]', '_', brand.lower())[:40]
                checkbox_key = f"row_sel_{brand_key}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = brand in selected_brands

                rcols = st.columns([0.35, 2.3, 0.9, 1.2, 1.0, 0.85, 1.1, 1.5])
                with rcols[0]:
                    checked = st.checkbox("Select", key=checkbox_key, label_visibility="collapsed")
                    if checked:
                        selected_brands.add(brand)
                    else:
                        selected_brands.discard(brand)
                with rcols[1]:
                    cls = clean_text(row.get("Classification", ""), "—")
                    cls_short = cls[:52] + "…" if len(cls) > 52 else cls
                    st.markdown(
                        f'<div style="padding:4px 0;">'
                        f'<div style="color:{c["text"]};font-size:13px;font-weight:700;'
                        f'letter-spacing:-0.01em;">{brand}</div>'
                        f'<div style="color:{c["text_muted"]};font-size:10px;margin-top:2px;">'
                        f'{cls_short}</div></div>',
                        unsafe_allow_html=True,
                    )
                with rcols[2]:
                    st.markdown(risk_badge_html(level), unsafe_allow_html=True)
                with rcols[3]:
                    st.markdown(chip_html(regulator), unsafe_allow_html=True)
                with rcols[4]:
                    short_svc = service if len(service) <= 18 else service[:16] + "…"
                    st.markdown(chip_html(short_svc), unsafe_allow_html=True)
                with rcols[5]:
                    st.markdown(confidence_bar_html(clean_text(row.get("Confidence", ""))),
                                unsafe_allow_html=True)
                with rcols[6]:
                    st.markdown(state_badge_html(state), unsafe_allow_html=True)
                with rcols[7]:
                    acols = st.columns([1, 1])
                    nxt = next_primary_action(state)
                    primary_label = nxt[0] if nxt else "View"
                    if acols[0].button(primary_label, key=f"row_prim_{row.name}",
                                       use_container_width=True, type="primary"):
                        if nxt is not None:
                            set_workflow_state(brand, nxt[1])
                            st.rerun()
                        else:
                            show_entity_detail(row)
                    if acols[1].button("Detail", key=f"row_det_{row.name}", use_container_width=True):
                        show_entity_detail(row)

                st.markdown(f'<div style="height:1px;background:{c["border"]};margin:2px 0;"></div>',
                            unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Row render error: {e}")

        st.session_state.selected_rows = sorted(selected_brands)

        # Footer: bulk + pagination
        fcols = st.columns([2.3, 1.5, 1.5, 2.5, 0.9, 1.1])
        if fcols[0].button(f"Bulk Investigate ({len(selected_brands)})",
                           key=f"bulk_inv_{rc_version}", use_container_width=True,
                           disabled=not selected_brands,
                           type="primary" if selected_brands else "secondary"):
            for b in selected_brands:
                set_workflow_state(b, "INVESTIGATING")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        if fcols[1].button("Mark Reviewed", key=f"bulk_rev_{rc_version}",
                           use_container_width=True, disabled=not selected_brands):
            for b in selected_brands:
                set_workflow_state(b, "REVIEWED")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        if fcols[2].button("Close", key=f"bulk_close_{rc_version}",
                           use_container_width=True, disabled=not selected_brands):
            for b in selected_brands:
                set_workflow_state(b, "CLOSED")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        fcols[3].markdown(
            f"<div style='text-align:right;padding-top:0.45rem;color:{c['text_muted']};"
            f"font-size:11px;'>Page <strong style='color:{c['text']}'>{st.session_state.page}</strong> "
            f"of {total_pages}</div>",
            unsafe_allow_html=True,
        )
        if fcols[4].button("◀", key=f"p_prev_{rc_version}", use_container_width=True,
                           disabled=st.session_state.page <= 1):
            st.session_state.page -= 1; st.rerun()
        if fcols[5].button("Next →", key=f"p_next_{rc_version}", use_container_width=True,
                           disabled=st.session_state.page >= total_pages):
            st.session_state.page += 1; st.rerun()

        st.markdown("")
        try:
            export_df = filtered.drop(
                columns=[col for col in filtered.columns if col.startswith("__")],
                errors="ignore",
            )
            d1, d2 = st.columns(2)
            csv = export_df.to_csv(index=False).encode("utf-8-sig")
            d1.download_button(
                "↓ Download CSV", data=csv,
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv", use_container_width=True,
            )
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                export_df.to_excel(w, index=False, sheet_name="Filtered")
            d2.download_button(
                "↓ Download Excel", data=buf.getvalue(),
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"Export unavailable: {e}")


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — INSIGHTS
# ══════════════════════════════════════════════════════════════════════════
with tab_insights:
    try:
        import altair as alt

        RISK_COLORS = {v["label"]: v["color"] for v in RISK_META.values()}

        def _axis_x(label_angle: int = 0):
            return alt.Axis(
                labelColor=c["text_dim"],
                tickColor="transparent",
                domainColor=c["border"],
                labelFontSize=11,
                labelAngle=label_angle,
            )

        def _axis_y(title: str = "Count"):
            return alt.Axis(
                labelColor=c["text_dim"],
                gridColor=c["border"],
                domainColor="transparent",
                tickColor="transparent",
                title=title,
                titleColor=c["text_muted"],
            )

        def bar_chart(series, title, subtitle, color_val="#818cf8", rotate=-30, height=240):
            if series is None or series.empty:
                return False
            df_c = series.reset_index()
            df_c.columns = ["label", "value"]
            chart = (
                alt.Chart(df_c)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, opacity=0.92)
                .encode(
                    x=alt.X("label:N", sort="-y", axis=_axis_x(label_angle=rotate), title=None),
                    y=alt.Y("value:Q", axis=_axis_y("Count")),
                    color=alt.value(color_val),
                    tooltip=["label:N", alt.Tooltip("value:Q", title="Count")],
                )
                .properties(height=height,
                            title=alt.TitleParams(title, subtitle=[subtitle],
                                                  color=c["text"], fontSize=13, fontWeight=700,
                                                  subtitleColor=c["text_dim"], subtitleFontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"])
            )
            st.altair_chart(chart, use_container_width=True)
            return True

        # Summary cards
        top_risk_label = (
            df["Risk Level"].map(lambda x: RISK_META.get(int(x), {}).get("label", "")).value_counts().idxmax()
            if "Risk Level" in df.columns and not df.empty else "—"
        )
        top_reg = normalize_regulator(df["Regulator Scope"].value_counts().idxmax()) \
            if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty else "—"
        top_svc = df["Service Type"].value_counts().idxmax() \
            if "Service Type" in df.columns and not df["Service Type"].dropna().empty else "—"

        si_cols = st.columns(4)
        for scol, label, value, col_color in [
            (si_cols[0], "Most Common Risk", top_risk_label, "#E11D48"),
            (si_cols[1], "Top Regulator",    top_reg,        "#4A7FD4"),
            (si_cols[2], "Top Service Type", top_svc,        c["accent"]),
            (si_cols[3], "New This Run",     f"+{new_ents}", "#22C55E"),
        ]:
            scol.markdown(f"""
            <div style="background:{c['card_bg']};border-radius:12px;padding:14px 16px;
                        border:1px solid {c['border']};min-height:74px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">{label}</div>
              <div style="color:{col_color};font-size:14px;font-weight:800;overflow:hidden;
                          text-overflow:ellipsis;white-space:nowrap;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        ic1, ic2 = st.columns(2)
        with ic1:
            if "Risk Level" in df.columns:
                rc = df["Risk Level"].value_counts().reset_index()
                rc.columns = ["level", "count"]
                rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x), {}).get("label", "Unknown"))
                chart = (
                    alt.Chart(rc)
                    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, opacity=0.92)
                    .encode(
                        x=alt.X("label:N",
                                sort=alt.EncodingSortField("level", order="descending"),
                                axis=_axis_x(label_angle=0), title=None),
                        y=alt.Y("count:Q", axis=_axis_y("Entity Count")),
                        color=alt.Color("label:N",
                                        scale=alt.Scale(domain=list(RISK_COLORS.keys()),
                                                        range=list(RISK_COLORS.values())),
                                        legend=None),
                        tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                    )
                    .properties(height=240,
                                title=alt.TitleParams("Risk Level Distribution",
                                                      subtitle=["Entity count per risk category"],
                                                      color=c["text"], fontSize=13, fontWeight=700,
                                                      subtitleColor=c["text_dim"], subtitleFontSize=10))
                    .configure_view(strokeOpacity=0, fill=c["card_bg"])
                    .configure(background=c["card_bg"])
                )
                st.altair_chart(chart, use_container_width=True)

        with ic2:
            if "Regulator Scope" in df.columns:
                reg_series = df["Regulator Scope"].map(normalize_regulator).value_counts().head(10)
                bar_chart(reg_series, "Regulator Scope",
                          "Entities per regulatory body", "#4A7FD4")

        ic3, ic4 = st.columns(2)
        with ic3:
            if "Service Type" in df.columns:
                bar_chart(df["Service Type"].value_counts().head(10),
                          "Service Type Mix", "Top service categories identified", c["accent"])
        with ic4:
            if "Alert Status" in df.columns:
                alerts = df["Alert Status"].replace("", pd.NA).dropna()
                if not alerts.empty:
                    bar_chart(alerts.value_counts().head(10),
                              "Alert Status Mix", "Changes detected vs. prior run", "#F97316")
                else:
                    st.markdown("""
                    <div class="empty-state">
                      <div class="icon">✓</div>
                      <div class="title">No alerts this run</div>
                      <div class="desc">No new entities or risk changes detected vs. prior run.</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Trend (only 2+ runs)
        files_list = list_screening_files()
        if len(files_list) >= 2:
            st.markdown("---")
            st.markdown('<div class="section-title">Trend Across Runs</div>',
                        unsafe_allow_html=True)
            trend_rows = []
            for f in files_list[:10]:
                try:
                    d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                    d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                    trend_rows.append({
                        "Run":           f["timestamp"].strftime("%m/%d %H:%M"),
                        "High/Critical": int((d["Risk Level"] >= 4).sum()),
                        "Needs Review":  int(((d["Risk Level"] >= 2) & (d["Risk Level"] <= 3)).sum()),
                        "Licensed":      int((d["Risk Level"] == 0).sum()),
                    })
                except Exception:
                    continue
            if trend_rows:
                _trend = pd.DataFrame(trend_rows).iloc[::-1]
                _long = _trend.melt("Run", var_name="Category", value_name="Count")
                tcolors = {"High/Critical": "#E11D48", "Needs Review": "#EAB308", "Licensed": "#10B981"}
                chart = (
                    alt.Chart(_long)
                    .mark_line(point=alt.OverlayMarkDef(size=80, filled=True), strokeWidth=2.5)
                    .encode(
                        x=alt.X("Run:N", axis=_axis_x(label_angle=-20), title=None),
                        y=alt.Y("Count:Q", axis=_axis_y("Entity Count")),
                        color=alt.Color("Category:N",
                                        scale=alt.Scale(domain=list(tcolors.keys()),
                                                        range=list(tcolors.values())),
                                        legend=alt.Legend(labelColor=c["text_dim"],
                                                          titleColor=c["text_dim"])),
                        tooltip=["Run:N", "Category:N", alt.Tooltip("Count:Q", title="Entities")],
                    )
                    .properties(height=260,
                                title=alt.TitleParams("Risk Trend Across Runs",
                                                      subtitle=["Historical view of risk category counts"],
                                                      color=c["text"], fontSize=13, fontWeight=700,
                                                      subtitleColor=c["text_dim"], subtitleFontSize=10))
                    .configure_view(strokeOpacity=0, fill=c["card_bg"])
                    .configure(background=c["card_bg"])
                )
                st.altair_chart(chart, use_container_width=True)

        if "Classification" in df.columns:
            st.markdown("---")
            st.markdown('<div class="section-title">Classification Breakdown</div>',
                        unsafe_allow_html=True)
            cls = df["Classification"].value_counts().reset_index()
            cls.columns = ["Classification", "Count"]
            cls["% of Total"] = (cls["Count"] / total * 100).round(1).astype(str) + "%"
            st.dataframe(
                cls, use_container_width=True, hide_index=True,
                column_config={
                    "Count": st.column_config.ProgressColumn(
                        "Count", min_value=0,
                        max_value=int(cls["Count"].max()) if not cls.empty else 1,
                        format="%d",
                    )
                },
            )

    except Exception as e:
        st.error(f"Insights error: {e}")


# ══════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════
wf_count = len(st.session_state.workflow)
st.markdown(f"""
<div class="trust-bar">
  <span>📁 <b>{Path(selected_path).name}</b></span>
  <span>🕐 Last updated: <b>{now_str}</b></span>
  <span>🗃 Sources: <b>VARA · CBUAE · DFSA · ADGM · SCA</b></span>
  {"<span>✓ <b>"+str(wf_count)+"</b> workflow actions logged this session</span>" if wf_count else ""}
  <span>ℹ️ Automated first-pass — not a legal determination</span>
</div>
""", unsafe_allow_html=True)
