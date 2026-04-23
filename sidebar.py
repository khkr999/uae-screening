from __future__ import annotations
from pathlib import Path
import streamlit as st
from config import DATA_DIR
from exceptions import DataLoadError
import services
import state
from ui.components import empty_state

def render(session) -> Path | None:
    with st.sidebar:
        st.markdown("### 🛡️ UAE Screening")
        st.caption("Risk monitoring platform")
        theme_label = "☀ Light Mode" if session.get("theme") == "dark" else "☾ Dark Mode"
        if st.button(theme_label, use_container_width=True, key="sidebar_theme_toggle"):
            state.toggle_theme(session)
            st.rerun()
        st.divider()
        st.markdown("**Screening Run**")
        runs = services.list_runs()
        selected_path = None
        if runs:
            options = {r.display_label(): r.path for r in runs}
            choice = st.selectbox("Pick a run", list(options.keys()), index=0, label_visibility="collapsed", key="sidebar_run_select")
            selected_path = options[choice]
        else:
            empty_state("No screening files", "Upload a UAE_Screening_*.xlsx to begin.")
        st.divider()
        _render_upload(session)
        st.divider()
        st.caption(f"Runs archived: **{len(runs)}**")
        st.caption(f"`{DATA_DIR}`")
        st.caption("Internal tool · not a legal determination.")
    return selected_path

def _render_upload(session) -> None:
    st.markdown("**Upload a run**")
    nonce = session.get("file_upload_nonce", 0)
    uploaded = st.file_uploader("Drop a UAE_Screening_*.xlsx here", type=["xlsx"], label_visibility="collapsed", key=f"sidebar_uploader_{nonce}")
    if uploaded is not None:
        try:
            dest = services.save_upload(uploaded)
            st.success(f"Saved: {dest.name}")
            session["file_upload_nonce"] = nonce + 1
            st.rerun()
        except DataLoadError as exc:
            st.error(exc.user_message)
