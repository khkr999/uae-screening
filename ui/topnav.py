"""Top navigation bar — brand, tabs, live indicator, theme toggle, run selector."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

import services
import state
import auth


def render(session, df_loaded: bool = False) -> tuple[str, Path | None]:
    """Render the top nav bar. Returns (active_tab_key, selected_run_path)."""

    # Get available runs
    runs = services.list_runs()

    # Determine current tab
    active_tab = session.get("active_tab", "overview")

    # ── Container ─────────────────────────────────────────────────────────────
    cols = st.columns([0.18, 0.42, 0.40])

    # Left: brand
    with cols[0]:
        st.markdown(
            f'<div class="uae-brand">'
            f'<div class="uae-brand-logo">🛡</div>'
            f'<div>'
            f'<div class="uae-brand-name">UAE Screening</div>'
            f'<div class="uae-brand-sub">Risk Monitoring</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # Middle: tab buttons
    with cols[1]:
        tab_cols = st.columns(4)
        tabs = [
            ("overview", "📊 Overview"),
            ("search",   "🔎 Search & Filter"),
            ("insights", "📈 Insights"),
            ("review",   "📋 Review Queue"),
        ]
        for i, (key, label) in enumerate(tabs):
            with tab_cols[i]:
                is_active = (active_tab == key)
                btn_label = ("● " + label) if is_active else label
                if st.button(btn_label, key=f"nav_{key}", use_container_width=True):
                    session["active_tab"] = key
                    st.rerun()

    # Right: live indicator + run + theme
    with cols[2]:
        right_cols = st.columns([1, 2, 0.7, 0.7])

        with right_cols[0]:
            st.markdown(
                '<div style="padding-top:8px;text-align:center;">'
                '<span class="uae-live"><span class="uae-live-dot"></span>LIVE</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        with right_cols[1]:
            # Run selector dropdown
            if runs:
                opts = {r.timestamp.strftime("%Y-%m-%d %H:%M"): r.path for r in runs}
                choice = st.selectbox(
                    "Run", options=list(opts.keys()),
                    key="topnav_run_select",
                    label_visibility="collapsed",
                )
                selected_path = opts[choice]
            else:
                st.markdown(
                    '<div style="padding-top:8px;font-size:11px;color:var(--muted);'
                    'text-align:center;font-family:\'JetBrains Mono\',monospace;">No runs</div>',
                    unsafe_allow_html=True,
                )
                selected_path = None

        with right_cols[2]:
            # Theme toggle
            is_dark = session.get("theme", "dark") == "dark"
            icon    = "☀" if is_dark else "☾"
            if st.button(icon, key="topnav_theme",
                         use_container_width=True,
                         help="Toggle theme"):
                state.toggle_theme(session)
                st.rerun()

        with right_cols[3]:
            # Sign out
            if st.button("⏻", key="topnav_signout",
                         use_container_width=True,
                         help="Sign out"):
                session["current_user"] = ""
                st.rerun()

    return active_tab, selected_path


def render_user_strip(session) -> None:
    """A small strip showing logged-in user info under the top nav."""
    user = auth.current_user(session)
    is_owner = auth.is_owner(session)
    role = "Owner" if is_owner else "Analyst"
    role_color = "#E5B547" if is_owner else "#3B82F6"

    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;align-items:center;gap:10px;'
        f'padding:0 8px 12px 0;font-size:11px;color:var(--muted);'
        f'font-family:\'JetBrains Mono\',monospace;">'
        f'Signed in as <b style="color:var(--text);font-weight:600;">{user}</b>'
        f' · <span style="color:{role_color};font-weight:700;">{role}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
