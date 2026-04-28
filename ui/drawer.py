"""Entity detail drawer — slides in style matching mockup."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import (
    risk_pill_html, regulator_pill_html, action_label,
)


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

    # Display as expander to look like a drawer
    brand = str(row.get(Col.BRAND, "—") or "—")
    with st.expander(f"📋  {brand}  ·  Entity Details", expanded=True):
        _render_drawer_content(row, session)


def _render_drawer_content(row: pd.Series, session) -> None:
    eid       = str(row.get("id", ""))
    brand     = str(row.get(Col.BRAND, "—") or "—")
    service   = str(row.get(Col.SERVICE, "—") or "—")
    regulator = str(row.get(Col.REGULATOR, "—") or "—")
    level     = int(row.get(Col.RISK_LEVEL, 1))
    confidence = str(row.get(Col.CONFIDENCE, "—") or "—")
    rationale = str(row.get(Col.RATIONALE, "") or "No rationale recorded.")
    snippet   = str(row.get(Col.SNIPPET, "") or "")
    action    = str(row.get(Col.ACTION, "") or "")
    classification = str(row.get(Col.CLASSIFICATION, "") or "")

    # ── Header ────────────────────────────────────────────────────────────────
    pills = ""
    if level >= 4:
        pills += '<span class="uae-pill risk-up">↑ RISK UP</span>'
    pills += regulator_pill_html(regulator)

    st.markdown(
        f'<div class="uae-drawer-head">'
        f'<div>'
        f'<div class="uae-drawer-title">{escape(brand)}</div>'
        f'<div class="uae-drawer-pills">'
        f'{risk_pill_html(level)}'
        f'{pills}'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Service / Regulator / Confidence ──────────────────────────────────────
    st.markdown(
        f'<div class="uae-drawer-section">'
        f'<div class="uae-drawer-row">'
        f'<span class="uae-drawer-label">Service</span>'
        f'<span class="uae-drawer-val">{escape(service)}</span>'
        f'</div>'
        f'<div class="uae-drawer-row">'
        f'<span class="uae-drawer-label">Regulator</span>'
        f'<span>{regulator_pill_html(regulator)}</span>'
        f'</div>'
        f'<div class="uae-drawer-row">'
        f'<span class="uae-drawer-label">Confidence</span>'
        f'<span class="uae-drawer-val" style="color:var(--licensed);">{escape(confidence)}</span>'
        f'</div>'
        + (
            f'<div class="uae-drawer-row">'
            f'<span class="uae-drawer-label">Classification</span>'
            f'<span class="uae-drawer-val" style="font-family:\'JetBrains Mono\',monospace;'
            f'font-size:10px;">{escape(classification[:40])}</span>'
            f'</div>'
            if classification else ""
        )
        + f'</div>',
        unsafe_allow_html=True,
    )

    # ── Rationale ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="uae-drawer-label" style="margin:16px 0 8px 0;">Rationale</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="uae-drawer-section">'
        f'<div class="uae-drawer-rationale">{escape(rationale)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Key Evidence (snippet) ────────────────────────────────────────────────
    if snippet:
        st.markdown(
            '<div class="uae-drawer-label" style="margin:16px 0 8px 0;">Key Evidence</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="uae-drawer-section" style="border-left:3px solid var(--gold);">'
            f'<div class="uae-drawer-rationale" style="font-style:italic;'
            f'font-family:\'JetBrains Mono\',monospace;font-size:12px;">'
            f'{escape(snippet)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Required Action ───────────────────────────────────────────────────────
    if action:
        st.markdown(
            '<div class="uae-drawer-label" style="margin:16px 0 8px 0;">Required Action</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="uae-drawer-action">'
            f'{escape(action_label(action))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Action buttons ────────────────────────────────────────────────────────
    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    current = state.get_workflow(session, eid)

    with c1:
        is_cleared = current == "Cleared"
        if st.button("✓ Mark Reviewed" if not is_cleared else "✓ Reviewed",
                     key=f"draw_review_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Open" if is_cleared else "Cleared")
            st.rerun()

    with c2:
        is_esc = current == "Escalated"
        if st.button("↑ Escalate" if not is_esc else "✓ Escalated",
                     key=f"draw_esc_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Open" if is_esc else "Escalated")
            st.rerun()

    with c3:
        if st.button("◯ Clear", key=f"draw_clear_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Open")
            st.rerun()

    with c4:
        if st.button("✕ Close", key=f"draw_close_{eid}", use_container_width=True):
            state.set_selected(session, None)
            st.rerun()
