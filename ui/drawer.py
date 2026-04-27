"""Entity detail drawer — shown when a row is selected."""
from __future__ import annotations

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
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        _render_signals(row)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        _render_rationale(row)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        _render_workflow(row, session)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        _render_annotations(row, session)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        c1, _ = st.columns([1, 4])
        with c1:
            if st.button("✕  Close", key="drawer_close"):
                state.set_selected(session, None)
                st.rerun()


def _render_header(row: pd.Series) -> None:
    brand     = escape(str(row.get(Col.BRAND,     "—")))
    service   = escape(str(row.get(Col.SERVICE,   "—")))
    regulator = escape(str(row.get(Col.REGULATOR, "—")))
    level     = int(row.get(Col.RISK_LEVEL, 1))
    action    = escape(str(row.get(Col.ACTION, "") or ""))

    action_html = (
        f'<div style="margin-top:8px;display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);'
        f'background:var(--accent-soft);border-radius:4px;padding:2px 8px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{action}</div>'
        if action else ""
    )

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-start;
                    padding: 16px 20px; background:var(--bg-secondary,#0F172A);
                    border-radius:10px; border: 1px solid var(--border);">
            <div>
                <div style="font-size:20px; font-weight:800; color:var(--text);">{brand}</div>
                <div style="font-size:11px; color:var(--muted); margin-top:3px;
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


def _render_signals(row: pd.Series) -> None:
    section_header("Signals")
    c1, c2, c3 = st.columns(3)
    c1.metric("UAE Present",       "Yes" if row.get(Col.UAE_PRESENT)        else "No")
    c2.metric("License Signal",    "Yes" if row.get(Col.LICENSE_SIGNAL)     else "No")
    c3.metric("Unlicensed Signal", "Yes" if row.get(Col.UNLICENSED_SIGNAL)  else "No")


def _render_rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE) or "No rationale recorded."
    snippet   = row.get(Col.SNIPPET)   or ""
    url       = row.get(Col.SOURCE_URL) or ""

    section_header("Rationale")
    st.markdown(
        f'<div style="background:rgba(37,99,235,0.06); border:1px solid rgba(37,99,235,0.18); '
        f'border-radius:8px; padding:12px 14px; font-size:12px; color:var(--dim); line-height:1.6;">'
        f'{escape(str(rationale))}</div>',
        unsafe_allow_html=True,
    )

    if snippet:
        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
        section_header("Key Snippet")
        st.markdown(
            f'<div style="font-size:11px; color:var(--muted); font-family:\'IBM Plex Mono\',monospace; '
            f'border-left:2px solid var(--border); padding-left:10px; line-height:1.6;">'
            f'{escape(str(snippet))}</div>',
            unsafe_allow_html=True,
        )
    if url:
        st.markdown(
            f'<div style="margin-top:8px; font-size:11px;">'
            f'<span style="color:var(--muted);">Source:</span> '
            f'<a href="{url}" target="_blank" style="color:var(--accent); text-decoration:none;">'
            f'{escape(str(url)[:80])}{"…" if len(str(url)) > 80 else ""}</a></div>',
            unsafe_allow_html=True,
        )


def _render_workflow(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    current   = session.get("workflow_overrides", {}).get(entity_id, "Open")
    color     = _STATUS_COLORS.get(current, "#6B7280")

    section_header("Workflow Status")
    st.markdown(
        f'<div style="margin-bottom:8px; font-size:11px; color:var(--muted);">'
        f'Current: <span style="color:{color}; font-weight:700; font-family:\'IBM Plex Mono\',monospace;">'
        f'{current}</span></div>',
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
        st.success(f"✓ Marked as {new_status}")


def _render_annotations(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    notes     = session.get("annotations", {}).get(entity_id, [])

    section_header("Annotations")
    if notes:
        notes_html = "".join(
            f'<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);">'
            f'<span style="color:var(--accent);font-size:11px;">›</span>'
            f'<span style="font-size:12px;color:var(--dim);">{escape(n)}</span>'
            f'</div>'
            for n in notes
        )
        st.markdown(
            f'<div style="background:var(--card);border:1px solid var(--border);'
            f'border-radius:8px;padding:8px 12px;margin-bottom:10px;">{notes_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);margin-bottom:8px;">No annotations yet.</div>',
            unsafe_allow_html=True,
        )

    note = st.text_input(
        "Add a note",
        key=f"drawer_note_{entity_id}",
        placeholder="Type a note and press Enter…",
    )
    if note:
        state.add_annotation(session, entity_id, note)
        st.success("✓ Annotation saved")
        st.rerun()
