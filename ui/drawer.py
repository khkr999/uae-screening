"""Entity detail drawer — task-based workflow system (Asana-inspired)."""
from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import risk_badge_html, section_header

_WORKFLOW      = ("Open", "In Review", "Escalated", "Cleared")
_WF_COLOR      = {"Open": "#6B7280", "In Review": "#FBBF24",
                  "Escalated": "#EF4444", "Cleared": "#34D399"}
_WF_BG         = {"Open": "rgba(107,114,128,0.10)", "In Review": "rgba(251,191,36,0.10)",
                  "Escalated": "rgba(239,68,68,0.10)", "Cleared": "rgba(52,211,153,0.10)"}
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

    with st.expander(
        f"📋  {row.get(Col.BRAND, '—')}  ·  Entity Details",
        expanded=True,
    ):
        # ── TOP STRIP: status + close ──
        _status_strip(row, session)
        _sp(8)

        # ── HEADER ──
        _header(row)
        _sp(16)

        # ── PRIMARY ACTIONS ──
        _action_buttons(row, session)
        _sp(20)

        _divider()

        # ── TWO COLUMN LAYOUT ──
        left, right = st.columns([3, 2], gap="large")

        with left:
            # Signals
            _sp(4)
            _signals(row)
            _sp(16)

            # Rationale + Source
            _rationale(row)
            _sp(16)

            # Notes / Annotations
            _annotations(row, session)

        with right:
            # Workflow
            _workflow(row, session)
            _sp(16)

            # Entity metadata
            _metadata(row)

        _sp(12)
        _divider()
        _sp(8)

        c1, _ = st.columns([1, 6])
        with c1:
            if st.button("✕ Close", key="drawer_close"):
                state.set_selected(session, None)
                st.rerun()


# ── HELPERS ──────────────────────────────────────────────────────────────────
def _sp(px: int = 14) -> None:
    st.markdown(f'<div style="height:{px}px;"></div>', unsafe_allow_html=True)


def _divider() -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:0;"></div>',
        unsafe_allow_html=True,
    )


# ── STATUS STRIP ─────────────────────────────────────────────────────────────
def _status_strip(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = session.get("workflow_overrides", {}).get(eid, "Open")
    color   = _WF_COLOR.get(current, "#6B7280")
    bg      = _WF_BG.get(current, "rgba(107,114,128,0.10)")
    wl      = session.get(_WATCHLIST_KEY, set())
    in_wl   = eid in wl

    wl_badge = (
        '<span style="margin-left:8px;font-size:9px;font-weight:700;'
        'color:#C9A84C;background:rgba(201,168,76,0.10);'
        'border-radius:4px;padding:2px 7px;font-family:\'IBM Plex Mono\',monospace;">'
        '★ WATCHLIST</span>'
    ) if in_wl else ""

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'padding:6px 12px;background:{bg};border-radius:8px;">'
        f'<span style="width:8px;height:8px;border-radius:999px;'
        f'background:{color};display:inline-block;flex-shrink:0;"></span>'
        f'<span style="font-size:11px;font-weight:700;color:{color};'
        f'font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.06em;">{current.upper()}</span>'
        f'{wl_badge}</div>',
        unsafe_allow_html=True,
    )


# ── HEADER ───────────────────────────────────────────────────────────────────
def _header(row: pd.Series) -> None:
    brand  = escape(str(row.get(Col.BRAND,     "—")))
    svc    = escape(str(row.get(Col.SERVICE,   "—")))
    reg    = escape(str(row.get(Col.REGULATOR, "—")))
    level  = int(row.get(Col.RISK_LEVEL, 1))
    action = str(row.get(Col.ACTION, "") or "")

    act_html = (
        f'<span style="display:inline-block;font-size:9px;font-weight:700;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);'
        f'background:var(--accent-s);border-radius:4px;padding:2px 8px;'
        f'font-family:\'IBM Plex Mono\',monospace;margin-left:8px;">{escape(action)}</span>'
    ) if action else ""

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:22px;font-weight:800;color:var(--text);line-height:1.2;">{brand}</div>'
        f'<div style="font-size:12px;color:var(--muted);margin-top:4px;'
        f'font-family:\'IBM Plex Mono\',monospace;">'
        f'{svc} &nbsp;·&nbsp; {reg}{act_html}</div>'
        f'</div>'
        f'<div style="flex-shrink:0;margin-left:16px;">{risk_badge_html(level)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── ACTION BUTTONS ────────────────────────────────────────────────────────────
