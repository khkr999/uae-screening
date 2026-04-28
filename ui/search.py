"""Search & Filter tab — redesigned to match mockup with single search + chips + table."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, HIGH_RISK_THRESHOLD
import services
import state
from models import FilterState
from ui.components import (
    risk_pill_html, regulator_pill_html, action_label,
    empty_state, section_header,
)


# Regulator filter chips (matching mockup: ADGM / CBUAE / FSRA / VARA)
_REG_CHIPS = ["ADGM", "CBUAE", "FSRA", "VARA"]

_SORT_OPTIONS = {
    "risk_desc":   "Risk ↓ High first",
    "risk_asc":    "Risk ↑ Low first",
    "brand_asc":   "Brand A → Z",
    "brand_desc":  "Brand Z → A",
}


def render(df: pd.DataFrame, session) -> None:
    fs = state.get_filter(session)

    # ── Search bar + filter chips ─────────────────────────────────────────────
    _render_search(df, session, fs)
    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = _apply_filters(df, session, fs)

    # ── Result count ──────────────────────────────────────────────────────────
    if fs.query and not filtered.empty:
        st.markdown(
            f'<div style="background:var(--card);border:1px solid var(--border);'
            f'border-left:3px solid var(--gold);border-radius:10px;'
            f'padding:12px 18px;margin-bottom:12px;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="color:var(--gold);font-weight:700;font-size:13px;'
            f'font-family:\'JetBrains Mono\',monospace;">{escape(fs.query)}</span>'
            f'<span style="color:var(--muted);font-size:11px;'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'{len(filtered)} result{"s" if len(filtered) != 1 else ""}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Table ─────────────────────────────────────────────────────────────────
    if filtered.empty:
        empty_state("No matches",
                    "Try clearing filters or adjusting your search.")
        return

    _render_table(filtered, session)


# ── SEARCH BAR ────────────────────────────────────────────────────────────────
def _render_search(df: pd.DataFrame, session, fs: FilterState) -> None:
    # Layout: search input | regulator chips | sort dropdown
    c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 0.5, 0.5, 0.5, 0.5, 0.5, 1.2])

    with c1:
        nonce = session.get("filter_input_nonce", 0)
        typed = st.text_input(
            "Search",
            value=fs.query,
            placeholder="🔍  Search entity, service, or regulator…",
            label_visibility="collapsed",
            key=f"search_input_{nonce}",
        )
        if typed != fs.query:
            state.update_filter(session, query=typed)
            st.rerun()

    # Active reg filter
    active_regs = set(fs.regulators)

    for i, reg in enumerate(_REG_CHIPS):
        col = [c2, c3, c4, c5][i]
        with col:
            is_active = any(reg.lower() in r.lower() for r in active_regs)
            label = ("● " + reg) if is_active else reg
            if st.button(label, key=f"reg_chip_{reg}", use_container_width=True):
                # Toggle: find any matching regulator value in df and toggle it
                matching = [r for r in df[Col.REGULATOR].dropna().unique()
                            if reg.lower() in str(r).lower()]
                new_regs = list(active_regs)
                if is_active:
                    new_regs = [r for r in new_regs if reg.lower() not in r.lower()]
                else:
                    new_regs.extend(matching)
                state.update_filter(session, regulators=new_regs)
                st.rerun()

    with c6:
        if st.button("Clear", use_container_width=True, key="search_clear"):
            session["filter_state"] = FilterState()
            session["filter_input_nonce"] = session.get("filter_input_nonce", 0) + 1
            st.rerun()

    with c7:
        # Sort dropdown
        current_sort = f"{fs.sort_key}_{fs.sort_dir}"
        if current_sort not in _SORT_OPTIONS:
            current_sort = "risk_desc"
        new_sort = st.selectbox(
            "Sort",
            options=list(_SORT_OPTIONS.keys()),
            format_func=lambda k: _SORT_OPTIONS[k],
            index=list(_SORT_OPTIONS.keys()).index(current_sort),
            label_visibility="collapsed",
            key="search_sort",
        )
        if new_sort != current_sort:
            key, direction = new_sort.rsplit("_", 1)
            state.update_filter(session, sort_key=key, sort_dir=direction)
            st.rerun()


# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
def _apply_filters(df: pd.DataFrame, session, fs: FilterState) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()

    # Text search
    if fs.query:
        q = fs.query.strip().lower()
        if q:
            mask = pd.Series(False, index=filtered.index)
            for col in [Col.BRAND, Col.SERVICE, Col.REGULATOR, Col.MATCHED_ENTITY]:
                if col in filtered.columns:
                    mask |= filtered[col].fillna("").astype(str).str.lower().str.contains(q, regex=False)
            filtered = filtered[mask]

    # Regulator filter
    if fs.regulators and Col.REGULATOR in filtered.columns:
        filtered = filtered[filtered[Col.REGULATOR].isin(fs.regulators)]

    # Sort
    sort_col_map = {"risk": Col.RISK_LEVEL, "brand": Col.BRAND}
    sort_col = sort_col_map.get(fs.sort_key, Col.RISK_LEVEL)
    if sort_col in filtered.columns:
        ascending = (fs.sort_dir == "asc")
        filtered = filtered.sort_values(by=sort_col, ascending=ascending,
                                        na_position="last", kind="stable")

    return filtered


# ── TABLE ─────────────────────────────────────────────────────────────────────
def _render_table(df: pd.DataFrame, session) -> None:
    # Table header
    st.markdown(
        '<div class="uae-table-head">'
        '<span>Entity</span>'
        '<span>Regulator</span>'
        '<span>Risk</span>'
        '<span>Alert</span>'
        '<span>Required Action</span>'
        '<span style="text-align:right;">Status</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Show rows (paginate to 50 max for performance)
    display_df = df.head(50)

    rows_container = st.container()
    with rows_container:
        st.markdown('<div style="background:var(--card);border:1px solid var(--border);'
                    'border-radius:12px;overflow:hidden;">', unsafe_allow_html=True)

        for idx, (_, row) in enumerate(display_df.iterrows()):
            _render_table_row(row, session, idx)

        st.markdown('</div>', unsafe_allow_html=True)

    if len(df) > 50:
        st.markdown(
            f'<div style="text-align:center;padding:12px;font-size:11px;'
            f'color:var(--muted);font-family:\'JetBrains Mono\',monospace;">'
            f'Showing first 50 of {len(df):,} entities · Refine your search to see more</div>',
            unsafe_allow_html=True,
        )


def _render_table_row(row: pd.Series, session, idx: int) -> None:
    eid       = str(row.get("id", idx))
    brand     = str(row.get(Col.BRAND, "—") or "—")
    service   = str(row.get(Col.SERVICE, "—") or "—")
    regulator = str(row.get(Col.REGULATOR, "—") or "—")
    level     = int(row.get(Col.RISK_LEVEL, 1))
    action    = str(row.get(Col.ACTION, "") or "")

    # Determine alert: RISK UP for level >= 4, NEW for new sources, else "—"
    alert_html = "—"
    if level >= 4:
        alert_html = '<span class="uae-pill risk-up">↑ RISK UP</span>'
    elif "new" in str(row.get(Col.SOURCE, "")).lower():
        alert_html = '<span class="uae-pill new">+ NEW</span>'

    # Status: derive from workflow state if exists
    status = state.get_workflow(session, eid) if hasattr(state, "get_workflow") else "Pending"
    if status == "Open":
        status = "Pending"

    # Render entire row as HTML for clean look
    row_html = (
        f'<div class="uae-table-row">'
        # Entity column with name + service subtitle
        f'<div>'
        f'<div class="uae-table-cell-name">{escape(brand)}</div>'
        f'<div class="uae-table-cell-svc">{escape(service[:35])}</div>'
        f'</div>'
        # Regulator pill
        f'<div>{regulator_pill_html(regulator)}</div>'
        # Risk pill
        f'<div>{risk_pill_html(level)}</div>'
        # Alert
        f'<div>{alert_html}</div>'
        # Required action
        f'<div class="uae-table-action">{escape(action_label(action))}</div>'
        # Status
        f'<div class="uae-table-status" style="text-align:right;">{escape(status)}</div>'
        f'</div>'
    )
    st.markdown(row_html, unsafe_allow_html=True)

    # Click button (subtle)
    if st.button(f"View {brand}", key=f"tbl_{eid}_{idx}",
                 use_container_width=True):
        state.set_selected(session, eid)
        st.rerun()
