from __future__ import annotations
import streamlit as st
from config import THEMES, Theme

def current_theme(session) -> Theme:
    return THEMES.get(session.get("theme", "dark"), THEMES["dark"])

def inject_css(theme: Theme) -> None:
    st.markdown(f"""
        <style>
        :root {{
            --bg: {theme.app_bg}; --card: {theme.card_bg};
            --text: {theme.text}; --dim: {theme.text_dim};
            --muted: {theme.text_muted}; --border: {theme.border};
            --accent: {theme.accent}; --accent-soft: {theme.accent_soft};
        }}
        html, body, [data-testid="stAppViewContainer"] {{ background: var(--bg) !important; color: var(--text); }}
        [data-testid="stSidebar"] > div:first-child {{ background: var(--card); border-right: 1px solid var(--border); }}
        .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}
        .uae-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
        .uae-card.subtle {{ padding: 14px 16px; }}
        .uae-kpi-label {{ color: var(--dim); font-size: 12px; font-weight: 600; }}
        .uae-kpi-value {{ color: var(--text); font-size: 28px; font-weight: 800; line-height: 1.1; margin-top: 4px; }}
        .uae-kpi-hint {{ color: var(--muted); font-size: 11px; margin-top: 6px; }}
        .uae-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; border: 1px solid transparent; }}
        .uae-topbar {{ display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-radius: 14px; background: var(--card); border: 1px solid var(--border); margin-bottom: 14px; }}
        .uae-topbar h1 {{ font-size: 18px; font-weight: 800; color: var(--text); margin: 0; }}
        .uae-topbar .sub {{ font-size: 11px; color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase; }}
        .uae-live {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: rgba(80,200,138,0.12); color: #50C88A; font-size: 11px; font-weight: 700; }}
        .uae-live-dot {{ width: 6px; height: 6px; border-radius: 999px; background: #50C88A; box-shadow: 0 0 0 3px rgba(80,200,138,0.2); }}
        .stButton > button {{ border-radius: 10px; border: 1px solid var(--border); font-weight: 600; }}
        [data-testid="stDataFrame"] {{ border: 1px solid var(--border); border-radius: 12px; }}
        footer, header {{ visibility: hidden; }}
        </style>""", unsafe_allow_html=True)
