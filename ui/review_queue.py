"""Review Queue tab — Kanban-style entity review workflow."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, RISK_BY_LEVEL
import state
from ui.components import empty_state, risk_badge_html, section_header

_WF_COLOR = {
    "Open":      "#6B7280",
    "In Review": "#FBBF24",
    "Escalated": "#EF4444",
    "Cleared":   "#34D399",
}

_WF_BG = {
    "Open":      "rgba(107,114,128,0.10)",
    "In Review": "rgba(251,191,36,0.10)",
    "Escalated": "rgba(239,68,68,0.10)",
    "Cleared":   "rgba(52,211,153,0.10)",
}

# Entities with risk >= this are auto-added to the queue
_AUTO_QUEUE_THRESHOLD = 3


def render(df: pd.DataFrame, session) -> None:
    if df.empty:
        empty_state("No data loaded", "Upload a screening file to begin.")
        return

    _render_header(session)
    st.write("")
    _render_stats_bar(df, session)
    st.write("")

    tabs = st.tabs(["📌 To Do", "🔄 In Progress", "⚠️ Escalated", "✅ Done", "★ Watchlist"])

    with tabs[0]:
        _render_column(df, session, statuses=["Open"], title="To Do",
                       desc="High-risk entities not yet reviewed — action required.",
                       empty_msg="Nothing left to do", empty_icon="✅", tab_prefix="todo")

    with tabs[1]:
        _render_column(df, session, statuses=["In Review"], title="In Progress",
                       desc="Entities currently under review.",
                       empty_msg="Nothing in review", empty_icon="📋", tab_prefix="inprog")

    with tabs[2]:
        _render_column(df, session, statuses=["Escalated"], title="Escalated",
                       desc="Entities escalated for urgent attention.",
                       empty_msg="No escalations", empty_icon="✓", tab_prefix="esc")

    with tabs[3]:
        _render_column(df, session, statuses=["Cleared"], title="Done",
                       desc="Reviewed and cleared entities.",
                       empty_msg="No cleared entities yet", empty_icon="📋",
                       show_reopen=True, tab_prefix="done")

    with tabs[4]:
        _render_watchlist(df, session)


# ── HEADER ────────────────────────────────────────────────────────────────────
def _render_header(session) -> None:
    stats = state.get_review_stats(session)
    wl    = state.get_watchlist(session)
    total_actioned = sum(stats.values())

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:16px 20px;background:var(--card);border:1px solid var(--border);'
        f'border-radius:12px;position:relative;overflow:hidden;margin-bottom:4px;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,#C9A84C,#3DA5E0,#34D399);"></div>'
        f'<div>'
        f'<div style="font-size:16px;font-weight:700;color:var(--text);">📋 Review Queue</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:2px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'{total_actioned} entities actioned &nbsp;·&nbsp; {len(wl)} watchlisted</div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;">'
        + "".join(
            f'<div style="text-align:center;">'
            f'<div style="font-size:20px;font-weight:700;color:{_WF_COLOR[s]};'
            f'font-family:\'IBM Plex Mono\',monospace;">{stats.get(s, 0)}</div>'
            f'<div style="font-size:9px;color:var(--muted);text-transform:uppercase;'
            f'letter-spacing:0.08em;font-family:\'IBM Plex Mono\',monospace;">{s}</div>'
            f'</div>'
            for s in ["Open", "In Review", "Escalated", "Cleared"]
        )
        + f'</div></div>',
        unsafe_allow_html=True,
    )


# ── STATS BAR ─────────────────────────────────────────────────────────────────
def _render_stats_bar(df: pd.DataFrame, session) -> None:
    overrides = session.get("workflow_overrides", {})
    total     = len(df)

    # Entities that have been touched
    touched   = len(overrides)
    remaining = max(0, len(df[df[Col.RISK_LEVEL] >= _AUTO_QUEUE_THRESHOLD]) - touched)
    pct_done  = round(touched / max(total, 1) * 100)

    # Progress bar
    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:10px;padding:12px 18px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:8px;">'
        f'<span style="font-size:11px;color:var(--dim);font-family:\'IBM Plex Mono\',monospace;">'
        f'Review Progress</span>'
        f'<span style="font-size:11px;font-weight:700;color:var(--text);'
        f'font-family:\'IBM Plex Mono\',monospace;">{pct_done}% actioned</span>'
        f'</div>'
        f'<div style="height:6px;border-radius:999px;background:rgba(128,128,128,0.12);">'
        f'<div style="height:100%;width:{pct_done}%;border-radius:999px;'
        f'background:linear-gradient(90deg,#C9A84C,#34D399);'
        f'transition:width 0.5s ease;"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:6px;">'
        f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
        f'{touched} actioned of {total} total</span>'
        f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
        f'{remaining} high-risk remaining</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── COLUMN RENDERER ───────────────────────────────────────────────────────────
def _render_column(
    df: pd.DataFrame,
    session,
    statuses: list[str],
    title: str,
    desc: str,
    empty_msg: str,
    empty_icon: str,
    show_reopen: bool = False,
    tab_prefix: str = "",
) -> None:
    overrides = session.get("workflow_overrides", {})

    # Get entity IDs with matching status
    matching_ids = {eid for eid, s in overrides.items() if s in statuses}

    # For "To Do" also include high-risk entities with no status set
    if "Open" in statuses:
        high_risk = df[df[Col.RISK_LEVEL] >= _AUTO_QUEUE_THRESHOLD]
        unactioned_ids = set(high_risk["id"].astype(str).tolist()) - set(overrides.keys())
        matching_ids = matching_ids | unactioned_ids

    if not matching_ids:
        st.write("")
        empty_state(empty_msg, "", icon=empty_icon)
        return

    # Get rows for matching IDs
    rows = df[df["id"].astype(str).isin(matching_ids)].copy()
    rows = rows.sort_values(Col.RISK_LEVEL, ascending=False)

    st.markdown(
        f'<div style="font-size:11px;color:var(--muted);margin-bottom:12px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'{desc} &nbsp;·&nbsp; <b style="color:var(--dim);">{len(rows)}</b> entities</div>',
        unsafe_allow_html=True,
    )

    for _, row in rows.iterrows():
        _render_queue_card(row, session, show_reopen=show_reopen, tab_prefix=tab_prefix)


# ── QUEUE CARD ────────────────────────────────────────────────────────────────
def _render_queue_card(row: pd.Series, session, show_reopen: bool = False, tab_prefix: str = "") -> None:
    eid       = str(row.get("id", ""))
    brand     = str(row.get(Col.BRAND,     "—") or "—")
    svc       = str(row.get(Col.SERVICE,   "—") or "—")
    reg       = str(row.get(Col.REGULATOR, "—") or "—")
    level     = int(row.get(Col.RISK_LEVEL, 1))
    rationale = str(row.get(Col.RATIONALE, "") or "")[:120]
    current   = state.get_workflow(session, eid)
    notes     = state.get_annotations(session, eid)
    note_count = len(notes)
    in_wl     = state.in_watchlist(session, eid)

    color  = _WF_COLOR.get(current, "#6B7280")
    status_html = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{color};background:{_WF_BG.get(current,"transparent")};'
        f'border-radius:4px;padding:2px 6px;font-family:\'IBM Plex Mono\',monospace;">'
        f'{current}</span>'
    )
    wl_html = (
        '<span style="font-size:9px;color:#C9A84C;margin-left:6px;">★ Watchlist</span>'
        if in_wl else ""
    )
    note_html = (
        f'<span style="font-size:9px;color:var(--muted);margin-left:6px;">'
        f'💬 {note_count} note{"s" if note_count != 1 else ""}</span>'
    ) if note_count > 0 else ""

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:10px;padding:14px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:14px;font-weight:700;color:var(--text);">'
        f'{escape(brand)}</div>'
        f'<div style="font-size:11px;color:var(--muted);margin-top:2px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'{escape(svc)} &nbsp;·&nbsp; {escape(reg)}</div>'
        f'<div style="margin-top:6px;display:flex;align-items:center;">'
        f'{status_html}{wl_html}{note_html}</div>'
        f'</div>'
        f'<div style="flex-shrink:0;margin-left:12px;">{risk_badge_html(level)}</div>'
        f'</div>'
        + (
            f'<div style="font-size:11px;color:var(--muted);margin-top:8px;'
            f'border-top:1px solid var(--border);padding-top:8px;line-height:1.5;">'
            f'{escape(rationale)}{"…" if len(rationale) >= 120 else ""}</div>'
            if rationale else ""
        )
        + f'</div>',
        unsafe_allow_html=True,
    )

    # Action buttons
    btn_cols = st.columns(4)

    with btn_cols[0]:
        if st.button("Open Details", key=f"rq_open_{tab_prefix}_{eid}", use_container_width=True):
            state.set_selected(session, eid)
            st.rerun()

    with btn_cols[1]:
        if current != "In Review":
            if st.button("→ In Review", key=f"rq_inreview_{tab_prefix}_{eid}", use_container_width=True):
                state.set_workflow(session, eid, "In Review")
                st.rerun()
        else:
            if st.button("→ Escalate", key=f"rq_esc_{tab_prefix}_{eid}", use_container_width=True):
                state.set_workflow(session, eid, "Escalated")
                st.rerun()

    with btn_cols[2]:
        if current != "Cleared":
            if st.button("✓ Clear", key=f"rq_clear_{tab_prefix}_{eid}", use_container_width=True):
                state.set_workflow(session, eid, "Cleared")
                st.success(f"✓ {brand} cleared")
                st.rerun()
        elif show_reopen:
            if st.button("↩ Reopen", key=f"rq_reopen_{tab_prefix}_{eid}", use_container_width=True):
                state.set_workflow(session, eid, "Open")
                st.rerun()

    with btn_cols[3]:
        wl_lbl = "★ Watchlisted" if in_wl else "☆ Watchlist"
        if st.button(wl_lbl, key=f"rq_wl_{tab_prefix}_{eid}", use_container_width=True):
            state.toggle_watchlist(session, eid)
            st.rerun()

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)


# ── WATCHLIST ─────────────────────────────────────────────────────────────────
def _render_watchlist(df: pd.DataFrame, session) -> None:
    wl = state.get_watchlist(session)

    if not wl:
        st.write("")
        empty_state("No entities watchlisted",
                    "Add entities to your watchlist from the entity details view.",
                    icon="★")
        return

    wl_rows = df[df["id"].astype(str).isin(wl)].copy()
    wl_rows = wl_rows.sort_values(Col.RISK_LEVEL, ascending=False)

    st.markdown(
        f'<div style="font-size:11px;color:var(--muted);margin-bottom:12px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'Entities you are monitoring closely &nbsp;·&nbsp; '
        f'<b style="color:var(--dim);">{len(wl_rows)}</b> watchlisted</div>',
        unsafe_allow_html=True,
    )

    for _, row in wl_rows.iterrows():
        _render_queue_card(row, session, show_reopen=False, tab_prefix="wl")
