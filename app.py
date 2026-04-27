from __future__ import annotations
import logging, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import streamlit as st
from exceptions import DataLoadError, ValidationError
import services, state
import ui.drawer as drawer
import ui.insights as insights
import ui.overview as overview
import ui.search as search
import ui.sidebar as sidebar
import ui.review_queue as review_queue
from ui.components import error_state, empty_state, now_label, top_bar
from ui.theme import current_theme, inject_css

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uae_screening.app")

st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

state.init_state(st.session_state)
inject_css(current_theme(st.session_state))


@st.cache_data(show_spinner="Loading screening data…")
def _cached_load(path_str, run_classifier):
    return services.load_run(path_str, run_classifier=run_classifier)


@st.cache_data(show_spinner=False)
def _cached_previous(path_str):
    from pathlib import Path as _P
    return services.load_previous_df(services.list_runs(), _P(path_str))


selected_path = sidebar.render(st.session_state)
top_bar(run_label=now_label(), live=True)

if selected_path is None:
    empty_state("No screening file loaded",
                "Upload a UAE_Screening_*.xlsx file in the sidebar.", icon="📭")
    st.stop()

try:
    df = _cached_load(str(selected_path), run_classifier=False)
except DataLoadError as exc:
    error_state("Failed to load the file", exc.user_message); st.stop()
except ValidationError as exc:
    error_state("File is not valid", exc.user_message); st.stop()
except Exception as exc:
    logger.exception("Unexpected error")
    error_state("Unexpected error", str(exc)); st.stop()

if df.empty:
    empty_state("Empty dataset", "No rows after validation."); st.stop()

previous_df = _cached_previous(str(selected_path))
metrics     = services.get_metrics(df, previous=previous_df)

# ── Review Queue badge count ──────────────────────────────────────────────────
review_stats  = state.get_review_stats(st.session_state)
pending_count = review_stats.get("Open", 0) + review_stats.get("In Review", 0) + review_stats.get("Escalated", 0)
queue_label   = f"📋 Review Queue ({pending_count})" if pending_count else "📋 Review Queue"

tabs = st.tabs(["📊 Overview", "🔎 Search & Filter", "📈 Insights", queue_label])

with tabs[0]: overview.render(df, metrics, st.session_state)
with tabs[1]: search.render(df, st.session_state)
with tabs[2]: insights.render(df)
with tabs[3]: review_queue.render(df, st.session_state)

drawer.render(df, st.session_state)

st.markdown(
    '<div style="text-align:center;color:var(--muted);font-size:11px;'
    'padding:24px 0 8px 0;">'
    'Internal screening tool &nbsp;·&nbsp; not a legal determination &nbsp;·&nbsp; '
    'Data refreshed every screening run.</div>',
    unsafe_allow_html=True,
)
