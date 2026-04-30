"""Search & Filter tab — accurate stats, highlighted active filters, grouped service types."""
from __future__ import annotations
from html import escape
import pandas as pd
import streamlit as st

from config import Col, PAGE_SIZE_OPTIONS, RISK_BY_LEVEL
from processing import apply_filters
import services
import state
from models import FilterState
from ui.components import (
    empty_state, risk_badge_html, section_header,
    service_pill_html, regulator_badge_html, classification_badge_html,
    confidence_meter_html, avatar_html, action_icon,
)

# Quick filter chips — key matches processing._QUICK_CHIP_FILTERS
_CHIPS = [
    ("highCritical", "🔴  High Risk"),
    ("needsReview",  "🟡  Needs Review"),
    ("licensed",     "🟢  Licensed"),
    ("crypto",       "🔷  Crypto / VA"),
    ("uaePresent",   "🇦🇪  UAE Present"),
    ("unlicensed",   "⚠️  Unlicensed"),
]

# Grouped service categories — maps display label → list of substrings to match
_SVC_GROUPS = {
    "Banking":          ["banking"],
    "Exchange":         ["money exchange", "exchange – business"],
    "Payments":         ["payment", "retail payment", "merchant acquiring"],
    "Wallet / SVF":     ["stored value", "wallet", "prepaid"],
    "BNPL":             ["bnpl", "short-term credit", "buy now"],
    "Finance":          ["finance company", "finance – conventional", "finance – islamic",
                         "consumer lending", "sme lending", "trade finance", "invoice finance",
                         "earned wage access", "ewa"],
    "Remittance":       ["remittance", "money transfer", "international transfer"],
    "Crypto / VA":      ["virtual asset", "crypto", "payment token"],
}

_ROW_TINT = {
    5: "rgba(239,68,68,0.07)",
    4: "rgba(248,113,113,0.05)",
    3: "rgba(251,191,36,0.04)",
}


def _svc_group_for(svc: str) -> str | None:
    """Return the group label for a service string, or None."""
    s = svc.lower()
    for label, keywords in _SVC_GROUPS.items():
        if any(k in s for k in keywords):
            return label
    return None


def _apply_svc_filter(df: pd.DataFrame, session) -> pd.DataFrame:
    active = session.get("filter_svc", "")
    if not active or Col.SERVICE not in df.columns:
        return df
    keywords = _SVC_GROUPS.get(active, [active.lower()])
    mask = df[Col.SERVICE].fillna("").astype(str).str.lower().apply(
        lambda s: any(k in s for k in keywords)
    )
    return df[mask]


def render(df: pd.DataFrame, session) -> None:
    fs      = state.get_filter(session)
    options = services.get_filter_options(df)

    _toolbar(session, fs, options, df)
    _chips_row(session, fs, df)
    _svc_chips(session, df)

    # Get full filtered set (all pages) for accurate totals
    all_filtered = _apply_svc_filter(apply_filters(df, fs), session)
    total        = len(all_filtered)

    if total == 0:
        st.write("")
        empty_state("No entities match these filters",
                    "Try clearing some filters or broadening your search.")
        return

    # Paginate from the full filtered set
    from processing import paginate
    page_df = paginate(all_filtered, fs.page, fs.page_size)

    st.write("")
    _stats_bar(fs, total, all_filtered)
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    _render_table(page_df, session)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    _pagination(session, fs, total)
    st.write("")
    _exports(df)


