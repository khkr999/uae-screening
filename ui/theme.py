from __future__ import annotations
import streamlit as st
from config import THEMES, Theme

def current_theme(session) -> Theme:
    return THEMES.get(session.get("theme", "dark"), THEMES["dark"])

def inject_css(theme: Theme) -> None:
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

        :root {{
            --bg: #0A0E1A;
            --bg-secondary: #0F172A;
            --card: #111827;
            --card-hover: #161E2E;
            --border: #1F2937;
            --border-light: #2D3748;
            --text: #E5E7EB;
            --dim: #9CA3AF;
            --muted: #6B7280;
            --accent: #C9A84C;
            --accent-soft: rgba(201,168,76,0.10);
            --radius: 12px;
            --radius-sm: 8px;
        }}

        *, *::before, *::after {{ box-sizing: border-box; }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: var(--bg) !important;
            color: var(--text);
            font-family: 'IBM Plex Sans', sans-serif;
        }}
        [data-testid="stAppViewContainer"] > .main {{ background: var(--bg) !important; }}
        [data-testid="stSidebar"] > div:first-child {{
            background: var(--card) !important;
            border-right: 1px solid var(--border);
        }}
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 1400px !important;
        }}

        /* TOPBAR */
        .uae-topbar {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 20px; border-radius: var(--radius);
            background: var(--card); border: 1px solid var(--border);
            margin-bottom: 16px; position: relative; overflow: hidden;
        }}
        .uae-topbar::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, #C9A84C 0%, #3DA5E0 50%, #34D399 100%);
        }}
        .uae-topbar h1 {{
            font-size: 16px; font-weight: 700; color: var(--text); margin: 0; letter-spacing: 0.02em;
        }}
        .uae-topbar .sub {{
            font-size: 10px; color: var(--muted); letter-spacing: 0.12em;
            text-transform: uppercase; margin-top: 2px; font-family: 'IBM Plex Mono', monospace;
        }}

        /* LIVE BADGE */
        .uae-live {{
            display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px;
            border-radius: 999px; background: rgba(52,211,153,0.08);
            border: 1px solid rgba(52,211,153,0.25); color: #34D399;
            font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
            font-family: 'IBM Plex Mono', monospace;
        }}
        .uae-live-dot {{
            width: 6px; height: 6px; border-radius: 999px; background: #34D399;
            box-shadow: 0 0 0 3px rgba(52,211,153,0.2);
            animation: pulsedot 2s infinite;
        }}
        @keyframes pulsedot {{
            0%,100% {{ box-shadow: 0 0 0 3px rgba(52,211,153,0.2); }}
            50% {{ box-shadow: 0 0 0 6px rgba(52,211,153,0.04); }}
        }}

        /* CARDS */
        .uae-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 18px 20px;
            transition: border-color 0.2s, background 0.2s;
        }}
        .uae-card:hover {{ border-color: var(--border-light); background: var(--card-hover); }}
        .uae-card.subtle {{ padding: 14px 16px; }}
        .uae-card.nohover:hover {{ border-color: var(--border); background: var(--card); }}

        /* KPI */
        .uae-kpi-label {{
            color: var(--muted); font-size: 10px; font-weight: 700;
            letter-spacing: 0.1em; text-transform: uppercase;
            font-family: 'IBM Plex Mono', monospace;
        }}
        .uae-kpi-value {{
            color: var(--text); font-size: 30px; font-weight: 700;
            line-height: 1; margin-top: 6px; font-family: 'IBM Plex Mono', monospace;
            letter-spacing: -0.02em;
        }}
        .uae-kpi-hint {{
            color: var(--muted); font-size: 10px; margin-top: 6px;
            font-family: 'IBM Plex Mono', monospace;
        }}

        /* BADGE */
        .uae-badge {{
            display: inline-flex; align-items: center; gap: 5px;
            padding: 3px 10px; border-radius: 999px; font-size: 10px;
            font-weight: 700; border: 1px solid transparent;
            letter-spacing: 0.06em; font-family: 'IBM Plex Mono', monospace; white-space: nowrap;
        }}

        /* SECTION HEADER */
        .uae-sec-title {{
            font-size: 11px; font-weight: 700; color: var(--dim);
            letter-spacing: 0.12em; text-transform: uppercase;
            font-family: 'IBM Plex Mono', monospace; margin-bottom: 2px;
        }}
        .uae-sec-sub {{ font-size: 11px; color: var(--muted); margin-bottom: 12px; }}

        /* ENTITY CARD */
        .uae-entity-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 16px; margin-bottom: 10px;
            transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
        }}
        .uae-entity-card:hover {{
            border-color: var(--border-light); transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .uae-entity-brand {{ font-size: 14px; font-weight: 700; color: var(--text); }}
        .uae-entity-meta {{
            font-size: 11px; color: var(--dim); margin-top: 2px;
            font-family: 'IBM Plex Mono', monospace;
        }}
        .uae-entity-rationale {{
            font-size: 11px; color: var(--muted); margin-top: 10px;
            line-height: 1.55; border-top: 1px solid var(--border); padding-top: 8px;
        }}
        .uae-action-label {{
            display: inline-block; font-size: 9px; font-weight: 700;
            letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent);
            background: var(--accent-soft); border-radius: 4px; padding: 2px 7px;
            margin-top: 8px; font-family: 'IBM Plex Mono', monospace;
        }}

        /* SUMMARY ROW */
        .uae-sum-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 9px 0; border-bottom: 1px solid var(--border);
        }}
        .uae-sum-row:last-child {{ border-bottom: none; }}
        .uae-sum-label {{ color: var(--muted); font-size: 11px; font-family: 'IBM Plex Mono', monospace; }}
        .uae-sum-value {{ color: var(--text); font-size: 12px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }}

        /* RISK BAR */
        .uae-bar-row {{ display: flex; align-items: center; gap: 10px; margin: 5px 0; }}
        .uae-bar-label {{
            width: 80px; font-size: 9px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.08em; color: var(--muted); font-family: 'IBM Plex Mono', monospace; text-align: right;
        }}
        .uae-bar-track {{
            flex: 1; height: 6px; border-radius: 999px; background: rgba(255,255,255,0.05); overflow: hidden;
        }}
        .uae-bar-fill {{ height: 100%; border-radius: 999px; }}
        .uae-bar-count {{
            width: 28px; text-align: right; font-size: 11px; font-weight: 700;
            color: var(--text); font-family: 'IBM Plex Mono', monospace;
        }}

        /* EMPTY */
        .uae-empty {{
            text-align: center; padding: 40px 20px; background: var(--card);
            border: 1px solid var(--border); border-radius: var(--radius);
        }}
        .uae-empty-icon {{ font-size: 28px; margin-bottom: 10px; }}
        .uae-empty-title {{ font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 4px; }}
        .uae-empty-desc {{ font-size: 12px; color: var(--muted); }}

        /* BUTTONS */
        .stButton > button {{
            border-radius: var(--radius-sm) !important;
            border: 1px solid var(--border) !important;
            background: var(--card) !important;
            color: var(--dim) !important;
            font-weight: 600 !important; font-size: 12px !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            transition: all 0.15s !important;
        }}
        .stButton > button:hover {{
            border-color: var(--border-light) !important;
            color: var(--text) !important; background: var(--card-hover) !important;
        }}

        /* TABS */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background: transparent !important; border-bottom: 1px solid var(--border) !important;
            gap: 0 !important; padding: 0 !important; margin-bottom: 20px !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            background: transparent !important; border: none !important;
            border-bottom: 2px solid transparent !important; color: var(--muted) !important;
            font-weight: 600 !important; font-size: 11px !important;
            letter-spacing: 0.1em !important; text-transform: uppercase !important;
            padding: 10px 20px !important; font-family: 'IBM Plex Mono', monospace !important;
            transition: color 0.15s !important;
        }}
        [data-testid="stTabs"] [aria-selected="true"] {{
            color: var(--accent) !important; border-bottom-color: var(--accent) !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ display: none !important; }}

        /* DATAFRAME */
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--border) !important; border-radius: var(--radius) !important; overflow: hidden !important;
        }}

        /* INPUTS */
        [data-testid="stTextInput"] input {{
            background: var(--card) !important; border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important; color: var(--text) !important;
            font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px !important;
        }}
        [data-testid="stTextInput"] input:focus {{
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px rgba(201,168,76,0.15) !important;
        }}

        /* SIDEBAR */
        [data-testid="stSidebar"] .stButton > button {{ width: 100% !important; }}

        /* METRICS */
        [data-testid="stMetric"] {{
            background: var(--card) !important; border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important; padding: 12px 16px !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: var(--muted) !important; font-size: 10px !important; font-weight: 700 !important;
            letter-spacing: 0.08em !important; text-transform: uppercase !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }}
        [data-testid="stMetricValue"] {{
            color: var(--text) !important; font-size: 22px !important; font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* EXPANDER */
        [data-testid="stExpander"] {{
            background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
        }}
        [data-testid="stExpander"] summary {{
            font-size: 13px !important; font-weight: 600 !important; color: var(--text) !important;
        }}

        /* DOWNLOAD */
        [data-testid="stDownloadButton"] > button {{
            border-radius: var(--radius-sm) !important; border: 1px solid var(--border) !important;
            background: var(--card) !important; color: var(--dim) !important; font-weight: 600 !important; font-size: 12px !important;
        }}
        [data-testid="stDownloadButton"] > button:hover {{
            border-color: var(--accent) !important; color: var(--accent) !important;
        }}

        /* SUCCESS/INFO */
        [data-testid="stSuccess"] {{
            background: rgba(5,150,105,0.08) !important; border: 1px solid rgba(5,150,105,0.25) !important;
            border-radius: var(--radius-sm) !important; color: #34D399 !important; font-size: 12px !important;
        }}
        [data-testid="stInfo"] {{
            background: rgba(37,99,235,0.08) !important; border: 1px solid rgba(37,99,235,0.2) !important;
            border-radius: var(--radius-sm) !important; color: var(--dim) !important; font-size: 12px !important;
        }}

        /* MISC */
        hr {{ border-color: var(--border) !important; margin: 12px 0 !important; }}
        footer, header {{ visibility: hidden !important; }}
        #MainMenu {{ visibility: hidden !important; }}
        [data-testid="stDeployButton"] {{ display: none !important; }}
        ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 3px; }}
        </style>
    """, unsafe_allow_html=True)
