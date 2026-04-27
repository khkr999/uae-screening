"""
UAE Regulatory Screening – Internal Search UI (v5 · Full redesign)
Improvements:
  - Night/day mode toggle with fully implemented light theme
  - Clickable table rows → entity detail dialog panel
  - Workflow actions: review, escalate, clear, annotate
  - Proper filter system with active chips + clear all
  - Autocomplete search with suggestions (streamlit-searchbox)
  - Improved table: truncated text, sorting, better layout
  - Loading, empty, and error states
  - Trust indicators: last updated, data source, run status
  - Improved chart clarity: titles, insights, axis labels
  - Accessibility improvements: contrast, labels, aria roles
"""
from __future__ import annotations

import glob
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SESSION STATE DEFAULTS ────────────────────────────────────────────────
def _init():
    defaults = {
        "theme":          "dark",
        "workflow_log":   {},   # {brand: {action, note, ts}}
        "status_overrides": {},
        "action_overrides": {},
        "search_selected_rows": [],
        "selected_brand": None,
        "active_chip":    None,
        "page":           1,
        "sort_col":       "Risk Level",
        "sort_asc":       False,
        "risk_filter":    [],
        "reg_filter":     [],
        "search_query":   None,
        "search_risk_chip": None,
        "reset_search_autocomplete": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

dark = st.session_state.theme == "dark"

# ── THEME TOKENS ──────────────────────────────────────────────────────────
T = {
    "dark": {
        "app_bg":        "#0b1020",
        "sidebar_bg":    "#0b1020",
        "card_bg":       "#111827",
        "raised_bg":     "#0f172a",
        "text":          "#ffffff",
        "text_dim":      "#9ca3af",
        "text_muted":    "#9ca3af",
        "gold":          "#6366f1",
        "gold_dim":      "rgba(99,102,241,0.14)",
        "gold_border":   "rgba(99,102,241,0.28)",
        "border":        "rgba(255,255,255,0.06)",
        "input_bg":      "#0f172a",
    },
    "light": {
        "app_bg":        "#0b1020",
        "sidebar_bg":    "#0b1020",
        "card_bg":       "#111827",
        "raised_bg":     "#0f172a",
        "text":          "#ffffff",
        "text_dim":      "#9ca3af",
        "text_muted":    "#9ca3af",
        "gold":          "#6366f1",
        "gold_dim":      "rgba(99,102,241,0.14)",
        "gold_border":   "rgba(99,102,241,0.28)",
        "border":        "rgba(255,255,255,0.05)",
        "input_bg":      "#0f172a",
    },
}
c = T[st.session_state.theme]

# ── RISK METADATA ─────────────────────────────────────────────────────────
RISK_META = {
    5: {"label":"Critical",  "color":"#E11D48", "bg":"rgba(225,29,72,0.12)",  "border":"rgba(225,29,72,0.3)"},
    4: {"label":"High",      "color":"#F97316", "bg":"rgba(249,115,22,0.12)", "border":"rgba(249,115,22,0.3)"},
    3: {"label":"Medium",    "color":"#EAB308", "bg":"rgba(234,179,8,0.12)",  "border":"rgba(234,179,8,0.3)"},
    2: {"label":"Monitor",   "color":"#4A7FD4", "bg":"rgba(74,127,212,0.12)", "border":"rgba(74,127,212,0.3)"},
    1: {"label":"Low",       "color":"#4A7FD4", "bg":"rgba(74,127,212,0.08)", "border":"rgba(74,127,212,0.2)"},
    0: {"label":"Licensed",  "color":"#10B981", "bg":"rgba(16,185,129,0.12)", "border":"rgba(16,185,129,0.3)"},
}

def risk_badge_html(level: int) -> str:
    m = RISK_META.get(level, RISK_META[2])
    dot = f'<span style="width:5px;height:5px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:5px;"></span>'
    return (f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;'
            f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
            f'font-size:10px;font-weight:800;white-space:nowrap;">{dot}{m["label"]} {level}</span>')

def alert_badge_html(status: str) -> str:
    if "NEW" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,0.12);color:#22C55E;border:1px solid rgba(34,197,94,0.3);font-size:9px;font-weight:800;">NEW</span>'
    if "INCREASED" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(249,115,22,0.12);color:#F97316;border:1px solid rgba(249,115,22,0.3);font-size:9px;font-weight:800;">↑ RISK UP</span>'
    return ""


def table_chip_html(text: str) -> str:
    clean = str(text).strip() or "—"
    return f'<span class="search-chip">{clean}</span>'


CONFIDENCE_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
STATUS_PRIORITY = {"NOT FOUND": 3, "POSSIBLE UNLICENSED": 2, "REVIEWED": 1, "LICENSED": 0}
STATUS_META = {
    "NOT FOUND": {"icon": "❌", "label": "NOT FOUND", "color": "#E11D48", "bg": "rgba(225,29,72,0.1)", "border": "rgba(225,29,72,0.22)"},
    "POSSIBLE UNLICENSED": {"icon": "⚠️", "label": "POSSIBLE UNLICENSED", "color": "#F97316", "bg": "rgba(249,115,22,0.1)", "border": "rgba(249,115,22,0.22)"},
    "LICENSED": {"icon": "✔", "label": "LICENSED", "color": "#10B981", "bg": "rgba(16,185,129,0.1)", "border": "rgba(16,185,129,0.22)"},
    "REVIEWED": {"icon": "✔", "label": "REVIEWED", "color": "#4A7FD4", "bg": "rgba(74,127,212,0.1)", "border": "rgba(74,127,212,0.22)"},
}
SERVICE_LABEL_OVERRIDES = {
    "BNPL / short-term credit": "BNPL / Credit",
    "Digital wallet / stored value": "Wallet / Stored Value",
    "Wallet / payments / finance": "Wallet / Payments",
    "Money transfer / remittance": "Remittance",
    "International money transfer": "Intl. Transfer",
    "International remittance": "Intl. Remittance",
    "Trade finance / invoice finance": "Trade Finance",
    "Business account / prepaid card": "Business Account",
}
REGULATOR_LABEL_OVERRIDES = {
    "CBUAE_ONSHORE": "CBUAE Onshore",
    "DFSA_DIFC": "DFSA / DIFC",
    "DFSA_DIFC_VA": "DFSA / DIFC VA",
    "FSRA_ADGM_VA": "FSRA / ADGM VA",
    "VARA_DUBAI_VA": "VARA / Dubai VA",
    "GOVERNMENT": "Government",
}


def normalize_brand_key(value: str) -> str:
    return str(value).strip().lower()


def row_brand(row: pd.Series) -> str:
    return str(row.get("Brand", "")).strip()


def get_effective_action_required(row: pd.Series) -> str:
    brand = row_brand(row)
    return st.session_state.action_overrides.get(brand, str(row.get("Action Required", "")).strip() or "—")


def get_effective_status(row: pd.Series) -> str:
    brand = row_brand(row)
    if brand in st.session_state.status_overrides:
        return st.session_state.status_overrides[brand]
    classification = str(row.get("Classification", "")).upper()
    risk_level = int(row.get("Risk Level", 2))
    if "LICENSED" in classification or "GOVERNMENT PLATFORM" in classification or risk_level == 0:
        return "LICENSED"
    if "NOT FOUND" in classification:
        return "NOT FOUND"
    return "POSSIBLE UNLICENSED"


def status_badge_html(status: str) -> str:
    meta = STATUS_META.get(status, STATUS_META["POSSIBLE UNLICENSED"])
    return (
        f'<span title="{meta["label"]}" '
        f'style="display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:999px;'
        f'background:{meta["bg"]};border:1px solid {meta["border"]};color:{meta["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;">{meta["icon"]} {meta["label"]}</span>'
    )


def simplify_service_label(service: str) -> str:
    clean = str(service).strip() or "—"
    if clean in SERVICE_LABEL_OVERRIDES:
        return SERVICE_LABEL_OVERRIDES[clean]
    if len(clean) > 20:
        return clean[:18].rstrip() + "..."
    return clean


def service_chip_html(service: str) -> str:
    full = str(service).strip() or "—"
    short = simplify_service_label(full)
    return (
        f'<span class="search-chip" title="{full}" '
        f'style="max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{short}</span>'
    )


def normalize_regulator_label(scope: str) -> str:
    clean = clean_text(scope, fallback="—")
    if clean in REGULATOR_LABEL_OVERRIDES:
        return REGULATOR_LABEL_OVERRIDES[clean]
    return clean.replace("_", " ").title()


def clean_text(value: object, fallback: str = "") -> str:
    if value is None or pd.isna(value):
        return fallback
    clean = str(value).strip()
    if clean.lower() in {"nan", "none", "nat", "<na>"}:
        return fallback
    return clean


def confidence_rank(value: str) -> int:
    return CONFIDENCE_RANK.get(str(value).strip().upper(), 0)


def confidence_label(value: str) -> str:
    clean = str(value).strip().title()
    return clean or "Unknown"


def confidence_meter_html(value: str) -> str:
    clean = confidence_label(value)
    rank = confidence_rank(clean)
    colors = {3: "#10B981", 2: "#EAB308", 1: "#F97316", 0: "#64748B"}
    widths = {3: 100, 2: 68, 1: 40, 0: 18}
    return (
        f'<div title="Confidence: {clean}. Based on signal strength, source quality, and regulator matching." '
        f'style="min-width:72px;">'
        f'<div style="height:6px;background:{c["border"]};border-radius:999px;overflow:hidden;">'
        f'<div style="width:{widths[rank]}%;height:100%;background:{colors[rank]};border-radius:999px;"></div>'
        f'</div>'
        f'</div>'
    )


