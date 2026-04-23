"""
UAE Regulatory Screening – Internal Search UI
Refactored single-file Streamlit app.
Focus: stability, clean UX, simple state machine, production-readiness.
"""
from __future__ import annotations

import glob
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Optional fuzzy search (graceful fallback)
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
#   OPEN → INVESTIGATING → REVIEWED → CLOSED
# ══════════════════════════════════════════════════════════════════════════
WORKFLOW_STATES = ["OPEN", "INVESTIGATING", "REVIEWED", "CLOSED"]

WORKFLOW_STYLES = {
    "OPEN":          {"label": "Open",          "color": "#F87171", "bg": "rgba(239,68,68,0.10)", "border": "rgba(239,68,68,0.24)"},
    "INVESTIGATING": {"label": "Investigating", "color": "#FBBF24", "bg": "rgba(251,191,36,0.10)", "border": "rgba(251,191,36,0.24)"},
    "REVIEWED":      {"label": "Reviewed",      "color": "#93C5FD", "bg": "rgba(37,99,235,0.12)",  "border": "rgba(37,99,235,0.24)"},
    "CLOSED":        {"label": "Closed",        "color": "#34D399", "bg": "rgba(52,211,153,0.10)", "border": "rgba(52,211,153,0.24)"},
}


def default_workflow_state(risk_level: int, classification: str) -> str:
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
def _init_state():
    defaults = {
        "theme":                 "dark",
        "workflow":              {},     # {brand: {"state": str, "note": str|None, "ts": str}}
        "selected_brand":        None,
        "page":                  1,
        "risk_filter":           None,   # single int or None
        "quick_filter":          None,   # "high" | "new" | "riskup" | "licensed" | "va" | None
        "search_query":          "",
        "regulator_choice":      "All Regulators",
        "status_choice":         "All Statuses",
        "confidence_choice":     "All Confidence",
        "sort_choice":           "Priority",
        "actionable_only":       False,
        "selected_rows":         [],
        "confirm_clear_brand":   None,
        "clicked_risk_level":    None,   # for interactive chart filter
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()
dark = st.session_state.theme == "dark"


# ══════════════════════════════════════════════════════════════════════════
# THEME TOKENS
# ══════════════════════════════════════════════════════════════════════════
THEMES = {
    "dark": {
        "app_bg":      "#0b1020",
        "sidebar_bg":  "#0b1020",
        "card_bg":     "#111827",
        "raised_bg":   "#0f172a",
        "text":        "#ffffff",
        "text_dim":    "#cbd5e1",
        "text_muted":  "#94a3b8",
        "accent":      "#6366f1",
        "accent_dim":  "rgba(99,102,241,0.14)",
        "accent_bd":   "rgba(99,102,241,0.32)",
        "border":      "rgba(255,255,255,0.08)",
        "input_bg":    "#0f172a",
        "danger":      "#ef4444",
    },
    "light": {
        "app_bg":      "#f8fafc",
        "sidebar_bg":  "#ffffff",
        "card_bg":     "#ffffff",
        "raised_bg":   "#f1f5f9",
        "text":        "#0f172a",
        "text_dim":    "#334155",
        "text_muted":  "#64748b",
        "accent":      "#6366f1",
        "accent_dim":  "rgba(99,102,241,0.08)",
        "accent_bd":   "rgba(99,102,241,0.28)",
        "border":      "rgba(15,23,42,0.08)",
        "input_bg":    "#ffffff",
        "danger":      "#dc2626",
    },
}
c = THEMES[st.session_state.theme]


# ══════════════════════════════════════════════════════════════════════════
# RISK METADATA
# ══════════════════════════════════════════════════════════════════════════
RISK_META = {
    5: {"label": "Critical", "color": "#E11D48", "bg": "rgba(225,29,72,0.12)",  "border": "rgba(225,29,72,0.3)"},
    4: {"label": "High",     "color": "#F97316", "bg": "rgba(249,115,22,0.12)", "border": "rgba(249,115,22,0.3)"},
    3: {"label": "Medium",   "color": "#EAB308", "bg": "rgba(234,179,8,0.12)",  "border": "rgba(234,179,8,0.3)"},
    2: {"label": "Monitor",  "color": "#4A7FD4", "bg": "rgba(74,127,212,0.12)", "border": "rgba(74,127,212,0.3)"},
    1: {"label": "Low",      "color": "#4A7FD4", "bg": "rgba(74,127,212,0.08)", "border": "rgba(74,127,212,0.2)"},
    0: {"label": "Licensed", "color": "#10B981", "bg": "rgba(16,185,129,0.12)", "border": "rgba(16,185,129,0.3)"},
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
        clean = str(value).strip()
        if clean.lower() in {"nan", "none", "nat", "<na>"}:
            return fallback
        return clean
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
    clean = clean_text(scope, fallback="—")
    if clean in REGULATOR_LABELS:
        return REGULATOR_LABELS[clean]
    return clean.replace("_", " ").title()


def confidence_rank(value) -> int:
    return CONFIDENCE_RANK.get(clean_text(value).upper(), 0)


def confidence_label(value) -> str:
    return clean_text(value).title() or "Unknown"


# ── WORKFLOW STATE MACHINE ────────────────────────────────────────────────
def get_workflow(brand: str) -> dict:
    """Always returns a dict; never None."""
    return st.session_state.workflow.get(brand, {"state": None, "note": None, "ts": None})


def get_effective_state(row) -> str:
    """
    Scalar-safe: ALWAYS returns a single string.
    This is the canonical per-row state used in tables.
    """
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


def next_primary_action(state: str) -> tuple[str, str] | None:
    """What the primary CTA should do next, given current state."""
    if state == "OPEN":
        return ("Investigate", "INVESTIGATING")
    if state == "INVESTIGATING":
        return ("Mark Reviewed", "REVIEWED")
    if state == "REVIEWED":
        return ("Close", "CLOSED")
    return None


# ══════════════════════════════════════════════════════════════════════════
# BADGE / CHIP HTML
# ══════════════════════════════════════════════════════════════════════════
def risk_badge_html(level: int) -> str:
    m = RISK_META.get(level, RISK_META[2])
    dot = f'<span style="width:5px;height:5px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:5px;"></span>'
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;'
        f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;">{dot}{m["label"]} {level}</span>'
    )


def state_badge_html(state: str) -> str:
    m = WORKFLOW_STYLES.get(state, WORKFLOW_STYLES["OPEN"])
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;'
        f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;letter-spacing:0.04em;">{m["label"]}</span>'
    )


