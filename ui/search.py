"""Search & Filter tab — filter toolbar + paginated entity table."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import Col, PAGE_SIZE_OPTIONS, RISK_BY_LEVEL
import services
import state
from models import FilterState
from ui.components import empty_state, risk_badge_html, section_header


def render(df: pd.DataFrame, session) -> None:
    filter_state = state.get_filter(session)
    options = services.get_filter_options(df)

    _render_toolbar(session, filter_state, options)
    page_df, total_matching = services.get_page(df, filter_state)

    if total_matching == 0:
        empty_state("No entities match these filters",
                    "Try clearing some filters or broadening your search.")
        return

    _render_quick_chips(session, filter_state)
    _render_table(page_df)
    _render_pagination(session, filter_state, total_matching)
    _render_export_controls(df, page_df)


# ---------------------------------------------------------------------------
# Toolbar
# ---------------------------------------------------------------------------
def _render_toolbar(session,
                    fs: FilterState,
                    options: dict) -> None:
    with st.container():
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])

        with c1:
            query = st.text_input(
                "Search brand, service, regulator…",
                value=fs.query,
                placeholder="Type to filter",
                label_visibility="collapsed",
                key="filter_query_input",
            )
            if query != fs.query:
                state.update_filter(session, query=query)
                st.rerun()

        with c2:
            risk_labels = {f"{t.label} ({t.level})": t.level
                           for t in RISK_BY_LEVEL.values()}
            selected = st.multiselect(
                "Risk levels",
                options=list(risk_labels.keys()),
                default=[k for k, v in risk_labels.items()
                         if v in fs.risk_levels],
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
            if st.button("Clear", use_container_width=True,
                         key="filter_clear_btn"):
                session["filter_state"] = FilterState()
                st.rerun()


# ---------------------------------------------------------------------------
# Quick chips
# ---------------------------------------------------------------------------
_CHIPS = [
    ("highCritical", "High / Critical"),
    ("needsReview",  "Needs Review"),
    ("licensed",     "Licensed"),
    ("crypto",       "Crypto / VA"),
    ("uaePresent",   "UAE Present"),
    ("unlicensed",   "Unlicensed Signal"),
]


def _render_quick_chips(session, fs: FilterState) -> None:
    cols = st.columns(len(_CHIPS) + 1)
    for idx, (key, label) in enumerate(_CHIPS):
        with cols[idx]:
            active = fs.quick_chip == key
            prefix = "● " if active else ""
            if st.button(f"{prefix}{label}", use_container_width=True,
                         key=f"chip_{key}"):
                state.update_filter(session,
                                    quick_chip=None if active else key)
                st.rerun()
    with cols[-1]:
        if fs.quick_chip and st.button("Reset chip", key="chip_reset",
                                       use_container_width=True):
            state.update_filter(session, quick_chip=None)
            st.rerun()


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------
_DISPLAY_COLUMNS = [
    Col.BRAND, Col.SERVICE, Col.REGULATOR,
    Col.RISK_LEVEL, Col.CLASSIFICATION, Col.ACTION, Col.CONFIDENCE,
]


def _render_table(page_df: pd.DataFrame) -> None:
    cols = [c for c in _DISPLAY_COLUMNS if c in page_df.columns]
    view = page_df[cols].copy()

    # Map risk level → tier label for readability
    view[Col.RISK_LEVEL] = view[Col.RISK_LEVEL].map(
        lambda lvl: f"{lvl} · {RISK_BY_LEVEL.get(int(lvl), RISK_BY_LEVEL[1]).label}"
    )

    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            Col.BRAND: st.column_config.TextColumn("Brand", width="medium"),
            Col.SERVICE: st.column_config.TextColumn("Service"),
            Col.REGULATOR: st.column_config.TextColumn("Regulator",
                                                        width="small"),
            Col.RISK_LEVEL: st.column_config.TextColumn("Risk", width="small"),
            Col.CLASSIFICATION: st.column_config.TextColumn("Classification"),
            Col.ACTION: st.column_config.TextColumn("Action", width="medium"),
            Col.CONFIDENCE: st.column_config.TextColumn("Confidence",
                                                        width="small"),
        },
        height=460,
    )


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
def _render_pagination(session,
                       fs: FilterState,
                       total_matching: int) -> None:
    total_pages = max(1, (total_matching + fs.page_size - 1) // fs.page_size)
    start = (fs.page - 1) * fs.page_size + 1
    end = min(fs.page * fs.page_size, total_matching)

    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 2, 2])
    c1.caption(f"Showing **{start:,}–{end:,}** of **{total_matching:,}**")

    with c2:
        if st.button("← Prev", disabled=fs.page <= 1,
                     use_container_width=True, key="page_prev"):
            state.update_filter(session, page=max(1, fs.page - 1))
            st.rerun()
    with c3:
        if st.button("Next →", disabled=fs.page >= total_pages,
                     use_container_width=True, key="page_next"):
            state.update_filter(session,
                                page=min(total_pages, fs.page + 1))
            st.rerun()
    with c4:
        c4.caption(f"Page **{fs.page}** / {total_pages}")
    with c5:
        new_size = st.selectbox(
            "Page size",
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
# Exports
# ---------------------------------------------------------------------------
def _render_export_controls(full_df: pd.DataFrame,
                            page_df: pd.DataFrame) -> None:
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        csv_bytes, csv_name, csv_mime = services.export(full_df, "csv")
        st.download_button("⬇ CSV (all matching)", data=csv_bytes,
                           file_name=csv_name, mime=csv_mime,
                           use_container_width=True, key="dl_csv")
    with c2:
        xlsx_bytes, xlsx_name, xlsx_mime = services.export(full_df, "xlsx")
        st.download_button("⬇ Excel", data=xlsx_bytes,
                           file_name=xlsx_name, mime=xlsx_mime,
                           use_container_width=True, key="dl_xlsx")
