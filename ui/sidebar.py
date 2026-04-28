"""Sidebar: run selection, upload (owners only), theme toggle, user identity."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from exceptions import DataLoadError
import services
import state
import auth
from ui.components import empty_state


def render(session) -> Path | None:
    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────────────────
        st.markdown(
            '<div style="padding:8px 0 16px 0;">'
            '<div style="font-size:15px;font-weight:700;color:var(--text);">'
            '🛡️ UAE Screening</div>'
            '<div style="font-size:10px;color:var(--muted);letter-spacing:0.1em;'
            'text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;margin-top:2px;">'
            'Risk Monitoring Platform</div></div>',
            unsafe_allow_html=True,
        )
        _div()

        # ── Logged-in user ─────────────────────────────────────────────────────
        user    = auth.current_user(session)
        is_own  = auth.is_owner(session)
        role_lbl = "Owner" if is_own else "Analyst"
        role_col = "#C9A84C" if is_own else "#3DA5E0"

        # Avatar + name + role
        avatar_letter = user[0].upper() if user else "?"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:10px 12px;background:var(--card);border:1px solid var(--border);'
            f'border-radius:10px;margin-bottom:4px;">'
            f'<span style="width:32px;height:32px;border-radius:999px;'
            f'background:rgba(201,168,76,0.15);border:1.5px solid #C9A84C40;'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'font-size:14px;font-weight:800;color:#C9A84C;">{avatar_letter}</span>'
            f'<div>'
            f'<div style="font-size:13px;font-weight:700;color:var(--text);">{user}</div>'
            f'<div style="font-size:10px;font-weight:600;color:{role_col};'
            f'font-family:\'IBM Plex Mono\',monospace;">{role_lbl}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


        _div()

        # ── Theme toggle ───────────────────────────────────────────────────────
        is_dark = session.get("theme", "dark") == "dark"
        if st.button("☀  Light Mode" if is_dark else "☾  Dark Mode",
                     use_container_width=True, key="sidebar_theme_toggle"):
            state.toggle_theme(session)
            st.rerun()


        _div()

        # ── Screening run selector ─────────────────────────────────────────────
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
            choice  = st.selectbox(
                "Pick a run", list(options.keys()),
                index=0, label_visibility="collapsed",
                key="sidebar_run_select",
            )
            selected_path = options[choice]
        else:
            if is_own:
                empty_state("No screening files",
                            "Upload a UAE_Screening_*.xlsx below.")
            else:
                empty_state("No screening files",
                            "Ask an owner to upload a screening run.")

        _div()

        # ── Upload — OWNERS ONLY ───────────────────────────────────────────────
        if is_own:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;color:var(--muted);'
                'letter-spacing:0.1em;text-transform:uppercase;'
                'font-family:\'IBM Plex Mono\',monospace;margin-bottom:8px;">Upload Run</div>',
                unsafe_allow_html=True,
            )
            _upload(session)
            _div()
        else:
            # Non-owners see a friendly message instead
            st.markdown(
                '<div style="font-size:11px;color:var(--muted);padding:6px 0;">'
                '📁 File uploads are restricted to owners.</div>',
                unsafe_allow_html=True,
            )
            _div()

        # ── Footer ─────────────────────────────────────────────────────────────
        runs_count = len(runs) if runs else 0
        st.markdown(
            f'<div style="font-size:10px;color:var(--muted);'
            f'font-family:\'IBM Plex Mono\',monospace;line-height:1.8;">'
            f'<div>Runs archived: <span style="color:var(--dim);font-weight:600;">'
            f'{runs_count}</span></div>'
            # Only show data path to owners
            + (f'<div style="margin-top:4px;word-break:break-all;font-size:9px;">'
               f'</div>' if not is_own else '')
            + f'<div style="margin-top:8px;">Internal tool · not a legal determination.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    return selected_path


def _div() -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:14px 0;"></div>',
        unsafe_allow_html=True,
    )


def _upload(session) -> None:
    nonce    = session.get("file_upload_nonce", 0)
    uploaded = st.file_uploader(
        "Drop file here", type=["xlsx"],
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
