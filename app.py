from __future__ import annotations
import logging, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import streamlit as st
from exceptions import DataLoadError, ValidationError
import services, state, auth
import ui.drawer as drawer
import ui.insights as insights
import ui.overview as overview
import ui.search as search
import ui.review_queue as review_queue
import ui.topnav as topnav
from ui.components import error_state, empty_state
from ui.theme import current_theme, inject_css

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uae_screening.app")

st.set_page_config(
    page_title="UAE Screening · Risk Monitoring",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state(st.session_state)

# ── LOGIN GATE ────────────────────────────────────────────────────────────────
if not auth.is_logged_in(st.session_state):
    auth.render_login(st.session_state)
    st.stop()

# ── Inject theme ──────────────────────────────────────────────────────────────
inject_css(current_theme(st.session_state))


@st.cache_data(show_spinner="Loading screening data…")
def _cached_load(path_str, run_classifier):
    return services.load_run(path_str, run_classifier=run_classifier)


@st.cache_data(show_spinner=False)
def _cached_previous(path_str):
    from pathlib import Path as _P
    return services.load_previous_df(services.list_runs(), _P(path_str))


# ── TOP NAVIGATION ────────────────────────────────────────────────────────────
active_tab, selected_path = topnav.render(st.session_state)
topnav.render_user_strip(st.session_state)

# ── No file loaded ────────────────────────────────────────────────────────────
if selected_path is None:
    st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if auth.is_owner(st.session_state):
            st.markdown(
                '<div class="uae-empty">'
                '<div class="uae-empty-icon">📂</div>'
                '<div class="uae-empty-title">No screening file loaded</div>'
                '<div class="uae-empty-desc">Upload a UAE_Screening_*.xlsx file to begin</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            nonce = st.session_state.get("main_upload_nonce", 0)
            uploaded = st.file_uploader(
                "Upload screening file", type=["xlsx"],
                label_visibility="collapsed",
                key=f"main_uploader_{nonce}",
            )
            if uploaded is not None:
                try:
                    dest = services.save_upload(uploaded)
                    st.success(f"✓ Saved: {dest.name} — reloading…")
                    st.session_state["main_upload_nonce"] = nonce + 1
                    st.rerun()
                except DataLoadError as exc:
                    st.error(exc.user_message)
        else:
            user = auth.current_user(st.session_state)
            st.markdown(
                f'<div class="uae-empty">'
                f'<div class="uae-empty-icon">⏳</div>'
                f'<div class="uae-empty-title">Welcome, {user}</div>'
                f'<div class="uae-empty-desc">Ask an owner to upload a screening file.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
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

# ── Tab routing (using session state, not Streamlit tabs) ─────────────────────
if active_tab == "overview":
    overview.render(df, metrics, st.session_state)
elif active_tab == "search":
    search.render(df, st.session_state)
elif active_tab == "insights":
    insights.render(df)
elif active_tab == "review":
    review_queue.render(df, st.session_state)

# ── Detail drawer (conditional render) ────────────────────────────────────────
drawer.render(df, st.session_state)

# ── Footer ────────────────────────────────────────────────────────────────────
from html import escape as _esc
file_label = _esc(selected_path.name) if selected_path else ""
st.markdown(
    f'<div class="uae-footer">'
    f'<span>Internal tool — for monitoring and review support only, not a legal determination</span>'
    f'<span>{file_label} · {len(df)} entities</span>'
    f'</div>',
    unsafe_allow_html=True,
)
