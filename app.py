"""
UAE Regulatory Screening — Streamlit entry point.

This file only wires modules together. All logic lives in:
    - config.py         constants, rules, theme
    - models.py         typed domain objects
    - data_loader.py    ingestion, validation, normalization
    - classification.py rule-based risk engine
    - processing.py     pure pandas transforms (filter, metrics, aggs)
    - services.py       orchestration (UI/API-agnostic)
    - state.py          session-state helpers
    - ui/               presentation components

Run with:  streamlit run app.py
"""
from __future__ import annotations

import logging

import streamlit as st

from exceptions import DataLoadError, ValidationError
import services
import state
import ui.drawer as drawer
import ui.insights as insights
import ui.overview as overview
import ui.search as search
import ui.sidebar as sidebar
from ui.components import error_state, empty_state, now_label, top_bar
from ui.theme import current_theme, inject_css


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
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

state.init_state(st.session_state)
inject_css(current_theme(st.session_state))


# ---------------------------------------------------------------------------
# Streamlit-level caching of expensive data ops.
# `hash_funcs` on DataFrames is avoided — services.load_run is already
# cached inside data_loader via a file-signature key.
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading screening data…")
def _cached_load(path_str: str, run_classifier: bool):
    return services.load_run(path_str, run_classifier=run_classifier)


@st.cache_data(show_spinner=False)
def _cached_previous(path_str: str):
    runs = services.list_runs()
    from pathlib import Path as _P
    return services.load_previous_df(runs, _P(path_str))


# ---------------------------------------------------------------------------
# Sidebar (selection + upload)
# ---------------------------------------------------------------------------
selected_path = sidebar.render(st.session_state)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
top_bar(run_label=now_label(), live=True)


# ---------------------------------------------------------------------------
# Main body
# ---------------------------------------------------------------------------
if selected_path is None:
    empty_state(
        "No screening file loaded",
        "Upload a UAE_Screening_*.xlsx file in the sidebar to get started.",
        icon="📭",
    )
    st.stop()


try:
    df = _cached_load(str(selected_path), run_classifier=False)
except DataLoadError as exc:
    error_state("Failed to load the file", exc.user_message)
    st.stop()
except ValidationError as exc:
    error_state("File is not valid", exc.user_message)
    st.stop()
except Exception as exc:  # pragma: no cover — last-resort safety net
    logger.exception("Unexpected error loading %s", selected_path)
    error_state("Unexpected error", str(exc))
    st.stop()


if df.empty:
    empty_state("Empty dataset",
                "This file contains no rows after validation. "
                "Try another run or upload a fresh export.")
    st.stop()


previous_df = _cached_previous(str(selected_path))
metrics = services.get_metrics(df, previous=previous_df)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_labels = {
    "overview": f"📊 Overview",
    "search":   f"🔎 Search & Filter",
    "insights": f"📈 Insights",
}

tabs = st.tabs(list(tab_labels.values()))

with tabs[0]:
    overview.render(df, metrics, st.session_state)

with tabs[1]:
    search.render(df, st.session_state)

with tabs[2]:
    insights.render(df)


# ---------------------------------------------------------------------------
# Drawer (if an entity is selected)
# ---------------------------------------------------------------------------
drawer.render(df, st.session_state)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div style="text-align:center;color:var(--muted);font-size:11px;'
    'padding:24px 0 8px 0;">'
    'Internal screening tool · not a legal determination · '
    'Data refreshed every screening run.'
    '</div>',
    unsafe_allow_html=True,
)
