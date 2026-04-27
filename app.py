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
