"""User authentication — name-based login gate with owner privileges."""
from __future__ import annotations

import streamlit as st

# ── Owner list — only these names can upload files and manage runs ────────────
# Add or remove names as needed (case-insensitive match)
OWNERS: frozenset[str] = frozenset({
    "khalil",
    "khkr999",
})

# ── Known team members (optional — for display/autocomplete) ─────────────────
TEAM_MEMBERS: list[str] = [
    "Khalil",
    # Add your colleagues' names here
]


def is_owner(session) -> bool:
    """Return True if the logged-in user has owner privileges."""
    name = session.get("current_user", "")
    return name.lower().strip() in OWNERS


def current_user(session) -> str:
    """Return the current user's display name."""
    return session.get("current_user", "")


def is_logged_in(session) -> bool:
    """Return True if user has completed the login step."""
    return bool(session.get("current_user", "").strip())


def render_login(session) -> None:
    """Render the full-screen login gate. Blocks app until name is entered."""
    # Inject minimal CSS needed before full theme loads
    st.markdown("""
        <style>
        html,body,[data-testid="stAppViewContainer"]{background:#0F172A!important;}
        .block-container{max-width:480px!important;margin:auto;padding-top:8vh!important;}
        footer,header{visibility:hidden!important;}
        #MainMenu{visibility:hidden!important;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="text-align:center;margin-bottom:32px;">'
        '<div style="font-size:40px;margin-bottom:12px;">🛡️</div>'
        '<div style="font-size:22px;font-weight:800;color:#E5E7EB;margin-bottom:6px;">'
        'UAE Regulatory Screening</div>'
        '<div style="font-size:12px;color:#6B7280;letter-spacing:0.1em;'
        'text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Internal Risk Monitoring Platform</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:#111827;border:1px solid #1F2937;border-radius:14px;'
        'padding:32px;margin-bottom:16px;">'
        '<div style="font-size:14px;font-weight:700;color:#E5E7EB;margin-bottom:6px;">'
        'Enter your name to continue</div>'
        '<div style="font-size:12px;color:#6B7280;margin-bottom:20px;">'
        'Your name will be attached to all notes and actions you take.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    name = st.text_input(
        "Your name",
        placeholder="e.g. Khalil",
        label_visibility="collapsed",
        key="login_name_input",
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        enter = st.button("Enter →", use_container_width=True, key="login_submit")

    if enter or (name and name.strip()):
        clean = name.strip()
        if len(clean) < 2:
            st.error("Please enter at least 2 characters.")
        else:
            session["current_user"] = clean
            st.rerun()

    st.markdown(
        '<div style="text-align:center;margin-top:24px;font-size:11px;color:#374151;">'
        'Internal tool · not a legal determination · access is logged</div>',
        unsafe_allow_html=True,
    )
