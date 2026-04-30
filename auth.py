"""Authentication — owner requires name + password, analysts name only."""
from __future__ import annotations
import hashlib
import streamlit as st

_OWNER_CREDENTIALS: dict[str, str] = {
    "khalil":  hashlib.sha256("uae2024secure".encode()).hexdigest(),
    "khkr999": hashlib.sha256("uae2024secure".encode()).hexdigest(),
}

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _persist_login(session) -> None:
    """Write login to Supabase sessions table so refresh keeps user logged in."""
    try:
        from db import get_client
        db = get_client()
        if db is None:
            return
        db.table("sessions").upsert({
            "username":  session.get("current_user", ""),
            "is_owner":  bool(session.get("is_owner", False)),
            "last_seen": __import__("datetime").datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass

def sign_out(session) -> None:
    """Clear login from session and from Supabase sessions table."""
    username = session.get("current_user", "")
    session["current_user"] = ""
    session["is_owner"] = False
    session["_workspace_loaded"] = False
    if username:
        try:
            from db import get_client
            db = get_client()
            if db:
                db.table("sessions").delete().eq("username", username).execute()
        except Exception:
            pass

def is_owner(session) -> bool:
    return bool(session.get("is_owner", False))

def current_user(session) -> str:
    return session.get("current_user", "")

def is_logged_in(session) -> bool:
    return bool(session.get("current_user", "").strip())

def _try_restore_from_supabase(session) -> bool:
    """
    Streamlit has no native session cookies, so we can't know WHICH user
    is refreshing. Login always requires name entry — this is intentional.
    """
    return False

def render_login(session) -> None:
    st.markdown("""
        <style>
        html,body,[data-testid="stAppViewContainer"]{background:#0F172A!important;}
        .block-container{max-width:460px!important;margin:auto;padding-top:8vh!important;}
        footer,header{visibility:hidden!important;}
        #MainMenu{visibility:hidden!important;}
        [data-testid="stSidebar"]{display:none!important;}
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
        '<div style="background:#111827;border:1px solid #1F2937;'
        'border-radius:14px;padding:28px 28px 20px 28px;margin-bottom:16px;">'
        '<div style="font-size:14px;font-weight:700;color:#E5E7EB;margin-bottom:4px;">'
        'Sign in to continue</div>'
        '<div style="font-size:12px;color:#6B7280;margin-bottom:20px;">'
        'Enter your name. Owners also enter their password to unlock file uploads.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    name = st.text_input(
        "Your name", placeholder="Enter your name…",
        label_visibility="collapsed", key="login_name",
    )

    name_clean  = name.strip().lower()
    is_an_owner = name_clean in _OWNER_CREDENTIALS
    password    = ""

    if is_an_owner and name.strip():
        st.markdown(
            '<div style="margin-top:8px;font-size:11px;color:#C9A84C;'
            'font-family:\'IBM Plex Mono\',monospace;margin-bottom:4px;">'
            '🔑 Owner account detected — enter password to unlock upload access</div>',
            unsafe_allow_html=True,
        )
        password = st.text_input(
            "Password", type="password", placeholder="Owner password…",
            label_visibility="collapsed", key="login_password",
        )

    col1, col2 = st.columns([3, 1])
    with col2:
        enter = st.button("Enter →", use_container_width=True, key="login_submit")

    if enter:
        name_stripped = name.strip()
        if len(name_stripped) < 2:
            st.error("Please enter at least 2 characters.")
            return
        if is_an_owner:
            if not password:
                st.error("Password required for owner access.")
                return
            if _hash(password) == _OWNER_CREDENTIALS[name_clean]:
                session["current_user"] = name_stripped
                session["is_owner"]     = True
                _persist_login(session)
                st.rerun()
            else:
                st.error("Incorrect password. Try again, or enter without password for view-only access.")
                return
        else:
            session["current_user"] = name_stripped
            session["is_owner"]     = False
            _persist_login(session)
            st.rerun()

    st.markdown(
        '<div style="text-align:center;margin-top:20px;font-size:11px;color:#374151;">'
        'Internal tool · not a legal determination · access is logged</div>',
        unsafe_allow_html=True,
    )