def alert_badge_html(status) -> str:
    s = clean_text(status).upper()
    if "NEW" in s:
        return ('<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
                'background:rgba(34,197,94,0.12);color:#22C55E;border:1px solid rgba(34,197,94,0.3);'
                'font-size:9px;font-weight:800;">NEW</span>')
    if "INCREASED" in s:
        return ('<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
                'background:rgba(249,115,22,0.12);color:#F97316;border:1px solid rgba(249,115,22,0.3);'
                'font-size:9px;font-weight:800;">↑ RISK UP</span>')
    return ""


def chip_html(text: str) -> str:
    clean = clean_text(text, fallback="—")
    return (
        f'<span style="display:inline-flex;align-items:center;padding:4px 10px;border-radius:8px;'
        f'background:{c["accent_dim"]};border:1px solid {c["accent_bd"]};color:{c["accent"]};'
        f'font-size:11px;font-weight:700;max-width:100%;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;" title="{clean}">{clean}</span>'
    )


def confidence_bar_html(value) -> str:
    label = confidence_label(value)
    rank = confidence_rank(value)
    widths = {3: 100, 2: 66, 1: 33, 0: 15}
    colors = {3: "#34D399", 2: "#FBBF24", 1: "#F87171", 0: "#64748B"}
    return (
        f'<div style="display:flex;align-items:center;gap:6px;" title="Confidence: {label}">'
        f'<div style="width:44px;height:5px;background:{c["border"]};border-radius:999px;overflow:hidden;">'
        f'<div style="width:{widths[rank]}%;height:100%;background:{colors[rank]};border-radius:999px;"></div>'
        f'</div>'
        f'<span style="font-size:10px;color:{c["text_muted"]};font-weight:700;">{label[:4]}</span>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: {c['app_bg']} !important;
    color: {c['text']} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {c['app_bg']} !important; }}
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1280px !important;
}}

[data-testid="stSidebar"] {{
    background: {c['sidebar_bg']} !important;
    border-right: 1px solid {c['border']} !important;
}}
[data-testid="stSidebar"] * {{ color: {c['text_dim']} !important; }}
[data-testid="stSidebar"] h3 {{ color: {c['text']} !important; }}

div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-baseweb="input"] input, .stTextInput input,
[data-testid="stSelectbox"] > div > div > div {{
    background: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
    min-height: 42px !important;
    box-shadow: none !important;
}}
ul[data-baseweb="menu"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
}}
[data-baseweb="option"] {{ color: {c['text']} !important; }}
[data-baseweb="option"]:hover {{ background: {c['raised_bg']} !important; }}
[data-baseweb="tag"] {{ background: {c['accent_dim']} !important; color: {c['text']} !important; }}

[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {c['card_bg']} !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid {c['border']} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    color: {c['text_dim']} !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1rem !important;
    border-radius: 8px !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
    background: {c['raised_bg']} !important;
    color: {c['text']} !important;
    font-weight: 700 !important;
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none !important; }}

div.stButton > button, .stDownloadButton button {{
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
    background: {c['accent']} !important;
    border-color: {c['accent']} !important;
    color: #ffffff !important;
}}
div.stButton > button:hover:not(:disabled) {{
    background: {c['raised_bg']} !important;
    border-color: {c['accent_bd']} !important;
    transform: translateY(-1px);
}}
div.stButton > button[kind="primary"]:hover:not(:disabled) {{
    background: #585cf0 !important;
    border-color: #585cf0 !important;
}}
div.stButton > button:disabled {{ opacity: 0.35 !important; cursor: not-allowed !important; }}

[data-testid="stDataFrame"] {{
    border-radius: 10px !important;
    border: 1px solid {c['border']} !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] table {{ background: {c['card_bg']} !important; }}
[data-testid="stDataFrame"] th {{
    background: {c['raised_bg']} !important;
    color: {c['text_muted']} !important;
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}}
[data-testid="stDataFrame"] td {{
    color: {c['text']} !important;
    font-size: 0.84rem !important;
    border-bottom: 1px solid {c['border']} !important;
}}
[data-testid="stDataFrame"] tr:hover td {{ background: {c['raised_bg']} !important; }}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {c['accent_bd']}; border-radius: 99px; }}

/* === Components === */