def confidence_fill_width(value: str) -> int:
    return {3: 100, 2: 68, 1: 40, 0: 18}[confidence_rank(value)]


def confidence_compact_html(value: str) -> str:
    clean = confidence_label(value)
    rank = confidence_rank(clean)
    colors = {3: "#34D399", 2: "#FBBF24", 1: "#A5B4FC", 0: "#64748B"}
    short_labels = {"High": "High", "Medium": "Med", "Low": "Low", "Unknown": "—"}
    return (
        f'<div style="display:flex;align-items:center;gap:6px;" '
        f'title="Confidence: {clean}. Based on signal strength, source quality, and regulator matching.">'
        f'<div style="width:40px;height:4px;background:{c["border"]};border-radius:999px;overflow:hidden;">'
        f'<div style="width:{confidence_fill_width(clean)}%;height:100%;background:{colors[rank]};border-radius:999px;"></div>'
        f'</div>'
        f'<span style="font-size:10px;color:{c["text_muted"]};font-weight:700;">{short_labels.get(clean, clean[:4])}</span>'
        f'</div>'
    )


def status_compact_html(status: str) -> str:
    label_map = {
        "LICENSED": ("✓ Licensed", "#34D399", "rgba(52,211,153,0.10)", "rgba(52,211,153,0.2)"),
        "REVIEWED": ("✓ Reviewed", "#93C5FD", "rgba(37,99,235,0.12)", "rgba(37,99,235,0.24)"),
        "NOT FOUND": ("✗ Unlicensed", "#F87171", "rgba(239,68,68,0.10)", "rgba(239,68,68,0.24)"),
        "POSSIBLE UNLICENSED": ("✗ Unlicensed", "#F87171", "rgba(239,68,68,0.10)", "rgba(239,68,68,0.24)"),
    }
    label, color, bg, border = label_map.get(status, ("Needs Review", "#FBBF24", "rgba(251,191,36,0.08)", "rgba(251,191,36,0.2)"))
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 8px;border-radius:999px;'
        f'background:{bg};border:1px solid {border};color:{color};font-size:10px;font-weight:700;white-space:nowrap;">{label}</span>'
    )


def action_required_badge_html(action_required: str) -> str:
    clean = clean_text(action_required, fallback="No action needed")
    upper = clean.upper()
    if upper == "INVESTIGATE THIS WEEK":
        color, bg, border = "#F87171", "rgba(239,68,68,0.10)", "rgba(239,68,68,0.22)"
    elif upper in {"REVIEW THIS MONTH", "MONITOR"}:
        color, bg, border = "#FBBF24", "rgba(251,191,36,0.08)", "rgba(251,191,36,0.20)"
    else:
        color, bg, border = c["text_muted"], "rgba(255,255,255,0.04)", c["border"]
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 8px;border-radius:8px;'
        f'background:{bg};border:1px solid {border};color:{color};font-size:10px;font-weight:700;white-space:nowrap;">{clean.title()}</span>'
    )


def entity_subtitle(row: pd.Series) -> str:
    status = get_effective_status(row)
    if status == "NOT FOUND":
        return "NOT FOUND · possible unlicensed"
    if status == "LICENSED":
        return "MATCH FOUND / licensed"
    if status == "REVIEWED":
        return "REVIEWED in current session"

    classification = clean_text(row.get("Classification", "")) or clean_text(row.get("Group", ""))
    classification = re.sub(r"[🟢🟡🟠🔴]", "", classification)
    classification = classification.replace(" – ", " · ").replace(" — ", " · ")
    classification = re.sub(r"\s+", " ", classification).strip(" ·")
    if len(classification) > 42:
        classification = classification[:40].rstrip() + "..."
    return classification or "Needs review"


def primary_row_action_label(action_required: str) -> str:
    clean = clean_text(action_required).upper()
    if clean in {"", "NO ACTION NEEDED"}:
        return "View Detail"
    return action_button_label(action_required)


def action_button_label(action_required: str) -> str:
    mapping = {
        "INVESTIGATE THIS WEEK": "Investigate",
        "REVIEW THIS MONTH": "Review",
        "MONITOR": "Monitor",
        "NO ACTION NEEDED": "No Action",
    }
    return mapping.get(str(action_required).strip().upper(), "Open")


def set_status(brand: str, status: str) -> None:
    st.session_state.status_overrides[brand] = status
    if status == "LICENSED":
        st.session_state.action_overrides[brand] = "NO ACTION NEEDED"
    elif status == "REVIEWED" and brand not in st.session_state.action_overrides:
        st.session_state.action_overrides[brand] = "REVIEWED"


def set_action_required(brand: str, action_required: str) -> None:
    st.session_state.action_overrides[brand] = action_required
    if action_required == "NO ACTION NEEDED":
        st.session_state.status_overrides[brand] = "LICENSED"


def log_workflow_action(brand: str, action_id: str, note: str | None = None) -> None:
    st.session_state.workflow_log[brand] = {
        "action": action_id,
        "note": note,
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


def build_search_suggestions(query: str, brands: list[str], regulators: list[str], services: list[str]) -> list[str]:
    if not query:
        return []
    normalized = query.lower().strip()
    suggestions: list[str] = []
    for brand in brands:
        if normalized in brand.lower():
            suggestions.append(f"Entity: {brand}")
    for regulator in regulators:
        display = normalize_regulator_label(regulator)
        if normalized in regulator.lower() or normalized in display.lower():
            suggestions.append(f"Regulator: {display}")
    for service in services:
        if normalized in service.lower():
            suggestions.append(f"Service: {service}")
    return suggestions[:12]

# ── CSS INJECTION ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: {c['app_bg']} !important;
    color: {c['text']} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {c['app_bg']} !important; }}
.block-container {{ padding-top: 1rem !important; padding-bottom: 2.5rem !important; max-width: 1200px !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: {c['sidebar_bg']} !important; border-right: 1px solid {c['border']} !important; }}
[data-testid="stSidebar"] * {{ color: {c['text_dim']} !important; }}
[data-testid="stSidebar"] h3 {{ color: {c['text']} !important; }}
[data-testid="stSidebar"] .stCaption {{ color: {c['text_muted']} !important; font-size: 0.78rem !important; }}

/* Inputs */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-baseweb="input"] input, .stTextInput input,
[data-testid="stSelectbox"] > div > div > div {{
    background: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 12px !important;
    color: {c['text']} !important;
    min-height: 46px !important;
    box-shadow: none !important;
}}
div[data-baseweb="select"] svg {{ fill: {c['text_dim']} !important; }}
ul[data-baseweb="menu"] {{ background: {c['card_bg']} !important; border: 1px solid {c['border']} !important; border-radius: 12px !important; }}
[data-baseweb="option"]:hover {{ background: {c['raised_bg']} !important; color: {c['text']} !important; }}
.stMultiSelect > div > div {{ background: {c['input_bg']} !important; border-color: {c['border']} !important; border-radius: 12px !important; }}
[data-baseweb="tag"] {{ background: rgba(255,255,255,0.06) !important; color: {c['text']} !important; }}

/* Metrics */
[data-testid="stMetric"] {{ display:none !important; }}
.kpi-card {{
    background:{c['card_bg']};
    border:1px solid {c['border']};
    border-radius:12px;
    padding:18px 18px 16px 18px;
    min-height:108px;
    box-shadow:0 14px 32px rgba(0,0,0,0.24);
}}
.kpi-label {{
    color:{c['text_muted']};
    font-size:11px;
    font-weight:700;
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin-bottom:14px;
}}
.kpi-value {{
    color:{c['text']};
    font-size:34px;
    font-weight:800;
    line-height:1;
    margin-bottom:10px;
}}
.kpi-note {{
    color:{c['text_dim']};
    font-size:12px;
    line-height:1.5;
}}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ background: {c['card_bg']} !important; border-radius: 12px !important; padding: 4px !important; gap: 6px !important; border: 1px solid {c['border']} !important; }}
[data-testid="stTabs"] [data-baseweb="tab"] {{ background: transparent !important; color: {c['text_dim']} !important; font-weight: 600 !important; font-size: 0.9rem !important; padding: 0.65rem 1.1rem !important; border-radius: 10px !important; transition: all 0.15s; }}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{ background: rgba(255,255,255,0.05) !important; color: {c['text']} !important; font-weight: 800 !important; border: 1px solid {c['border']} !important; }}
[data-baseweb="tab-highlight"] {{ display: none !important; }}
[data-baseweb="tab-border"] {{ background-color: {c['border']} !important; }}

/* Buttons */
div.stButton > button, .stDownloadButton button {{
    background: {c['card_bg']} !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: {c['text']} !important;
    font-weight: 700 !important;
    font-size: 0.84rem !important;
    min-height: 40px !important;
    transition: all 0.18s ease !important;
}}
div.stButton > button[kind="primary"] {{
    background: #6366f1 !important;
    border-color: #6366f1 !important;
    color: #ffffff !important;
}}
div.stButton > button:hover, .stDownloadButton button:hover {{
    background: {c['raised_bg']} !important;
    border-color: rgba(255,255,255,0.14) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 22px rgba(0,0,0,0.24) !important;
}}
div.stButton > button[kind="primary"]:hover {{
    background: #585cf0 !important;
    border-color: #585cf0 !important;
}}
div.stButton > button:disabled {{ opacity: 0.3 !important; transform: none !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 10px !important; border: 1px solid {c['border']} !important; overflow: hidden !important; box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important; }}
[data-testid="stDataFrame"] table {{ background: {c['card_bg']} !important; }}
[data-testid="stDataFrame"] th {{ background: {c['raised_bg']} !important; color: {c['text_muted']} !important; font-size: 0.77rem !important; font-weight: 700 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; border-bottom: 1px solid {c['border']} !important; padding: 8px 10px !important; }}
[data-testid="stDataFrame"] td {{ color: {c['text']} !important; font-size: 0.84rem !important; border-bottom: 1px solid {c['border']} !important; padding: 7px 10px !important; }}
[data-testid="stDataFrame"] tr:hover td {{ background: {c['raised_bg']} !important; }}

