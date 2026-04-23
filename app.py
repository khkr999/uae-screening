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


def render_workflow_actions(brand: str) -> None:
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
        if column.button(f"{'✓ ' if is_active else ''}{label}", key=f"wf_{action_id}_{brand}", use_container_width=True):
            if action_id == "annotate":
                st.session_state[f"show_note_{brand}"] = True
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

    if st.session_state.get(f"show_note_{brand}"):
        note = st.text_area("Annotation note", placeholder="Enter your note…", key=f"note_{brand}")
        if st.button("Save note", key=f"save_note_{brand}"):
            st.session_state.workflow_log[brand] = {
                "action": "annotated",
                "note": note,
                "ts": now_label(),
            }
            st.session_state[f"show_note_{brand}"] = False
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


def render_entity_panel(row: pd.Series, closeable: bool = False) -> None:
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
        if header_cols[1].button("Close", key=f"close_{brand}", use_container_width=True):
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
    if actions[0].button("Open detail", key=f"drawer_dialog_{brand}", use_container_width=True):
        show_entity_detail(row)
    if url.startswith("http"):
        actions[1].link_button("Source", url, use_container_width=True)

    st.markdown('<div class="drawer-section"><div class="section-title">Workflow Actions</div>', unsafe_allow_html=True)
    render_workflow_actions(brand)
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
    render_entity_panel(row, closeable=False)


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
k1.metric("Entities Screened", f'{metrics["total"]:,}', delta=metric_delta(metrics["total"], prev_total), help="Total entities after noise filtering")
k1.caption("Coverage is stable across this run." if metrics["total"] >= prev_total else "This run is smaller than the previous export.")
k2.metric("Critical / High", metrics["critical"] + metrics["high"], delta=metric_delta(metrics["critical"] + metrics["high"], prev_priority), delta_color="inverse", help="Risk levels 4–5 requiring immediate attention")
k2.caption("Priority queue grew." if (metrics["critical"] + metrics["high"]) > prev_priority else "Priority queue is holding or improving.")
k3.metric("Needs Review", metrics["needs_review"], delta=metric_delta(metrics["needs_review"], prev_review), help="Risk levels 2–3, monitor or review")
k3.caption("Broad review workload remains elevated." if metrics["needs_review"] > 0 else "No monitor-tier entities in this run.")
k4.metric("Licensed / Clear", metrics["licensed"], delta=metric_delta(metrics["licensed"], prev_licensed), help="Risk level 0, no action required")
k4.caption("Clear matches improved." if metrics["licensed"] >= prev_licensed else "Fewer clear matches than the last run.")
k5.metric("New Entities", metrics["new_entities"], delta=metric_delta(metrics["new_entities"], prev_new) or (f'↑ {metrics["risk_up"]} risk increased' if metrics["risk_up"] else None), delta_color="inverse", help="Entities not seen in prior run")
k5.caption("New intake needs triage." if metrics["new_entities"] else ("Risk increases flagged." if metrics["risk_up"] else "No fresh additions detected."))

st.markdown("---")
tab_home, tab_search, tab_insights = st.tabs(["🏠  Overview", "🔍  Search & Filter", "📊  Insights"])