# ── TOOLBAR ───────────────────────────────────────────────────────────────────
def _toolbar(session, fs: FilterState, options: dict, df: pd.DataFrame) -> None:
    brands    = sorted(df[Col.BRAND].dropna().astype(str).unique().tolist()) if Col.BRAND in df.columns else []
    services_ = sorted(df[Col.SERVICE].dropna().astype(str).unique().tolist()) if Col.SERVICE in df.columns else []
    all_opts  = brands + [s for s in services_ if s not in brands]

    c1, c2, c3, c4 = st.columns([3, 1.8, 1.8, 0.9])

    with c1:
        nonce = session.get("filter_input_nonce", 0)
        typed = st.text_input(
            "Search", value=fs.query,
            placeholder="🔍  Search by brand, service, regulator…",
            label_visibility="collapsed",
            key=f"filter_text_{nonce}",
        )
        if typed != fs.query:
            state.update_filter(session, query=typed)
            st.rerun()

    with c2:
        risk_map = {
            t.label: t.level
            for t in sorted(RISK_BY_LEVEL.values(), key=lambda t: t.level, reverse=True)
        }
        sel = st.multiselect(
            "Risk", options=list(risk_map.keys()),
            default=[k for k, v in risk_map.items() if v in fs.risk_levels],
            placeholder="All risk levels",
            label_visibility="collapsed",
            key="filter_risk",
        )
        new_levels = sorted(risk_map[k] for k in sel)
        if new_levels != fs.risk_levels:
            state.update_filter(session, risk_levels=new_levels)
            st.rerun()

    with c3:
        reg_opts = options.get("regulators", [])
        regs = st.multiselect(
            "Regulator", options=reg_opts,
            default=fs.regulators,
            placeholder="All regulators",
            label_visibility="collapsed",
            key="filter_reg",
        )
        if regs != fs.regulators:
            state.update_filter(session, regulators=regs)
            st.rerun()

    with c4:
        st.markdown('<div style="margin-top:4px;"></div>', unsafe_allow_html=True)
        if st.button("✕  Clear all", use_container_width=True, key="filter_clear"):
            session["filter_state"]       = FilterState()
            session["filter_svc"]         = ""
            session["filter_input_nonce"] = session.get("filter_input_nonce", 0) + 1
            st.rerun()


# ── QUICK FILTER CHIPS — with active highlighting ─────────────────────────────
def _chips_row(session, fs: FilterState, df: pd.DataFrame) -> None:
    # Pre-compute true counts for each chip so labels are accurate
    counts = _chip_counts(df)

    st.markdown(
        '<div style="margin:12px 0 5px 0;font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Quick Filters</div>',
        unsafe_allow_html=True,
    )

    # Render active chip highlight via CSS injection
    active_chip = fs.quick_chip
    if active_chip:
        st.markdown(
            f'<style>[data-testid="stButton"] button[kind="secondary"]'
            f'[aria-label*="{active_chip}"] {{}}</style>',
            unsafe_allow_html=True,
        )

    cols = st.columns(len(_CHIPS) + 1)
    for i, (key, label) in enumerate(_CHIPS):
        with cols[i]:
            active = fs.quick_chip == key
            count  = counts.get(key, 0)
            # Show count in label, and visually distinguish active state with prefix
            display = f"✓ {label} ({count})" if active else f"{label} ({count})"
            if st.button(display, use_container_width=True, key=f"chip_{key}"):
                state.update_filter(session, quick_chip=None if active else key)
                st.rerun()

    with cols[-1]:
        if active_chip:
            if st.button("✕ Reset", key="chip_reset", use_container_width=True):
                state.update_filter(session, quick_chip=None)
                st.rerun()


def _chip_counts(df: pd.DataFrame) -> dict[str, int]:
    """True counts from the full dataset for each chip."""
    from config import HIGH_RISK_THRESHOLD, REVIEW_MIN, REVIEW_MAX
    rl  = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL in df.columns else pd.Series(dtype=int)
    return {
        "highCritical": int((rl >= HIGH_RISK_THRESHOLD).sum()),
        "needsReview":  int(rl.between(REVIEW_MIN, REVIEW_MAX).sum()),
        "licensed":     int((rl == 0).sum()),
        "crypto":       int(df[Col.SERVICE].fillna("").astype(str).str.lower()
                            .str.contains(r"crypto|virtual asset|token|stable", regex=True).sum())
                        if Col.SERVICE in df.columns else 0,
        "uaePresent":   int((df[Col.UAE_PRESENT] == True).sum())  # noqa: E712
                        if Col.UAE_PRESENT in df.columns else 0,
        "unlicensed":   int((df[Col.UNLICENSED_SIGNAL] == True).sum())  # noqa: E712
                        if Col.UNLICENSED_SIGNAL in df.columns else 0,
    }


