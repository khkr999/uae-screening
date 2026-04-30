"""Entity detail drawer — enriched with provenance, warnings, tooltips."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col
import state
from ui.components import (
    risk_badge_html, section_header,
    regulator_badge_html, service_pill_html,
    classification_badge_html, confidence_meter_html,
)

_WORKFLOW = ("Open", "In Review", "Escalated", "Cleared")
_WF_COLOR = {"Open": "#6B7280", "In Review": "#FBBF24",
             "Escalated": "#EF4444", "Cleared": "#34D399"}
_WF_BG    = {"Open": "rgba(107,114,128,0.10)", "In Review": "rgba(251,191,36,0.10)",
             "Escalated": "rgba(239,68,68,0.10)", "Cleared": "rgba(52,211,153,0.10)"}

_SOURCE_LABELS = {
    "serpapi":       ("SerpAPI", "#3DA5E0"),
    "ddg":           ("DuckDuckGo", "#C9A84C"),
    "known":         ("Known Evidence", "#34D399"),
    "seed_watchlist":("Seed Watchlist", "#A78BFA"),
    "web_discovery": ("Web Discovery",  "#F87171"),
}

_SOURCE_FIELD_LABELS = {
    "seed_watchlist": ("📌 Pre-seeded", "rgba(167,139,250,0.10)", "#A78BFA",
                       "This entity was pre-loaded from a known watchlist, not discovered via live search."),
    "web_discovery":  ("🔍 Web Discovery", "rgba(248,113,113,0.10)", "#F87171",
                       "This entity was actively discovered via web search during this screening run."),
}

_SIGNAL_TOOLTIPS = {
    "uae": "Evidence of UAE-facing operations was found — website, app store listing, or social media targeting UAE users.",
    "license": "A licensing signal was detected — the entity appeared in a regulator's public register or referenced a license.",
    "unlicensed": "An unlicensed signal was detected — explicit evidence of operating without authorization was found.",
}


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

    with st.expander(f"📋  {row.get(Col.BRAND, '—')}  ·  Entity Details", expanded=True):
        # ── Warning banner (unlicensed) ──
        _warning_banner(row)
        _sp(6)
        _status_strip(row, session)
        _sp(8)
        _header(row)
        _sp(14)
        _action_buttons(row, session)
        _sp(18)
        _divider()

        left, right = st.columns([3, 2], gap="large")
        with left:
            _sp(4)
            _signals(row)
            _sp(14)
            _rationale(row)
            _sp(14)
            _annotations(row, session)

        with right:
            _workflow(row, session)
            _sp(14)
            _register_match(row)
            _sp(14)
            _metadata(row)

        _sp(12)
        _divider()
        _provenance_footer(row)
        _sp(8)

        c1, _ = st.columns([1, 6])
        with c1:
            if st.button("✕ Close", key="drawer_close"):
                state.set_selected(session, None)
                st.rerun()


def _sp(px: int = 14) -> None:
    st.markdown(f'<div style="height:{px}px;"></div>', unsafe_allow_html=True)


def _divider() -> None:
    st.markdown('<div style="height:1px;background:var(--border);margin:0;"></div>',
                unsafe_allow_html=True)


# ── WARNING BANNER ────────────────────────────────────────────────────────────
def _warning_banner(row: pd.Series) -> None:
    unlicensed = str(row.get(Col.UNLICENSED_SIGNAL, "") or "").lower()
    if unlicensed in ("yes", "true", "1"):
        st.markdown(
            '<div style="background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);'
            'border-left:4px solid #EF4444;border-radius:8px;padding:10px 14px;'
            'display:flex;align-items:center;gap:10px;">'
            '<span style="font-size:18px;">⚠️</span>'
            '<div>'
            '<div style="font-size:12px;font-weight:700;color:#EF4444;">'
            'Unlicensed Signal Detected</div>'
            '<div style="font-size:11px;color:var(--muted);margin-top:2px;">'
            'Evidence of unauthorized operation was found. Prioritize investigation.</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )


# ── STATUS STRIP ──────────────────────────────────────────────────────────────
def _status_strip(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = state.get_workflow(session, eid)
    color   = _WF_COLOR.get(current, "#6B7280")
    bg      = _WF_BG.get(current, "transparent")
    in_wl   = state.in_watchlist(session, eid)
    notes   = state.get_annotations(session, eid)

    wl_badge   = ('<span style="margin-left:8px;font-size:9px;font-weight:700;color:#C9A84C;'
                  'background:rgba(201,168,76,0.10);border-radius:4px;padding:2px 7px;'
                  'font-family:\'IBM Plex Mono\',monospace;">★ WATCHLIST</span>') if in_wl else ""
    note_badge = (f'<span style="margin-left:8px;font-size:9px;color:var(--muted);'
                  f'font-family:\'IBM Plex Mono\',monospace;">💬 {len(notes)} note'
                  f'{"s" if len(notes) != 1 else ""}</span>') if notes else ""

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:6px 12px;'
        f'background:{bg};border-radius:8px;">'
        f'<span style="width:8px;height:8px;border-radius:999px;background:{color};'
        f'display:inline-block;flex-shrink:0;"></span>'
        f'<span style="font-size:11px;font-weight:700;color:{color};'
        f'font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.06em;">{current.upper()}</span>'
        f'{wl_badge}{note_badge}</div>',
        unsafe_allow_html=True,
    )


# ── HEADER ───────────────────────────────────────────────────────────────────
def _header(row: pd.Series) -> None:
    brand  = str(row.get(Col.BRAND,     "—") or "—")
    svc    = str(row.get(Col.SERVICE,   "—") or "—")
    reg    = str(row.get(Col.REGULATOR, "—") or "—")
    level  = int(row.get(Col.RISK_LEVEL, 1))
    action = str(row.get(Col.ACTION,    "") or "")
    url    = str(row.get(Col.SOURCE_URL,"") or "")

    # Source button — prominent in header
    src_btn = (
        f'<a href="{url}" target="_blank" style="display:inline-flex;align-items:center;'
        f'gap:5px;font-size:11px;font-weight:600;color:var(--accent);'
        f'background:var(--accent-s);border:1px solid rgba(201,168,76,0.3);'
        f'border-radius:6px;padding:4px 10px;text-decoration:none;'
        f'font-family:\'IBM Plex Mono\',monospace;margin-top:8px;">'
        f'View Source →</a>'
    ) if url else ""

    act_html = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:var(--accent);background:var(--accent-s);'
        f'border-radius:4px;padding:2px 8px;font-family:\'IBM Plex Mono\',monospace;'
        f'margin-left:8px;">{escape(action)}</span>'
    ) if action else ""

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:22px;font-weight:800;color:var(--text);line-height:1.2;">'
        f'{escape(brand)}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:6px;flex-wrap:wrap;">'
        f'{service_pill_html(svc)}'
        f'{regulator_badge_html(reg)}'
        f'{act_html}'
        f'</div>'
        f'{src_btn}'
        f'</div>'
        f'<div style="flex-shrink:0;margin-left:16px;">{risk_badge_html(level)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── ACTION BUTTONS ────────────────────────────────────────────────────────────
def _action_buttons(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = state.get_workflow(session, eid)
    in_wl   = state.in_watchlist(session, eid)

    c1, c2, c3 = st.columns(3)
    with c1:
        reviewed = current == "Cleared"
        if st.button("✓ Marked Reviewed" if reviewed else "✓ Mark as Reviewed",
                     key=f"act_review_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Open" if reviewed else "Cleared")
            st.rerun()
    with c2:
        escalated = current == "Escalated"
        if st.button("⚑ De-escalate" if escalated else "⚑ Escalate",
                     key=f"act_escalate_{eid}", use_container_width=True):
            state.set_workflow(session, eid, "Open" if escalated else "Escalated")
            st.rerun()
    with c3:
        if st.button("★ Remove Watchlist" if in_wl else "★ Add to Watchlist",
                     key=f"act_watch_{eid}", use_container_width=True):
            state.toggle_watchlist(session, eid)
            st.rerun()


# ── SIGNALS (with tooltips) ───────────────────────────────────────────────────
def _signals(row: pd.Series) -> None:
    section_header("Signals")

    def _val(col): return str(row.get(col, "") or "").lower() in ("yes", "true", "1")

    uae = _val(Col.UAE_PRESENT)
    lic = _val(Col.LICENSE_SIGNAL)
    unl = _val(Col.UNLICENSED_SIGNAL)
    url = str(row.get(Col.SOURCE_URL, "") or "")

    def _card(label: str, val: bool, tooltip: str, link: str = "") -> str:
        color = "#34D399" if val else ("#EF4444" if label == "Unlicensed" and val else "#6B7280")
        if label == "Unlicensed" and val:
            color = "#EF4444"
        elif label == "Unlicensed":
            color = "#6B7280"
        icon = "●" if val else "○"
        txt  = "Yes" if val else "No"

        # License signal → clickable if URL available
        inner = (
            f'<a href="{link}" target="_blank" style="text-decoration:none;">'
            f'<div style="font-size:16px;font-weight:800;color:{color};margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{icon} {txt} ↗</div></a>'
        ) if (val and link and label == "License Signal") else (
            f'<div style="font-size:16px;font-weight:800;color:{color};margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{icon} {txt}</div>'
        )

        border_color = color if val else "var(--border)"
        return (
            f'<div title="{escape(tooltip)}" style="flex:1;background:var(--card);'
            f'border:1px solid {border_color};border-left:3px solid {border_color};'
            f'border-radius:8px;padding:10px 14px;cursor:help;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'font-family:\'IBM Plex Mono\',monospace;">{escape(label)}</div>'
            f'{inner}</div>'
        )

    st.markdown(
        f'<div style="display:flex;gap:8px;">'
        f'{_card("UAE Present",    uae, _SIGNAL_TOOLTIPS["uae"])}'
        f'{_card("License Signal", lic, _SIGNAL_TOOLTIPS["license"], url)}'
        f'{_card("Unlicensed",     unl, _SIGNAL_TOOLTIPS["unlicensed"])}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── RATIONALE + BLOCKQUOTE SNIPPET ───────────────────────────────────────────
def _rationale(row: pd.Series) -> None:
    rationale = row.get(Col.RATIONALE)  or "No rationale recorded."
    snippet   = row.get(Col.SNIPPET)    or ""

    section_header("Analysis")
    st.markdown(
        f'<div style="background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.15);'
        f'border-left:3px solid rgba(37,99,235,0.5);border-radius:8px;'
        f'padding:12px 14px;font-size:12px;color:var(--dim);line-height:1.7;">'
        f'{escape(str(rationale))}</div>',
        unsafe_allow_html=True,
    )

    if snippet:
        _sp(8)
        section_header("Key Evidence")
        st.markdown(
            f'<blockquote style="margin:0;border-left:4px solid var(--accent);'
            f'padding:10px 16px;background:rgba(201,168,76,0.05);border-radius:0 8px 8px 0;">'
            f'<p style="margin:0;font-size:12px;color:var(--dim);line-height:1.65;'
            f'font-style:italic;font-family:\'IBM Plex Mono\',monospace;">'
            f'{escape(str(snippet))}</p>'
            f'</blockquote>',
            unsafe_allow_html=True,
        )


# ── WORKFLOW ──────────────────────────────────────────────────────────────────
def _workflow(row: pd.Series, session) -> None:
    eid     = str(row.get("id", ""))
    current = state.get_workflow(session, eid)

    section_header("Workflow Status")
    new_status = st.radio(
        "Change status", options=_WORKFLOW,
        index=_WORKFLOW.index(current) if current in _WORKFLOW else 0,
        horizontal=False, key=f"drawer_workflow_{eid}",
        label_visibility="collapsed",
    )
    if new_status != current:
        state.set_workflow(session, eid, new_status)
        st.rerun()


# ── REGISTER MATCH ────────────────────────────────────────────────────────────
def _register_match(row: pd.Series) -> None:
    section_header("Register Match")
    matched  = str(row.get(Col.MATCHED_ENTITY, "")    or "")
    category = str(row.get(Col.REGISTER_CATEGORY, "") or "")

    # Treat N/A, nan, none as no match
    no_match = matched.lower() in ("n/a", "na", "nan", "none", "", "—", "-")

    if no_match:
        st.markdown(
            '<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);'
            'border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:8px;">'
            '<span style="color:#EF4444;font-size:14px;">✗</span>'
            '<div>'
            '<div style="font-size:12px;font-weight:600;color:var(--dim);">No match found</div>'
            '<div style="font-size:10px;color:var(--muted);margin-top:2px;">Entity not found in any official register snapshot</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        cat_html = (
            f'<div style="font-size:10px;color:var(--muted);margin-top:2px;">{escape(category)}</div>'
        ) if category and category.lower() not in ("n/a", "na", "nan", "none") else ""
        st.markdown(
            f'<div style="background:rgba(52,211,153,0.06);border:1px solid rgba(52,211,153,0.2);'
            f'border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:8px;">'
            f'<span style="color:#34D399;font-size:14px;">✓</span>'
            f'<div>'
            f'<div style="font-size:12px;font-weight:600;color:var(--dim);">{escape(matched)}</div>'
            f'{cat_html}</div></div>',
            unsafe_allow_html=True,
        )


# ── METADATA ──────────────────────────────────────────────────────────────────
def _metadata(row: pd.Series) -> None:
    section_header("Details")
    conf = str(row.get(Col.CONFIDENCE, "") or "")
    clf  = str(row.get(Col.CLASSIFICATION, "") or "")

    rows_html = ""
    if clf:
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 0;border-bottom:1px solid var(--border);">'
            f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">Classification</span>'
            f'<span>{classification_badge_html(clf)}</span></div>'
        )
    if conf:
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 0;border-bottom:1px solid var(--border);">'
            f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">Confidence</span>'
            f'<span>{confidence_meter_html(conf)}</span></div>'
        )

    if rows_html:
        st.markdown(
            f'<div style="background:var(--card);border:1px solid var(--border);'
            f'border-radius:10px;padding:4px 14px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )


# ── PROVENANCE FOOTER ─────────────────────────────────────────────────────────
def _provenance_footer(row: pd.Series) -> None:
    provider = str(row.get(Col.SEARCH_PROVIDER, "") or "").lower()
    source   = str(row.get(Col.SOURCE,          "") or "").lower()
    query    = str(row.get(Col.DISCOVERY_QUERY, "") or "")

    # Provider badge
    prov_label, prov_color = "Unknown", "#6B7280"
    for key, (lbl, color) in _SOURCE_LABELS.items():
        if key in provider:
            prov_label, prov_color = lbl, color
            break

    # Source tag
    src_label, src_bg, src_color, src_tip = "Unknown Source", "transparent", "#9CA3AF", ""
    for key, (lbl, bg, color, tip) in _SOURCE_FIELD_LABELS.items():
        if key in source:
            src_label, src_bg, src_color, src_tip = lbl, bg, color, tip
            break

    _sp(4)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;'
        f'padding:8px 0;border-top:1px solid var(--border);">'
        f'<span style="font-size:9px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
        f'Data provenance:</span>'
        f'<span style="font-size:9px;font-weight:700;color:{prov_color};'
        f'background:rgba(0,0,0,0.1);border-radius:4px;padding:2px 6px;'
        f'font-family:\'IBM Plex Mono\',monospace;">{escape(prov_label)}</span>'
        f'<span title="{escape(src_tip)}" style="font-size:9px;font-weight:700;'
        f'color:{src_color};background:{src_bg};border-radius:4px;padding:2px 6px;'
        f'font-family:\'IBM Plex Mono\',monospace;cursor:help;">{escape(src_label)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Collapsible discovery query
    if query and query.lower() not in ("nan", "none", "n/a", ""):
        with st.expander("🔍 How was this found?", expanded=False):
            st.markdown(
                f'<div style="font-size:11px;color:var(--muted);'
                f'font-family:\'IBM Plex Mono\',monospace;'
                f'background:var(--card);border:1px solid var(--border);'
                f'border-radius:8px;padding:10px 14px;line-height:1.6;">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
                f'text-transform:uppercase;color:var(--muted);margin-bottom:6px;">'
                f'Discovery Query</div>'
                f'{escape(query)}</div>',
                unsafe_allow_html=True,
            )
            st.caption("This query was used during the screening run to surface this entity. Supports audit trail and reproducibility.")


# ── ANNOTATIONS ───────────────────────────────────────────────────────────────
def _annotations(row: pd.Series, session) -> None:
    eid       = str(row.get("id", ""))
    input_key = f"note_input_{eid}"
    btn_key   = f"note_btn_{eid}"
    notes     = state.get_annotations(session, eid)
    current_user = session.get("current_user", "")

    section_header("Notes", f"{len(notes)} comment{'s' if len(notes) != 1 else ''}")

    if notes:
        for idx, entry in enumerate(notes):
            txt    = entry.get("text",   "") if isinstance(entry, dict) else str(entry)
            ts     = entry.get("ts",     "") if isinstance(entry, dict) else ""
            author = entry.get("author", "You") if isinstance(entry, dict) else "You"
            av_ltr = author[0].upper() if author else "?"

            note_col, del_col = st.columns([9, 1])
            with note_col:
                st.markdown(
                    f'<div style="padding:10px 12px;margin-bottom:4px;background:var(--card);'
                    f'border:1px solid var(--border);border-radius:8px;'
                    f'border-left:2px solid var(--accent);">'
                    f'<div style="display:flex;align-items:center;margin-bottom:5px;">'
                    f'<span style="width:22px;height:22px;border-radius:999px;'
                    f'background:var(--accent-s);display:inline-flex;align-items:center;'
                    f'justify-content:center;font-size:10px;font-weight:700;color:var(--accent);">{av_ltr}</span>'
                    f'<span style="font-size:11px;font-weight:700;color:var(--dim);'
                    f'margin-left:8px;font-family:\'IBM Plex Mono\',monospace;">{escape(author)}</span>'
                    + (f'<span style="color:var(--muted);font-size:10px;font-family:\'IBM Plex Mono\',monospace;margin-left:6px;">{escape(ts)}</span>' if ts else "")
                    + f'</div><div style="font-size:12px;color:var(--text);line-height:1.55;padding-left:30px;">{escape(txt)}</div></div>',
                    unsafe_allow_html=True,
                )
            with del_col:
                st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
                # Allow deletion by the author or by owners
                can_delete = (author == current_user) or session.get("is_owner", False)
                if can_delete:
                    if st.button("✕", key=f"del_note_{eid}_{idx}", help="Delete this comment"):
                        state.delete_annotation(session, eid, idx)
                        session[f"note_nonce_{eid}"] = session.get(f"note_nonce_{eid}", 0) + 1
                        st.rerun()
    else:
        st.markdown('<div style="font-size:11px;color:var(--muted);padding:8px 0;">'
                    'No comments yet. Add one below.</div>', unsafe_allow_html=True)

    nonce = session.get(f"note_nonce_{eid}", 0)
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        note_text = st.text_input("Note", key=f"{input_key}_{nonce}",
                                  placeholder="Add a comment…", label_visibility="collapsed")
    with col_btn:
        add = st.button("Add", key=btn_key, use_container_width=True)

    if add:
        text = (note_text or "").strip()
        if text:
            state.add_annotation(session, eid, text)
            session[f"note_nonce_{eid}"] = session.get(f"note_nonce_{eid}", 0) + 1
            st.rerun()