with tab_home:
    left_col, right_col = st.columns([1.7, 1])
    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="insight-callout"><strong>Urgent queue:</strong> these are the highest-risk entities in the current run. Start with Critical and High items first, then move into monitor-tier reviews.</div>',
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
                render_priority_card(row)

    with right_col:
        if selected_entity_row is not None:
            render_entity_panel(selected_entity_row, closeable=True)
        elif metrics["new_entities"] > 0 or metrics["risk_up"] > 0:
            st.markdown(
                f"""
                <div style="background:rgba(249,115,22,0.07);border:1px solid rgba(249,115,22,0.2);border-radius:10px;padding:12px 14px;margin-bottom:14px;">
                  <div style="color:#F97316;font-size:9px;font-weight:800;letter-spacing:0.09em;margin-bottom:6px;">ALERTS THIS RUN</div>
                  {"<div style='color:"+c["text_dim"]+";font-size:11px;margin-bottom:3px;'><span style='color:#22C55E;font-weight:700;'>"+str(metrics["new_entities"])+" new</span> entities added</div>" if metrics["new_entities"] else ""}
                  {"<div style='color:"+c["text_dim"]+";font-size:11px;'><span style='color:#F97316;font-weight:700;'>"+str(metrics["risk_up"])+"</span> risk level increases</div>" if metrics["risk_up"] else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="section-title">Run Summary</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="insight-callout"><strong>Working panel:</strong> select any entity from the queue or search results to turn this area into a focused review workspace. Until then, this summary keeps the run context visible.</div>',
                unsafe_allow_html=True,
            )
            for label, value in [
                ("File", Path(selected_path).name[:40]),
                ("Top Regulator", dominant_value(df, "Regulator Scope")),
                ("Top Service", dominant_value(df, "Service Type")),
                ("Total Rows", f'{len(df):,}'),
                ("Last Updated", now_str),
            ]:
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {c['border']};gap:8px;">
                      <span style="color:{c['text_muted']};font-size:10px;">{label}</span>
                      <span style="color:{c['text']};font-size:10px;font-weight:700;text-align:right;word-break:break-word;max-width:160px;">{value}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            risk_counts = df["Risk Level"].value_counts().reset_index()
            risk_counts.columns = ["level", "count"]
            risk_counts["label"] = risk_counts["level"].map(lambda value: RISK_META[int(value)]["label"])
            risk_chart = (
                alt.Chart(risk_counts)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
                .encode(
                    x=alt.X("label:N", axis=alt.Axis(labelAngle=0, title=None, labelColor=c["text_dim"])),
                    y=alt.Y("count:Q", axis=alt.Axis(title=None, gridColor=c["border"], labelColor=c["text_dim"])),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(
                            domain=[RISK_META[i]["label"] for i in sorted(RISK_META)],
                            range=[RISK_META[i]["color"] for i in sorted(RISK_META)],
                        ),
                        legend=None,
                    ),
                    tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                )
                .properties(height=200, title="Risk Distribution")
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"])
            )
            st.altair_chart(risk_chart, use_container_width=True)


with tab_search:
    options = build_filter_options(df)
    search_brands = search_brands_factory(options["brands"])

    st.markdown('<div class="filter-shell">', unsafe_allow_html=True)
    filter_cols = st.columns([1.8, 1, 1, 0.72])
    with filter_cols[0]:
        st.markdown('<div class="filter-label">Search Entity</div>', unsafe_allow_html=True)
        if HAS_SEARCHBOX:
            selected_brand = st_searchbox(
                search_brands,
                placeholder="Search by brand, wallet, exchange, or partner name…",
                key="brand_searchbox",
                clear_on_submit=False,
            )
        else:
            raw = st.selectbox("Brand", ["— All —"] + options["brands"], index=0, label_visibility="collapsed")
            selected_brand = None if raw == "— All —" else raw
        st.markdown('<div class="helper-note">Search is the fastest way to jump to one entity and open its review panel.</div>', unsafe_allow_html=True)
    with filter_cols[1]:
        st.markdown('<div class="filter-label">Risk Filter</div>', unsafe_allow_html=True)
        risk_filter = st.multiselect(
            "Risk Level",
            options=options["risk_levels"],
            format_func=lambda value: RISK_META[int(value)]["label"],
            placeholder="All risk levels",
            label_visibility="collapsed",
            key="risk_filter",
        )
    with filter_cols[2]:
        st.markdown('<div class="filter-label">Regulator</div>', unsafe_allow_html=True)
        reg_filter = st.multiselect(
            "Regulator",
            options=options["regulators"],
            placeholder="All regulators",
            label_visibility="collapsed",
            key="reg_filter",
        )
    with filter_cols[3]:
        st.markdown('<div class="filter-label">Sort</div>', unsafe_allow_html=True)
        sort_by = st.selectbox("Sort by", ["Risk ↓", "Risk ↑", "Name A–Z", "Confidence ↓"], label_visibility="collapsed")

    chips = [
        ("Critical / High", "high"),
        ("New Entities", "new"),
        ("Risk Up", "riskup"),
        ("Licensed", "licensed"),
        ("VASP / Crypto", "va"),
    ]
    chip_cols = st.columns(len(chips) + 1)
    for index, (label, key) in enumerate(chips):
        active = st.session_state.active_chip == key
        if chip_cols[index].button(f"{'✓ ' if active else ''}{label}", key=f"chip_{key}", use_container_width=True):
            st.session_state.active_chip = None if active else key
            st.session_state.page = 1
            st.rerun()
    if chip_cols[-1].button("✕ Clear", key="chip_clear", use_container_width=True):
        st.session_state.active_chip = None
        st.session_state.page = 1
        st.rerun()

    active_filters = build_active_filters(
        selected_brand,
        risk_filter,
        reg_filter,
        st.session_state.active_chip,
        risk_label_resolver=lambda value: RISK_META[int(value)]["label"],
        chip_label_resolver=lambda key: dict(chips).get(key, key),
    )
    if active_filters:
        st.markdown('<div class="active-filter-bar">', unsafe_allow_html=True)
        st.markdown(" ".join(f'<span class="filter-chip">{value}</span>' for value in active_filters), unsafe_allow_html=True)
        if st.button(f"Clear all ({len(active_filters)})", key="clear_all_filters"):
            st.session_state.active_chip = None
            st.session_state.risk_filter = []
            st.session_state.reg_filter = []
            st.session_state.page = 1
            if "brand_searchbox" in st.session_state:
                st.session_state["brand_searchbox"] = None
            set_selected_entity(None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="helper-note">Use search plus one or two filters to narrow the review queue quickly.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = apply_filters(df, selected_brand, risk_filter, reg_filter, st.session_state.active_chip, sort_by)
    if filtered.empty:
        st.markdown(
            """
            <div class="empty-state">
              <div class="icon">🔍</div>
              <div class="title">No entities found</div>
              <div class="desc">Try clearing filters, searching by a shorter brand name, or switching to a different run in the sidebar.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        page_df, total_pages = paginate(filtered, st.session_state.page, per_page=25)
        st.session_state.page = min(max(st.session_state.page, 1), total_pages)
        results_col, detail_col = st.columns([1.7, 0.95], vertical_alignment="top")
        with results_col:
            caption_cols = st.columns([3, 1.2])
            caption_cols[0].caption(f'**{len(filtered):,}** of **{len(df):,}** entities')
            caption_cols[1].caption(f'Page **{st.session_state.page}** / **{total_pages}**')
            st.markdown(
                """
                <div class="result-shell">
                  <div class="result-head">
                    <span>Entity</span>
                    <span>Classification</span>
                    <span>Risk / Confidence</span>
                    <span>Register Match</span>
                    <span>Actions</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for _, row in page_df.iterrows():
                render_search_result(row, selected_entity_brand)

        with detail_col:
            if selected_entity_row is not None:
                render_entity_panel(selected_entity_row, closeable=True)
            else:
                st.markdown(
                    f"""
                    <div class="drawer-panel">
                      <div class="section-title">Entity Detail</div>
                      <div style="color:{c['text']};font-size:15px;font-weight:800;margin:6px 0;">Choose a row to inspect it</div>
                      <div style="color:{c['text_muted']};font-size:12px;line-height:1.7;">
                        Click any result card or use the primary <b>Open detail</b> button to pin an entity here. From this panel you can review rationale, open the full dialog, and log workflow actions.
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        pager = st.columns([1, 1, 4, 1, 1])
        if pager[0].button("⏮", use_container_width=True, disabled=st.session_state.page <= 1, key="p_first"):
            st.session_state.page = 1
            st.rerun()
        if pager[1].button("◀", use_container_width=True, disabled=st.session_state.page <= 1, key="p_prev"):
            st.session_state.page -= 1
            st.rerun()
        pager[2].markdown(
            f"<div style='text-align:center;padding-top:0.5rem;color:{c['text_muted']};font-size:12px;'>Page <b style='color:{c['text']}'>{st.session_state.page}</b> of {total_pages}</div>",
            unsafe_allow_html=True,
        )
        if pager[3].button("▶", use_container_width=True, disabled=st.session_state.page >= total_pages, key="p_next"):
            st.session_state.page += 1
            st.rerun()
        if pager[4].button("⏭", use_container_width=True, disabled=st.session_state.page >= total_pages, key="p_last"):
            st.session_state.page = total_pages
            st.rerun()

        csv_bytes, excel_bytes = export_buffers(filtered)
        downloads = st.columns(2)
        downloads[0].download_button(
            "↓ Download CSV",
            data=csv_bytes,
            file_name=f"filtered_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if excel_bytes:
            downloads[1].download_button(
                "↓ Download Excel",
                data=excel_bytes,
                file_name=f"filtered_{pd.Timestamp.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


with tab_insights:
    def axis(label_angle: int = 0, title: str | None = None, grid: bool = False) -> alt.Axis:
        return alt.Axis(
            labelColor=c["text_dim"],
            tickColor="transparent",
            domainColor=c["border"],
            labelFont="DM Sans,sans-serif",
            labelAngle=label_angle,
            title=title,
            gridColor=c["border"] if grid else "transparent",
        )

    def chart_title(title: str, subtitle: str) -> alt.TitleParams:
        return alt.TitleParams(
            title,
            subtitle=[subtitle],
            color=c["text"],
            fontSize=12,
            subtitleColor=c["text_dim"],
            subtitleFontSize=10,
        )

    def horizontal_bar(series: pd.Series, title: str, subtitle: str, color: str) -> None:
        if series.empty:
            st.markdown(
                f'<div class="empty-state"><div class="icon">📊</div><div class="title">{title}</div><div class="desc">No data available</div></div>',
                unsafe_allow_html=True,
            )
            return
        frame = series.reset_index()
        frame.columns = ["label", "value"]
        chart = (
            alt.Chart(frame)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, opacity=0.9)
            .encode(
                y=alt.Y("label:N", sort="-x", axis=axis()),
                x=alt.X("value:Q", axis=axis(title="Count", grid=True)),
                color=alt.value(color),
                tooltip=["label:N", alt.Tooltip("value:Q", title="Count")],
            )
            .properties(height=280, title=chart_title(title, subtitle))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"])
        )
        st.altair_chart(chart, use_container_width=True)

    summary_cards = st.columns(4)
    summary_values = [
        ("Most Common Risk", df["Risk Label"].value_counts().idxmax(), "#E11D48"),
        ("Top Regulator", dominant_value(df, "Regulator Scope", "—"), "#4A7FD4"),
        ("Top Service Type", dominant_value(df, "Service Type", "—"), c["gold"]),
        ("New This Run", f'+{metrics["new_entities"]}', "#22C55E"),
    ]
    for column, (label, value, color_value) in zip(summary_cards, summary_values):
        column.markdown(
            f"""
            <div style="background:{c['card_bg']};border-radius:8px;padding:10px 14px;border:1px solid {c['border']};">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.09em;text-transform:uppercase;margin-bottom:4px;">{label}</div>
              <div style="color:{color_value};font-size:14px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    chart_cols_top = st.columns(2)
    risk_counts = df["Risk Level"].value_counts().reset_index()
    risk_counts.columns = ["level", "count"]
    risk_counts["label"] = risk_counts["level"].map(lambda value: RISK_META[int(value)]["label"])
    with chart_cols_top[0]:
        dominant_risk = risk_counts.sort_values("count", ascending=False).iloc[0]
        st.markdown(
            f'<div class="insight-callout"><strong>{dominant_risk["label"]}</strong> is the dominant risk tier in this run, which helps explain where the team should spend the most review effort.</div>',
            unsafe_allow_html=True,
        )
        risk_chart = (
            alt.Chart(risk_counts)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
            .encode(
                x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"), axis=axis()),
                y=alt.Y("count:Q", axis=axis(title="Entity Count", grid=True)),
                color=alt.Color("label:N", legend=None),
                tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
            )
            .properties(height=240, title=chart_title("Risk Level Distribution", "Entity count per risk category"))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"])
        )
        st.altair_chart(risk_chart, use_container_width=True)
    with chart_cols_top[1]:
        top_regulator_name = dominant_value(df, "Regulator Scope", "—")
        st.markdown(
            f'<div class="insight-callout"><strong>{top_regulator_name}</strong> appears most often in the dataset, so regulator-driven review patterns are concentrated there.</div>',
            unsafe_allow_html=True,
        )
        horizontal_bar(df["Regulator Scope"].value_counts().head(10), "Regulator Scope", "Entities per regulatory body", "#4A7FD4")

    chart_cols_bottom = st.columns(2)
    with chart_cols_bottom[0]:
        top_service_name = dominant_value(df, "Service Type", "—")
        st.markdown(
            f'<div class="insight-callout"><strong>{top_service_name}</strong> is the most common service type in this run, which gives a quick read on where market exposure is clustered.</div>',
            unsafe_allow_html=True,
        )
        horizontal_bar(df["Service Type"].value_counts().head(10), "Service Type Mix", "Top service categories identified", c["gold"])
    with chart_cols_bottom[1]:
        alert_series = df["Alert Status"].replace("", pd.NA).dropna()
        if not alert_series.empty:
            top_alert = alert_series.value_counts().idxmax()
            st.markdown(
                f'<div class="insight-callout"><strong>{top_alert}</strong> is the strongest alert pattern in this run, highlighting the change type most visible against prior screening history.</div>',
                unsafe_allow_html=True,
            )
            horizontal_bar(alert_series.value_counts().head(10), "Alert Status Mix", "Changes detected vs. prior run", "#F97316")
        else:
            st.markdown(
                """
                <div class="empty-state">
                  <div class="icon">📭</div>
                  <div class="title">No Alert Data</div>
                  <div class="desc">Alert Status is not present or empty in this run.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:4px;">Trend Across Runs</div>', unsafe_allow_html=True)
    trend_df = build_trend_dataframe(files, load_screening_data)
    if len(trend_df) >= 2:
        latest_trend = trend_df.iloc[-1]
        st.markdown(
            f'<div class="insight-callout"><strong>{latest_trend["High/Critical"]}</strong> entities currently sit in High/Critical tiers across the latest run, giving a quick historical anchor before you inspect the line chart.</div>',
            unsafe_allow_html=True,
        )
        trend_long = trend_df.melt("Run", var_name="Category", value_name="Count")
        trend_chart = (
            alt.Chart(trend_long)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("Run:N", axis=axis()),
                y=alt.Y("Count:Q", axis=axis(title="Entity Count", grid=True)),
                color=alt.Color("Category:N", legend=alt.Legend(labelColor=c["text_dim"], titleColor=c["text_dim"])),
                tooltip=["Run:N", "Category:N", alt.Tooltip("Count:Q", title="Entities")],
            )
            .properties(height=260, title=chart_title("Risk Trend Across Runs", "Historical view of risk category counts per run"))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"])
        )
        st.altair_chart(trend_chart, use_container_width=True)
    else:
        st.caption(f"Only {len(files)} run archived — trend chart requires 2+ runs.")

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:8px;">Classification Breakdown</div>', unsafe_allow_html=True)
    cls = classification_breakdown(df)
    if not cls.empty:
        st.dataframe(
            cls,
            use_container_width=True,
            hide_index=True,
            column_config={"Count": st.column_config.ProgressColumn("Count", min_value=0, max_value=int(cls["Count"].max()), format="%d")},
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
