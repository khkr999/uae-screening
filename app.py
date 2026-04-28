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


# ── SIDEBAR (with sign out) ───────────────────────────────────────────────────
selected_path = sidebar.render(st.session_state)

# Sign out always renders — independent of sidebar.py auth calls
with st.sidebar:
    st.markdown('---')
    if st.button('⏻  Sign out', use_container_width=True, key='app_signout'):
        st.session_state['current_user'] = ''
        st.rerun()

# ── TOP BAR ───────────────────────────────────────────────────────────────────
top_bar(run_label=now_label(), live=True)

# ── No file loaded ────────────────────────────────────────────────────────────
if selected_path is None:
    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if auth.is_owner(st.session_state):
            st.markdown(
                '<div style="background:var(--card);border:1px solid var(--border);'
                'border-radius:14px;padding:40px 32px;text-align:center;">'
                '<div style="font-size:40px;margin-bottom:16px;">📂</div>'
                '<div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;">'
                'No screening file loaded</div>'
                '<div style="font-size:13px;color:var(--muted);margin-bottom:24px;">'
                'Upload a <code style="background:rgba(201,168,76,0.10);color:var(--accent);'
                'padding:2px 6px;border-radius:4px;">UAE_Screening_*.xlsx</code> file to begin'
                '</div></div>',
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
                f'<div style="background:var(--card);border:1px solid var(--border);'
                f'border-radius:14px;padding:40px 32px;text-align:center;">'
                f'<div style="font-size:40px;margin-bottom:16px;">⏳</div>'
                f'<div style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;">'
                f'Welcome, {user}</div>'
                f'<div style="font-size:13px;color:var(--muted);">'
                f'Ask an owner to upload a screening file.</div>'
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

# ── Review Queue tab badge ────────────────────────────────────────────────────
review_stats = state.get_review_stats(st.session_state)
pending      = sum(review_stats.get(s, 0) for s in ("Open", "In Review", "Escalated"))
queue_label  = f"📋 Review Queue ({pending})" if pending else "📋 Review Queue"

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📊 Overview", "🔎 Search & Filter", "📈 Insights", queue_label])
with tabs[0]: overview.render(df, metrics, st.session_state)
with tabs[1]: search.render(df, st.session_state)
with tabs[2]: insights.render(df)
with tabs[3]: review_queue.render(df, st.session_state)

# ── Detail drawer ─────────────────────────────────────────────────────────────
drawer.render(df, st.session_state)

st.markdown(
    '<div style="text-align:center;color:var(--muted);font-size:11px;'
    'padding:24px 0 8px 0;">'
    'Internal screening tool &nbsp;·&nbsp; not a legal determination &nbsp;·&nbsp; '
    'Data refreshed every screening run.</div>',
    unsafe_allow_html=True,
)
