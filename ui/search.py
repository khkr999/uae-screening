"""Search & Filter tab — grouped view, service chips, action filter, regulator badges."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, PAGE_SIZE_OPTIONS, RISK_BY_LEVEL
import services
import state
from models import FilterState
from ui.components import (
    empty_state, risk_badge_html, section_header,
    service_pill_html, regulator_badge_html, classification_badge_html,
    confidence_meter_html, priority_dots_html, avatar_html, action_icon,
)

_ROW_BG = {
    5: "rgba(239,68,68,0.09)",
    4: "rgba(248,113,113,0.06)",
    3: "rgba(251,191,36,0.05)",
}

# ── Group order + display ─────────────────────────────────────────────────────
_GROUP_ORDER   = ["High Risk", "Needs Review", "Likely Licensed"]
_GROUP_COLORS  = {
    "High Risk":       ("#EF4444", "rgba(239,68,68,0.08)"),
    "Needs Review":    ("#FBBF24", "rgba(251,191,36,0.07)"),
    "Likely Licensed": ("#34D399", "rgba(52,211,153,0.07)"),
}
_GROUP_ICONS   = {"High Risk": "⬆", "Needs Review": "⚑", "Likely Licensed": "✓"}

# ── Quick filter chips ────────────────────────────────────────────────────────
_CHIPS = [
    ("highCritical", "High Risk"),
    ("needsReview",  "Needs Review"),
    ("licensed",     "Licensed"),
    ("crypto",       "Crypto / VA"),
    ("uaePresent",   "UAE Present"),
    ("unlicensed",   "Unlicensed"),
]

# ── Service type chips ────────────────────────────────────────────────────────
_SVC_CHIPS = [
    "BNPL", "Wallet", "VA Exchange", "Payment Gateway",
    "Remittance", "Finance", "Payments",
]

# ── Action icons ──────────────────────────────────────────────────────────────
_ACTION_MAP = {
    "investigate": "🔍 Investigate",
    "review":      "📋 Review",
    "monitor":     "👁 Monitor",
    "no action":   "✓ No Action",
}


def render(df: pd.DataFrame, session) -> None:
    fs      = state.get_filter(session)
    options = services.get_filter_options(df)

    _toolbar(session, fs, options, df)
    _chips_row(session, fs)
    _svc_chips(session, fs, df)

    page_df, total = services.get_page(df, fs)

    if total == 0:
        st.write("")
        empty_state("No entities match these filters",
                    "Try clearing some filters or broadening your search.")
        return

    st.write("")
    _stats(fs, total)
    _grouped_rows(page_df, session)
    _pagination(session, fs, total)
    st.write("")
    _exports(df)


# ── TOOLBAR ──────────────────────────────────────────────────────────────────
def _toolbar(session, fs: FilterState, options: dict, df: pd.DataFrame) -> None:
    brands    = sorted(df[Col.BRAND].dropna().astype(str).unique().tolist()) if Col.BRAND in df.columns else []
    services_ = sorted(df[Col.SERVICE].dropna().astype(str).unique().tolist()) if Col.SERVICE in df.columns else []
    all_opts  = brands + [s for s in services_ if s not in brands]

    # Actions list from data
    actions_raw = df[Col.ACTION].dropna().astype(str).unique().tolist() if Col.ACTION in df.columns else []
    actions_opts = sorted(set(actions_raw))

    c1, c2, c3, c4, c5 = st.columns([3, 1.8, 1.8, 1.8, 0.9])

    with c1:
        typed = st.text_input(
            "Search", value=fs.query,
            placeholder="Search brand or service…",
            label_visibility="collapsed",
            key="filter_text_input",
        )
        if typed and typed != fs.query:
            matches = [o for o in all_opts if typed.lower() in o.lower()][:8]
            if matches:
                for m in matches:
                    if st.button(m, key=f"ac_{m}", use_container_width=True):
                        state.update_filter(session, query=m)
                        st.rerun()
        if typed != fs.query:
            state.update_filter(session, query=typed)
            st.rerun()

    with c2:
        risk_map = {f"{t.label} ({t.level})": t.level for t in RISK_BY_LEVEL.values()}
        sel = st.multiselect(
            "Risk", options=list(risk_map.keys()),
            default=[k for k, v in risk_map.items() if v in fs.risk_levels],
            placeholder="All risk levels",
            label_visibility="collapsed",
            key="filter_risk_input",
        )
        new_levels = sorted(risk_map[k] for k in sel)
        if new_levels != fs.risk_levels:
            state.update_filter(session, risk_levels=new_levels)
            st.rerun()

    with c3:
        # Color-coded regulator dropdown
        reg_opts = options.get("regulators", [])
        regs = st.multiselect(
            "Regulator", options=reg_opts,
            default=fs.regulators,
            placeholder="All regulators",
            label_visibility="collapsed",
            key="filter_reg_input",
        )
        if regs != fs.regulators:
            state.update_filter(session, regulators=regs)
            st.rerun()

    with c4:
        # Action Required filter
        action_filter = session.get("filter_action", "")
        sel_action = st.selectbox(
            "Action", options=[""] + actions_opts,
            index=([""] + actions_opts).index(action_filter) if action_filter in actions_opts else 0,
            format_func=lambda x: "All actions" if x == "" else f"{action_icon(x)} {x}",
            label_visibility="collapsed",
            key="filter_action_select",
        )
        if sel_action != action_filter:
            session["filter_action"] = sel_action
            st.rerun()

    with c5:
        st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True, key="filter_clear_btn"):
            session["filter_state"] = FilterState()
            session["filter_action"] = ""
            session["filter_svc"]    = ""
            st.rerun()


# ── QUICK FILTER CHIPS ────────────────────────────────────────────────────────
def _chips_row(session, fs: FilterState) -> None:
    st.markdown(
        '<div style="margin:10px 0 4px 0;font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Quick Filters</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(_CHIPS) + 1)
    for i, (key, label) in enumerate(_CHIPS):
        with cols[i]:
            active = fs.quick_chip == key
            if st.button(("● " + label) if active else label,
                         use_container_width=True, key=f"chip_{key}"):
                state.update_filter(session, quick_chip=None if active else key)
                st.rerun()
    with cols[-1]:
        if fs.quick_chip and st.button("Reset", key="chip_reset", use_container_width=True):
            state.update_filter(session, quick_chip=None)
            st.rerun()


# ── SERVICE TYPE CHIPS ────────────────────────────────────────────────────────
def _svc_chips(session, fs: FilterState, df: pd.DataFrame) -> None:
    # Only show services that exist in data
    svcs_in_data = set()
    if Col.SERVICE in df.columns:
        for svc in df[Col.SERVICE].dropna().astype(str):
            for chip in _SVC_CHIPS:
                if chip.lower() in svc.lower():
                    svcs_in_data.add(chip)
    if not svcs_in_data:
        return

    st.markdown(
        '<div style="margin:4px 0 4px 0;font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Service Type</div>',
        unsafe_allow_html=True,
    )
    active_svc = session.get("filter_svc", "")
    avail = sorted(svcs_in_data)
    cols  = st.columns(len(avail) + 1)
    for i, svc in enumerate(avail):
        with cols[i]:
            active = active_svc == svc
            if st.button(("● " if active else "") + svc,
                         use_container_width=True, key=f"svc_chip_{svc}"):
                session["filter_svc"] = "" if active else svc
                st.rerun()
    with cols[-1]:
        if active_svc and st.button("Reset", key="svc_chip_reset", use_container_width=True):
            session["filter_svc"] = ""
            st.rerun()


# ── STATS BAR ────────────────────────────────────────────────────────────────
def _stats(fs: FilterState, total: int) -> None:
    start = (fs.page - 1) * fs.page_size + 1
    end   = min(fs.page * fs.page_size, total)
    pages = max(1, (total + fs.page_size - 1) // fs.page_size)
    st.markdown(
        f'<div style="font-size:11px;color:var(--muted);'
        f'font-family:\'IBM Plex Mono\',monospace;margin-bottom:8px;">'
        f'Showing <b style="color:var(--dim);">{start:,}&ndash;{end:,}</b>'
        f' of <b style="color:var(--dim);">{total:,}</b> entities'
        f'&nbsp;&middot;&nbsp; Page {fs.page} / {pages}</div>',
        unsafe_allow_html=True,
    )


# ── GROUPED ENTITY ROWS ───────────────────────────────────────────────────────
def _grouped_rows(page_df: pd.DataFrame, session) -> None:
    """Render rows grouped by the Group field with section dividers."""
    # Apply service chip filter client-side
    active_svc    = session.get("filter_svc", "")
    active_action = session.get("filter_action", "")

    filtered = page_df.copy()
    if active_svc and Col.SERVICE in filtered.columns:
        filtered = filtered[
            filtered[Col.SERVICE].astype(str).str.lower().str.contains(active_svc.lower(), na=False)
        ]
    if active_action and Col.ACTION in filtered.columns:
        filtered = filtered[
            filtered[Col.ACTION].astype(str).str.lower().str.contains(active_action.lower(), na=False)
        ]

    if filtered.empty:
        empty_state("No entities match service/action filter", "Try resetting chips.")
        return

    # Group by Group field if available, else flat
    if Col.GROUP in filtered.columns:
        # Render known groups in order, then any extra groups
        groups_in_data = filtered[Col.GROUP].fillna("Other").unique().tolist()
        ordered = [g for g in _GROUP_ORDER if g in groups_in_data]
        extra   = [g for g in groups_in_data if g not in _GROUP_ORDER]
        for grp in ordered + extra:
            grp_df = filtered[filtered[Col.GROUP].fillna("Other") == grp]
            if grp_df.empty:
                continue
            color, bg = _GROUP_COLORS.get(grp, ("#9CA3AF", "rgba(156,163,175,0.06)"))
            icon       = _GROUP_ICONS.get(grp, "›")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'padding:8px 14px;background:{bg};border-radius:8px;'
                f'margin-bottom:6px;border-left:3px solid {color};">'
                f'<span style="color:{color};font-size:12px;">{icon}</span>'
                f'<span style="font-size:11px;font-weight:700;color:{color};'
                f'font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.08em;">'
                f'{escape(grp)}</span>'
                f'<span style="font-size:10px;color:var(--muted);margin-left:auto;'
                f'font-family:\'IBM Plex Mono\',monospace;">{len(grp_df)} entities</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _render_rows(grp_df, session, bg_override=bg)
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    else:
        _render_rows(filtered, session)


def _render_rows(df: pd.DataFrame, session, bg_override: str = "") -> None:
    # Column headers
    hdr = st.columns([0.4, 2, 1.2, 1, 0.8, 1.6, 0.8])
    for col, h in zip(hdr, ["", "Brand / Service", "Regulator", "Risk", "Conf.", "Classification", ""]):
        col.markdown(
            f'<span style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'font-family:\'IBM Plex Mono\',monospace;">{h}</span>',
            unsafe_allow_html=True,
        )

    for i, (_, row) in enumerate(df.iterrows()):
        level  = int(row.get(Col.RISK_LEVEL, 1)) if Col.RISK_LEVEL in df.columns else 1
        brand  = str(row.get(Col.BRAND,         "—") or "—")
        svc    = str(row.get(Col.SERVICE,        "—") or "—")
        reg    = str(row.get(Col.REGULATOR,      "—") or "—")
        clf    = str(row.get(Col.CLASSIFICATION, "—") or "—")
        conf   = str(row.get(Col.CONFIDENCE,     "—") or "—")
        eid    = str(row.get("id", i))

        stripe = "rgba(255,255,255,0.015)" if i % 2 == 0 else "transparent"
        row_bg = _ROW_BG.get(level, stripe)

        row_cols = st.columns([0.4, 2, 1.2, 1, 0.8, 1.6, 0.8])

        with row_cols[0]:
            st.markdown(
                f'<div style="padding:8px 4px;">{avatar_html(brand, reg, 30)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[1]:
            st.markdown(
                f'<div style="background:{row_bg};border-radius:6px;padding:8px 10px;">'
                f'<div style="font-size:13px;font-weight:700;color:var(--text);">{escape(brand)}</div>'
                f'<div style="margin-top:3px;">{service_pill_html(svc)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            st.markdown(
                f'<div style="padding:8px 4px;">{regulator_badge_html(reg)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[3]:
            st.markdown(
                f'<div style="padding:8px 4px;">{risk_badge_html(level)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[4]:
            st.markdown(
                f'<div style="padding:8px 4px;">{confidence_meter_html(conf)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[5]:
            st.markdown(
                f'<div style="padding:8px 4px;">{classification_badge_html(clf)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[6]:
            if st.button("Details", key=f"row_open_{eid}_{i}", use_container_width=True):
                state.set_selected(st.session_state, eid)
                st.rerun()


# ── PAGINATION ────────────────────────────────────────────────────────────────
def _pagination(session, fs: FilterState, total: int) -> None:
    pages = max(1, (total + fs.page_size - 1) // fs.page_size)
    c1, c2, c3, c4 = st.columns([1, 1, 4, 2])
    with c1:
        if st.button("← Prev", disabled=fs.page <= 1,
                     use_container_width=True, key="page_prev"):
            state.update_filter(session, page=max(1, fs.page - 1))
            st.rerun()
    with c2:
        if st.button("Next →", disabled=fs.page >= pages,
                     use_container_width=True, key="page_next"):
            state.update_filter(session, page=min(pages, fs.page + 1))
            st.rerun()
    with c4:
        new_size = st.selectbox(
            "Per page", options=list(PAGE_SIZE_OPTIONS),
            index=PAGE_SIZE_OPTIONS.index(fs.page_size) if fs.page_size in PAGE_SIZE_OPTIONS else 0,
            label_visibility="collapsed", key="page_size_select",
        )
        if new_size != fs.page_size:
            state.update_filter(session, page_size=new_size, page=1)
            st.rerun()


# ── EXPORT ───────────────────────────────────────────────────────────────────
def _exports(full_df: pd.DataFrame) -> None:
    section_header("Export Data")
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        b, name, mime = services.export(full_df, "csv")
        st.download_button("⬇ CSV", data=b, file_name=name, mime=mime,
                           use_container_width=True, key="dl_csv")
    with c2:
        b, name, mime = services.export(full_df, "xlsx")
        st.download_button("⬇ Excel", data=b, file_name=name, mime=mime,
                           use_container_width=True, key="dl_xlsx")
