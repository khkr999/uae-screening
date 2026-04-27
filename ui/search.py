"""Search & Filter tab — autocomplete search, styled card rows, quick chips."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, PAGE_SIZE_OPTIONS, RISK_BY_LEVEL
import services
import state
from models import FilterState
from ui.components import empty_state, risk_badge_html, section_header

_ROW_HIGHLIGHTS = {
    5: "rgba(239,68,68,0.08)",
    4: "rgba(248,113,113,0.06)",
    3: "rgba(251,191,36,0.05)",
}

_CHIP_DEFS = [
    ("highCritical", "High / Critical"),
    ("needsReview",  "Needs Review"),
    ("licensed",     "Licensed"),
    ("crypto",       "Crypto / VA"),
    ("uaePresent",   "UAE Present"),
    ("unlicensed",   "Unlicensed"),
]


def render(df: pd.DataFrame, session) -> None:
    filter_state = state.get_filter(session)
    options      = services.get_filter_options(df)

    _render_toolbar(session, filter_state, options, df)
    _render_quick_chips(session, filter_state)

    page_df, total_matching = services.get_page(df, filter_state)

    if total_matching == 0:
        st.write("")
        empty_state(
            "No entities match these filters",
            "Try clearing some filters or broadening your search.",
        )
        return

    st.write("")
    _render_stats_bar(filter_state, total_matching)
    _render_entity_rows(page_df, session)
    _render_pagination(session, filter_state, total_matching)
    st.write("")
    _render_export_controls(df)


# ---------------------------------------------------------------------------
# Toolbar  — autocomplete via selectbox (no extra packages)
# ---------------------------------------------------------------------------
def _render_toolbar(session, fs: FilterState, options: dict, df: pd.DataFrame) -> None:
    brand_opts   = sorted(df[Col.BRAND].dropna().astype(str).unique().tolist()) if Col.BRAND in df.columns else []
    service_opts = sorted(df[Col.SERVICE].dropna().astype(str).unique().tolist()) if Col.SERVICE in df.columns else []
    # merge: brands first, then services not already in brands
    ac_opts = [""] + brand_opts + [s for s in service_opts if s not in brand_opts]

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])

    with c1:
        ac_idx = ac_opts.index(fs.query) if fs.query in ac_opts else 0
        chosen = st.selectbox(
            "Search",
            options=ac_opts,
            index=ac_idx,
            format_func=lambda x: "Search brand or service…" if x == "" else x,
            label_visibility="collapsed",
            key="filter_ac_select",
        )
        if chosen != fs.query:
            state.update_filter(session, query=chosen)
            st.rerun()

    with c2:
        risk_labels = {f"{t.label} ({t.level})": t.level for t in RISK_BY_LEVEL.values()}
        selected = st.multiselect(
            "Risk levels",
            options=list(risk_labels.keys()),
            default=[k for k, v in risk_labels.items() if v in fs.risk_levels],
            placeholder="All risk levels",
            label_visibility="collapsed",
            key="filter_risk_input",
        )
        new_levels = sorted(risk_labels[k] for k in selected)
        if new_levels != fs.risk_levels:
            state.update_filter(session, risk_levels=new_levels)
            st.rerun()

    with c3:
        regs = st.multiselect(
            "Regulators",
            options=options["regulators"],
            default=fs.regulators,
            placeholder="All regulators",
            label_visibility="collapsed",
            key="filter_reg_input",
        )
        if regs != fs.regulators:
            state.update_filter(session, regulators=regs)
            st.rerun()

    with c4:
        st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True, key="filter_clear_btn"):
            session["filter_state"] = FilterState()
            st.rerun()


# ---------------------------------------------------------------------------
# Quick chips
# ---------------------------------------------------------------------------
def _render_quick_chips(session, fs: FilterState) -> None:
    st.markdown(
        '<div style="margin:10px 0 6px 0;font-size:10px;font-weight:700;'
        'color:var(--muted);letter-spacing:0.1em;text-transform:uppercase;'
        'font-family:\'IBM Plex Mono\',monospace;">Quick Filters</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(_CHIP_DEFS) + 1)
    for idx, (key, label) in enumerate(_CHIP_DEFS):
        with cols[idx]:
            active    = fs.quick_chip == key
            btn_label = ("● " + label) if active else label
            if st.button(btn_label, use_container_width=True, key=f"chip_{key}"):
                state.update_filter(session, quick_chip=None if active else key)
                st.rerun()
    with cols[-1]:
        if fs.quick_chip and st.button("Reset", key="chip_reset", use_container_width=True):
            state.update_filter(session, quick_chip=None)
            st.rerun()


# ---------------------------------------------------------------------------
# Stats bar
# ---------------------------------------------------------------------------
def _render_stats_bar(fs: FilterState, total_matching: int) -> None:
    start       = (fs.page - 1) * fs.page_size + 1
    end         = min(fs.page * fs.page_size, total_matching)
    total_pages = max(1, (total_matching + fs.page_size - 1) // fs.page_size)
    st.markdown(
        f'<div style="font-size:11px;color:var(--muted);'
        f'font-family:\'IBM Plex Mono\',monospace;margin-bottom:8px;padding:0 2px;">'
        f'Showing <span style="color:var(--dim);font-weight:600;">{start:,}&ndash;{end:,}</span>'
        f' of <span style="color:var(--dim);font-weight:600;">{total_matching:,}</span> entities'
        f'&nbsp;&middot;&nbsp; Page {fs.page} / {total_pages}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Styled entity rows  (replaces raw st.dataframe)
# ---------------------------------------------------------------------------
def _render_entity_rows(page_df: pd.DataFrame, session) -> None:
    # Column headers
    st.markdown(
        '<div style="display:grid;grid-template-columns:2fr 1.2fr 1fr 0.8fr 2fr;'
        'gap:12px;padding:6px 14px;margin-bottom:2px;">'
        + "".join(
            f'<span style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'font-family:\'IBM Plex Mono\',monospace;">{h}</span>'
            for h in ["Brand / Service", "Regulator", "Risk", "Conf.", "Classification"]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    for i, (_, row) in enumerate(page_df.iterrows()):
        level      = int(row.get(Col.RISK_LEVEL, 1)) if Col.RISK_LEVEL in page_df.columns else 1
        brand      = str(row.get(Col.BRAND,         "—") or "—")
        service    = str(row.get(Col.SERVICE,        "—") or "—")
        regulator  = str(row.get(Col.REGULATOR,      "—") or "—")
        clf        = str(row.get(Col.CLASSIFICATION, "—") or "—")
        confidence = str(row.get(Col.CONFIDENCE,     "—") or "—")
        entity_id  = str(row.get("id", i))

        bg       = _ROW_HIGHLIGHTS.get(level, "transparent")
        stripe   = "rgba(255,255,255,0.015)" if i % 2 == 0 else "transparent"
        row_bg   = bg if bg != "transparent" else stripe
        badge    = risk_badge_html(level)
        clf_disp = (escape(clf[:58]) + "…") if len(clf) > 58 else escape(clf)

        st.markdown(
            f'<div style="display:grid;grid-template-columns:2fr 1.2fr 1fr 0.8fr 2fr;'
            f'gap:12px;padding:10px 14px;border-radius:8px;background:{row_bg};'
            f'border:1px solid var(--border);margin-bottom:3px;">'
            f'<div>'
            f'<div style="font-size:13px;font-weight:700;color:var(--text);">{escape(brand)}</div>'
            f'<div style="font-size:10px;color:var(--muted);margin-top:1px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{escape(service)}</div>'
            f'</div>'
            f'<div style="font-size:11px;color:var(--dim);align-self:center;'
            f'font-family:\'IBM Plex Mono\',monospace;">{escape(regulator)}</div>'
            f'<div style="align-self:center;">{badge}</div>'
            f'<div style="font-size:11px;color:var(--dim);align-self:center;'
            f'font-family:\'IBM Plex Mono\',monospace;">{escape(confidence)}</div>'
            f'<div style="font-size:11px;color:var(--dim);align-self:center;">{clf_disp}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        open_key = f"row_open_{entity_id}_{i}"
        if st.button("Open Details", key=open_key):
            state.set_selected(st.session_state, entity_id)
            st.rerun()


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
def _render_pagination(session, fs: FilterState, total_matching: int) -> None:
    total_pages = max(1, (total_matching + fs.page_size - 1) // fs.page_size)
    c1, c2, c3, c4 = st.columns([1, 1, 4, 2])

    with c1:
        if st.button("Prev", disabled=fs.page <= 1,
                     use_container_width=True, key="page_prev"):
            state.update_filter(session, page=max(1, fs.page - 1))
            st.rerun()
    with c2:
        if st.button("Next", disabled=fs.page >= total_pages,
                     use_container_width=True, key="page_next"):
            state.update_filter(session, page=min(total_pages, fs.page + 1))
            st.rerun()
    with c4:
        new_size = st.selectbox(
            "Rows per page",
            options=list(PAGE_SIZE_OPTIONS),
            index=PAGE_SIZE_OPTIONS.index(fs.page_size)
                  if fs.page_size in PAGE_SIZE_OPTIONS else 0,
            label_visibility="collapsed",
            key="page_size_select",
        )
        if new_size != fs.page_size:
            state.update_filter(session, page_size=new_size, page=1)
            st.rerun()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def _render_export_controls(full_df: pd.DataFrame) -> None:
    section_header("Export Data")
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        csv_bytes, csv_name, csv_mime = services.export(full_df, "csv")
        st.download_button(
            "Download CSV",
            data=csv_bytes, file_name=csv_name, mime=csv_mime,
            use_container_width=True, key="dl_csv",
        )
    with c2:
        xlsx_bytes, xlsx_name, xlsx_mime = services.export(full_df, "xlsx")
        st.download_button(
            "Download Excel",
            data=xlsx_bytes, file_name=xlsx_name, mime=xlsx_mime,
            use_container_width=True, key="dl_xlsx",
        )
