"""Search & Filter tab — text autocomplete, styled rows, quick chips."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, PAGE_SIZE_OPTIONS, RISK_BY_LEVEL
import services
import state
from models import FilterState
from ui.components import empty_state, risk_badge_html, section_header

_ROW_BG = {
    5: "rgba(239,68,68,0.09)",
    4: "rgba(248,113,113,0.06)",
    3: "rgba(251,191,36,0.05)",
}

_CHIPS = [
    ("highCritical", "High / Critical"),
    ("needsReview",  "Needs Review"),
    ("licensed",     "Licensed"),
    ("crypto",       "Crypto / VA"),
    ("uaePresent",   "UAE Present"),
    ("unlicensed",   "Unlicensed"),
]


def render(df: pd.DataFrame, session) -> None:
    fs      = state.get_filter(session)
    options = services.get_filter_options(df)

    _toolbar(session, fs, options, df)
    _chips(session, fs)

    page_df, total = services.get_page(df, fs)

    if total == 0:
        st.write("")
        empty_state("No entities match these filters",
                    "Try clearing some filters or broadening your search.")
        return

    st.write("")
    _stats(fs, total)
    _rows(page_df, session)
    _pagination(session, fs, total)
    st.write("")
    _exports(df)


# ── TOOLBAR ─────────────────────────────────────────────────────────────────
def _toolbar(session, fs: FilterState, options: dict, df: pd.DataFrame) -> None:
    # Build suggestion list for autocomplete hint
    brands   = sorted(df[Col.BRAND].dropna().astype(str).unique().tolist()) if Col.BRAND in df.columns else []
    services_= sorted(df[Col.SERVICE].dropna().astype(str).unique().tolist()) if Col.SERVICE in df.columns else []
    all_opts = brands + [s for s in services_ if s not in brands]

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])

    with c1:
        # Text input for typing — shows matching suggestions below
        typed = st.text_input(
            "Search",
            value=fs.query,
            placeholder="Search brand or service…",
            label_visibility="collapsed",
            key="filter_text_input",
        )
        # Show autocomplete suggestions when typing
        if typed and typed != fs.query:
            matches = [o for o in all_opts if typed.lower() in o.lower()][:8]
            if matches:
                st.markdown(
                    '<div style="background:var(--card);border:1px solid var(--border);'
                    'border-radius:8px;overflow:hidden;margin-top:2px;">',
                    unsafe_allow_html=True,
                )
                for m in matches:
                    if st.button(m, key=f"ac_{m}", use_container_width=True):
                        state.update_filter(session, query=m)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        if typed != fs.query and not any(
            typed.lower() in o.lower() for o in all_opts[:8]
        ):
            state.update_filter(session, query=typed)
            st.rerun()

    with c2:
        risk_map = {f"{t.label} ({t.level})": t.level for t in RISK_BY_LEVEL.values()}
        sel = st.multiselect(
            "Risk",
            options=list(risk_map.keys()),
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
        regs = st.multiselect(
            "Regulator",
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


# ── QUICK CHIPS ──────────────────────────────────────────────────────────────
def _chips(session, fs: FilterState) -> None:
    st.markdown(
        '<div style="margin:10px 0 6px 0;font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Quick Filters</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(_CHIPS) + 1)
    for i, (key, label) in enumerate(_CHIPS):
        with cols[i]:
            active = fs.quick_chip == key
            lbl    = ("● " + label) if active else label
            if st.button(lbl, use_container_width=True, key=f"chip_{key}"):
                state.update_filter(session, quick_chip=None if active else key)
                st.rerun()
    with cols[-1]:
        if fs.quick_chip and st.button("Reset", key="chip_reset", use_container_width=True):
            state.update_filter(session, quick_chip=None)
            st.rerun()


# ── STATS BAR ────────────────────────────────────────────────────────────────
def _stats(fs: FilterState, total: int) -> None:
    start = (fs.page - 1) * fs.page_size + 1
    end   = min(fs.page * fs.page_size, total)
    pages = max(1, (total + fs.page_size - 1) // fs.page_size)
    st.markdown(
        f'<div style="font-size:11px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;'
        f'margin-bottom:8px;">'
        f'Showing <b style="color:var(--dim);">{start:,}&ndash;{end:,}</b>'
        f' of <b style="color:var(--dim);">{total:,}</b> entities'
        f'&nbsp;&middot;&nbsp; Page {fs.page} / {pages}</div>',
        unsafe_allow_html=True,
    )


# ── STYLED ENTITY ROWS ───────────────────────────────────────────────────────
def _rows(page_df: pd.DataFrame, session) -> None:
    # Column header
    hdr_cols = st.columns([2, 1.2, 1, 0.8, 2, 1])
    headers  = ["Brand / Service", "Regulator", "Risk", "Conf.", "Classification", ""]
    for col, h in zip(hdr_cols, headers):
        col.markdown(
            f'<span style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'font-family:\'IBM Plex Mono\',monospace;">{h}</span>',
            unsafe_allow_html=True,
        )

    for i, (_, row) in enumerate(page_df.iterrows()):
        level  = int(row.get(Col.RISK_LEVEL, 1)) if Col.RISK_LEVEL in page_df.columns else 1
        brand  = str(row.get(Col.BRAND,         "—") or "—")
        svc    = str(row.get(Col.SERVICE,        "—") or "—")
        reg    = str(row.get(Col.REGULATOR,      "—") or "—")
        clf    = str(row.get(Col.CLASSIFICATION, "—") or "—")
        conf   = str(row.get(Col.CONFIDENCE,     "—") or "—")
        eid    = str(row.get("id", i))

        bg     = _ROW_BG.get(level, "transparent")
        stripe = "rgba(255,255,255,0.018)" if i % 2 == 0 else "transparent"
        row_bg = bg if bg != "transparent" else stripe
        badge  = risk_badge_html(level)
        clf_s  = (escape(clf[:55]) + "…") if len(clf) > 55 else escape(clf)

        row_cols = st.columns([2, 1.2, 1, 0.8, 2, 1])

        # Wrap the data columns in a visual background
        container_style = (
            f'background:{row_bg};border-radius:8px;'
            f'border:1px solid var(--border);padding:10px 0;'
        )

        with row_cols[0]:
            st.markdown(
                f'<div style="{container_style} padding-left:14px;">'
                f'<div style="font-size:13px;font-weight:700;color:var(--text);">{escape(brand)}</div>'
                f'<div style="font-size:10px;color:var(--muted);margin-top:1px;'
                f'font-family:\'IBM Plex Mono\',monospace;">{escape(svc)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with row_cols[1]:
            st.markdown(
                f'<div style="{container_style} font-size:11px;color:var(--dim);'
                f'font-family:\'IBM Plex Mono\',monospace;padding-left:8px;">'
                f'{escape(reg)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            st.markdown(
                f'<div style="{container_style} padding-left:8px;">{badge}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[3]:
            st.markdown(
                f'<div style="{container_style} font-size:11px;color:var(--dim);'
                f'font-family:\'IBM Plex Mono\',monospace;padding-left:8px;">'
                f'{escape(conf)}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[4]:
            st.markdown(
                f'<div style="{container_style} font-size:11px;color:var(--dim);'
                f'padding-left:8px;">{clf_s}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[5]:
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
            "Per page",
            options=list(PAGE_SIZE_OPTIONS),
            index=PAGE_SIZE_OPTIONS.index(fs.page_size) if fs.page_size in PAGE_SIZE_OPTIONS else 0,
            label_visibility="collapsed",
            key="page_size_select",
        )
        if new_size != fs.page_size:
            state.update_filter(session, page_size=new_size, page=1)
            st.rerun()


# ── EXPORT ────────────────────────────────────────────────────────────────────
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
