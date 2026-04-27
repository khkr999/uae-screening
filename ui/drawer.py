"""Entity detail drawer — shown when a row is selected."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import risk_badge_html, section_header

_WORKFLOW = ("Open", "In Review", "Escalated", "Cleared")
_WF_COLOR = {
    "Open":      "#6B7280",
    "In Review": "#FBBF24",
    "Escalated": "#EF4444",
    "Cleared":   "#34D399",
}
_WATCHLIST_KEY = "watchlist"


def render(df: pd.DataFrame, session) -> None:
    eid = state.get_selected(session)
    if not eid:
        return
    if "id" not in df.columns:
        return
    hits = df[df["id"] == eid]
    if hits.empty:
        state.set_selected(session, None)
        return
    row = hits.iloc[0]

    with st.expander(f"📋  Entity Details — {row.get(Col.BRAND, '—')}", expanded=True):
        _header(row)
        _sp()
        _action_buttons(row, session)
        _sp()
        _signals(row)
        _sp()
        _rationale(row)
        _sp()
        _workflow(row, session)
        _sp()
        _annotations(row, session)
        _sp()
        c1, _ = st.columns([1, 5])
        with c1:
            if st.button("✕  Close", key="drawer_close"):
                state.set_selected(session, None)
                st.rerun()


def _sp() -> None:
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)


# ── HEADER ──────────────────────────────────────────────────────────────────
def _header(row: pd.Series) -> None:
    brand  = escape(str(row.get(Col.BRAND,     "—")))
    svc    = escape(str(row.get(Col.SERVICE,   "—")))
    reg    = escape(str(row.get(Col.REGULATOR, "—")))
    level  = int(row.get(Col.RISK_LEVEL, 1))
    action = str(row.get(Col.ACTION, "") or "")

    act_html = (
        f'<div style="margin-top:8px;display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);'
        f'background:var(--accent-s);border-radius:4px;padding:2px 8px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{escape(action)}</div>'
    ) if action else ""

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        f'padding:16px 20px;background:var(--bg,#0F172A);border-radius:10px;'
        f'border:1px solid var(--border);">'
        f'<div>'
        f'<div style="font-size:20px;font-weight:800;color:var(--text);">{brand}</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:3px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{svc} &nbsp;·&nbsp; {reg}</div>'
        f'{act_html}</div>'
        f'<div style="flex-shrink:0;">{risk_badge_html(level)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── ACTION BUTTONS ───────────────────────────────────────────────────────────
def _action_buttons(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = session.get("workflow_overrides", {}).get(eid, "Open")
    wl      = session.get(_WATCHLIST_KEY, set())

    section_header("Quick Actions")
    c1, c2, c3 = st.columns(3)

    with c1:
        lbl = "✓ Reviewed" if current == "Cleared" else "Mark as Reviewed"
        if st.button(lbl, key=f"act_review_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Cleared")
            st.success("✓ Marked as Reviewed")
            st.rerun()

    with c2:
        lbl = "🔴 Escalated" if current == "Escalated" else "Escalate"
        if st.button(lbl, key=f"act_escalate_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Escalated")
            st.warning("⚑ Entity escalated")
            st.rerun()

    with c3:
        in_wl = eid in wl
        lbl   = "★ In Watchlist" if in_wl else "Add to Watchlist"
        if st.button(lbl, key=f"act_watch_{eid}", use_container_width=True):
            updated = set(session.get(_WATCHLIST_KEY, set()))
            if in_wl:
                updated.discard(eid)
            else:
                updated.add(eid)
            session[_WATCHLIST_KEY] = updated
            st.success("★ Watchlist updated")
            st.rerun()


# ── SIGNALS ──────────────────────────────────────────────────────────────────
def _signals(row: pd.Series) -> None:
    section_header("Signals")
    c1, c2, c3 = st.columns(3)

    def _sig(col_obj, label: str, val: bool) -> None:
        color = "#34D399" if val else "#6B7280"
        icon  = "●" if val else "○"
        col_obj.markdown(
            f'<div style="background:var(--bg,#0F172A);border:1px solid var(--border);'
            f'border-radius:10px;padding:12px 14px;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
            f'{escape(label)}</div>'
            f'<div style="font-size:18px;font-weight:800;color:{color};margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{icon} {"Yes" if val else "No"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _sig(c1, "UAE Present",       bool(row.get(Col.UAE_PRESENT)))
    _sig(c2, "License Signal",    bool(row.get(Col.LICENSE_SIGNAL)))
    _sig(c3, "Unlicensed Signal", bool(row.get(Col.UNLICENSED_SIGNAL)))


# ── RATIONALE ────────────────────────────────────────────────────────────────
def _rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE)  or "No rationale recorded."
    snippet   = row.get(Col.SNIPPET)    or ""
    url       = row.get(Col.SOURCE_URL) or ""

    section_header("Rationale")
    st.markdown(
        f'<div style="background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.18);'
        f'border-radius:8px;padding:12px 14px;font-size:12px;color:var(--dim);line-height:1.65;">'
        f'{escape(str(rationale))}</div>',
        unsafe_allow_html=True,
    )

    if snippet:
        _sp()
        section_header("Key Snippet")
        st.markdown(
            f'<div style="font-size:11px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;'
            f'border-left:2px solid var(--border);padding-left:10px;line-height:1.6;">'
            f'{escape(str(snippet))}</div>',
            unsafe_allow_html=True,
        )
    if url:
        st.markdown(
            f'<div style="margin-top:8px;font-size:11px;">'
            f'<span style="color:var(--muted);">Source: </span>'
            f'<a href="{url}" target="_blank" style="color:var(--accent);text-decoration:none;">'
            f'{escape(str(url)[:90])}{"…" if len(str(url)) > 90 else ""}</a></div>',
            unsafe_allow_html=True,
        )


# ── WORKFLOW ──────────────────────────────────────────────────────────────────
def _workflow(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = session.get("workflow_overrides", {}).get(eid, "Open")
    color   = _WF_COLOR.get(current, "#6B7280")

    section_header("Workflow Status")
    st.markdown(
        f'<div style="margin-bottom:8px;font-size:11px;color:var(--muted);">'
        f'Current: <span style="color:{color};font-weight:700;'
        f'font-family:\'IBM Plex Mono\',monospace;">{current}</span></div>',
        unsafe_allow_html=True,
    )
    new_status = st.radio(
        "Status",
        options=_WORKFLOW,
        index=_WORKFLOW.index(current) if current in _WORKFLOW else 0,
        horizontal=True,
        key=f"drawer_workflow_{eid}",
        label_visibility="collapsed",
    )
    if new_status != current:
        state.set_workflow(session, eid, new_status)
        st.success(f"✓ Status updated to {new_status}")
        st.rerun()


# ── ANNOTATIONS  (fixed: button-click only, timestamped, no duplication) ────
def _annotations(row: pd.Series, session) -> None:
    eid       = str(row.get("id", ""))
    input_key = f"note_input_{eid}"
    btn_key   = f"note_btn_{eid}"

    all_notes: dict  = session.get("annotations", {})
    notes: list      = all_notes.get(eid, [])

    section_header("Annotations", f"{len(notes)} note{'s' if len(notes) != 1 else ''}")

    # Display existing notes
    if notes:
        parts = []
        for entry in notes:
            if isinstance(entry, dict):
                txt = escape(entry.get("text", ""))
                ts  = escape(entry.get("ts",   ""))
            else:
                txt = escape(str(entry))
                ts  = ""
            ts_html = (f'<span style="color:var(--muted);font-size:10px;'
                       f'font-family:\'IBM Plex Mono\',monospace;"> · {ts}</span>') if ts else ""
            parts.append(
                f'<div style="padding:8px 0;border-bottom:1px solid var(--border);">'
                f'<div style="font-size:10px;font-weight:700;color:var(--accent);'
                f'font-family:\'IBM Plex Mono\',monospace;margin-bottom:3px;">'
                f'You{ts_html}</div>'
                f'<div style="font-size:12px;color:var(--dim);line-height:1.5;">{txt}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:var(--bg,#0F172A);border:1px solid var(--border);'
            f'border-radius:8px;padding:4px 12px;margin-bottom:12px;">'
            + "".join(parts) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);margin-bottom:10px;">'
            'No annotations yet.</div>',
            unsafe_allow_html=True,
        )

    # Input + button — note saved ONLY on button click (fixes rerun duplication bug)
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        note_text = st.text_input(
            "Note",
            key=input_key,
            placeholder="Type a note…",
            label_visibility="collapsed",
        )
    with col_btn:
        add = st.button("Add", key=btn_key, use_container_width=True)

    if add:
        text = (note_text or "").strip()
        if text:
            ts      = datetime.now().strftime("%d %b %H:%M")
            updated = dict(session.get("annotations", {}))
            updated[eid] = [*updated.get(eid, []), {"text": text, "ts": ts}]
            session["annotations"] = updated
            # Bump nonce to reset the text input on next render
            session[f"note_nonce_{eid}"] = session.get(f"note_nonce_{eid}", 0) + 1
            st.success("✓ Note added")
            st.rerun()