# ── SERVICE TYPE CHIPS — grouped + highlighted ────────────────────────────────
def _svc_chips(session, df: pd.DataFrame) -> None:
    if Col.SERVICE not in df.columns:
        return

    # Only show groups that have at least 1 entity in the data
    groups_present = []
    for label, keywords in _SVC_GROUPS.items():
        mask = df[Col.SERVICE].fillna("").astype(str).str.lower().apply(
            lambda s: any(k in s for k in keywords)
        )
        count = int(mask.sum())
        if count > 0:
            groups_present.append((label, count))

    if not groups_present:
        return

    st.markdown(
        '<div style="margin:6px 0 5px 0;font-size:10px;font-weight:700;color:var(--muted);'
        'letter-spacing:0.1em;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace;">'
        'Service Type</div>',
        unsafe_allow_html=True,
    )

    active_svc = session.get("filter_svc", "")
    cols = st.columns(len(groups_present) + 1)
    for i, (label, count) in enumerate(groups_present):
        with cols[i]:
            active  = active_svc == label
            display = f"✓ {label} ({count})" if active else f"{label} ({count})"
            if st.button(display, use_container_width=True, key=f"svc_{label}"):
                session["filter_svc"] = "" if active else label
                st.rerun()

    with cols[-1]:
        if active_svc:
            if st.button("✕ Reset", key="svc_reset", use_container_width=True):
                session["filter_svc"] = ""
                st.rerun()


