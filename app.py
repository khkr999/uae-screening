"""
Streamlit UI for UAE Regulatory Screening.

This file is intentionally UI-focused. Data ingestion, normalization,
classification, and processing live in dedicated backend modules:

- data_loader.py
- processing.py
- logic.py
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st

from data_loader import (
    DATA_DIR,
    ScreeningDataError,
    list_screening_files,
    load_run_summary,
    load_screening_data,
    save_uploaded_file,
)
from logic import RISK_META
from processing import (
    apply_filters,
    build_active_filters,
    build_filter_options,
    build_trend_dataframe,
    classification_breakdown,
    compute_metrics,
    dominant_value,
    export_buffers,
    init_session_state,
    metric_delta,
    now_label,
    paginate,
)

try:
    from streamlit_searchbox import st_searchbox

    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("uae_screening.app")


st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state(st.session_state)
dark = st.session_state.theme == "dark"

THEMES = {
    "dark": {
        "app_bg": "#07091C",
        "sidebar_bg": "#040610",
        "card_bg": "#0C1228",
        "raised_bg": "#111830",
        "text": "#D8E1F2",
        "text_dim": "#8896B4",
        "text_muted": "#4E5E7A",
        "gold": "#C9A84C",
        "gold_dim": "rgba(201,168,76,0.12)",
        "gold_border": "rgba(201,168,76,0.22)",
        "border": "rgba(255,255,255,0.06)",
        "input_bg": "#0C1228",
    },
    "light": {
        "app_bg": "#DCE5F2",
        "sidebar_bg": "#CEDAEB",
        "card_bg": "#FFFFFF",
        "raised_bg": "#E8EEF8",
        "text": "#0F172A",
        "text_dim": "#334155",
        "text_muted": "#64748B",
        "gold": "#8A6012",
        "gold_dim": "rgba(138,96,18,0.12)",
        "gold_border": "rgba(138,96,18,0.34)",
        "border": "rgba(15,23,42,0.12)",
        "input_bg": "#FFFFFF",
    },
}
c = THEMES[st.session_state.theme]


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: {c['app_bg']} !important;
            color: {c['text']} !important;
        }}
        #MainMenu, footer, header {{ visibility: hidden; }}
        .stApp {{ background: {c['app_bg']} !important; }}
        .block-container {{ padding-top: 0.8rem !important; padding-bottom: 2rem !important; max-width: 1480px !important; }}

        [data-testid="stSidebar"] {{ background: {c['sidebar_bg']} !important; border-right: 1px solid {c['border']} !important; }}
        [data-testid="stSidebar"] * {{ color: {c['text_dim']} !important; }}
        [data-testid="stSidebar"] h3 {{ color: {c['gold']} !important; }}
        [data-testid="stSidebar"] .stCaption {{ color: {c['text_muted']} !important; font-size: 0.78rem !important; }}
        [data-testid="collapsedControl"] {{
            background: {c['card_bg']} !important;
            border: 1px solid {c['gold_border']} !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        }}
        [data-testid="collapsedControl"] svg {{ fill: {c['gold']} !important; }}

        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
        div[data-baseweb="input"] input, .stTextInput input,
        [data-testid="stSelectbox"] > div > div > div {{
            background: {c['input_bg']} !important;
            border-color: {c['gold_border']} !important;
            border-radius: 12px !important;
            color: {c['text']} !important;
        }}
        div[data-baseweb="select"] svg {{ fill: {c['gold']} !important; }}
        ul[data-baseweb="menu"] {{ background: {c['raised_bg']} !important; border: 1px solid {c['gold_border']} !important; border-radius: 12px !important; }}
        [data-baseweb="option"]:hover {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; }}
        .stMultiSelect > div > div {{ background: {c['input_bg']} !important; border-color: {c['gold_border']} !important; border-radius: 12px !important; }}
        [data-baseweb="tag"] {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; }}

        div.stButton > button, .stDownloadButton button {{
            background: {c['gold_dim']} !important;
            border: 1px solid {c['gold_border']} !important;
            border-radius: 10px !important;
            color: {c['gold']} !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            transition: all 0.15s !important;
        }}
        div.stButton > button:hover, .stDownloadButton button:hover {{
            background: rgba(201,168,76,0.2) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 8px 18px rgba(0,0,0,0.12) !important;
        }}

        [data-testid="stMetric"] {{
            background: {c['card_bg']} !important;
            border: 1px solid {c['border']} !important;
            border-top: 3px solid {c['gold']} !important;
            border-radius: 14px !important;
            padding: 1rem 1.1rem !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.14) !important;
        }}
        [data-testid="stMetricLabel"] {{ color: {c['text_muted']} !important; font-size: 0.77rem !important; font-weight: 700 !important; letter-spacing: 0.07em !important; text-transform: uppercase !important; }}
        [data-testid="stMetricValue"] {{ color: {c['text']} !important; font-size: 1.9rem !important; font-weight: 800 !important; letter-spacing: -0.03em !important; }}

        [data-testid="stTabs"] [data-baseweb="tab-list"] {{ background: {c['card_bg']} !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border: 1px solid {c['border']} !important; }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{ background: transparent !important; color: {c['text_dim']} !important; font-weight: 600 !important; font-size: 0.88rem !important; padding: 0.5rem 1.1rem !important; border-radius: 8px !important; transition: all 0.15s; }}
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; font-weight: 800 !important; border: 1px solid {c['gold_border']} !important; }}
        [data-baseweb="tab-highlight"] {{ display: none !important; }}

        .topbar {{
            display:flex; align-items:center; justify-content:space-between; gap:16px;
            padding:14px 18px; margin:0 0 14px 0;
            background:linear-gradient(180deg,{c['card_bg']} 0%, {c['raised_bg']} 100%);
            border:1px solid {c['gold_border']};
            border-radius:16px;
            box-shadow:0 10px 28px rgba(0,0,0,0.22);
        }}
        .topbar-logo {{ display:flex; align-items:center; gap:10px; }}
        .topbar-icon {{
            width:40px; height:40px; border-radius:11px;
            background:linear-gradient(135deg,{c['gold']},#7A5B10);
            display:flex; align-items:center; justify-content:center;
            font-size:18px; box-shadow:0 6px 18px rgba(201,168,76,0.25);
            flex-shrink:0;
        }}
        .topbar-title {{ color:{c['text']}; font-size:18px; font-weight:800; line-height:1.15; }}
        .topbar-sub {{ color:{c['text_muted']}; font-size:10px; font-weight:700; letter-spacing:0.12em; margin-top:2px; }}
        .topbar-status {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; justify-content:flex-end; }}
        .topbar-meta {{ text-align:right; }}
        .topbar-meta .run {{ color:{c['text_dim']}; font-size:11px; }}
        .topbar-meta .run b {{ color:{c['text']}; }}
        .topbar-meta .src {{ color:{c['text_muted']}; font-size:10px; }}
        .theme-status {{
            color:{c['text_muted']};
            font-size:10px;
            text-align:right;
            margin-top:6px;
            font-weight:700;
            letter-spacing:0.08em;
            text-transform:uppercase;
        }}
        .live-badge {{
            display:inline-flex; align-items:center; gap:5px; padding:5px 11px;
            border-radius:999px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25);
        }}
        .live-dot {{ width:5px; height:5px; border-radius:50%; background:#10B981; display:inline-block; }}
        .live-txt {{ color:#10B981; font-size:10px; font-weight:800; letter-spacing:0.06em; }}

        .section-title {{ color:{c['text']}; font-size:11px; font-weight:800; letter-spacing:0.07em; text-transform:uppercase; margin:0 0 0.6rem 0; }}
        .filter-shell {{
            background:{c['card_bg']};
            border:1px solid {c['border']};
            border-radius:16px;
            padding:14px;
            margin-bottom:12px;
            box-shadow:0 8px 22px rgba(0,0,0,0.12);
        }}
        .filter-label {{
            color:{c['text_muted']};
            font-size:9px;
            font-weight:800;
            letter-spacing:0.1em;
            text-transform:uppercase;
            margin-bottom:6px;
        }}
        .helper-note {{ color:{c['text_muted']}; font-size:11px; margin-top:4px; }}
        .active-filter-bar {{
            display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:10px 0 4px 0;
        }}
        .filter-chip {{
            display:inline-flex; align-items:center; gap:4px; padding:3px 10px;
            border-radius:999px; background:{c['gold_dim']}; border:1px solid {c['gold_border']};
            color:{c['gold']}; font-size:10px; font-weight:700;
        }}

        .entity-card {{
            background:{c['card_bg']}; border:1px solid {c['border']};
            border-radius:12px; padding:14px 16px; margin-bottom:8px;
            transition:border-color 0.2s, box-shadow 0.2s, transform 0.2s;
            position:relative;
            overflow:hidden;
        }}
        .entity-card:hover {{ border-color:{c['gold_border']}; box-shadow:0 10px 24px rgba(0,0,0,0.2); transform:translateY(-1px); }}
        .entity-card.priority {{
            border-color:rgba(225,29,72,0.28);
            box-shadow:0 12px 28px rgba(225,29,72,0.08), 0 8px 20px rgba(0,0,0,0.18);
        }}
        .entity-card.priority::before {{
            content:"";
            position:absolute;
            inset:0 auto 0 0;
            width:4px;
            background:linear-gradient(180deg,#FB7185,#E11D48);
        }}
        .priority-kicker {{
            color:#FB7185;
            font-size:9px;
            font-weight:800;
            letter-spacing:0.12em;
            text-transform:uppercase;
            margin-bottom:8px;
        }}
        .entity-card h4 {{ margin:0 0 3px 0; color:{c['text']}; font-size:0.97rem; font-weight:800; }}
        .entity-card .meta {{ color:{c['text_muted']}; font-size:0.8rem; margin-bottom:0.3rem; }}
        .entity-card .rationale {{ color:{c['text_dim']}; font-size:0.84rem; line-height:1.55; }}
        .entity-card .action-note {{ color:{c['text_muted']}; font-size:0.76rem; border-left:2px solid {c['gold_border']}; padding-left:7px; margin-top:6px; }}

        .overview-kpi {{
            background:{c['card_bg']};
            border:1px solid rgba(15,23,42,0.08);
            border-radius:18px;
            padding:18px 18px 16px 18px;
            min-height:112px;
            box-shadow:0 8px 18px rgba(31,41,55,0.08);
            position:relative;
            overflow:hidden;
        }}
        .overview-kpi::before {{
            content:"";
            position:absolute;
            inset:0 auto 0 0;
            width:4px;
            background:var(--kpi-accent, {c['gold']});
        }}
        .overview-kpi .label {{
            color:#A0A9BA;
            font-size:12px;
            font-weight:800;
            letter-spacing:0.14em;
            text-transform:uppercase;
            margin-bottom:10px;
        }}
        .overview-kpi .value {{
            color:#111827;
            font-size:28px;
            font-weight:900;
            line-height:1;
            margin-bottom:8px;
        }}
        .overview-kpi .note {{
            color:#8B95A7;
            font-size:12px;
            font-weight:600;
        }}
        .overview-grid-note {{
            color:#A0A9BA;
            font-size:12px;
            text-align:right;
            padding-top:4px;
        }}
        .overview-priority-card {{
            background:#FFFFFF;
            border:1px solid rgba(15,23,42,0.08);
            border-radius:18px;
            padding:18px 18px 16px 18px;
            box-shadow:0 10px 22px rgba(31,41,55,0.08);
            margin-bottom:14px;
        }}
        .overview-priority-title {{
            display:flex;
            align-items:center;
            gap:10px;
            margin-bottom:10px;
            color:#111827;
            font-size:16px;
            font-weight:900;
        }}
        .overview-priority-tags {{
            display:flex;
            gap:8px;
            flex-wrap:wrap;
            margin-bottom:10px;
        }}
        .overview-chip {{
            display:inline-flex;
            align-items:center;
            padding:5px 12px;
            border-radius:9px;
            background:#F7F7FA;
            border:1px solid #E5E7EB;
            color:#6B7280;
            font-size:12px;
            font-weight:700;
        }}
        .overview-status-chip {{
            display:inline-flex;
            align-items:center;
            padding:4px 10px;
            border-radius:999px;
            font-size:12px;
            font-weight:800;
            border:1px solid transparent;
        }}
        .overview-rationale {{
            color:#4B5563;
            font-size:13px;
            line-height:1.6;
            margin-bottom:10px;
        }}
        .overview-action {{
            color:#6B7280;
            font-size:12px;
            line-height:1.6;
            padding-left:12px;
            border-left:2px solid #E5E7EB;
        }}
        .overview-riskbox {{
            text-align:right;
            min-width:126px;
        }}
        .overview-riskbox .conf {{
            color:#9CA3AF;
            font-size:12px;
            font-weight:700;
            margin-top:8px;
        }}
        .overview-side-card {{
            background:#FFFFFF;
            border:1px solid rgba(15,23,42,0.08);
            border-radius:18px;
            padding:18px;
            box-shadow:0 10px 22px rgba(31,41,55,0.08);
            margin-bottom:14px;
        }}
        .overview-side-card.alerts {{
            background:#FFF8F4;
            border-color:#F1D4C2;
        }}
        .overview-side-title {{
            color:#111827;
            font-size:12px;
            font-weight:900;
            letter-spacing:0.12em;
            text-transform:uppercase;
            margin-bottom:14px;
        }}
        .overview-summary-row {{
            display:flex;
            justify-content:space-between;
            gap:12px;
            padding:12px 0;
            border-bottom:1px solid #EEF1F5;
        }}
        .overview-summary-row:last-child {{
            border-bottom:none;
        }}
        .overview-summary-row .name {{
            color:#9CA3AF;
            font-size:12px;
        }}
        .overview-summary-row .value {{
            color:#111827;
            font-size:12px;
            font-weight:800;
            text-align:right;
        }}
        .overview-risk-row {{
            display:grid;
            grid-template-columns: 90px 1fr 26px;
            gap:12px;
            align-items:center;
            margin-bottom:12px;
        }}
        .overview-risk-row:last-child {{
            margin-bottom:0;
        }}
        .overview-risk-row .name {{
            color:#4B5563;
            font-size:13px;
        }}
        .overview-risk-track {{
            height:28px;
            border-radius:8px;
            background:#EEF2FF;
            overflow:hidden;
        }}
        .overview-risk-fill {{
            height:100%;
            border-radius:8px;
        }}
        .overview-risk-row .count {{
            color:#111827;
            font-size:13px;
            font-weight:800;
            text-align:right;
        }}

        .result-shell {{ display:flex; flex-direction:column; gap:10px; }}
        .result-head {{
            display:grid;
            grid-template-columns: minmax(240px, 1.35fr) minmax(120px, 0.7fr) minmax(150px, 0.9fr) minmax(160px, 1fr) 98px;
            gap:14px; padding:12px 16px; background:{c['raised_bg']};
            border:1px solid {c['border']}; border-radius:16px;
        }}
        .result-head span {{
            color:{c['text_muted']}; font-size:10px; font-weight:800; letter-spacing:0.1em; text-transform:uppercase;
        }}
        .result-row-wrap {{ position:relative; }}
        .result-row-link {{ display:block; text-decoration:none; }}
        .result-row {{
            display:grid;
            grid-template-columns: minmax(240px, 1.35fr) minmax(120px, 0.7fr) minmax(150px, 0.9fr) minmax(160px, 1fr) 98px;
            gap:14px; padding:14px 16px;
            background:{c['card_bg']}; border:1px solid {c['border']}; border-radius:16px;
            transition:background 0.18s ease, transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
            box-shadow:0 8px 22px rgba(0,0,0,0.14);
        }}
        .result-row-link:hover .result-row, .result-row-link:focus .result-row {{
            background:{c['raised_bg']}; border-color:{c['gold_border']};
            transform:translateY(-1px); box-shadow:0 14px 28px rgba(0,0,0,0.2);
        }}
        .result-row.selected {{ border-color:{c['gold_border']}; box-shadow:0 14px 28px rgba(0,0,0,0.2); }}
        .result-brand {{ color:{c['text']}; font-size:14px; font-weight:800; margin-bottom:6px; }}
        .result-meta {{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }}
        .result-tag {{
            display:inline-flex; align-items:center; padding:3px 8px; border-radius:999px;
            background:{c['gold_dim']}; border:1px solid {c['gold_border']}; color:{c['gold']};
            font-size:10px; font-weight:700;
        }}
        .result-rationale {{ color:{c['text_dim']}; font-size:12px; line-height:1.6; }}
        .result-label {{ color:{c['text_muted']}; font-size:9px; font-weight:800; letter-spacing:0.09em; text-transform:uppercase; margin-bottom:6px; }}
        .result-value {{ color:{c['text']}; font-size:12px; line-height:1.5; }}
        .result-action {{
            color:{c['text']}; font-size:11px; line-height:1.55;
            background:rgba(255,255,255,0.02); border:1px solid {c['border']};
            border-radius:10px; padding:8px 10px;
        }}
        .drawer-panel {{
            background:linear-gradient(180deg,{c['card_bg']} 0%, {c['raised_bg']} 100%);
            border:1px solid {c['gold_border']}; border-radius:18px; padding:18px;
            box-shadow:0 18px 34px rgba(0,0,0,0.18);
        }}
        .working-panel {{
            border-color:rgba(225,29,72,0.22);
            box-shadow:0 18px 40px rgba(225,29,72,0.08), 0 18px 34px rgba(0,0,0,0.18);
        }}
        .insight-callout {{
            color:{c['text_dim']};
            font-size:12px;
            line-height:1.65;
            margin:0 0 8px 0;
        }}
        .insight-callout strong {{
            color:{c['text']};
        }}
        .drawer-section {{ padding-top:14px; margin-top:14px; border-top:1px solid {c['border']}; }}
        .empty-state {{ text-align:center; padding:40px 20px; }}
        .empty-state .icon {{ font-size:36px; margin-bottom:12px; }}
        .empty-state .title {{ color:{c['text']}; font-size:14px; font-weight:700; margin-bottom:6px; }}
        .empty-state .desc {{ color:{c['text_muted']}; font-size:12px; line-height:1.6; }}
        .error-state {{ background:rgba(225,29,72,0.07); border:1px solid rgba(225,29,72,0.2); border-radius:10px; padding:16px; }}
        .trust-bar {{
            display:flex; gap:16px; flex-wrap:wrap; align-items:center;
            padding:8px 0; border-top:1px solid {c['border']};
            color:{c['text_muted']}; font-size:10px;
        }}
        .trust-bar b {{ color:{c['text_dim']}; }}
        ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {c['gold_border']}; border-radius: 99px; }}

        @media (max-width: 1100px) {{
            .result-head {{ display:none; }}
            .result-row {{ grid-template-columns: 1fr; gap:10px; }}
            .topbar {{ flex-direction:column; align-items:flex-start; }}
            .topbar-status {{ width:100%; justify-content:space-between; }}
            .topbar-meta {{ text-align:left; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def risk_badge_html(level: int) -> str:
    meta = RISK_META.get(level, RISK_META[2])
    dot = f'<span style="width:5px;height:5px;border-radius:50%;background:{meta["color"]};display:inline-block;margin-right:5px;"></span>'
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;'
        f'background:{meta["bg"]};border:1px solid {meta["border"]};color:{meta["color"]};'
        f'font-size:10px;font-weight:800;white-space:nowrap;">{dot}{meta["label"]} {level}</span>'
    )


def alert_badge_html(status: str) -> str:
    if "NEW" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,0.12);color:#22C55E;border:1px solid rgba(34,197,94,0.3);font-size:9px;font-weight:800;">NEW</span>'
    if "INCREASED" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(249,115,22,0.12);color:#F97316;border:1px solid rgba(249,115,22,0.3);font-size:9px;font-weight:800;">↑ RISK UP</span>'
    return ""


def entity_href(brand: str) -> str:
    return f"?entity={quote(brand)}"


def set_selected_entity(brand: str | None) -> None:
    if brand:
        st.query_params["entity"] = brand
    elif "entity" in st.query_params:
        del st.query_params["entity"]


def get_selected_entity() -> str | None:
    entity = st.query_params.get("entity")
    if isinstance(entity, list):
        return entity[0] if entity else None
    return entity


def render_workflow_actions(brand: str, scope: str = "default") -> None:
    wf = st.session_state.workflow_log.get(brand)
    columns = st.columns(4)
    actions = [
        ("Reviewed", "reviewed"),
        ("Escalate", "escalated"),
        ("Clear", "cleared"),
        ("Annotate", "annotate"),
    ]
    for column, (label, action_id) in zip(columns, actions):
        is_active = wf and wf.get("action") == action_id
        if column.button(f"{'✓ ' if is_active else ''}{label}", key=f"{scope}_wf_{action_id}_{brand}", use_container_width=True):
            if action_id == "annotate":
                st.session_state[f"{scope}_show_note_{brand}"] = True
            elif is_active:
                del st.session_state.workflow_log[brand]
                st.rerun()
            else:
                st.session_state.workflow_log[brand] = {
                    "action": action_id,
                    "note": None,
                    "ts": now_label(),
                }
                st.rerun()

    if st.session_state.get(f"{scope}_show_note_{brand}"):
        note = st.text_area("Annotation note", placeholder="Enter your note…", key=f"{scope}_note_{brand}")
        if st.button("Save note", key=f"{scope}_save_note_{brand}"):
            st.session_state.workflow_log[brand] = {
                "action": "annotated",
                "note": note,
                "ts": now_label(),
            }
            st.session_state[f"{scope}_show_note_{brand}"] = False
            st.rerun()

    if wf:
        note_text = f' — "{wf["note"]}"' if wf.get("note") else ""
        st.success(f"✓ Logged as **{wf['action']}** at {wf['ts']}{note_text}")


def render_search_result(row: pd.Series, selected_brand: str | None) -> None:
    level = int(row.get("Risk Level", 2))
    brand = str(row.get("Brand", ""))
    classification = str(row.get("Classification", "")) or "Unclassified"
    regulator = str(row.get("Regulator Scope", "")) or "Unspecified"
    service = str(row.get("Service Type", "")) or "Unspecified"
    matched = str(row.get("Matched Entity (Register)", "")) or "No direct register match"
    action = str(row.get("Action Required", "")) or "Review recommended"
    rationale = str(row.get("Rationale", "")).strip()
    rationale = rationale[:180] + "…" if len(rationale) > 180 else rationale
    conf = str(row.get("Confidence", "")).strip() or "—"
    source_url = str(row.get("Top Source URL", "")).strip()
    alert = alert_badge_html(str(row.get("Alert Status", "")))
    row_class = "result-row selected" if brand == selected_brand else "result-row"

    st.markdown(
        f"""
        <div class="result-row-wrap">
          <a class="result-row-link" href="{entity_href(brand)}">
            <div class="{row_class}">
              <div>
                <div class="result-brand">{brand} {alert}</div>
                <div class="result-meta">
                  <span class="result-tag">{service}</span>
                  <span class="result-tag">{regulator}</span>
                </div>
                <div class="result-rationale">{rationale or "No rationale available."}</div>
              </div>
              <div>
                <div class="result-label">Classification</div>
                <div class="result-value">{classification}</div>
              </div>
              <div>
                <div class="result-label">Risk / Confidence</div>
                <div class="result-value">{risk_badge_html(level)}</div>
                <div class="result-value" style="margin-top:8px;">Confidence: <b>{conf}%</b></div>
              </div>
              <div>
                <div class="result-label">Register Match</div>
                <div class="result-value">{matched}</div>
                <div class="result-action" style="margin-top:10px;">{action}</div>
              </div>
              <div>
                <div class="result-label">Actions</div>
                <div class="result-value">Open the full review panel</div>
              </div>
            </div>
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns([1.2, 1.05, 3.1])
    if action_cols[0].button("Open detail", key=f"search_detail_{row.name}", use_container_width=True):
        set_selected_entity(brand)
        st.rerun()
    if source_url.startswith("http"):
        action_cols[1].link_button("Source", source_url, use_container_width=True)
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