.topbar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 18px; margin-bottom: 16px;
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
.topbar-logo {{ display:flex; align-items:center; gap:10px; }}
.topbar-icon {{
    width:32px; height:32px; border-radius:9px;
    background: linear-gradient(135deg, {c['accent']}, #4f46e5);
    display:flex; align-items:center; justify-content:center;
    font-size:16px; flex-shrink:0;
}}
.topbar-title {{ color: {c['text']}; font-size:14px; font-weight:800; line-height:1.2; }}
.topbar-sub {{ color: {c['text_muted']}; font-size:9px; font-weight:600; letter-spacing:0.08em; }}
.topbar-meta {{ text-align:right; }}
.topbar-meta .run {{ color: {c['text_dim']}; font-size:10px; }}
.topbar-meta .run b {{ color: {c['text']}; }}
.topbar-meta .src {{ color: {c['text_muted']}; font-size:9px; }}
.live-badge {{
    display:inline-flex; align-items:center; gap:5px; padding:4px 10px;
    border-radius:999px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.28);
}}
.live-dot {{ width:5px; height:5px; border-radius:50%; background:#10B981; display:inline-block; }}
.live-txt {{ color:#10B981; font-size:10px; font-weight:800; letter-spacing:0.06em; }}

.kpi-card {{
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    padding: 16px 18px;
    min-height: 100px;
}}
.kpi-label {{
    color: {c['text_muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 10px;
}}
.kpi-value {{
    color: {c['text']};
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 8px;
}}
.kpi-note {{ color: {c['text_dim']}; font-size: 11px; line-height: 1.45; }}

.section-title {{
    color: {c['text']};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 0 0 0.6rem 0;
}}

.entity-card {{
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
}}
.entity-card h4 {{ margin: 0 0 4px 0; color: {c['text']}; font-size: 0.95rem; font-weight: 800; }}
.entity-card .meta {{ color: {c['text_muted']}; font-size: 0.78rem; margin-bottom: 0.4rem; }}
.entity-card .rationale {{ color: {c['text_dim']}; font-size: 0.82rem; line-height: 1.5; }}
.entity-card .rationale.empty {{ color: {c['text_muted']}; font-style: italic; }}

.empty-state {{ text-align:center; padding:40px 20px; }}
.empty-state .icon {{ font-size:32px; margin-bottom:10px; }}
.empty-state .title {{ color: {c['text']}; font-size: 14px; font-weight: 700; margin-bottom: 6px; }}
.empty-state .desc {{ color: {c['text_muted']}; font-size: 12px; }}

.error-state {{
    background: rgba(225,29,72,0.08);
    border: 1px solid rgba(225,29,72,0.25);
    border-radius: 10px;
    padding: 14px;
}}

.trust-bar {{
    display:flex; gap:16px; flex-wrap:wrap; align-items:center;
    padding:10px 0; border-top:1px solid {c['border']};
    color: {c['text_muted']}; font-size:10px;
}}
.trust-bar b {{ color: {c['text_dim']}; }}

.filter-group {{
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
}}
.filter-group .heading {{
    color: {c['text_muted']};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
}}

.row-card {{
    background: {c['card_bg']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 6px;
    transition: border-color 0.15s, background 0.15s;
}}
.row-card:hover {{ border-color: {c['accent_bd']}; background: {c['raised_bg']}; }}

hr {{ border-color: {c['border']} !important; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# NOISE FILTERING
# ══════════════════════════════════════════════════════════════════════════
NOISE_BRANDS = {
    "rulebook", "the complete rulebook", "licensing", "centralbank",
    "globenewswire", "globe newswire", "cbuae rulebook",
    "insights for businesses", "insights", "businesses",
    "money transfers", "gccbusinesswatch", "financialit",
    "visamiddleeast", "khaleejtimes", "khaleej times", "gulfnews",
    "gulf news", "thenational", "the national", "arabianbusiness",
    "arabian business", "zawya", "wam", "reuters", "bloomberg",
    "ft.com", "cnbc", "forbes", "crunchbase", "techcrunch",
    "wikipedia", "medium", "page", "home", "about", "contact",
    "terms", "privacy", "fintech news", "press release",
    "media release", "news release", "blog", "white paper",
    "whitepaper", "report", "research", "survey", "study",
    "conference", "event", "webinar", "podcast", "linkedin",
    "twitter", "facebook", "instagram", "youtube", "warning",
    "vasps", "vasps licensing process", "rules", "guide", "overview",
    "trends", "plan", "news", "article", "introduction", "summary",
    "conclusion", "documentation", "docs", "help", "support",
    "faq", "faqs", "sitemap", "copyright",
}

NOISE_PATTERNS = re.compile(
    r"^(\s*[&'\"\-–—]|\s*\d+[\.\)\s]|top \d+|best \d+|leading \d+|"
    r"guide to|how to|what is|list of|complete list|overview|"
    r"introduction|insights for|transforming|mobile development|"
    r"press release|whitepaper|business plan|licensing process|"
    r"warning|\d{4}\s|"
    r".*\.(com|ae|net|org|io|co)$|"
    r".*(news|times|watch|magazine|journal|newsletter|review|"
    r"press|media|blog|gazette|tribune|post|herald|daily|weekly)$)",
    re.I,
)

GENERIC_WORDS = {
    "bank", "banks", "banking", "payment", "payments", "finance",
    "financial", "wallet", "wallets", "exchange", "exchanges",
    "crypto", "cryptocurrency", "trading", "investment", "investments",
    "fintech", "regulation", "regulations", "regulatory", "compliance",
    "license", "licenses", "licensing", "money", "transfer", "transfers",
    "remittance", "remittances", "loan", "loans", "lending", "credit",
    "debit", "card", "cards", "digital", "mobile", "online", "virtual",
    "electronic", "service", "services", "solution", "solutions",
    "platform", "technology", "technologies", "app", "apps", "application",
    "company", "companies", "corporation", "corp", "limited", "ltd",
    "uae", "dubai", "abu", "dhabi", "emirates", "gulf", "middle", "east",
    "gcc", "regional", "international", "global", "local",
}


def is_noise_brand(brand) -> bool:
    try:
        if not brand or not isinstance(brand, str):
            return True
        b = brand.strip().lower()
        if not b or len(b) < 3:
            return True
        if b in NOISE_BRANDS:
            return True
        if NOISE_PATTERNS.match(b):
            return True
        if re.match(r"^[\s&'\"\-–—_\.,;:]", brand):
            return True
        if b[0].isdigit():
            return True
        if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", b):
            return True
        words = b.split()
        if all(w in GENERIC_WORDS for w in words):
            return True
        if len(words) > 5:
            return True
        letters = sum(ch.isalpha() for ch in brand)
        if letters < len(brand) * 0.5:
            return True
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
                files.append({
                    "path": path,
                    "name": p.name,
                    "timestamp": ts,
                    "size_kb": p.stat().st_size // 1024,
                })
    except Exception:
        pass
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)


@st.cache_data(show_spinner=False)
def load_data(path: str) -> tuple[pd.DataFrame, str | None]:
    try:
        try:
            df = pd.read_excel(path, sheet_name="📋 All Results")
        except Exception:
            df = pd.read_excel(path, sheet_name=0)
    except Exception as e:
        return pd.DataFrame(), str(e)

    text_cols = [
        "Brand", "Classification", "Group", "Service Type", "Regulator Scope",
        "Alert Status", "Rationale", "Action Required", "Top Source URL",
        "Matched Entity (Register)", "Register Category", "Key Snippet",
        "Source", "Discovery Query", "Confidence",
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
def fuzzy_suggestions(query: str, choices: list[str], limit: int = 10) -> list[str]:
    if not query or not choices:
        return []
    query = query.strip()
    if not query:
        return []
    try:
        if HAS_RAPIDFUZZ:
            results = rf_process.extract(
                query, choices, scorer=fuzz.WRatio, limit=limit
            )
            return [item for item, score, _ in results if score >= 55]
        else:
            # Simple substring fallback
            q = query.lower()
            return [c for c in choices if q in c.lower()][:limit]
    except Exception:
        return []


def build_search_suggestions(query: str, brands, regulators, services) -> list[str]:
    if not query:
        return []
    out: list[str] = []
    for b in fuzzy_suggestions(query, list(brands), limit=8):
        out.append(f"Entity: {b}")
    for r in fuzzy_suggestions(query, [normalize_regulator(x) for x in regulators], limit=4):
        out.append(f"Regulator: {r}")
    for s in fuzzy_suggestions(query, list(services), limit=4):
        out.append(f"Service: {s}")
    return out[:12]


def fuzzy_filter_df(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Filter a dataframe by fuzzy-matching a free-text query across brand/regulator/service."""
    if not query or df.empty:
        return df
    if query.startswith("Entity: "):
        return df[df["Brand"] == query[len("Entity: "):]]
    if query.startswith("Regulator: "):
        label = query[len("Regulator: "):]
        if "Regulator Scope" in df.columns:
            mask = df["Regulator Scope"].astype(str).map(normalize_regulator) == label
            return df[mask]
        return df
    if query.startswith("Service: "):
        return df[df["Service Type"] == query[len("Service: "):]] if "Service Type" in df.columns else df
    # Free-form fuzzy match
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

        # Header
        st.markdown(f"""
        <div style="background:{c['card_bg']};border:1px solid {c['border']};border-radius:12px;
                    padding:16px 18px;margin-bottom:14px;">
          <div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
            {risk_badge_html(level)}
            {state_badge_html(state)}
            {alert_badge_html(row.get("Alert Status", ""))}
          </div>
          <h3 style="color:{c['text']};font-size:20px;font-weight:800;margin:4px 0 4px 0;">{brand}</h3>
          <div style="color:{c['text_muted']};font-size:12px;">{clean_text(row.get('Classification',''), '—')}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Workflow Actions ──
        st.markdown(f'<div class="section-title">Workflow</div>', unsafe_allow_html=True)

        nxt = next_primary_action(state)
        cols = st.columns(4)
        # Primary CTA (state machine)
        with cols[0]:
            if nxt is not None:
                label, target = nxt
                if st.button(label, key=f"wf_primary_{brand}", type="primary", use_container_width=True):
                    set_workflow_state(brand, target)
                    st.rerun()
            else:
                st.button("Done", key=f"wf_done_{brand}", disabled=True, use_container_width=True)
        # Escalate → INVESTIGATING (higher urgency)
        with cols[1]:
            if st.button("↑ Escalate", key=f"wf_esc_{brand}", use_container_width=True,
                         disabled=state == "INVESTIGATING"):
                set_workflow_state(brand, "INVESTIGATING")
                st.rerun()
        # Reviewed
        with cols[2]:
            if st.button("✓ Mark Reviewed", key=f"wf_rev_{brand}", use_container_width=True,
                         disabled=state == "REVIEWED"):
                set_workflow_state(brand, "REVIEWED")
                st.rerun()
        # Clear (danger; confirm)
        with cols[3]:
            if st.session_state.confirm_clear_brand == brand:
                if st.button("⚠ Confirm Clear", key=f"wf_clr_confirm_{brand}", use_container_width=True):
                    clear_workflow(brand)
                    st.session_state.confirm_clear_brand = None
                    st.rerun()
            else:
                if st.button("✕ Clear", key=f"wf_clr_{brand}", use_container_width=True,
                             disabled=wf.get("state") is None):
                    st.session_state.confirm_clear_brand = brand
                    st.rerun()

        # Annotation
        with st.expander("✎ Add / update note", expanded=False):
            current_note = wf.get("note") or ""
            note = st.text_area(
                "Note",
                value=current_note,
                placeholder="Add context, link, or reason…",
                key=f"note_input_{brand}",
                label_visibility="collapsed",
            )
            note_cols = st.columns([1, 1, 4])
            with note_cols[0]:
                if st.button("Save note", key=f"save_note_{brand}", use_container_width=True):
                    effective_state = wf.get("state") or default_workflow_state(level, row.get("Classification", ""))
                    set_workflow_state(brand, effective_state, note=note.strip() or None)
                    st.rerun()
            with note_cols[1]:
                if st.button("Clear note", key=f"clr_note_{brand}", use_container_width=True,
                             disabled=not current_note):
                    effective_state = wf.get("state") or default_workflow_state(level, row.get("Classification", ""))
                    set_workflow_state(brand, effective_state, note=None)
                    st.rerun()

        if wf.get("state"):
            note_txt = f' · Note: "{wf["note"]}"' if wf.get("note") else ""
            st.markdown(f"""
            <div style="background:{c['accent_dim']};border:1px solid {c['accent_bd']};
                        border-radius:8px;padding:8px 12px;margin-top:8px;color:{c['text_dim']};font-size:11px;">
              Current state: <b style="color:{c['text']};">{WORKFLOW_STYLES[wf['state']]['label']}</b>
              · Updated at {wf.get('ts','—')}{note_txt}
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── Metadata ──
        mc1, mc2 = st.columns(2)
        with mc1:
            for label, key in [
                ("Service Type",    "Service Type"),
                ("Regulator Scope", "Regulator Scope"),
                ("Classification",  "Classification"),
            ]:
                raw = clean_text(row.get(key, ""), fallback="—")
                val = normalize_regulator(raw) if key == "Regulator Scope" else raw
                st.markdown(f"""
                <div style="margin-bottom:12px;">
                  <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                              letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">{label}</div>
                  <div style="color:{c['text']};font-size:12px;">{val}</div>
                </div>
                """, unsafe_allow_html=True)

        with mc2:
            conf = clean_text(row.get("Confidence", ""))
            matched = clean_text(row.get("Matched Entity (Register)", ""), fallback="—")
            url = clean_text(row.get("Top Source URL", ""))
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Confidence</div>
              {confidence_bar_html(conf)}
            </div>
            <div style="margin-bottom:12px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">Matched Entity</div>
              <div style="color:{c['text']};font-size:12px;">{matched}</div>
            </div>
            """, unsafe_allow_html=True)
            if url.startswith("http"):
                st.link_button("↗ View Source", url, use_container_width=True)

        st.divider()

        # ── Rationale ──
        rat = clean_text(row.get("Rationale", ""),
                         fallback="No description available from this run — review source manually.")
        st.markdown(f"""
        <div style="margin-bottom:14px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                      letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Rationale</div>
          <div style="color:{c['text_dim']};font-size:12px;line-height:1.65;">{rat}</div>
        </div>
        """, unsafe_allow_html=True)

        act = clean_text(row.get("Action Required", ""))
        if act:
            st.markdown(f"""
            <div style="background:{c['accent_dim']};border:1px solid {c['accent_bd']};
                        border-radius:8px;padding:10px 14px;">
              <div style="color:{c['accent']};font-size:9px;font-weight:800;letter-spacing:0.1em;
                          text-transform:uppercase;margin-bottom:4px;">Action Required</div>
              <div style="color:{c['text']};font-size:12px;line-height:1.6;">{act}</div>
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Could not render details: {e}")


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 14px 0;
                border-bottom:1px solid {c['border']};margin-bottom:14px;">
        <div class="topbar-icon">🛡️</div>
        <div>
            <div class="topbar-title">UAE Screening</div>
            <div class="topbar-sub">RISK MONITORING</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    theme_label = "☀ Light Mode" if dark else "☾ Dark Mode"
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
                              label_visibility="collapsed", key="sb_run_select")
        selected_path = options[choice]
    else:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">📭</div>
          <div class="title">No screening files</div>
          <div class="desc">Upload a UAE_Screening_*.xlsx file below</div>
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
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
st.markdown(f"""
<div class="topbar">
  <div class="topbar-logo">
    <div class="topbar-icon">🛡️</div>
    <div>
      <div class="topbar-title">UAE Regulatory Screening</div>
      <div class="topbar-sub">INTERNAL RISK MONITORING PLATFORM</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="topbar-meta">
      <div class="run">Run: <b>{now_str}</b></div>
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
                border:1px solid {c['accent_bd']};border-radius:16px;padding:24px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="width:42px;height:42px;border-radius:12px;background:{c['accent_dim']};
                    border:1px solid {c['accent_bd']};display:flex;align-items:center;
                    justify-content:center;font-size:18px;">📂</div>
        <div>
          <div style="color:{c['text']};font-size:18px;font-weight:800;">Upload a screening run</div>
          <div style="color:{c['text_muted']};font-size:12px;margin-top:4px;">
            This app is built for <code>UAE_Screening_*.xlsx</code> files.
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_main = st.file_uploader(
        "Upload a UAE_Screening_*.xlsx file",
        type=["xlsx"],
        key="main_upload",
    )
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


# Pre-compute the state column ONCE (scalar-safe, deterministic)
df = df.copy()
df["__state"] = df.apply(get_effective_state, axis=1)
df["__conf_rank"] = df["Confidence"].map(confidence_rank) if "Confidence" in df.columns else 0
df["Risk Level"] = df["Risk Level"].fillna(2).astype(int) if "Risk Level" in df.columns else 2


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
    ("Entities Screened", f"{total:,}", "Total entities after noise filtering"),
    ("Critical / High",   f"{critical + high:,}", f"{(critical + high) / total * 100:.0f}% of total" if total else "0%"),
    ("Needs Review",      f"{needs_rev:,}", "Risk levels 2–3"),
    ("Licensed / Clear",  f"{licensed:,}", "Risk level 0, no action required"),
    ("New Entities",      f"{new_ents:,}", f"{risk_up} risk increased" if risk_up else "No risk increases this run"),
]

k_cols = st.columns(5)
for col, (label, value, note) in zip(k_cols, kpi_cards):
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")


# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_home, tab_search, tab_insights = st.tabs(["🏠 Overview", "🔍 Search & Filter", "📊 Insights"])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
with tab_home:
    left_col, right_col = st.columns([1.7, 1])

    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.caption("High & Critical entities — click an entity to open detail.")

        top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)

        if top_risk.empty:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.24);
                        border-radius:10px;padding:20px;text-align:center;">
              <div style="color:#10B981;font-size:13px;font-weight:700;">
                ✓ No high-risk entities this run
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for _, row in top_risk.iterrows():
                try:
                    brand = row_brand(row)
                    level = safe_int(row.get("Risk Level", 2))
                    state = get_effective_state(row)
                    svc   = clean_text(row.get("Service Type", ""), "—")
                    reg   = normalize_regulator(row.get("Regulator Scope", ""))
                    rat_raw = clean_text(row.get("Rationale", ""))
                    rat = (rat_raw[:240] + "…") if len(rat_raw) > 240 else (rat_raw or "No description available.")

                    st.markdown(f"""
                    <div class="entity-card">
                      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
                        <div style="flex:1;min-width:0;">
                          <h4>{brand}</h4>
                          <div class="meta">
                            <span style="margin-right:6px;">{chip_html(reg)}</span>
                            <span>{chip_html(svc)}</span>
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

                    ctrl_cols = st.columns([1.4, 1.1, 4])
                    with ctrl_cols[0]:
                        if st.button("View Detail", key=f"ov_det_{row.name}", type="primary", use_container_width=True):
                            show_entity_detail(row)
                    with ctrl_cols[1]:
                        url = clean_text(row.get("Top Source URL", ""))
                        if url.startswith("http"):
                            st.link_button("Source", url, use_container_width=True)
                except Exception as e:
                    st.caption(f"Could not render row: {e}")

    with right_col:
        if new_ents > 0 or risk_up > 0:
            st.markdown(f"""
            <div style="background:rgba(249,115,22,0.07);border:1px solid rgba(249,115,22,0.22);
                        border-radius:10px;padding:12px 14px;margin-bottom:14px;">
              <div style="color:#F97316;font-size:9px;font-weight:800;letter-spacing:0.09em;
                          margin-bottom:6px;">ALERTS THIS RUN</div>
              {"<div style='color:"+c["text_dim"]+";font-size:11px;margin-bottom:3px;'>"
                "<span style='color:#22C55E;font-weight:700;'>"+str(new_ents)+"</span> new entities added</div>"
                if new_ents else ""}
              {"<div style='color:"+c["text_dim"]+";font-size:11px;'>"
                "<span style='color:#F97316;font-weight:700;'>"+str(risk_up)+"</span> risk level increases</div>"
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
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("label:N",
                            sort=alt.EncodingSortField("level", order="descending"),
                            title=None,
                            axis=alt.Axis(labelColor=c["text_dim"], domainColor=c["border"], labelAngle=0)),
                    y=alt.Y("count:Q",
                            axis=alt.Axis(labelColor=c["text_dim"], gridColor=c["border"],
                                          domainColor="transparent", title="Entities")),
                    color=alt.Color("label:N",
                                    scale=alt.Scale(domain=list(colors_map.keys()),
                                                    range=list(colors_map.values())),
                                    legend=None),
                    opacity=alt.condition(selection, alt.value(0.95), alt.value(0.4)),
                    tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                )
                .add_params(selection)
                .properties(height=220)
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"])
            )
            event = st.altair_chart(chart, use_container_width=True, on_select="rerun", key="ov_risk_chart")

            # Capture clicked level → quick-jump to Search tab with filter
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


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — SEARCH & FILTER
# ══════════════════════════════════════════════════════════════════════════
with tab_search:
    all_brands     = sorted(df["Brand"].dropna().astype(str).tolist()) if "Brand" in df.columns else []
    all_regulators = sorted(df["Regulator Scope"].dropna().astype(str).unique().tolist()) if "Regulator Scope" in df.columns else []
    all_services   = sorted(df["Service Type"].dropna().astype(str).unique().tolist()) if "Service Type" in df.columns else []

    # ── Search row ──
    st.markdown('<div class="section-title">Search</div>', unsafe_allow_html=True)
    if HAS_SEARCHBOX:
        sbox_val = st_searchbox(
            lambda q: build_search_suggestions(q, all_brands, all_regulators, all_services),
            placeholder="Fuzzy search entity, regulator, or service…",
            key="search_autocomplete",
            clear_on_submit=False,
        )
        search_query = (sbox_val or "").strip()
    else:
        search_query = st.text_input(
            "Search",
            value=st.session_state.get("search_query", ""),
            placeholder="Search entity, regulator, or service…",
            key="search_text",
            label_visibility="collapsed",
        ).strip()
        # Surface fuzzy suggestions inline
        if search_query and not HAS_SEARCHBOX:
            sugg = build_search_suggestions(search_query, all_brands, all_regulators, all_services)
            if sugg:
                st.caption("Did you mean: " + " · ".join(sugg[:5]))
    st.session_state.search_query = search_query

    # ── Filter groups ──
    st.markdown('<div class="section-title" style="margin-top:14px;">Filters</div>', unsafe_allow_html=True)

    # Risk Level chip row
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:10px;font-weight:700;'
                f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Risk Level</div>',
                unsafe_allow_html=True)
    risk_cols = st.columns(7)
    risk_defs = [("All", None), ("Critical", 5), ("High", 4), ("Medium", 3),
                 ("Monitor", 2), ("Low", 1), ("Licensed", 0)]
    for i, (label, level) in enumerate(risk_defs):
        active = st.session_state.risk_filter == level
        btn_label = f"● {label}" if active else label
        if risk_cols[i].button(btn_label, key=f"risk_btn_{label}",
                               use_container_width=True,
                               type="primary" if active else "secondary"):
            st.session_state.risk_filter = level
            st.session_state.page = 1
            st.rerun()

    # Regulator / Status / Quick filters row
    f_cols = st.columns([1.3, 1.3, 1.3, 1.1, 1.2])
    with f_cols[0]:
        reg_counts = df["Regulator Scope"].fillna("—").astype(str).value_counts() if "Regulator Scope" in df.columns else pd.Series(dtype=int)
        reg_map = {"All Regulators": None}
        for r, cnt in reg_counts.items():
            reg_map[f"{normalize_regulator(r)} ({cnt})"] = r
        reg_choice = st.selectbox(
            "Regulator",
            list(reg_map.keys()),
            index=list(reg_map.keys()).index(st.session_state.regulator_choice)
                  if st.session_state.regulator_choice in reg_map else 0,
            key="regulator_choice",
            help="Filter by regulatory body",
        )
    with f_cols[1]:
        st.selectbox(
            "Status (Workflow)",
            ["All Statuses"] + [WORKFLOW_STYLES[s]["label"] for s in WORKFLOW_STATES],
            index=(["All Statuses"] + [WORKFLOW_STYLES[s]["label"] for s in WORKFLOW_STATES]).index(
                st.session_state.status_choice
            ) if st.session_state.status_choice in (
                ["All Statuses"] + [WORKFLOW_STYLES[s]["label"] for s in WORKFLOW_STATES]
            ) else 0,
            key="status_choice",
            help="Workflow state: Open → Investigating → Reviewed → Closed",
        )
    with f_cols[2]:
        st.selectbox(
            "Confidence",
            ["All Confidence", "High Only", "Medium Only", "Low Only"],
            index=["All Confidence", "High Only", "Medium Only", "Low Only"].index(
                st.session_state.confidence_choice
            ) if st.session_state.confidence_choice in
               ["All Confidence", "High Only", "Medium Only", "Low Only"] else 0,
            key="confidence_choice",
            help="Model's confidence in the match",
        )
    with f_cols[3]:
        st.selectbox(
            "Sort",
            ["Priority", "Risk", "Status", "Confidence", "Regulator", "Brand"],
            index=["Priority", "Risk", "Status", "Confidence", "Regulator", "Brand"].index(
                st.session_state.sort_choice
            ) if st.session_state.sort_choice in
               ["Priority", "Risk", "Status", "Confidence", "Regulator", "Brand"] else 0,
            key="sort_choice",
        )
    with f_cols[4]:
        st.toggle(
            "Actionable only",
            key="actionable_only",
            help="Only rows that currently require action (Open or Investigating).",
        )

    # Quick filter chips
    quick_defs = [
        ("Critical/High", "high"),
        ("New Entities", "new"),
        ("Risk Up", "riskup"),
        ("Licensed", "licensed"),
        ("VASP/Crypto", "va"),
    ]
    qcols = st.columns(len(quick_defs) + 1)
    for i, (label, key) in enumerate(quick_defs):
        active = st.session_state.quick_filter == key
        btn_label = f"● {label}" if active else label
        if qcols[i].button(btn_label, key=f"quick_{key}",
                           use_container_width=True,
                           type="primary" if active else "secondary"):
            st.session_state.quick_filter = None if active else key
            st.session_state.page = 1
            st.rerun()
    with qcols[-1]:
        if st.button("Clear all", key="clear_all", use_container_width=True):
            st.session_state.risk_filter = None
            st.session_state.quick_filter = None
            st.session_state.search_query = ""
            st.session_state.regulator_choice = "All Regulators"
            st.session_state.status_choice = "All Statuses"
            st.session_state.confidence_choice = "All Confidence"
            st.session_state.sort_choice = "Priority"
            st.session_state.actionable_only = False
            st.session_state.page = 1
            st.session_state.selected_rows = []
            st.session_state.clicked_risk_level = None
            for k in list(st.session_state.keys()):
                if k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

    # ── Apply filters ──
    filtered = df.copy()

    try:
        # Search
        if st.session_state.search_query:
            filtered = fuzzy_filter_df(filtered, st.session_state.search_query)

        # Regulator
        sel_reg = reg_map.get(st.session_state.regulator_choice)
        if sel_reg:
            filtered = filtered[filtered["Regulator Scope"] == sel_reg]

        # Risk level
        if st.session_state.risk_filter is not None:
            filtered = filtered[filtered["Risk Level"] == st.session_state.risk_filter]

        # Status (workflow state) — map back label → state key
        label_to_state = {WORKFLOW_STYLES[s]["label"]: s for s in WORKFLOW_STATES}
        if st.session_state.status_choice != "All Statuses":
            want = label_to_state.get(st.session_state.status_choice)
            if want:
                filtered = filtered[filtered["__state"] == want]

        # Confidence
        conf_map = {"High Only": 3, "Medium Only": 2, "Low Only": 1}
        if st.session_state.confidence_choice in conf_map:
            filtered = filtered[filtered["__conf_rank"] == conf_map[st.session_state.confidence_choice]]

        # Actionable only
        if st.session_state.actionable_only:
            filtered = filtered[filtered["__state"].isin(["OPEN", "INVESTIGATING"])]

        # Quick chip
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

        # Sort
        state_priority = {"OPEN": 3, "INVESTIGATING": 2, "REVIEWED": 1, "CLOSED": 0}
        filtered["__state_pri"] = filtered["__state"].map(state_priority).fillna(0).astype(int)

        sort_by = st.session_state.sort_choice
        if sort_by == "Priority":
            filtered = filtered.sort_values(
                ["Risk Level", "__state_pri", "__conf_rank", "Brand"],
                ascending=[False, False, False, True])
        elif sort_by == "Risk":
            filtered = filtered.sort_values(["Risk Level", "Brand"], ascending=[False, True])
        elif sort_by == "Status":
            filtered = filtered.sort_values(["__state_pri", "Risk Level", "Brand"], ascending=[False, False, True])
        elif sort_by == "Confidence":
            filtered = filtered.sort_values(["__conf_rank", "Risk Level", "Brand"], ascending=[False, False, True])
        elif sort_by == "Regulator":
            filtered = filtered.sort_values(["Regulator Scope", "Risk Level", "Brand"], ascending=[True, False, True])
        else:
            filtered = filtered.sort_values(["Brand", "Risk Level"], ascending=[True, False])

    except Exception as e:
        st.error(f"Filter error: {e}")
        filtered = df.copy()

    # ── Count line ──
    st.markdown(f"""
    <div style="color:{c['text_muted']};font-size:11px;margin:6px 0 12px 0;">
      <strong style="color:{c['text_dim']};">{len(filtered):,} of {total:,}</strong> entities
    </div>
    """, unsafe_allow_html=True)

    selected_brands = set(st.session_state.selected_rows)

    if filtered.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🔍</div>
          <div class="title">No entities match these filters</div>
          <div class="desc">Clear one or two filters and the review table will repopulate.</div>
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
        sort_arrow = " ↓" if st.session_state.sort_choice in {"Priority", "Risk"} else ""
        status_arrow = " ↓" if st.session_state.sort_choice == "Status" else ""
        conf_arrow = " ↓" if st.session_state.sort_choice == "Confidence" else ""
        reg_arrow = " ↑" if st.session_state.sort_choice == "Regulator" else ""
        brand_arrow = " ↑" if st.session_state.sort_choice == "Brand" else ""
        headers = ["", f"Entity{brand_arrow}", f"Risk{sort_arrow}",
                   f"Regulator{reg_arrow}", "Service", f"Conf.{conf_arrow}",
                   f"Status{status_arrow}", "Actions"]
        for col, label in zip(h_cols, headers):
            col.markdown(
                f'<div style="color:{c["text_muted"]};font-size:10px;font-weight:800;'
                f'letter-spacing:0.08em;text-transform:uppercase;padding:10px 6px;'
                f'border-bottom:1px solid {c["border"]};">{label}</div>',
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

                brand_key = brand.lower().replace(" ", "_")[:40]
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
                    st.markdown(
                        f'<div style="padding:4px 0;">'
                        f'<div style="color:{c["text"]};font-size:13px;font-weight:800;">{brand}</div>'
                        f'<div style="color:{c["text_muted"]};font-size:10px;">{clean_text(row.get("Classification",""),"—")[:50]}</div>'
                        f'</div>',
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

                st.markdown(f'<div style="height:1px;background:{c["border"]};margin:4px 0;"></div>',
                            unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Row render error: {e}")

        st.session_state.selected_rows = sorted(selected_brands)

        # Footer: bulk actions + pagination
        fcols = st.columns([2.3, 1.5, 1.5, 2.5, 0.9, 1.1])
        if fcols[0].button(
            f"Bulk Investigate ({len(selected_brands)})",
            key="bulk_inv",
            use_container_width=True,
            disabled=not selected_brands,
            type="primary" if selected_brands else "secondary",
        ):
            for b in selected_brands:
                set_workflow_state(b, "INVESTIGATING")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        if fcols[1].button(
            "Mark Reviewed",
            key="bulk_rev",
            use_container_width=True,
            disabled=not selected_brands,
        ):
            for b in selected_brands:
                set_workflow_state(b, "REVIEWED")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        if fcols[2].button(
            "Close",
            key="bulk_close",
            use_container_width=True,
            disabled=not selected_brands,
        ):
            for b in selected_brands:
                set_workflow_state(b, "CLOSED")
            st.session_state.selected_rows = []
            for k in list(st.session_state.keys()):
                if k.startswith("row_sel_"):
                    st.session_state[k] = False
            st.rerun()

        fcols[3].markdown(
            f"<div style='text-align:right;padding-top:0.45rem;color:{c['text_muted']};font-size:11px;'>"
            f"Page <strong style='color:{c['text']}'>{st.session_state.page}</strong> of {total_pages}</div>",
            unsafe_allow_html=True,
        )
        if fcols[4].button("◀", key="p_prev", use_container_width=True,
                           disabled=st.session_state.page <= 1):
            st.session_state.page -= 1
            st.rerun()
        if fcols[5].button("Next →", key="p_next", use_container_width=True,
                           disabled=st.session_state.page >= total_pages):
            st.session_state.page += 1
            st.rerun()

        # Export
        st.markdown("")
        try:
            export_df = filtered.drop(
                columns=[col for col in filtered.columns if col.startswith("__")],
                errors="ignore",
            )
            d1, d2 = st.columns(2)
            csv = export_df.to_csv(index=False).encode("utf-8-sig")
            d1.download_button(
                "↓ Download CSV",
                data=csv,
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                export_df.to_excel(w, index=False, sheet_name="Filtered")
            d2.download_button(
                "↓ Download Excel",
                data=buf.getvalue(),
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

        def _axis_x():
            return alt.Axis(labelColor=c["text_dim"], tickColor="transparent",
                            domainColor=c["border"], labelFont="DM Sans,sans-serif")

        def _axis_y(title="Count"):
            return alt.Axis(labelColor=c["text_dim"], gridColor=c["border"],
                            domainColor="transparent", tickColor="transparent",
                            labelFont="DM Sans,sans-serif", title=title)

        def bar_chart(series, title, subtitle, color="#6366f1", rotate=-30, height=240):
            if series is None or series.empty:
                return False
            df_c = series.reset_index()
            df_c.columns = ["label", "value"]
            chart = (
                alt.Chart(df_c)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.92)
                .encode(
                    x=alt.X("label:N", sort="-y", axis=_axis_x().copy(labelAngle=rotate), title=None),
                    y=alt.Y("value:Q", axis=_axis_y("Count")),
                    color=alt.value(color),
                    tooltip=["label:N", alt.Tooltip("value:Q", title="Count")],
                )
                .properties(height=height,
                            title=alt.TitleParams(title, subtitle=[subtitle],
                                                  color=c["text"], fontSize=12,
                                                  subtitleColor=c["text_dim"], subtitleFontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"])
            )
            st.altair_chart(chart, use_container_width=True)
            return True

        # Summary row
        top_risk_label = (
            df["Risk Level"].map(lambda x: RISK_META.get(int(x), {}).get("label", "")).value_counts().idxmax()
            if "Risk Level" in df.columns and not df.empty else "—"
        )
        top_reg = normalize_regulator(df["Regulator Scope"].value_counts().idxmax()) \
            if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty else "—"
        top_svc = df["Service Type"].value_counts().idxmax() \
            if "Service Type" in df.columns and not df["Service Type"].dropna().empty else "—"

        si_cols = st.columns(4)
        for col, label, value, col_color in [
            (si_cols[0], "Most Common Risk", top_risk_label, "#E11D48"),
            (si_cols[1], "Top Regulator",    top_reg,        "#4A7FD4"),
            (si_cols[2], "Top Service Type", top_svc,        c["accent"]),
            (si_cols[3], "New This Run",     f"+{new_ents}", "#22C55E"),
        ]:
            col.markdown(f"""
            <div style="background:{c['card_bg']};border-radius:10px;padding:12px 14px;
                        border:1px solid {c['border']};">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;
                          letter-spacing:0.09em;text-transform:uppercase;margin-bottom:5px;">{label}</div>
              <div style="color:{col_color};font-size:14px;font-weight:800;overflow:hidden;
                          text-overflow:ellipsis;white-space:nowrap;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # Charts grid
        ic1, ic2 = st.columns(2)
        with ic1:
            if "Risk Level" in df.columns:
                rc = df["Risk Level"].value_counts().reset_index()
                rc.columns = ["level", "count"]
                rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x), {}).get("label", "Unknown"))
                chart = (
                    alt.Chart(rc)
                    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.92)
                    .encode(
                        x=alt.X("label:N",
                                sort=alt.EncodingSortField("level", order="descending"),
                                axis=_axis_x().copy(labelAngle=0), title=None),
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
                                                      color=c["text"], fontSize=12,
                                                      subtitleColor=c["text_dim"], subtitleFontSize=10))
                    .configure_view(strokeOpacity=0, fill=c["card_bg"])
                    .configure(background=c["card_bg"])
                )
                st.altair_chart(chart, use_container_width=True)

        with ic2:
            if "Regulator Scope" in df.columns:
                reg_series = df["Regulator Scope"].map(normalize_regulator).value_counts().head(10)
                bar_chart(reg_series, "Regulator Scope", "Entities per regulatory body", "#4A7FD4")

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

        # Trend (only if 2+ runs)
        files_list = list_screening_files()
        if len(files_list) >= 2:
            st.markdown("---")
            st.markdown(f'<div class="section-title">Trend Across Runs</div>', unsafe_allow_html=True)
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
                    .mark_line(point=True, strokeWidth=2)
                    .encode(
                        x=alt.X("Run:N", axis=_axis_x(), title=None),
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
                                                      color=c["text"], fontSize=12,
                                                      subtitleColor=c["text_dim"], subtitleFontSize=10))
                    .configure_view(strokeOpacity=0, fill=c["card_bg"])
                    .configure(background=c["card_bg"])
                )
                st.altair_chart(chart, use_container_width=True)

        # Classification table
        if "Classification" in df.columns:
            st.markdown("---")
            st.markdown('<div class="section-title">Classification Breakdown</div>', unsafe_allow_html=True)
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
# FOOTER / TRUST BAR
# ══════════════════════════════════════════════════════════════════════════
st.markdown("---")
wf_count = len(st.session_state.workflow)
st.markdown(f"""
<div class="trust-bar">
  <span>📁 {Path(selected_path).name}</span>
  <span>🕐 Last updated: <b>{now_str}</b></span>
  <span>🗃 Sources: <b>VARA · CBUAE · DFSA · ADGM · SCA</b></span>
  {"<span>✓ <b>"+str(wf_count)+"</b> workflow actions logged this session</span>" if wf_count else ""}
  <span>ℹ️ Automated first-pass — not a legal determination</span>
</div>
""", unsafe_allow_html=True)
