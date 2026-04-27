"""Sidebar: run selection, upload, theme toggle."""
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
        st.markdown(
            '<div style="padding:8px 0 16px 0;">'
            '<div style="font-size:15px;font-weight:700;color:var(--text);letter-spacing:0.02em;">'
            '🛡️ UAE Screening</div>'
            '<div style="font-size:10px;color:var(--muted);letter-spacing:0.1em;'
            'text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;margin-top:2px;">'
            'Risk Monitoring Platform</div></div>',
            unsafe_allow_html=True,
        )

        _divider()

        # ── THEME TOGGLE ──
        is_dark = session.get("theme", "dark") == "dark"
        theme_label = "☀  Light Mode" if is_dark else "☾  Dark Mode"
        if st.button(theme_label, use_container_width=True, key="sidebar_theme_toggle"):
            state.toggle_theme(session)
            st.rerun()

        _divider()

        # ── RUN SELECTOR ──
        st.markdown(
            '<div style="font-size:10px;font-weight:700;color:var(--muted);'
            'letter-spacing:0.1em;text-transform:uppercase;'
            'font-family:\'IBM Plex Mono\',monospace;margin-bottom:8px;">Screening Run</div>',
            unsafe_allow_html=True,
        )

        runs = services.list_runs()
        selected_path: Path | None = None

        if runs:
            options = {r.display_label(): r.path for r in runs}
            choice = st.selectbox(
                "Pick a run",
                list(options.keys()),
                index=0,
                label_visibility="collapsed",
                key="sidebar_run_select",
            )
            selected_path = options[choice]
        else:
            empty_state("No screening files", "Upload a UAE_Screening_*.xlsx to begin.")

        _divider()

        # ── UPLOAD ──
        _render_upload(session)

        _divider()

        # ── FOOTER ──
        runs_count = len(runs) if runs else 0
        st.markdown(
            f'<div style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;line-height:1.8;">'
            f'<div>Runs archived: <span style="color:var(--dim);font-weight:600;">{runs_count}</span></div>'
            f'<div style="margin-top:4px;word-break:break-all;font-size:9px;">{DATA_DIR}</div>'
            f'<div style="margin-top:8px;">Internal tool · not a legal determination.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    return selected_path


def _divider() -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:14px 0;"></div>',
        unsafe_allow_html=True,
    )


def _render_upload(session) -> None:
    st.markdown(
        '<div style="font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;'
        'font-family:\'IBM Plex Mono\',monospace;margin-bottom:8px;">Upload Run</div>',
        unsafe_allow_html=True,
    )
    nonce = session.get("file_upload_nonce", 0)
    uploaded = st.file_uploader(
        "Drop file here",
        type=["xlsx"],
        label_visibility="collapsed",
        key=f"sidebar_uploader_{nonce}",
    )
    if uploaded is not None:
        try:
            dest = services.save_upload(uploaded)
            st.success(f"✓ Saved: {dest.name}")
            session["file_upload_nonce"] = nonce + 1
            st.rerun()
        except DataLoadError as exc:
            st.error(exc.user_message)