# ── STATS BAR — accurate totals from full filtered set ───────────────────────
def _stats_bar(fs: FilterState, total: int, all_filtered: pd.DataFrame) -> None:
    from config import HIGH_RISK_THRESHOLD, REVIEW_MIN, REVIEW_MAX
    start = (fs.page - 1) * fs.page_size + 1
    end   = min(fs.page * fs.page_size, total)
    pages = max(1, (total + fs.page_size - 1) // fs.page_size)

    rl      = all_filtered[Col.RISK_LEVEL].astype(int) if Col.RISK_LEVEL in all_filtered.columns else pd.Series(dtype=int)
    high    = int((rl >= HIGH_RISK_THRESHOLD).sum())
    review  = int(rl.between(REVIEW_MIN, REVIEW_MAX).sum())
    lic     = int((rl == 0).sum())

    def pill(count, label, color, bg, border):
        return (
            f'<span style="background:{bg};color:{color};border:1px solid {border};'
            f'border-radius:5px;padding:2px 9px;font-size:9px;font-weight:700;'
            f'margin-left:8px;font-family:\'IBM Plex Mono\',monospace;">'
            f'{count:,} {label}</span>'
        )

    pills = ""
    if high:
        pills += pill(high,   "HIGH RISK", "#EF4444", "rgba(239,68,68,0.10)", "rgba(239,68,68,0.25)")
    if review:
        pills += pill(review, "REVIEW",    "#FBBF24", "rgba(251,191,36,0.10)", "rgba(251,191,36,0.25)")
    if lic:
        pills += pill(lic,    "LICENSED",  "#34D399", "rgba(52,211,153,0.10)", "rgba(52,211,153,0.25)")

    st.markdown(
        f'<div style="display:flex;align-items:center;padding:9px 16px;'
        f'background:var(--card);border:1px solid var(--border);border-radius:8px;">'
        f'<span style="font-size:11px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
        f'Showing <b style="color:var(--dim);">{start:,}–{end:,}</b>'
        f' of <b style="color:var(--dim);">{total:,}</b> entities'
        f'&nbsp;·&nbsp; Page {fs.page} / {pages}</span>'
        f'{pills}</div>',
        unsafe_allow_html=True,
    )


# ── TABLE ─────────────────────────────────────────────────────────────────────
def _render_table(df: pd.DataFrame, session) -> None:
    headers = ["Brand / Service", "Regulator", "Risk", "Confidence", "Classification"]
    header_cells = "".join(
        f'<span style="font-size:9px;font-weight:600;letter-spacing:0.10em;'
        f'text-transform:uppercase;color:var(--muted);'
        f'font-family:\'IBM Plex Sans\',sans-serif;">{h}</span>'
        for h in headers
    )
    st.markdown(
        f'<div style="display:grid;'
        f'grid-template-columns:44px 2.2fr 1fr 0.9fr 0.85fr 1.8fr 90px;'
        f'padding:0 4px 9px 4px;'
        f'border-bottom:1px solid var(--border);margin-bottom:4px;">'
        f'<span></span>{header_cells}<span></span></div>',
        unsafe_allow_html=True,
    )

    for i, (_, row) in enumerate(df.iterrows()):
        level = int(row.get(Col.RISK_LEVEL, 1)) if Col.RISK_LEVEL in df.columns else 1
        brand = str(row.get(Col.BRAND,         "—") or "—")
        svc   = str(row.get(Col.SERVICE,        "—") or "—")
        reg   = str(row.get(Col.REGULATOR,      "—") or "—")
        clf   = str(row.get(Col.CLASSIFICATION, "—") or "—")
        conf  = str(row.get(Col.CONFIDENCE,     "—") or "—")
        eid   = str(row.get("id", i))

        alt_bg = "rgba(255,255,255,0.012)" if i % 2 == 0 else "transparent"
        row_bg = _ROW_TINT.get(level, alt_bg)

        row_cols = st.columns([0.35, 2.2, 1.0, 0.9, 0.85, 1.8, 0.75])
        with row_cols[0]:
            st.markdown(f'<div style="padding:10px 4px 6px 0;">{avatar_html(brand, reg, 32)}</div>',
                        unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(
                f'<div style="background:{row_bg};border-radius:6px;padding:8px 10px;margin:3px 0;">'
                f'<div style="font-size:13px;font-weight:700;color:var(--text);">{escape(brand)}</div>'
                f'<div style="margin-top:4px;">{service_pill_html(svc)}</div></div>',
                unsafe_allow_html=True)
        with row_cols[2]:
            st.markdown(f'<div style="padding:10px 4px 6px 4px;">{regulator_badge_html(reg)}</div>',
                        unsafe_allow_html=True)
        with row_cols[3]:
            st.markdown(f'<div style="padding:10px 4px 6px 4px;">{risk_badge_html(level)}</div>',
                        unsafe_allow_html=True)
        with row_cols[4]:
            st.markdown(f'<div style="padding:10px 4px 6px 4px;">{confidence_meter_html(conf)}</div>',
                        unsafe_allow_html=True)
        with row_cols[5]:
            st.markdown(f'<div style="padding:10px 4px 6px 4px;">{classification_badge_html(clf)}</div>',
                        unsafe_allow_html=True)
        with row_cols[6]:
            st.markdown('<div style="margin-top:6px;"></div>', unsafe_allow_html=True)
            if st.button("Details →", key=f"row_open_{eid}_{i}", use_container_width=True):
                state.set_selected(st.session_state, eid)
                st.rerun()

        st.markdown(
            '<div style="height:1px;background:var(--border);opacity:0.4;margin:0 2px;"></div>',
            unsafe_allow_html=True)


# ── PAGINATION ────────────────────────────────────────────────────────────────
def _pagination(session, fs: FilterState, total: int) -> None:
    pages = max(1, (total + fs.page_size - 1) // fs.page_size)
    c1, c2, c3, c4 = st.columns([1, 1, 3, 1.5])
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
    with c3:
        st.markdown(
            f'<div style="text-align:center;padding-top:8px;font-size:11px;'
            f'color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
            f'Page {fs.page} of {pages}</div>',
            unsafe_allow_html=True)
    with c4:
        new_size = st.selectbox(
            "Per page", options=list(PAGE_SIZE_OPTIONS),
            index=PAGE_SIZE_OPTIONS.index(fs.page_size) if fs.page_size in PAGE_SIZE_OPTIONS else 0,
            label_visibility="collapsed", key="page_size_select",
            format_func=lambda x: f"{x} per page",
        )
        if new_size != fs.page_size:
            state.update_filter(session, page_size=new_size, page=1)
            st.rerun()


# ── EXPORT ───────────────────────────────────────────────────────────────────
def _exports(full_df: pd.DataFrame) -> None:
    st.markdown(
        '<div style="height:1px;background:var(--border);margin:4px 0 16px 0;"></div>',
        unsafe_allow_html=True)
    section_header("Export Data", "Download the full dataset")
    c1, c2, _ = st.columns([1, 1, 5])
    with c1:
        b, name, mime = services.export(full_df, "csv")
        st.download_button("⬇  CSV", data=b, file_name=name, mime=mime,
                           use_container_width=True, key="dl_csv")
    with c2:
        b, name, mime = services.export(full_df, "xlsx")
        st.download_button("⬇  Excel", data=b, file_name=name, mime=mime,
                           use_container_width=True, key="dl_xlsx")
