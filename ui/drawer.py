"""Entity detail drawer — shown when a row is selected."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import risk_badge_html


_WORKFLOW_STATUSES = ("Open", "In Review", "Escalated", "Cleared")


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

    with st.expander(f"📋 Entity details — {row.get(Col.BRAND, '—')}",
                     expanded=True):
        _render_header(row)
        st.write("")
        _render_signals(row)
        st.write("")
        _render_rationale(row)
        st.write("")
        _render_workflow(row, session)
        st.write("")
        _render_annotations(row, session)

        if st.button("Close", key="drawer_close"):
            state.set_selected(session, None)
            st.rerun()


def _render_header(row: pd.Series) -> None:
    brand = escape(str(row.get(Col.BRAND, "—")))
    service = escape(str(row.get(Col.SERVICE, "—")))
    regulator = escape(str(row.get(Col.REGULATOR, "—")))
    level = int(row.get(Col.RISK_LEVEL, 1))
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:start;">
            <div>
                <div style="font-size:20px;font-weight:800;">{brand}</div>
                <div style="color:var(--muted);font-size:12px;">
                    {service} · {regulator}
                </div>
            </div>
            <div>{risk_badge_html(level)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_signals(row: pd.Series) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("UAE Present",
              "Yes" if row.get(Col.UAE_PRESENT) else "No")
    c2.metric("License Signal",
              "Yes" if row.get(Col.LICENSE_SIGNAL) else "No")
    c3.metric("Unlicensed Signal",
              "Yes" if row.get(Col.UNLICENSED_SIGNAL) else "No")


def _render_rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE) or "No rationale recorded."
    snippet = row.get(Col.SNIPPET) or ""
    url = row.get(Col.SOURCE_URL) or ""

    st.markdown("**Rationale**")
    st.info(str(rationale))

    if snippet:
        st.markdown("**Key snippet**")
        st.caption(str(snippet))
    if url:
        st.markdown(f"**Source:** [{url}]({url})")


def _render_workflow(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    current = (session.get("workflow_overrides", {})
                     .get(entity_id, "Open"))
    st.markdown("**Workflow status**")
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
        st.success(f"Marked as {new_status}")


def _render_annotations(row: pd.Series, session) -> None:
    entity_id = str(row.get("id", ""))
    notes = session.get("annotations", {}).get(entity_id, [])

    st.markdown("**Annotations**")
    if notes:
        for n in notes:
            st.markdown(f"- {n}")
    else:
        st.caption("No annotations yet.")

    note = st.text_input("Add a note", key=f"drawer_note_{entity_id}",
                         placeholder="Type and press Enter")
    if note:
        state.add_annotation(session, entity_id, note)
        st.success("Annotation saved")
        st.rerun()