def _action_buttons(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = session.get("workflow_overrides", {}).get(eid, "Open")
    wl      = session.get(_WATCHLIST_KEY, set())
    in_wl   = eid in wl

    c1, c2, c3 = st.columns(3)

    with c1:
        reviewed = current == "Cleared"
        lbl = "✓ Marked Reviewed" if reviewed else "✓ Mark as Reviewed"
        if st.button(lbl, key=f"act_review_{eid}", use_container_width=True):
            new = "Open" if reviewed else "Cleared"
            state.set_workflow(session, eid, new)
            st.success("✓ Marked as Reviewed" if not reviewed else "↩ Reopened")
            st.rerun()

    with c2:
        escalated = current == "Escalated"
        lbl = "⚑ Escalated" if escalated else "⚑ Escalate"
        if st.button(lbl, key=f"act_escalate_{eid}", use_container_width=True):
            new = "Open" if escalated else "Escalated"
            state.set_workflow(session, eid, new)
            st.warning("⚑ Escalated" if not escalated else "↩ De-escalated")
            st.rerun()

    with c3:
        lbl = "★ Remove from Watchlist" if in_wl else "★ Add to Watchlist"
        if st.button(lbl, key=f"act_watch_{eid}", use_container_width=True):
            updated = set(session.get(_WATCHLIST_KEY, set()))
            updated.discard(eid) if in_wl else updated.add(eid)
            session[_WATCHLIST_KEY] = updated
            st.success("★ Watchlist updated")
            st.rerun()


# ── SIGNALS ──────────────────────────────────────────────────────────────────
def _signals(row: pd.Series) -> None:
    section_header("Signals")

    def _sig_card(label: str, val: bool) -> str:
        color = "#34D399" if val else "#EF4444"
        icon  = "●" if val else "○"
        txt   = "Yes" if val else "No"
        return (
            f'<div style="flex:1;background:var(--card);border:1px solid var(--border);'
            f'border-left:3px solid {color};border-radius:8px;padding:10px 14px;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
            f'{escape(label)}</div>'
            f'<div style="font-size:16px;font-weight:800;color:{color};margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{icon} {txt}</div>'
            f'</div>'
        )

    uae = bool(row.get(Col.UAE_PRESENT))
    lic = bool(row.get(Col.LICENSE_SIGNAL))
    unl = bool(row.get(Col.UNLICENSED_SIGNAL))

    st.markdown(
        f'<div style="display:flex;gap:8px;">'
        f'{_sig_card("UAE Present", uae)}'
        f'{_sig_card("License Signal", lic)}'
        f'{_sig_card("Unlicensed", unl)}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── RATIONALE ─────────────────────────────────────────────────────────────────
def _rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE)  or "No rationale recorded."
    snippet   = row.get(Col.SNIPPET)    or ""
    url       = row.get(Col.SOURCE_URL) or ""

    section_header("Analysis")
    st.markdown(
        f'<div style="background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.15);'
        f'border-left:3px solid rgba(37,99,235,0.5);'
        f'border-radius:8px;padding:12px 14px;font-size:12px;color:var(--dim);line-height:1.7;">'
        f'{escape(str(rationale))}</div>',
        unsafe_allow_html=True,
    )

    if snippet:
        _sp(10)
        st.markdown(
            f'<div style="font-size:11px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;'
            f'border-left:2px solid var(--border);padding:6px 10px;line-height:1.6;'
            f'background:rgba(255,255,255,0.02);border-radius:0 4px 4px 0;">'
            f'{escape(str(snippet))}</div>',
            unsafe_allow_html=True,
        )

    if url:
        _sp(6)
        st.markdown(
            f'<div style="font-size:11px;">'
            f'<span style="color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">Source → </span>'
            f'<a href="{url}" target="_blank" style="color:var(--accent);text-decoration:none;">'
            f'{escape(str(url)[:80])}{"…" if len(str(url)) > 80 else ""}</a></div>',
            unsafe_allow_html=True,
        )


# ── WORKFLOW ──────────────────────────────────────────────────────────────────
def _workflow(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = session.get("workflow_overrides", {}).get(eid, "Open")

    section_header("Workflow Status")

    # Visual status pills
    pills_html = '<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">'
    for status in _WORKFLOW:
        active = status == current
        color  = _WF_COLOR[status]
        bg     = _WF_BG[status] if active else "transparent"
        border = color if active else "var(--border)"
        weight = "700" if active else "400"
        dot    = f'<span style="width:7px;height:7px;border-radius:999px;background:{color};display:inline-block;margin-right:8px;"></span>' if active else '<span style="width:7px;height:7px;border-radius:999px;background:var(--border);display:inline-block;margin-right:8px;"></span>'
        pills_html += (
            f'<div style="display:flex;align-items:center;padding:7px 12px;'
            f'border-radius:8px;border:1px solid {border};background:{bg};">'
            f'{dot}'
            f'<span style="font-size:12px;font-weight:{weight};color:{"var(--text)" if active else "var(--muted)"};'
            f'font-family:\'IBM Plex Mono\',monospace;">{status}</span>'
            f'{"<span style=\"margin-left:auto;font-size:9px;color:" + color + ";font-weight:700;\">CURRENT</span>" if active else ""}'
            f'</div>'
        )
    pills_html += "</div>"
    st.markdown(pills_html, unsafe_allow_html=True)

    new_status = st.radio(
        "Change status",
        options=_WORKFLOW,
        index=_WORKFLOW.index(current) if current in _WORKFLOW else 0,
        horizontal=False,
        key=f"drawer_workflow_{eid}",
        label_visibility="collapsed",
    )
    if new_status != current:
        state.set_workflow(session, eid, new_status)
        st.success(f"✓ Status → {new_status}")
        st.rerun()


# ── METADATA ──────────────────────────────────────────────────────────────────
def _metadata(row: pd.Series) -> None:
    section_header("Details")

    fields = [
        ("Brand",          row.get(Col.BRAND,          "—")),
        ("Service",        row.get(Col.SERVICE,         "—")),
        ("Regulator",      row.get(Col.REGULATOR,       "—")),
        ("Classification", row.get(Col.CLASSIFICATION,  "—")),
        ("Confidence",     row.get(Col.CONFIDENCE,      "—")),
        ("Register Match", row.get(Col.MATCHED_ENTITY,  "—")),
        ("Category",       row.get(Col.REGISTER_CATEGORY, "—")),
    ]

    rows_html = ""
    for label, val in fields:
        val_str = str(val or "—")
        if val_str == "—" or val_str.lower() in ("nan", "none", "null"):
            continue
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:7px 0;border-bottom:1px solid var(--border);">'
            f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
            f'{escape(label)}</span>'
            f'<span style="font-size:11px;color:var(--dim);font-weight:600;'
            f'text-align:right;max-width:60%;word-break:break-word;">'
            f'{escape(val_str[:60])}{"…" if len(val_str) > 60 else ""}</span>'
            f'</div>'
        )

    if rows_html:
        st.markdown(
            f'<div style="background:var(--card);border:1px solid var(--border);'
            f'border-radius:10px;padding:4px 14px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);">No additional metadata.</div>',
            unsafe_allow_html=True,
        )


# ── ANNOTATIONS ───────────────────────────────────────────────────────────────
def _annotations(row: pd.Series, session) -> None:
    eid       = str(row.get("id", ""))
    input_key = f"note_input_{eid}"
    btn_key   = f"note_btn_{eid}"

    all_notes: dict = session.get("annotations", {})
    notes: list     = all_notes.get(eid, [])

    section_header("Notes", f"{len(notes)} comment{'s' if len(notes) != 1 else ''}")

    if notes:
        parts = []
        for entry in notes:
            if isinstance(entry, dict):
                txt = escape(entry.get("text", ""))
                ts  = escape(entry.get("ts",   ""))
            else:
                txt = escape(str(entry))
                ts  = ""
            ts_html = (
                f'<span style="color:var(--muted);font-size:10px;'
                f'font-family:\'IBM Plex Mono\',monospace;margin-left:6px;">{ts}</span>'
            ) if ts else ""
            parts.append(
                f'<div style="padding:10px 12px;margin-bottom:6px;'
                f'background:var(--card);border:1px solid var(--border);'
                f'border-radius:8px;border-left:2px solid var(--accent);">'
                f'<div style="display:flex;align-items:center;margin-bottom:5px;">'
                f'<span style="width:22px;height:22px;border-radius:999px;'
                f'background:var(--accent-s);display:inline-flex;align-items:center;'
                f'justify-content:center;font-size:10px;font-weight:700;color:var(--accent);">Y</span>'
                f'<span style="font-size:11px;font-weight:700;color:var(--dim);'
                f'margin-left:8px;font-family:\'IBM Plex Mono\',monospace;">You</span>'
                f'{ts_html}</div>'
                f'<div style="font-size:12px;color:var(--text);line-height:1.55;'
                f'padding-left:30px;">{txt}</div>'
                f'</div>'
            )
        st.markdown("".join(parts), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--muted);padding:8px 0;">'
            'No comments yet. Add one below.</div>',
            unsafe_allow_html=True,
        )

    # Input row — save ONLY on button click (no duplication)
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        note_text = st.text_input(
            "Note",
            key=input_key,
            placeholder="Add a comment…",
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
            session[f"note_nonce_{eid}"] = session.get(f"note_nonce_{eid}", 0) + 1
            st.success("✓ Comment added")
            st.rerun()