def render_priority_card(row: pd.Series) -> None:
    brand = str(row["Brand"])
    level = int(row.get("Risk Level", 2))
    meta = RISK_META.get(level, RISK_META[2])
    alert = alert_badge_html(str(row.get("Alert Status", "")))
    service = str(row.get("Service Type", "")) or "Unspecified"
    regulator = str(row.get("Regulator Scope", "")) or "Unspecified"
    rationale = str(row.get("Rationale", ""))[:260]
    action_required = str(row.get("Action Required", ""))
    source_url = str(row.get("Top Source URL", ""))
    confidence = str(row.get("Confidence", ""))
    urgency = "Immediate attention recommended" if level >= 5 else "Priority review recommended"
    st.markdown(
        f"""
        <div class="entity-card priority">
          <div class="priority-kicker">{urgency}</div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div style="flex:1;min-width:0;">
              <h4>{brand} {alert}</h4>
              <div class="meta"><span class="result-tag">{service}</span> <span class="result-tag">{regulator}</span></div>
              <div class="rationale">{rationale}</div>
              {f'<div class="action-note">{action_required}</div>' if action_required else ''}
            </div>
            <div style="text-align:right;min-width:128px;flex-shrink:0;">
              {risk_badge_html(level)}
              <div style="color:{meta['color']};font-size:10px;font-weight:800;margin-top:8px;">CONF {confidence}%</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    actions = st.columns([1.2, 1.1, 3])
    if actions[0].button("Open detail", key=f"overview_detail_{row.name}", use_container_width=True):
        set_selected_entity(brand)
        st.rerun()
    if source_url.startswith("http"):
        actions[1].link_button("Source", source_url, use_container_width=True)


def render_overview_kpi(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="overview-kpi" style="--kpi-accent:{accent};">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_priority_card(row: pd.Series) -> None:
    level = int(row.get("Risk Level", 2))
    brand = str(row.get("Brand", ""))
    service = str(row.get("Service Type", "")) or "Service"
    regulator = str(row.get("Regulator Scope", "")) or "Regulator"
    rationale = str(row.get("Rationale", ""))[:170]
    action_required = str(row.get("Action Required", ""))
    confidence = str(row.get("Confidence", "")) or "0"
    st.markdown(
        f"""
        <div class="overview-priority-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;">
            <div style="flex:1;min-width:0;">
              <div class="overview-priority-title">{brand}</div>
              <div class="overview-priority-tags">
                <span class="overview-chip">{service}</span>
                <span class="overview-chip">{regulator}</span>
              </div>
              <div class="overview-rationale">{rationale}</div>
              <div class="overview-action">{action_required or "Review this entity in detail."}</div>
            </div>
            <div class="overview-riskbox">
              {risk_badge_html(level)}
              <div class="conf">CONF {confidence}%</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_summary_card(selected_path: str, df: pd.DataFrame, now_str: str) -> None:
    rows = [
        ("File", Path(selected_path).name.replace("UAE_Screening_", "").replace(".xlsx", "")[:22]),
        ("Top Regulator", dominant_value(df, "Regulator Scope")),
        ("Top Service", dominant_value(df, "Service Type")),
        ("Total Entities", f"{len(df):,}"),
    ]
    rows_html = "".join(
        f'<div class="overview-summary-row"><span class="name">{name}</span><span class="value">{value}</span></div>'
        for name, value in rows
    )
    st.markdown(
        f"""
        <div class="overview-side-card">
          <div class="overview-side-title">Run Summary</div>
          {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_action_card(df: pd.DataFrame) -> None:
    action_counts = df["Action Required"].fillna("").value_counts()
    investigate = int(action_counts.get("INVESTIGATE THIS WEEK", 0))
    review = int(action_counts.get("REVIEW THIS MONTH", 0))
    monitor = int(action_counts.get("MONITOR", 0))
    st.markdown(
        f"""
        <div class="overview-side-card alerts">
          <div class="overview-side-title" style="color:#D0873F;">Action Queue</div>
          <div style="color:#D0873F;font-size:13px;font-weight:800;margin-bottom:10px;">{investigate} entities need investigation this week</div>
          <div style="color:#B08A24;font-size:13px;font-weight:800;margin-bottom:10px;">{review} entities need review this month</div>
          <div style="color:#64748B;font-size:13px;font-weight:800;">{monitor} entities are in monitor mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_risk_distribution(df: pd.DataFrame) -> None:
    ordered_levels = [5, 4, 3, 2, 1, 0]
    counts = df["Risk Level"].value_counts().to_dict()
    max_count = max(counts.values()) if counts else 1
    rows_html = ""
    for level in ordered_levels:
        count = int(counts.get(level, 0))
        if count == 0 and level == 1:
            continue
        meta = RISK_META[level]
        width = max(10, int((count / max_count) * 100)) if count else 0
        rows_html += (
            f'<div class="overview-risk-row">'
            f'<span class="name">{meta["label"]}</span>'
            f'<div class="overview-risk-track"><div class="overview-risk-fill" style="width:{width}%;background:{meta["color"]};"></div></div>'
            f'<span class="count">{count}</span>'
            f'</div>'
        )
    st.markdown(
        f"""
        <div class="overview-side-card">
          <div class="overview-side-title">Risk Distribution</div>
          {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_entity_panel(row: pd.Series, closeable: bool = False, scope: str = "default") -> None:
    brand = str(row.get("Brand", ""))
    level = int(row.get("Risk Level", 2))
    classification = str(row.get("Classification", "")) or "—"
    regulator = str(row.get("Regulator Scope", "")) or "—"
    service = str(row.get("Service Type", "")) or "—"
    matched = str(row.get("Matched Entity (Register)", "")) or "—"
    confidence = str(row.get("Confidence", "")) or "0"
    url = str(row.get("Top Source URL", ""))
    rationale = str(row.get("Rationale", "")) or "No rationale available."
    action_required = str(row.get("Action Required", "")) or "No action specified."

    st.markdown('<div class="drawer-panel working-panel">', unsafe_allow_html=True)
    if closeable:
        header_cols = st.columns([4, 1.2])
        header_cols[0].markdown('<div class="section-title">Active Working Panel</div>', unsafe_allow_html=True)
        if header_cols[1].button("Close", key=f"{scope}_close_{brand}", use_container_width=True):
            set_selected_entity(None)
            st.rerun()
    st.markdown(
        f"""
        {risk_badge_html(level)} {alert_badge_html(str(row.get("Alert Status", "")))}
        <div style="color:{c['text']};font-size:20px;font-weight:800;margin:10px 0 4px 0;">{brand}</div>
        <div style="color:{c['text_muted']};font-size:11px;">{classification}</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="insight-callout"><strong>Working context:</strong> this panel is pinned to <strong>{brand}</strong>. Use it to review rationale, log actions, and keep one entity in focus while filtering the rest of the run.</div>',
        unsafe_allow_html=True,
    )

    actions = st.columns([1.2, 1])
    if actions[0].button("Open detail", key=f"{scope}_drawer_dialog_{brand}", use_container_width=True):
        show_entity_detail(row)
    if url.startswith("http"):
        actions[1].link_button("Source", url, use_container_width=True)

    st.markdown('<div class="drawer-section"><div class="section-title">Workflow Actions</div>', unsafe_allow_html=True)
    render_workflow_actions(brand, scope=scope)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="drawer-section">', unsafe_allow_html=True)
    meta_cols = st.columns(2)
    meta_items = [
        ("Service Type", service),
        ("Regulator Scope", regulator),
        ("Matched Entity", matched),
        ("Confidence", f"{confidence}%"),
    ]
    for index, (label, value) in enumerate(meta_items):
        with meta_cols[index % 2]:
            st.markdown(
                f'<div class="result-label">{label}</div><div class="result-value" style="margin-bottom:12px;">{value}</div>',
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="drawer-section">', unsafe_allow_html=True)
    st.markdown(f'<div class="result-label">Rationale</div><div class="result-value">{rationale}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="result-label" style="margin-top:14px;">Action Required</div><div class="result-action">{action_required}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)


@st.dialog("Entity Detail", width="large")
def show_entity_detail(row: pd.Series) -> None:
    render_entity_panel(row, closeable=False, scope="dialog")


def search_brands_factory(brands: list[str]):
    def search_brands(query: str) -> list[str]:
        if not query:
            return []
        normalized = query.lower().strip()
        starts = [brand for brand in brands if brand.lower().startswith(normalized)]
        contains = [brand for brand in brands if normalized in brand.lower() and brand not in starts]
        return (starts + contains)[:12]

    return search_brands


def upload_fallback() -> None:
    st.markdown(
        f"""
        <div class="error-state">
          <div style="color:#E11D48;font-size:13px;font-weight:700;margin-bottom:4px;">⚠ No screening file loaded</div>
          <div style="color:#8896B4;font-size:11px;">Upload a <code>UAE_Screening_*.xlsx</code> file to continue.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="margin:14px 0 8px 0;color:{c["text"]};font-size:12px;font-weight:700;">Upload a screening file here if the sidebar is collapsed</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload a UAE_Screening_*.xlsx file", type=["xlsx"], key="main_file_uploader")
    if uploaded:
        save_uploaded_file(uploaded)
        st.success(f"Saved: {uploaded.name}")
        st.rerun()
    st.stop()


inject_css()

with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 14px 0;border-bottom:1px solid {c['border']};margin-bottom:14px;">
            <div class="topbar-icon">🛡️</div>
            <div>
                <div class="topbar-title">UAE Screening</div>
                <div class="topbar-sub">RISK MONITORING</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    theme_label = "☀ Switch to Light Mode" if dark else "☾ Switch to Dark Mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state.theme = "light" if dark else "dark"
        st.rerun()

    st.markdown("---")
    files = list_screening_files()
    st.markdown(
        f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Screening Run</div>',
        unsafe_allow_html=True,
    )
    selected_path = None
    if files:
        options = {
            f'{item["timestamp"].strftime("%d %b %Y, %H:%M")}  ·  {item["size_kb"]} KB': item["path"]
            for item in files
        }
        choice = st.selectbox("Run", list(options.keys()), index=0, label_visibility="collapsed")
        selected_path = options[choice]
    else:
        st.markdown(
            """
            <div class="empty-state">
              <div class="icon">📭</div>
              <div class="title">No screening files</div>
              <div class="desc">Upload a UAE_Screening_*.xlsx file below.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    uploaded = st.file_uploader("Drop a UAE_Screening_*.xlsx file", type=["xlsx"], label_visibility="collapsed")
    if uploaded:
        save_uploaded_file(uploaded)
        st.success(f"Saved: {uploaded.name}")
        st.rerun()

    st.markdown("---")
    st.caption(f"Runs archived: **{len(files)}**")
    st.caption(f"`{DATA_DIR}`")
    st.caption("Internal tool — not a legal determination.")


now_str = now_label()
theme_toggle_label = "☀ Light Mode" if dark else "☾ Dark Mode"
header_col, toggle_col = st.columns([6.2, 1.35])

with header_col:
    st.markdown(
        f"""
        <div class="topbar">
          <div class="topbar-logo">
            <div class="topbar-icon">🛡️</div>
            <div>
              <div class="topbar-title">UAE Regulatory Screening</div>
              <div class="topbar-sub">INTERNAL RISK MONITORING PLATFORM</div>
            </div>
          </div>
          <div class="topbar-status">
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
        """,
        unsafe_allow_html=True,
    )

with toggle_col:
    if st.button(theme_toggle_label, key="header_theme_toggle", use_container_width=True):
        st.session_state.theme = "light" if dark else "dark"
        st.rerun()
    st.markdown(f'<div class="theme-status">Theme: {"Dark" if dark else "Light"}</div>', unsafe_allow_html=True)

if selected_path is None:
    upload_fallback()

try:
    with st.spinner("Loading screening data…"):
        df = load_screening_data(selected_path)
except ScreeningDataError as exc:
    logger.warning("User-facing data load error: %s", exc)
    st.markdown(
        f"""
        <div class="error-state">
          <div style="color:#E11D48;font-size:13px;font-weight:700;margin-bottom:4px;">⚠ Failed to load data</div>
          <div style="color:#8896B4;font-size:11px;">{exc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

if df.empty:
    st.markdown(
        """
        <div class="empty-state">
          <div class="icon">📭</div>
          <div class="title">Empty dataset</div>
          <div class="desc">The selected file contains no valid entities after filtering. Try another run or upload a fresh screening export.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

selected_entity_brand = get_selected_entity()
selected_entity_row = None
if selected_entity_brand:
    match = df[df["Brand"] == selected_entity_brand]
    if not match.empty:
        selected_entity_row = match.iloc[0]
    else:
        set_selected_entity(None)

previous_summary = {}
current_idx = next((index for index, item in enumerate(files) if item["path"] == selected_path), None)
if current_idx is not None and current_idx + 1 < len(files):
    previous_summary = load_run_summary(files[current_idx + 1]["path"])

metrics = compute_metrics(df)
prev_total = previous_summary.get("total", 0)
prev_priority = previous_summary.get("critical_high", 0)
prev_review = previous_summary.get("needs_review", 0)
prev_licensed = previous_summary.get("licensed", 0)
prev_new = previous_summary.get("new_entities", 0)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_overview_kpi("Total Screened", f'{metrics["total"]:,}', "This run", "#9A7B34")
with k2:
    share = f'{round(((metrics["critical"] + metrics["high"]) / max(metrics["total"],1)) * 100)}% of total'
    render_overview_kpi("Critical / High", str(metrics["critical"] + metrics["high"]), share, "#D63C54")
with k3:
    render_overview_kpi("Needs Review", str(metrics["needs_review"]), "Risk levels 2–3", "#E0B534")
with k4:
    render_overview_kpi("Licensed / Clear", str(metrics["licensed"]), "No action required", "#50C88A")
with k5:
    investigate_count = int(df["Action Required"].fillna("").eq("INVESTIGATE THIS WEEK").sum())
    render_overview_kpi("Investigate", str(investigate_count), "This week", "#F2A65A")

st.markdown("---")
tab_home, tab_search, tab_insights = st.tabs(["🏠  Overview", "🔍  Search & Filter", "📊  Insights"])

with tab_home:
    left_col, right_col = st.columns([1.7, 1])
    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)
        st.markdown(
            f'<div class="overview-grid-note">{len(top_risk)} entities — click to open detail</div>',
            unsafe_allow_html=True,
        )
        top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)
        if top_risk.empty:
            st.markdown(
                """
                <div class="empty-state">
                  <div class="icon">✅</div>
                  <div class="title">No priority entities in this run</div>
                  <div class="desc">The current export contains no High or Critical entities. Use Search & Filter to inspect medium-risk items instead.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for _, row in top_risk.iterrows():
                render_overview_priority_card(row)

    with right_col:
        render_overview_action_card(df)
        render_overview_summary_card(selected_path, df, now_str)
        render_overview_risk_distribution(df)


with tab_search:
    st.markdown(
        """
        <div class="overview-side-card">
          <div class="overview-side-title">Search & Filter</div>
          <div style="color:#6B7280;font-size:13px;line-height:1.7;">
            This build is intentionally focused on the Overview page and the exact Excel schema you provided.
            Search & Filter will be rebuilt next using only the real columns in your file:
            Brand, Service Type, Group, Risk Level, Action Required, Confidence, and Regulator Scope.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with tab_insights:
    st.markdown(
        """
        <div class="overview-side-card">
          <div class="overview-side-title">Insights</div>
          <div style="color:#6B7280;font-size:13px;line-height:1.7;">
            Insights is temporarily simplified while the Overview page is rebuilt around the exact
            Excel format you provided. This also removes the crash caused by assuming optional
            columns like <code>Alert Status</code> exist in every file.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
wf_count = len(st.session_state.workflow_log)
st.markdown(
    f"""
    <div class="trust-bar">
      <span>📁 {Path(selected_path).name}</span>
      <span>🕐 Last updated: <b>{now_str}</b></span>
      <span>🗃 Sources: <b>VARA · CBUAE · DFSA · ADGM · SCA</b></span>
      {"<span>✓ <b>"+str(wf_count)+"</b> workflow actions logged this session</span>" if wf_count else ""}
      <span>ℹ️ Automated first-pass — not a legal determination</span>
    </div>
    """,
    unsafe_allow_html=True,
)
