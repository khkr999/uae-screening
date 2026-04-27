"""Entity detail drawer — shown when a row is selected."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import risk_badge_html, section_header

_WORKFLOW_STATUSES = ("Open", "In Review", "Escalated", "Cleared")

_STATUS_COLORS = {
    "Open":      "#6B7280",
    "In Review": "#FBBF24",
    "Escalated": "#EF4444",
    "Cleared":   "#34D399",
}

_WATCHLIST_KEY = "watchlist"


def render(df: pd.DataFrame, session) -> None:
    entity_id = state.get_selected(session)
    if not entity_id:
        return
    if "id" not in df.columns:
        return
    hits = df[df["id"] == entity_id]
    if hits.empty:
        state.set_selected(session, None)
        return
    row = hits.iloc[0]

    with st.expander(
        f"📋  Entity Details — {row.get(Col.BRAND, '—')}",
        expanded=True,
    ):
        _render_header(row)
        _sp()
        _render_action_buttons(row, session)
        _sp()
        _render_signals(row)
        _sp()
        _render_rationale(row)
        _sp()
        _render_workflow(row, session)
        _sp()
        _render_annotations(row, session)
        _sp()

        c1, _ = st.columns([1, 5])
        with c1:
            if st.button("✕  Close", key="drawer_close"):
                state.set_selected(session, None)
                st.rerun()


def _sp() -> None:
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header(row: pd.Series) -> None:
    brand     = escape(str(row.get(Col.BRAND,     "—")))
    service   = escape(str(row.get(Col.SERVICE,   "—")))
    regulator = escape(str(row.get(Col.REGULATOR, "—")))
    level     = int(row.get(Col.RISK_LEVEL, 1))
    action    = str(row.get(Col.ACTION, "") or "")

    action_html = (
        f'<div style="margin-top:8px;display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);'
        f'background:var(--accent-soft);border-radius:4px;padding:2px 8px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{escape(action)}</div>'
        if action else ""
    )
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    padding:16px 20px;background:#0F172A;border-radius:10px;
                    border:1px solid var(--border);">
            <div>
                <div style="font-size:20px;font-weight:800;color:var(--text);">{brand}</div>
                <div style="font-size:11px;color:var(--muted);margin-top:3px;
                            font-family:'IBM Plex Mono',monospace;">
                    {service} &nbsp;·&nbsp; {regulator}
                </div>
                {action_html}
            </div>
            <div style="flex-shrink:0;">{risk_badge_html(level)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Action buttons  (Mark Reviewed / Escalate / Watchlist)
# ---------------------------------------------------------------------------
def _render_action_buttons(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    current   = session.get("workflow_overrides", {}).get(entity_id, "Open")
    watchlist = session.get(_WATCHLIST_KEY, set())

    section_header("Quick Actions")
    c1, c2, c3 = st.columns(3)

    with c1:
        reviewed_label = "✓ Reviewed" if current == "Cleared" else "Mark as Reviewed"
        if st.button(reviewed_label, key=f"action_review_{entity_id}",
                     use_container_width=True):
            state.set_workflow(session, entity_id, "Cleared")
            st.success("✓ Marked as Reviewed")
            st.rerun()

    with c2:
        escalated_label = "🔴 Escalated" if current == "Escalated" else "Escalate"
        if st.button(escalated_label, key=f"action_escalate_{entity_id}",
                     use_container_width=True):
            state.set_workflow(session, entity_id, "Escalated")
            st.warning("⚑ Entity escalated")
            st.rerun()

    with c3:
        in_watch = entity_id in watchlist
        watch_label = "★ In Watchlist" if in_watch else "Add to Watchlist"
        if st.button(watch_label, key=f"action_watch_{entity_id}",
                     use_container_width=True):
            wl = set(session.get(_WATCHLIST_KEY, set()))
            if in_watch:
                wl.discard(entity_id)
            else:
                wl.add(entity_id)
            session[_WATCHLIST_KEY] = wl
            st.success("★ Watchlist updated")
            st.rerun()


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
def _render_signals(row: pd.Series) -> None:
    section_header("Signals")
    c1, c2, c3 = st.columns(3)

    def _sig_card(col_obj, label: str, value: bool) -> None:
        color = "#34D399" if value else "#6B7280"
        icon  = "●" if value else "○"
        col_obj.markdown(
            f'<div style="background:#0F172A;border:1px solid var(--border);border-radius:10px;'
            f'padding:12px 14px;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
            f'color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">{escape(label)}</div>'
            f'<div style="font-size:18px;font-weight:800;color:{color};margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{icon} {"Yes" if value else "No"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _sig_card(c1, "UAE Present",       bool(row.get(Col.UAE_PRESENT)))
    _sig_card(c2, "License Signal",    bool(row.get(Col.LICENSE_SIGNAL)))
    _sig_card(c3, "Unlicensed Signal", bool(row.get(Col.UNLICENSED_SIGNAL)))


# ---------------------------------------------------------------------------
# Rationale
# ---------------------------------------------------------------------------
def _render_rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE) or "No rationale recorded."
    snippet   = row.get(Col.SNIPPET)   or ""
    url       = row.get(Col.SOURCE_URL) or ""

    section_header("Rationale")
    st.markdown(
        f'<div style="background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.18);'
        f'border-radius:8px;padding:12px 14px;font-size:12px;color:var(--dim);line-height:1.65;">'
        f'{escape(str(rationale))}</div>',
        unsafe_allow_html=True,
    )

    if snippet:
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
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


# ---------------------------------------------------------------------------
# Workflow (radio — keeps full flexibility)
# ---------------------------------------------------------------------------
def _render_workflow(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    current   = session.get("workflow_overrides", {}).get(entity_id, "Open")
    color     = _STATUS_COLORS.get(current, "#6B7280")

    section_header("Workflow Status")
    st.markdown(
        f'<div style="margin-bottom:8px;font-size:11px;color:var(--muted);">'
        f'Current: <span style="color:{color};font-weight:700;'
        f'font-family:\'IBM Plex Mono\',monospace;">{current}</span></div>',
        unsafe_allow_html=True,
    )
    new_status = st.radio(
        "Status",
        options=_WORKFLOW_STATUSES,
        index=_WORKFLOW_STATUSES.index(current) if current in _WORKFLOW_STATUSES else 0,
        horizontal=True,
        key=f"drawer_workflow_{entity_id}",
        label_visibility="collapsed",
    )
    if new_status != current:
        state.set_workflow(session, entity_id, new_status)
        st.success(f"✓ Status updated to {new_status}")
        st.rerun()


# ---------------------------------------------------------------------------
# Annotations  — FIXED: button-click only, per-entity, timestamped, no duplication
# ---------------------------------------------------------------------------
def _render_annotations(row: pd.Series, session) -> None:
    entity_id  = str(row.get("id", ""))
    input_key  = f"note_input_{entity_id}"
    submit_key = f"note_submit_{entity_id}"

    # Notes are stored as list of dicts: {text, ts}
    all_annotations: dict = session.get("annotations", {})
    notes: list = all_annotations.get(entity_id, [])

    section_header("Annotations", f"{len(notes)} note{'s' if len(notes) != 1 else ''}")

    # Display existing notes
    if notes:
        notes_html_parts = []
        for entry in notes:
            if isinstance(entry, dict):
                text = escape(entry.get("text", ""))
                ts   = escape(entry.get("ts", ""))
            else:
                # legacy plain string
                text = escape(str(entry))
                ts   = ""
            ts_html = (
                f'<span style="color:var(--muted);font-size:10px;'
                f'font-family:\'IBM Plex Mono\',monospace;"> · {ts}</span>'
                if ts else ""
            )
            notes_html_parts.append(
                f'<div style="padding:8px 0;border-bottom:1px solid var(--border);">'
                f'<div style="font-size:10px;font-weight:700;color:var(--accent);'
                f'font-family:\'IBM Plex Mono\',monospace;margin-bottom:3px;">'
                f'You{ts_html}</div>'
                f'<div style="font-size:12px;color:var(--dim);line-height:1.5;">{text}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:#0F172A;border:1px solid var(--border);'
            f'border-radius:8px;padding:4px 12px;margin-bottom:12px;">'
            f'{"".join(notes_html_parts)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);margin-bottom:10px;">'
            'No annotations yet.</div>',
            unsafe_allow_html=True,
        )

    # Input row — button-click only (fixes duplication bug)
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        note_text = st.text_input(
            "Note",
            key=input_key,
            placeholder="Add a note…",
            label_visibility="collapsed",
        )
    with col_btn:
        add_clicked = st.button("Add", key=submit_key, use_container_width=True)

    if add_clicked:
        text = (session.get(input_key) or note_text or "").strip()
        if text:
            ts = datetime.now().strftime("%d %b %H:%M")
            new_entry = {"text": text, "ts": ts}
            updated = dict(session.get("annotations", {}))
            updated[entity_id] = [*updated.get(entity_id, []), new_entry]
            session["annotations"] = updated
            # Clear input by bumping a nonce used in key
            nonce_key = f"note_nonce_{entity_id}"
            session[nonce_key] = session.get(nonce_key, 0) + 1
            st.success("✓ Note added")
            st.rerun()