/* Vega charts */
[data-testid="stVegaLiteChart"] {{ border-radius: 10px !important; }}

/* Alerts */
[data-testid="stAlert"] {{ border-radius: 10px !important; border-left-width: 3px !important; background: {c['card_bg']} !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {c['gold_border']}; border-radius: 99px; }}

/* Chip buttons */
div[data-testid="stHorizontalBlock"] .stButton button {{
    height: 34px !important; min-height: 34px !important;
    white-space: nowrap !important; font-size: 0.79rem !important;
    padding: 0 0.7rem !important;
}}

/* Compact top bar */
.topbar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; margin-bottom: 16px;
    background:{c['card_bg']};
    border:1px solid {c['border']};
    border-radius:12px;
    box-shadow:0 14px 32px rgba(0,0,0,0.24);
}}
.topbar-logo {{ display:flex; align-items:center; gap:10px; }}
.topbar-icon {{
    width:32px; height:32px; border-radius:9px;
    background:linear-gradient(135deg,{c['gold']},#7A5B10);
    display:flex; align-items:center; justify-content:center;
    font-size:16px; box-shadow:0 4px 12px rgba(201,168,76,0.25);
    flex-shrink:0;
}}
.topbar-title {{ color:{c['text']}; font-size:14px; font-weight:800; line-height:1.2; }}
.topbar-sub {{ color:{c['text_muted']}; font-size:9px; font-weight:600; letter-spacing:0.08em; }}
.topbar-meta {{ text-align:right; }}
.topbar-meta .run {{ color:{c['text_dim']}; font-size:10px; }}
.topbar-meta .run b {{ color:{c['text']}; }}
.topbar-meta .src {{ color:{c['text_muted']}; font-size:9px; }}
.live-badge {{
    display:inline-flex; align-items:center; gap:5px; padding:4px 10px;
    border-radius:999px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25);
}}
.live-dot {{ width:5px; height:5px; border-radius:50%; background:#10B981; display:inline-block; }}
.live-txt {{ color:#10B981; font-size:10px; font-weight:800; letter-spacing:0.06em; }}

/* Pill */
.pill {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:10px; font-weight:800; white-space:nowrap; letter-spacing:0.04em; }}
.pill-critical {{ background:rgba(225,29,72,0.12); color:#E11D48; border:1px solid rgba(225,29,72,0.3); }}
.pill-high     {{ background:rgba(249,115,22,0.12); color:#F97316; border:1px solid rgba(249,115,22,0.3); }}
.pill-medium   {{ background:rgba(234,179,8,0.12);  color:#EAB308; border:1px solid rgba(234,179,8,0.3); }}
.pill-low      {{ background:rgba(74,127,212,0.12); color:#4A7FD4; border:1px solid rgba(74,127,212,0.3); }}
.pill-licensed {{ background:rgba(16,185,129,0.12); color:#10B981; border:1px solid rgba(16,185,129,0.3); }}

/* Cards */
.entity-card {{
    background:{c['card_bg']}; border:1px solid {c['border']};
    border-radius:12px; padding:16px 18px; margin-bottom:12px;
    transition:border-color 0.2s, box-shadow 0.2s;
    box-shadow:0 12px 28px rgba(0,0,0,0.18);
}}
.entity-card:hover {{ border-color:rgba(255,255,255,0.12); box-shadow:0 18px 34px rgba(0,0,0,0.24); }}
.entity-card h4 {{ margin:0 0 3px 0; color:{c['text']}; font-size:0.97rem; font-weight:800; }}
.entity-card .meta {{ color:{c['text_muted']}; font-size:0.8rem; margin-bottom:0.3rem; }}
.entity-card .rationale {{ color:{c['text_dim']}; font-size:0.84rem; line-height:1.55; }}
.entity-card .rationale.empty {{ color:{c['text_muted']}; font-style:italic; }}
.entity-card .action-note {{ color:{c['text_muted']}; font-size:0.76rem; border-left:2px solid {c['gold_border']}; padding-left:7px; margin-top:6px; }}
.overview-card-controls {{
    display:flex;
    gap:8px;
    margin:-4px 0 14px 0;
    padding-left:2px;
}}

/* Section titles */
.section-title {{ color:{c['text']}; font-size:11px; font-weight:800; letter-spacing:0.07em; text-transform:uppercase; margin:0 0 0.6rem 0; }}

/* Trust bar */
.trust-bar {{
    display:flex; gap:16px; flex-wrap:wrap; align-items:center;
    padding:8px 0; border-top:1px solid {c['border']};
    color:{c['text_muted']}; font-size:10px;
}}
.trust-bar b {{ color:{c['text_dim']}; }}

/* Detail panel */
.detail-panel {{
    background:{c['card_bg']}; border:1px solid {c['border']};
    border-radius:14px; padding:18px; margin-top:12px;
    box-shadow:0 4px 24px rgba(0,0,0,0.25);
}}
.detail-header {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:16px; padding-bottom:14px; border-bottom:1px solid {c['border']}; }}

/* Workflow action badge */
.wf-badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:9px; font-weight:800; background:{c['gold_dim']}; color:{c['gold']}; border:1px solid {c['gold_border']}; margin-left:6px; }}

/* Empty state */
.empty-state {{ text-align:center; padding:40px 20px; }}
.empty-state .icon {{ font-size:36px; margin-bottom:12px; }}
.empty-state .title {{ color:{c['text']}; font-size:14px; font-weight:700; margin-bottom:6px; }}
.empty-state .desc {{ color:{c['text_muted']}; font-size:12px; }}

/* Error state */
.error-state {{ background:rgba(225,29,72,0.07); border:1px solid rgba(225,29,72,0.2); border-radius:10px; padding:16px; }}

/* Active filter chip */
.filter-chip {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:999px; background:{c['gold_dim']}; border:1px solid {c['gold_border']}; color:{c['gold']}; font-size:10px; font-weight:700; margin-right:4px; }}

/* Search tab */
.search-card {{
    background:{c['card_bg']};
    border:1px solid {c['border']};
    border-radius:12px;
    padding:18px;
    box-shadow:0 14px 32px rgba(0,0,0,0.24);
    margin-bottom:20px;
}}
.search-kicker {{
    color:{c['text_muted']};
    font-size:10px;
    font-weight:800;
    letter-spacing:0.12em;
    text-transform:uppercase;
    margin-bottom:8px;
}}
.search-filter-note {{
    color:{c['text_dim']};
    font-size:12px;
    line-height:1.6;
}}
.search-count-line {{
    color:{c['text_muted']};
    font-size:11px;
    margin:2px 0 12px 0;
}}
.search-count-line strong {{
    color:{c['text_dim']};
}}
.search-column-head {{
    color:{c['text_muted']};
    font-size:10px;
    font-weight:800;
    letter-spacing:0.08em;
    text-transform:uppercase;
    padding-bottom:8px;
}}
.search-entity-cell {{
    display:flex;
    flex-direction:column;
    gap:3px;
}}
.search-entity-cell .name {{
    color:{c['text']};
    font-size:12px;
    font-weight:800;
}}
.search-entity-cell .sub {{
    color:{c['text_muted']};
    font-size:10px;
}}
.search-divider {{
    height:1px;
    background:{c['border']};
    margin:8px 0;
}}
.search-row-actions .stButton button {{
    min-height:30px !important;
    height:30px !important;
    padding:0 0.55rem !important;
    font-size:0.74rem !important;
}}
.search-table-header {{
    display:grid;
    grid-template-columns: 2.5fr 1fr 1fr 1.1fr 0.7fr 1.8fr 0.9fr 0.8fr;
    gap:14px;
    background:{c['raised_bg']};
    padding:14px 18px;
    border:1px solid {c['border']};
    border-radius:12px 12px 0 0;
    box-shadow:0 14px 32px rgba(0,0,0,0.24);
    position:sticky;
    top:0;
    z-index:3;
}}
.search-table-header span {{
    color:{c['text_muted']};
    font-size:10px;
    font-weight:800;
    letter-spacing:0.11em;
    text-transform:uppercase;
}}
.search-row {{
    display:grid;
    grid-template-columns: 2.5fr 1fr 1fr 1.1fr 0.7fr 1.8fr 0.9fr 0.8fr;
    gap:14px;
    align-items:center;
    padding:18px 18px;
    background:#111827;
    border-left:4px solid transparent;
    border-right:1px solid {c['border']};
    border-bottom:1px solid {c['border']};
    transition:background 0.18s ease, transform 0.18s ease;
}}
.search-row:last-child {{ border-bottom:none; }}
.search-row:hover {{ background:#161f33; transform:translateY(-1px); }}
.search-row.urgent {{
    background:linear-gradient(180deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04));
    border-left-color:#ef4444;
}}
.search-row.high-priority {{
    border-left-color:#ef4444;
}}
.search-row.medium {{
    border-left-color:#eab308;
}}
.search-row.safe {{
    border-left-color:#10b981;
}}
.search-brand {{
    color:{c['text']};
    font-size:14px;
    font-weight:800;
    margin-bottom:4px;
}}
.search-sub {{
    color:{c['text_muted']};
    font-size:11px;
}}
.search-rationale {{
    color:{c['text_dim']};
    font-size:11px;
    line-height:1.55;
    margin-top:7px;
    display:-webkit-box;
    -webkit-line-clamp:2;
    -webkit-box-orient:vertical;
    overflow:hidden;
}}
.search-chip {{
    display:inline-flex;
    align-items:center;
    padding:5px 10px;
    border-radius:10px;
    background:{c['gold_dim']};
    border:1px solid {c['gold_border']};
    color:{c['gold']};
    font-size:11px;
    font-weight:700;
    max-width:100%;
}}
.search-action {{
    color:{c['text_dim']};
    font-size:12px;
    line-height:1.55;
}}
.search-status {{
    display:flex;
    align-items:center;
}}
.search-controls {{
    display:flex;
    justify-content:flex-end;
    gap:8px;
    padding:8px 18px 16px 18px;
    border-left:1px solid {c['border']};
    border-right:1px solid {c['border']};
    border-bottom:1px solid {c['border']};
    background:{c['card_bg']};
}}
.search-summary {{
    display:flex;
    justify-content:space-between;
    gap:16px;
    align-items:flex-start;
    margin:10px 0 14px 0;
}}
.search-summary-card {{
    flex:1;
    background:{c['raised_bg']};
    border:1px solid {c['border']};
    border-radius:12px;
    padding:12px 14px;
    box-shadow:0 12px 28px rgba(0,0,0,0.2);
}}
.search-summary-card .label {{
    color:{c['text_muted']};
    font-size:10px;
    font-weight:800;
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin-bottom:6px;
}}
.search-summary-card .value {{
    color:{c['text']};
    font-size:13px;
    line-height:1.6;
    font-weight:700;
}}
.search-summary-card .subvalue {{
    color:{c['text_dim']};
    font-size:11px;
    line-height:1.6;
    margin-top:6px;
}}
.filter-chip-row {{
    display:flex;
    flex-wrap:wrap;
    gap:8px;
    align-items:center;
    margin-bottom:10px;
}}
.filter-chip-row .stButton {{
    min-width:110px;
}}

@media (max-width: 1200px) {{
    .search-table-header, .search-row {{
        grid-template-columns: 2fr 1fr 1fr 1fr 0.7fr 1.5fr 0.9fr 0.9fr;
        gap:10px;
    }}
    .search-summary {{
        flex-direction:column;
    }}
    .search-count-line {{
        line-height:1.6;
    }}
}}

hr {{ border-color: {c['border']} !important; }}
</style>
""", unsafe_allow_html=True)

# ── NOISE FILTER ──────────────────────────────────────────────────────────
NOISE_BRANDS = {
    "rulebook","the complete rulebook","licensing","centralbank",
    "globenewswire","globe newswire","cbuae rulebook",
    "insights for businesses","insights","businesses",
    "money transfers","companies law amendments","gccbusinesswatch",
    "financialit","visamiddleeast","khaleejtimes","khaleej times",
    "gulfnews","gulf news","thenational","the national",
    "arabianbusiness","arabian business","zawya","wam",
    "reuters","bloomberg","ft.com","cnbc","forbes",
    "crunchbase","techcrunch","wikipedia","medium",
    "page","home","about","contact","terms","privacy",
    "fintech news","press release","media release","news release",
    "blog","white paper","whitepaper","report","research","survey",
    "study","conference","event","webinar","podcast",
    "linkedin","twitter","facebook","instagram","youtube",
    "warning","vasps","vasps licensing process",
    "rules","guide","overview","trends","plan","news","article",
    "introduction","summary","conclusion","documentation","docs",
    "help","support","faq","faqs","sitemap","copyright",
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

GENERIC_ONLY_WORDS = {
    "bank","banks","banking","payment","payments","finance",
    "financial","wallet","wallets","exchange","exchanges",
    "crypto","cryptocurrency","trading","investment","investments",
    "fintech","regulation","regulations","regulatory",
    "compliance","license","licenses","licensing",
    "money","transfer","transfers","remittance","remittances",
    "loan","loans","lending","credit","debit","card","cards",
    "digital","mobile","online","virtual","electronic",
    "service","services","solution","solutions","platform",
    "technology","technologies","app","apps","application",
    "company","companies","corporation","corp","limited","ltd",
    "uae","dubai","abu","dhabi","emirates","gulf","middle",
    "east","gcc","regional","international","global","local",
}

NEWS_MEDIA_HOSTS = {
    "khaleejtimes","gulfnews","thenational","arabianbusiness",
    "zawya","wam","gccbusinesswatch","globenewswire",
    "financialit","tekrevol","visamiddleeast","reuters",
    "bloomberg","ftcom","cnbc","forbes","crunchbase",
    "techcrunch","wikipedia","medium",
}

def is_noise_brand(brand: str) -> bool:
    if not brand or not isinstance(brand, str): return True
    b = brand.strip().lower()
    if not b or len(b) < 3: return True
    if b in NOISE_BRANDS: return True
    if NOISE_PATTERNS.match(b): return True
    if re.match(r"^[\s&'\"\-–—_\.,;:]", brand): return True
    if b[0].isdigit(): return True
    if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", b): return True
    b_compact = re.sub(r"[^a-z0-9]", "", b)
    if b_compact in NEWS_MEDIA_HOSTS: return True
    words = b.split()
    if all(w in GENERIC_ONLY_WORDS for w in words): return True
    if len(words) > 5: return True
    if re.search(r"\b(and|or|the|in|on|of|for|with|to|by)\b.*\b(and|or|the|in|on|of|for|with|to|by)\b", b): return True
    if b.rstrip(".").split()[-1] in {"the","a","an","of","in","on","for","to","and","or","by","with","from","at","as"}: return True
    letters = sum(c.isalpha() for c in brand)
    if letters < len(brand) * 0.5: return True
    if len(words) == 1 and b in GENERIC_ONLY_WORDS: return True
    if any(ind in b for ind in ["news","times","watch","magazine","blog","gazette","tribune","herald","daily","weekly","journal","newsletter","review","press","media"]): return True
    return False

# ── DATA PATHS ────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

@st.cache_data(show_spinner=False)
def list_screening_files() -> list[dict]:
    files = []
    for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
        p = Path(path)
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})", p.name)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M")
            files.append({"path": path, "name": p.name,
                          "timestamp": ts, "size_kb": p.stat().st_size // 1024})
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)

@st.cache_data(show_spinner=False)
def load_data(path: str) -> tuple[pd.DataFrame, str | None]:
    try:
        try:    df = pd.read_excel(path, sheet_name="📋 All Results")
        except Exception: df = pd.read_excel(path, sheet_name=0)
    except Exception as e:
        return pd.DataFrame(), str(e)

    text_columns = [
        "Brand", "Classification", "Group", "Service Type", "Regulator Scope",
        "Alert Status", "Rationale", "Action Required", "Top Source URL",
        "Matched Entity (Register)", "Register Category", "Key Snippet", "Source",
        "Discovery Query", "Confidence",
    ]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].map(lambda value: clean_text(value))
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

def render_card(row: pd.Series):
    level = int(row.get("Risk Level", 2))
    m     = RISK_META.get(level, RISK_META[2])
    dot   = f'<span style="width:5px;height:5px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:5px;flex-shrink:0;"></span>'
    pill  = f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};font-size:10px;font-weight:800;">{dot}{m["label"]} · {level}</span>'

    alert = clean_text(row.get("Alert Status", ""))
    alert_html = alert_badge_html(alert)

    svc  = clean_text(row.get("Service Type", ""), fallback="—")
    reg  = normalize_regulator_label(row.get("Regulator Scope", ""))
    rat_raw = clean_text(row.get("Rationale", ""))
    rat = rat_raw[:300] if rat_raw else "No description available from this run — review source manually."
    rat_class = "rationale" if rat_raw else "rationale empty"
    act  = clean_text(row.get("Action Required", ""))
    brand = clean_text(row.get("Brand", ""), fallback="Unknown")

    wf = st.session_state.workflow_log.get(brand)
    wf_html = f'<span class="wf-badge">{wf["action"].upper()}</span>' if wf else ""

    tag_style = f'display:inline-block;padding:2px 8px;border-radius:4px;background:{c["gold_dim"]};color:{c["gold"]};font-size:10px;font-weight:600;margin-right:4px;'

    st.markdown(f"""
    <div class="entity-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
        <div style="flex:1;min-width:0;">
          <h4>{brand} {alert_html} {wf_html}</h4>
          <div class="meta">
            <span style="{tag_style}">{svc}</span>
            <span style="{tag_style}">{reg}</span>
          </div>
          <div class="{rat_class}">{rat}</div>
          {f'<div class="action-note">{act}</div>' if act else ''}
        </div>
        <div style="text-align:right;min-width:110px;flex-shrink:0;">
          {pill}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── ENTITY DETAIL DIALOG ──────────────────────────────────────────────────
@st.dialog("Entity Detail", width="large")
def show_entity_detail(row: pd.Series):
    brand = str(row.get("Brand",""))
    level = int(row.get("Risk Level", 2))
    m     = RISK_META.get(level, RISK_META[2])

    # Header
    st.markdown(f"""
    <div class="detail-header">
      <div style="flex:1;">
        {risk_badge_html(level)}
        {alert_badge_html(str(row.get("Alert Status","")))}
        <h3 style="color:{c['text']};font-size:18px;font-weight:800;margin:8px 0 4px 0;">{brand}</h3>
        <div style="color:{c['text_muted']};font-size:11px;">{row.get('Classification','')}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Workflow actions
    st.markdown(f'<div class="section-title">Workflow Actions</div>', unsafe_allow_html=True)
    wf = st.session_state.workflow_log.get(brand)

    wa1, wa2, wa3, wa4 = st.columns(4)
    actions = [
        (wa1, "✓ Mark Reviewed", "reviewed", "#10B981"),
        (wa2, "↑ Escalate",      "escalated", "#F97316"),
        (wa3, "✕ Clear",         "cleared",   "#4A7FD4"),
        (wa4, "✎ Annotate",      "annotate",  c["gold"]),
    ]
    for col, label, action_id, color in actions:
        is_active = wf and wf.get("action") == action_id
        btn_label = f"{'✓ ' if is_active else ''}{label}"
        if col.button(btn_label, key=f"wf_{action_id}_{brand}", use_container_width=True):
            if action_id == "annotate":
                st.session_state[f"show_note_{brand}"] = True
            elif is_active:
                del st.session_state.workflow_log[brand]
                st.rerun()
            else:
                st.session_state.workflow_log[brand] = {
                    "action": action_id, "note": None,
                    "ts": datetime.now().strftime("%H:%M:%S")
                }
                st.rerun()

    if st.session_state.get(f"show_note_{brand}"):
        note = st.text_area("Annotation note", placeholder="Enter your note…", key=f"note_{brand}")
        if st.button("Save note", key=f"save_note_{brand}"):
            st.session_state.workflow_log[brand] = {
                "action": "annotated", "note": note,
                "ts": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state[f"show_note_{brand}"] = False
            st.rerun()

    if wf:
        note_text = f' — "{wf["note"]}"' if wf.get("note") else ""
        st.success(f"✓ Logged as **{wf['action']}** at {wf['ts']}{note_text}")

    st.divider()

    # Metadata grid
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        for label, key in [("Service Type","Service Type"),("Regulator Scope","Regulator Scope"),("Classification","Classification")]:
            raw_val = clean_text(row.get(key, ""), fallback="—")
            val = normalize_regulator_label(raw_val) if key == "Regulator Scope" else raw_val
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">{label}</div>
              <div style="color:{c['text']};font-size:12px;">{val}</div>
            </div>""", unsafe_allow_html=True)
    with meta_col2:
        conf = clean_text(row.get("Confidence", ""))
        matched = clean_text(row.get("Matched Entity (Register)", ""), fallback="—")
        url = clean_text(row.get("Top Source URL", ""))
        st.markdown(f"""
        <div style="margin-bottom:12px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">Confidence</div>
          <div style="height:8px;background:{c['border']};border-radius:99px;overflow:hidden;margin-bottom:4px;">
            <div style="width:{confidence_fill_width(conf)}%;height:100%;background:#10B981;border-radius:99px;"></div>
          </div>
          <div style="color:{c['text_dim']};font-size:11px;font-weight:700;">{confidence_label(conf)}</div>
        </div>
        <div style="margin-bottom:12px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">Matched Entity</div>
          <div style="color:{c['text']};font-size:12px;">{matched}</div>
        </div>""", unsafe_allow_html=True)
        if url.startswith("http"):
            st.link_button("↗ View Source", url)

    st.divider()
    rat = clean_text(row.get("Rationale", ""), fallback="No description available from this run — review source manually.")
    act = clean_text(row.get("Action Required", ""))
    st.markdown(f"""
    <div style="margin-bottom:14px;">
      <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Rationale</div>
      <div style="color:{c['text_dim']};font-size:12px;line-height:1.7;">{rat}</div>
    </div>""", unsafe_allow_html=True)
    if act:
        st.markdown(f"""
        <div style="background:{c['gold_dim']};border:1px solid {c['gold_border']};border-radius:8px;padding:10px 14px;">
          <div style="color:{c['gold']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Action Required</div>
          <div style="color:{c['text']};font-size:12px;line-height:1.65;">{act}</div>
        </div>""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 14px 0;border-bottom:1px solid {c['border']};margin-bottom:14px;">
        <div class="topbar-icon">🛡️</div>
        <div>
            <div class="topbar-title">UAE Screening</div>
            <div class="topbar-sub">RISK MONITORING</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Theme toggle
    theme_label = "☀ Switch to Light Mode" if dark else "☾ Switch to Dark Mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state.theme = "light" if dark else "dark"
        st.rerun()

    st.markdown("---")

    files = list_screening_files()
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Screening Run</div>', unsafe_allow_html=True)
    selected_path = None
    if files:
        options = {
            f'{f["timestamp"].strftime("%d %b %Y, %H:%M")}  ·  {f["size_kb"]} KB': f["path"]
            for f in files
        }
        choice = st.selectbox("Run", list(options.keys()), index=0, label_visibility="collapsed")
        selected_path = options[choice]
    else:
        st.markdown(f"""
        <div class="empty-state">
          <div class="icon">📭</div>
          <div class="title">No screening files</div>
          <div class="desc">Upload a UAE_Screening_*.xlsx file below</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Upload New Run</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Drop a UAE_Screening_*.xlsx file", type=["xlsx"], label_visibility="collapsed")
    if uploaded:
        save_uploaded_run(uploaded)
        st.success(f"Saved: {uploaded.name}")
        st.rerun()

    st.markdown("---")
    st.caption(f"Runs archived: **{len(files)}**")
    st.caption(f"`{DATA_DIR}`")
    st.caption("Internal tool — not a legal determination.")

# ── HEADER (compact top bar) ──────────────────────────────────────────────
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
file_label = Path(selected_path).name if selected_path else "No file loaded"

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
</div>""", unsafe_allow_html=True)

if selected_path is None:
    st.markdown(f"""
    <div style="max-width:760px;margin:40px auto 0 auto;background:{c['card_bg']};border:1px solid {c['gold_border']};
                border-radius:18px;padding:28px 28px 24px 28px;box-shadow:0 14px 34px rgba(0,0,0,0.18);">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <div style="width:42px;height:42px;border-radius:12px;background:{c['gold_dim']};border:1px solid {c['gold_border']};
                    display:flex;align-items:center;justify-content:center;font-size:18px;">📂</div>
        <div>
          <div style="color:{c['text']};font-size:20px;font-weight:800;line-height:1.15;">Upload a screening run to get started</div>
          <div style="color:{c['text_muted']};font-size:12px;margin-top:4px;">This app is built for <code>UAE_Screening_*.xlsx</code> files exported from your screening process.</div>
        </div>
      </div>
      <div style="background:{c['raised_bg']};border:1px solid {c['border']};border-radius:14px;padding:14px 16px;margin-bottom:18px;">
        <div style="color:{c['text_dim']};font-size:12px;line-height:1.7;">
          No local screening file is available on this Streamlit deployment yet.
          Upload the latest Excel file here and the dashboard will load immediately.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded_main = st.file_uploader(
        "Upload a UAE_Screening_*.xlsx file",
        type=["xlsx"],
        key="main_empty_state_uploader",
        help="Use the screening Excel export you want to review in the dashboard.",
    )
    if uploaded_main:
        save_uploaded_run(uploaded_main)
        st.success(f"Uploaded: {uploaded_main.name}")
        st.rerun()
    st.stop()

# ── LOAD DATA ─────────────────────────────────────────────────────────────
with st.spinner("Loading screening data…"):
    df, load_error = load_data(selected_path)

if load_error:
    st.markdown(f"""
    <div class="error-state">
      <div style="color:#E11D48;font-size:13px;font-weight:700;margin-bottom:4px;">⚠ Failed to load data</div>
      <div style="color:#8896B4;font-size:11px;">{load_error}</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

if df.empty:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">📭</div>
      <div class="title">Empty dataset</div>
      <div class="desc">The selected file contains no valid entities after filtering.</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────
total     = len(df)
critical  = len(df[df["Risk Level"] >= 5])
high      = len(df[df["Risk Level"] == 4])
needs_rev = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)])
licensed  = len(df[df["Risk Level"] == 0])
new_ents  = len(df[df["Alert Status"] == "🆕 NEW"])   if "Alert Status" in df.columns else 0
risk_up   = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) if "Alert Status" in df.columns else 0

kpi_cards = [
    ("Entities Screened", f"{total:,}", "Total entities after noise filtering"),
    ("Critical / High", f"{critical + high:,}", f"{(critical + high) / total * 100:.0f}% of total" if total else "0% of total"),
    ("Needs Review", f"{needs_rev:,}", "Risk levels 2–3, monitor or review"),
    ("Licensed / Clear", f"{licensed:,}", "Risk level 0, no action required"),
    ("New Entities", f"{new_ents:,}", f"{risk_up} risk increased" if risk_up else "No risk increases this run"),
]
k1, k2, k3, k4, k5 = st.columns(5)
for col, (label, value, note) in zip((k1, k2, k3, k4, k5), kpi_cards):
    col.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────
tab_home, tab_search, tab_insights = st.tabs(["🏠  Overview", "🔍  Search & Filter", "📊  Insights"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tab_home:
    left_col, right_col = st.columns([1.7, 1])

    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.caption("High and Critical entities — use the inline actions to investigate, open detail, or inspect the source.")

        top_risk = (df[df["Risk Level"] >= 4]
                    .sort_values("Risk Level", ascending=False).head(10))

        if top_risk.empty:
            st.markdown("""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:20px;text-align:center;">
              <div style="color:#10B981;font-size:13px;font-weight:700;">✓ No high-risk entities this run</div>
            </div>""", unsafe_allow_html=True)
        else:
            for _, row in top_risk.iterrows():
                render_card(row)
                overview_controls = st.columns([1.3, 1.05, 4.0])
                with overview_controls[0]:
                    if st.button(
                        action_button_label(clean_text(row.get("Action Required", ""))),
                        key=f"det_{row.name}",
                        use_container_width=True,
                        type="primary",
                    ):
                        log_workflow_action(row_brand(row), action_button_label(clean_text(row.get("Action Required", ""))).lower())
                        show_entity_detail(row)
                with overview_controls[1]:
                    source_url = clean_text(row.get("Top Source URL", ""))
                    if source_url.startswith("http"):
                        st.link_button("Source", source_url, use_container_width=True)

    with right_col:
        if new_ents > 0 or risk_up > 0:
            st.markdown(f"""
            <div style="background:rgba(249,115,22,0.07);border:1px solid rgba(249,115,22,0.2);border-radius:10px;padding:12px 14px;margin-bottom:14px;">
              <div style="color:#F97316;font-size:9px;font-weight:800;letter-spacing:0.09em;margin-bottom:6px;">ALERTS THIS RUN</div>
              {"<div style='color:"+c["text_dim"]+";font-size:11px;margin-bottom:3px;'><span style='color:#22C55E;font-weight:700;'>"+str(new_ents)+" new</span> entities added</div>" if new_ents else ""}
              {"<div style='color:"+c["text_dim"]+";font-size:11px;'><span style='color:#F97316;font-weight:700;'>"+str(risk_up)+"</span> risk level increases</div>" if risk_up else ""}
            </div>""", unsafe_allow_html=True)

        if "Risk Level" in df.columns:
            import altair as alt
            st.markdown('<div class="section-title">Risk Distribution</div>', unsafe_allow_html=True)
            _RCOL = {"Critical":"#E11D48","High":"#F97316","Medium":"#EAB308","Monitor":"#4A7FD4","Low":"#4A7FD4","Licensed":"#10B981"}
            _rc = df["Risk Level"].value_counts().reset_index()
            _rc.columns = ["level","count"]
            _rc["label"] = _rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
            _chart = (alt.Chart(_rc)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
                .encode(
                    x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"),
                            title=None,
                            axis=alt.Axis(labelColor=c["text_dim"], tickColor="transparent",
                                          domainColor=c["border"], labelFont="DM Sans,sans-serif", labelAngle=0)),
                    y=alt.Y("count:Q", axis=alt.Axis(labelColor=c["text_dim"], gridColor=c["border"],
                                                      domainColor="transparent", tickColor="transparent",
                                                      labelFont="DM Sans,sans-serif", title="Entities")),
                    color=alt.Color("label:N", scale=alt.Scale(domain=list(_RCOL.keys()), range=list(_RCOL.values())), legend=None),
                    tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                )
                .properties(height=200, title=alt.TitleParams("Entity count by risk level", color=c["text_dim"], fontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"]))
            st.altair_chart(_chart, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – SEARCH & FILTER
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    all_brands = sorted(df["Brand"].dropna().astype(str).tolist())
    all_regulators = sorted(df["Regulator Scope"].dropna().astype(str).unique().tolist()) if "Regulator Scope" in df.columns else []
    all_services = sorted(df["Service Type"].dropna().astype(str).unique().tolist()) if "Service Type" in df.columns else []
    regulator_display_map = {normalize_regulator_label(value): value for value in all_regulators}
    if st.session_state.reset_search_autocomplete:
        st.session_state.pop("search_autocomplete", None)
        st.session_state.pop("search_query_text", None)
        st.session_state.reset_search_autocomplete = False

    filter_bar = st.columns([3.0, 1.15, 1.15, 1.15, 1.25])
    with filter_bar[0]:
        if HAS_SEARCHBOX:
            search_query = st_searchbox(
                lambda q: build_search_suggestions(q, all_brands, all_regulators, all_services),
                placeholder="Search entity, regulator, or service...",
                key="search_autocomplete",
                clear_on_submit=False,
            )
            search_query = (search_query or "").strip()
        else:
            search_query = st.text_input(
                "Search entity, regulator, or service",
                placeholder="Search entity, regulator, or service...",
                key="search_query_text",
                label_visibility="collapsed",
            ).strip()

    regulator_counts = df["Regulator Scope"].fillna("—").astype(str).value_counts() if "Regulator Scope" in df.columns else pd.Series(dtype=int)
    regulator_map = {"All Regulators": None}
    for regulator, count in regulator_counts.items():
        regulator_map[f"{normalize_regulator_label(regulator)} ({count})"] = regulator

    with filter_bar[1]:
        regulator_choice_label = st.selectbox(
            "Regulator",
            list(regulator_map.keys()),
            label_visibility="collapsed",
            key="search_regulator_choice",
        )
    with filter_bar[2]:
        status_filter = st.selectbox(
            "Status",
            ["All Statuses", "NOT FOUND", "POSSIBLE UNLICENSED", "LICENSED", "REVIEWED"],
            label_visibility="collapsed",
            key="search_status_choice",
        )
    with filter_bar[3]:
        confidence_filter = st.selectbox(
            "Confidence",
            ["All Confidence", "High Only", "Medium Only", "Low Only"],
            label_visibility="collapsed",
            key="search_confidence_choice",
        )
    with filter_bar[4]:
        sort_by = st.selectbox(
            "Sort",
            ["Priority", "Risk", "Status", "Confidence", "Regulator", "Brand"],
            label_visibility="collapsed",
            key="search_sort_choice",
        )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    risk_cols = st.columns(6)
    risk_chip_defs = [("Critical", 5), ("High", 4), ("Medium", 3), ("Monitor", 2), ("Low", 1), ("Licensed", 0)]
    for index, (label, level) in enumerate(risk_chip_defs):
        active = st.session_state.search_risk_chip == level
        btn_label = f"● {label}" if active else label
        if risk_cols[index].button(btn_label, key=f"risk_chip_{level}", use_container_width=True):
            st.session_state.search_risk_chip = None if active else level
            st.session_state.page = 1
            st.rerun()

    quick_cols = st.columns([1.15, 1.15, 1.05, 1.05, 1.25, 1.25, 1.0])
    quick_defs = [("Critical/High", "high"), ("New Entities", "new"), ("Risk Up", "riskup"), ("Licensed", "licensed"), ("VASP/Crypto", "va")]
    for index, (label, key) in enumerate(quick_defs):
        active = st.session_state.active_chip == key
        btn_label = f"● {label}" if active else label
        if quick_cols[index].button(btn_label, key=f"quick_chip_{key}", use_container_width=True):
            st.session_state.active_chip = None if active else key
            st.session_state.page = 1
            st.rerun()
    with quick_cols[5]:
        actionable_only = st.toggle("Actionable only", key="search_actionable_only")
    with quick_cols[6]:
        if st.button("Clear all", key="search_clear_filters", use_container_width=True):
            st.session_state.search_regulator_choice = "All Regulators"
            st.session_state.search_status_choice = "All Statuses"
            st.session_state.search_sort_choice = "Priority"
            st.session_state.search_confidence_choice = "All Confidence"
            st.session_state.search_actionable_only = False
            st.session_state.search_risk_chip = None
            st.session_state.active_chip = None
            st.session_state.reset_search_autocomplete = True
            st.session_state.page = 1
            st.rerun()

    filtered = df.copy()
    selected_search = search_query
    if selected_search:
        if selected_search.startswith("Entity: "):
            filtered = filtered[filtered["Brand"] == selected_search.replace("Entity: ", "", 1)]
        elif selected_search.startswith("Regulator: "):
            search_regulator = selected_search.replace("Regulator: ", "", 1)
            matched_scope = regulator_display_map.get(search_regulator, search_regulator)
            filtered = filtered[filtered["Regulator Scope"] == matched_scope]
        elif selected_search.startswith("Service: "):
            filtered = filtered[filtered["Service Type"] == selected_search.replace("Service: ", "", 1)]
        else:
            brand_mask = filtered["Brand"].astype(str).str.contains(selected_search, case=False, na=False)
            reg_mask = False
            if "Regulator Scope" in filtered.columns:
                raw_reg_mask = filtered["Regulator Scope"].astype(str).str.contains(selected_search, case=False, na=False)
                display_reg_mask = filtered["Regulator Scope"].astype(str).map(normalize_regulator_label).str.contains(selected_search, case=False, na=False)
                reg_mask = raw_reg_mask | display_reg_mask
            service_mask = filtered["Service Type"].astype(str).str.contains(selected_search, case=False, na=False) if "Service Type" in filtered.columns else False
            filtered = filtered[brand_mask | reg_mask | service_mask]

    selected_regulator = regulator_map.get(regulator_choice_label)
    if selected_regulator:
        filtered = filtered[filtered["Regulator Scope"] == selected_regulator]

    if st.session_state.search_risk_chip is not None:
        filtered = filtered[filtered["Risk Level"] == st.session_state.search_risk_chip]

    filtered = filtered.copy()
    filtered["__status"] = filtered.apply(get_effective_status, axis=1)
    filtered["__action_required"] = filtered.apply(get_effective_action_required, axis=1)
    filtered["__confidence_rank"] = filtered["Confidence"].astype(str).map(confidence_rank)
    filtered["__priority_flag"] = ((filtered["Risk Level"] >= 4) & (filtered["__status"] == "NOT FOUND")).astype(int)
    filtered["__status_priority"] = filtered["__status"].map(lambda value: STATUS_PRIORITY.get(value, 0))

    if status_filter != "All Statuses":
        filtered = filtered[filtered["__status"] == status_filter]

    if confidence_filter == "High Only":
        filtered = filtered[filtered["__confidence_rank"] == 3]
    elif confidence_filter == "Medium Only":
        filtered = filtered[filtered["__confidence_rank"] == 2]
    elif confidence_filter == "Low Only":
        filtered = filtered[filtered["__confidence_rank"] == 1]

    if actionable_only:
        filtered = filtered[~filtered["__action_required"].isin(["", "—", "NO ACTION NEEDED"])]

    chip = st.session_state.active_chip
    if chip == "high":
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "new" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"].astype(str).str.contains("NEW", case=False, na=False)]
    elif chip == "riskup" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"].astype(str).str.contains("INCREASED", case=False, na=False)]
    elif chip == "licensed":
        filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "va":
        va_mask = filtered["Regulator Scope"].astype(str).str.contains("VA|VASP|CRYPTO", case=False, na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains("crypto|virtual asset|token", case=False, na=False)
        filtered = filtered[va_mask]

    if sort_by == "Priority":
        filtered = filtered.sort_values(
            ["__priority_flag", "Risk Level", "__status_priority", "__confidence_rank", "Brand"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
    elif sort_by == "Risk":
        filtered = filtered.sort_values(["Risk Level", "__status_priority", "Brand"], ascending=[False, False, True], na_position="last")
    elif sort_by == "Status":
        filtered = filtered.sort_values(["__status_priority", "Risk Level", "Brand"], ascending=[False, False, True], na_position="last")
    elif sort_by == "Confidence":
        filtered = filtered.sort_values(["__confidence_rank", "Risk Level", "Brand"], ascending=[False, False, True], na_position="last")
    elif sort_by == "Regulator":
        filtered = filtered.sort_values(["Regulator Scope", "Risk Level", "Brand"], ascending=[True, False, True], na_position="last")
    else:
        filtered = filtered.sort_values(["Brand", "Risk Level"], ascending=[True, False], na_position="last")

    active_filters = []
    if selected_search:
        active_filters.append(selected_search)
    if selected_regulator:
        active_filters.append(normalize_regulator_label(selected_regulator))
    if status_filter != "All Statuses":
        active_filters.append(status_filter)
    if confidence_filter != "All Confidence":
        active_filters.append(confidence_filter)
    if actionable_only:
        active_filters.append("Actionable only")
    if st.session_state.search_risk_chip is not None:
        active_filters.append(RISK_META.get(int(st.session_state.search_risk_chip), {}).get("label", "Risk"))
    if chip:
        active_filters.append(next((label for label, key in quick_defs if key == chip), chip))

    high_not_found_count = int(((filtered["Risk Level"] >= 4) & (filtered["__status"] == "NOT FOUND")).sum()) if not filtered.empty else 0
    actionable_count = int((~filtered["__action_required"].isin(["", "—", "NO ACTION NEEDED"])).sum()) if not filtered.empty else 0
    reviewed_count = int((filtered["__status"] == "REVIEWED").sum()) if not filtered.empty else 0
    if not filtered.empty and not filtered[filtered["Risk Level"] >= 4].empty:
        top_high_regulator = normalize_regulator_label(filtered[filtered["Risk Level"] >= 4]["Regulator Scope"].mode().iloc[0])
        insight_text = f"Most high-risk entities currently sit under {top_high_regulator}."
    else:
        insight_text = "No high-risk entities remain after the active filters."
    dominant_action = "No action required"
    if not filtered.empty and not filtered["__action_required"].replace(["", "—"], pd.NA).dropna().empty:
        dominant_action = str(filtered["__action_required"].replace(["", "—"], pd.NA).dropna().mode().iloc[0]).title()
    st.markdown(
        f"""
        <div class="search-summary">
          <div class="search-summary-card">
            <div class="label">Queue Summary</div>
            <div class="value"><strong>{high_not_found_count} entities</strong> are high risk with no register match.</div>
            <div class="subvalue">{actionable_count} still need action in the current view · {reviewed_count} marked reviewed.</div>
          </div>
          <div class="search-summary-card">
            <div class="label">Column Insight</div>
            <div class="value">{insight_text}</div>
            <div class="subvalue">Most common action: <strong>{dominant_action}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    count_line = f"{len(filtered):,} of {total:,}"
    st.markdown(
        f'<div class="search-count-line"><strong>{count_line}</strong> entities · {len(active_filters)} filters active</div>',
        unsafe_allow_html=True,
    )

    selected_brands = set(st.session_state.search_selected_rows)

    if filtered.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🔍</div>
          <div class="title">No entities match these filters</div>
          <div class="desc">Clear one or two filters and the review table will repopulate.</div>
        </div>""", unsafe_allow_html=True)
    else:
        per_page = 10
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        if st.session_state.page > total_pages:
            st.session_state.page = 1
        start = (st.session_state.page - 1) * per_page
        page_df = filtered.iloc[start:start + per_page]

        header_cols = st.columns([0.45, 2.35, 0.95, 1.1, 1.05, 0.95, 1.3, 1.05, 1.65])
        header_labels = [
            "",
            f'Brand / Entity{" ↑" if sort_by == "Brand" else ""}',
            f'Risk{" ↓" if sort_by in {"Priority", "Risk"} else ""}',
            f'Regulator{" ↑" if sort_by == "Regulator" else ""}',
            "Service",
            f'Conf.{" ↓" if sort_by == "Confidence" else ""}',
            "Action required",
            f'Status{" ↓" if sort_by in {"Priority", "Status"} else ""}',
            "",
        ]
        for col, label in zip(header_cols, header_labels):
            col.markdown(f'<div class="search-column-head">{label}</div>', unsafe_allow_html=True)

        for _, row in page_df.iterrows():
            brand = row_brand(row)
            service = clean_text(row.get("Service Type", ""), fallback="—")
            regulator = normalize_regulator_label(row.get("Regulator Scope", "—"))
            action_required = clean_text(row.get("__action_required", "—"), fallback="—")
            status = str(row.get("__status", "POSSIBLE UNLICENSED"))
            subtitle = entity_subtitle(row)

            brand_key = normalize_brand_key(brand)
            checkbox_key = f"row_select_{brand_key}"
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = brand in selected_brands

            row_cols = st.columns([0.45, 2.35, 0.95, 1.1, 1.05, 0.95, 1.3, 1.05, 1.65])
            with row_cols[0]:
                checked = st.checkbox("Select row", key=checkbox_key, label_visibility="collapsed")
                if checked:
                    selected_brands.add(brand)
                else:
                    selected_brands.discard(brand)
            with row_cols[1]:
                st.markdown(
                    f'<div class="search-entity-cell"><div class="name">{brand}</div><div class="sub">{subtitle}</div></div>',
                    unsafe_allow_html=True,
                )
            with row_cols[2]:
                st.markdown(risk_badge_html(int(row.get("Risk Level", 2))), unsafe_allow_html=True)
            with row_cols[3]:
                st.markdown(table_chip_html(regulator), unsafe_allow_html=True)
            with row_cols[4]:
                st.markdown(service_chip_html(service), unsafe_allow_html=True)
            with row_cols[5]:
                st.markdown(confidence_compact_html(clean_text(row.get("Confidence", ""))), unsafe_allow_html=True)
            with row_cols[6]:
                st.markdown(action_required_badge_html(action_required), unsafe_allow_html=True)
            with row_cols[7]:
                st.markdown(status_compact_html(status), unsafe_allow_html=True)
            with row_cols[8]:
                action_cols = st.columns([1, 1])
                primary_label = primary_row_action_label(action_required)
                if action_cols[0].button(primary_label, key=f"row_action_{row.name}", use_container_width=True, type="primary"):
                    log_workflow_action(brand, primary_label.lower())
                    show_entity_detail(row)
                if action_cols[1].button("Reviewed", key=f"row_review_{row.name}", use_container_width=True):
                    set_status(brand, "REVIEWED")
                    log_workflow_action(brand, "reviewed")
                    st.rerun()
            st.markdown('<div class="search-divider"></div>', unsafe_allow_html=True)

        st.session_state.search_selected_rows = sorted(selected_brands)

        footer_cols = st.columns([2.6, 1.5, 3.7, 0.8, 1.1])
        if footer_cols[0].button(
            f"Bulk: Investigate selected ({len(selected_brands)})",
            key="bulk_investigate",
            use_container_width=True,
            disabled=not selected_brands,
        ):
            for brand in selected_brands:
                set_action_required(brand, "INVESTIGATE THIS WEEK")
                st.session_state[f"row_select_{normalize_brand_key(brand)}"] = False
            st.session_state.search_selected_rows = []
            st.rerun()
        if footer_cols[1].button(
            "Mark reviewed",
            key="bulk_review",
            use_container_width=True,
            disabled=not selected_brands,
        ):
            for brand in selected_brands:
                set_status(brand, "REVIEWED")
                log_workflow_action(brand, "reviewed")
                st.session_state[f"row_select_{normalize_brand_key(brand)}"] = False
            st.session_state.search_selected_rows = []
            st.rerun()
        footer_cols[2].markdown(
            f"<div style='text-align:right;padding-top:0.45rem;color:{c['text_muted']};font-size:11px;'>Page <strong style='color:{c['text']}'>{st.session_state.page}</strong> of {total_pages}</div>",
            unsafe_allow_html=True,
        )
        if footer_cols[3].button("◀", use_container_width=True, disabled=st.session_state.page <= 1, key="search_p_prev"):
            st.session_state.page -= 1
            st.rerun()
        if footer_cols[4].button("Next →", use_container_width=True, disabled=st.session_state.page >= total_pages, key="search_p_next"):
            st.session_state.page += 1
            st.rerun()

        export_df = filtered.drop(columns=[column for column in filtered.columns if column.startswith("__")], errors="ignore")
        d1, d2 = st.columns(2)
        csv = export_df.to_csv(index=False).encode("utf-8-sig")
        d1.download_button(
            "↓ Download CSV",
            data=csv,
            file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        try:
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
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with tab_insights:
    import altair as alt

    RISK_COLORS = {"Critical":"#E11D48","High":"#F97316","Medium":"#EAB308",
                   "Monitor":"#4A7FD4","Low":"#4A7FD4","Licensed":"#10B981"}

    def _chart_base(height=240):
        return dict(
            axis_x=dict(
                labelColor=c["text_dim"],
                tickColor="transparent",
                domainColor=c["border"],
                labelFont="DM Sans,sans-serif",
            ),
            axis_y=dict(
                labelColor=c["text_dim"],
                gridColor=c["border"],
                domainColor="transparent",
                tickColor="transparent",
                labelFont="DM Sans,sans-serif",
            ),
            height=height,
        )

    def bar_chart(series, title, subtitle, color="#C9A84C", rotate=-30, height=240):
        if series.empty:
            st.markdown(f'<div class="empty-state"><div class="icon">📊</div><div class="title">{title}</div><div class="desc">No data available</div></div>', unsafe_allow_html=True)
            return
        df_c = series.reset_index(); df_c.columns = ["label","value"]
        b = _chart_base(height)
        chart = (alt.Chart(df_c)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
            .encode(
                x=alt.X("label:N", sort="-y", axis=alt.Axis(**b["axis_x"], labelAngle=rotate, title=None)),
                y=alt.Y("value:Q", axis=alt.Axis(**b["axis_y"], title="Count")),
                color=alt.value(color),
                tooltip=["label:N", alt.Tooltip("value:Q", title="Count")],
            )
            .properties(height=b["height"],
                        title=alt.TitleParams(title, subtitle=[subtitle],
                                              color=c["text"], fontSize=12,
                                              subtitleColor=c["text_dim"], subtitleFontSize=10))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"]))
        st.altair_chart(chart, use_container_width=True)

    def risk_bar(height=240):
        if "Risk Level" not in df.columns: return
        rc = df["Risk Level"].value_counts().reset_index(); rc.columns = ["level","count"]
        rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
        rc["color"] = rc["label"].map(RISK_COLORS).fillna("#7E8FAD")
        b = _chart_base(height)
        chart = (alt.Chart(rc)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
            .encode(
                x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"),
                        axis=alt.Axis(**b["axis_x"], title=None, labelAngle=0)),
                y=alt.Y("count:Q", axis=alt.Axis(**b["axis_y"], title="Entity Count")),
                color=alt.Color("label:N", scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())), legend=None),
                tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
            )
            .properties(height=b["height"],
                        title=alt.TitleParams("Risk Level Distribution",
                                              subtitle=["Entity count per risk category"],
                                              color=c["text"], fontSize=12,
                                              subtitleColor=c["text_dim"], subtitleFontSize=10))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"]))
        st.altair_chart(chart, use_container_width=True)

    # Insight summary row
    top_risk_label = df["Risk Level"].map(lambda x: RISK_META.get(int(x),{}).get("label","")).value_counts().idxmax() if "Risk Level" in df.columns and not df.empty else "—"
    top_reg = normalize_regulator_label(df["Regulator Scope"].value_counts().idxmax()) if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty else "—"
    top_svc = df["Service Type"].value_counts().idxmax()    if "Service Type"    in df.columns and not df["Service Type"].dropna().empty    else "—"

    si1, si2, si3, si4 = st.columns(4)
    for col, label, value, color_ in [
        (si1, "Most Common Risk",  top_risk_label, "#E11D48"),
        (si2, "Top Regulator",     top_reg,        "#4A7FD4"),
        (si3, "Top Service Type",  top_svc,        c["gold"]),
        (si4, "New This Run",      f"+{new_ents}",  "#22C55E"),
    ]:
        col.markdown(f"""
        <div style="background:{c['card_bg']};border-radius:8px;padding:10px 14px;border:1px solid {c['border']};">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.09em;text-transform:uppercase;margin-bottom:4px;">{label}</div>
          <div style="color:{color_};font-size:14px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    ic1, ic2 = st.columns(2)
    with ic1: risk_bar()
    with ic2:
        if "Regulator Scope" in df.columns:
            regulator_series = df["Regulator Scope"].map(normalize_regulator_label).value_counts().head(10)
            bar_chart(regulator_series,
                      "Regulator Scope", "Entities per regulatory body", "#4A7FD4")

    ic3, ic4 = st.columns(2)
    with ic3:
        if "Service Type" in df.columns:
            bar_chart(df["Service Type"].value_counts().head(10),
                      "Service Type Mix", "Top service categories identified", c["gold"])
    with ic4:
        if "Alert Status" in df.columns and df["Alert Status"].replace("","nan").dropna().replace("nan","").any():
            bar_chart(df["Alert Status"].replace("","nan").dropna().replace("nan","").value_counts().head(10),
                      "Alert Status Mix", "Changes detected vs. prior run", "#F97316")
        else:
            st.markdown(f"""
            <div class="empty-state">
              <div class="icon">📭</div>
              <div class="title">No Alert Data</div>
              <div class="desc">Alert Status column not present or empty in this run.</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:4px;">Trend Across Runs</div>', unsafe_allow_html=True)
    files_list = list_screening_files()
    if len(files_list) >= 2:
        trend_rows = []
        for f in files_list[:10]:
            try:
                d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                trend_rows.append({
                    "Run":           f["timestamp"].strftime("%m/%d %H:%M"),
                    "High/Critical": int(len(d[d["Risk Level"] >= 4])),
                    "Needs Review":  int(len(d[(d["Risk Level"]>=2)&(d["Risk Level"]<=3)])),
                    "Licensed":      int(len(d[d["Risk Level"]==0])),
                })
            except Exception:
                continue
        if trend_rows:
            _trend = pd.DataFrame(trend_rows).iloc[::-1]
            _trend_long = _trend.melt("Run", var_name="Category", value_name="Count")
            _tcolors = {"High/Critical":"#E11D48","Needs Review":"#EAB308","Licensed":"#10B981"}
            b = _chart_base(260)
            _tchart = (alt.Chart(_trend_long)
                .mark_line(point=True, strokeWidth=2)
                .encode(
                    x=alt.X("Run:N", axis=alt.Axis(**b["axis_x"], title=None)),
                    y=alt.Y("Count:Q", axis=alt.Axis(**b["axis_y"], title="Entity Count")),
                    color=alt.Color("Category:N", scale=alt.Scale(
                        domain=list(_tcolors.keys()), range=list(_tcolors.values())),
                        legend=alt.Legend(labelColor=c["text_dim"], titleColor=c["text_dim"])),
                    tooltip=["Run:N","Category:N", alt.Tooltip("Count:Q", title="Entities")],
                )
                .properties(height=b["height"],
                            title=alt.TitleParams("Risk Trend Across Runs",
                                                  subtitle=["Historical view of risk category counts per run"],
                                                  color=c["text"], fontSize=12,
                                                  subtitleColor=c["text_dim"], subtitleFontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"],
                           legend=alt.LegendConfig(labelColor=c["text_dim"], titleColor=c["text_dim"])))
            st.altair_chart(_tchart, use_container_width=True)
    else:
        st.caption(f"Only {len(files_list)} run archived — trend chart requires 2+ runs.")

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:8px;">Classification Breakdown</div>', unsafe_allow_html=True)
    if "Classification" in df.columns:
        cls = df["Classification"].value_counts().reset_index()
        cls.columns = ["Classification","Count"]
        cls["% of Total"] = (cls["Count"]/total*100).round(1).astype(str)+"%"
        st.dataframe(cls, use_container_width=True, hide_index=True,
                     column_config={"Count": st.column_config.ProgressColumn("Count", min_value=0, max_value=int(cls["Count"].max()), format="%d")})

# ── FOOTER / TRUST INDICATORS ─────────────────────────────────────────────
st.markdown("---")
wf_count = len(st.session_state.workflow_log)
st.markdown(f"""
<div class="trust-bar">
  <span>📁 {Path(selected_path).name}</span>
  <span>🕐 Last updated: <b>{now_str}</b></span>
  <span>🗃 Sources: <b>VARA · CBUAE · DFSA · ADGM · SCA</b></span>
  {"<span>✓ <b>"+str(wf_count)+"</b> workflow actions logged this session</span>" if wf_count else ""}
  <span>ℹ️ Automated first-pass — not a legal determination</span>
</div>""", unsafe_allow_html=True)
