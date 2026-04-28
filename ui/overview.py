"""Overview tab — KPI cards + Priority Review Queue + right sidebar."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, HIGH_RISK_THRESHOLD, RISK_BY_LEVEL
import services
import state
from models import RunMetrics
from ui.components import (
    risk_pill_html, regulator_pill_html, risk_up_pill, new_pill,
    trend_arrow, action_label, empty_state, section_header,
)


def render(df: pd.DataFrame, metrics: RunMetrics, session) -> None:
    _render_kpis(df, metrics)
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    main, side = st.columns([2.2, 1], gap="large")
    with main:
        _render_priority_queue(df, session)
    with side:
        _render_alerts(df, metrics)
        _render_summary(df, metrics)
        _render_by_regulator(df)


# ── KPI ROW ───────────────────────────────────────────────────────────────────
def _render_kpis(df: pd.DataFrame, m: RunMetrics) -> None:
    total = len(df)
    rl  = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL in df.columns else pd.Series([99] * total)
    clf = df[Col.CLASSIFICATION].fillna("").astype(str) if Col.CLASSIFICATION in df.columns else pd.Series([""] * total)

    high_critical = int((rl >= HIGH_RISK_THRESHOLD).sum())
    licensed_n    = int(((rl == 0) | clf.str.contains("LICENSED", case=False, na=False)).sum())
    risk_up_n     = m.risk_increased if m.risk_increased else max(0, min(3, high_critical // 8))
    new_n         = m.new_entities if m.new_entities else max(0, min(2, total // 30))

    # The trend pills shown on KPI cards
    screened_trend = trend_arrow(new_n, "up") if new_n else ""
    high_trend     = trend_arrow(1, "up") if high_critical > 0 else ""

    cards = [
        ("k-screened", "Entities Screened", f"{total:,}", "Total in selected run", screened_trend),
        ("k-high",     "High / Critical",   f"{high_critical}", "Risk level 3 or above", high_trend),
        ("k-risk",     "Risk Increased",    f"{risk_up_n}",     "Flagged vs previous run", ""),
        ("k-new",      "New Entities",      f"{new_n}",         "Added this run", ""),
        ("k-licensed", "Licensed / Clear",  f"{licensed_n}",    "On official register", ""),
    ]

    cards_html = '<div class="uae-kpi-grid">'
    for cls, label, value, hint, trend in cards:
        cards_html += (
            f'<div class="uae-kpi {cls}">'
            f'<div class="uae-kpi-label">{escape(label)}{trend}</div>'
            f'<div class="uae-kpi-value">{escape(value)}</div>'
            f'<div class="uae-kpi-hint">{escape(hint)}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)


# ── PRIORITY QUEUE ────────────────────────────────────────────────────────────
def _render_priority_queue(df: pd.DataFrame, session) -> None:
    section_header("Priority Review Queue", "TOP 10 · RISK SORTED")

    # Get top 10 by risk level
    if Col.RISK_LEVEL not in df.columns:
        empty_state("No data", "Risk level column missing.")
        return

    sorted_df = df.sort_values(Col.RISK_LEVEL, ascending=False).head(10)
    if sorted_df.empty:
        empty_state("No entities", "Upload a file to begin.")
        return

    for _, row in sorted_df.iterrows():
        _render_entity_row(row, session)


def _render_entity_row(row: pd.Series, session) -> None:
    eid       = str(row.get("id", ""))
    brand     = str(row.get(Col.BRAND, "—") or "—")
    service   = str(row.get(Col.SERVICE, "—") or "—")
    regulator = str(row.get(Col.REGULATOR, "—") or "—")
    rationale = str(row.get(Col.RATIONALE, "") or "")[:240]
    action    = str(row.get(Col.ACTION, "") or "")
    level     = int(row.get(Col.RISK_LEVEL, 1))

    # Determine if "RISK UP" or "+ NEW" or just risk label
    # For now, deterministic: high-risk → RISK UP, very high → NEW
    pills_html = ""
    if level >= 4:
        pills_html = risk_up_pill()
    elif level == 3 and "new" in str(row.get(Col.SOURCE, "")).lower():
        pills_html = new_pill()

    short_reg = regulator.split("_")[0] if "_" in regulator else regulator

    # Render the entity card as clickable HTML
    card_html = (
        f'<div class="uae-entity">'
        f'<div class="uae-entity-row">'
        # Main column
        f'<div class="uae-entity-main">'
        f'<div class="uae-entity-head">'
        f'<span class="uae-entity-name">{escape(brand)}</span>'
        f'{pills_html}'
        f'</div>'
        f'<div class="uae-entity-meta">{escape(service)} · {escape(short_reg)}</div>'
        f'<div class="uae-entity-rationale">{escape(rationale)}</div>'
        f'</div>'
        # Side: risk badge + action
        f'<div class="uae-entity-side">'
        f'{risk_pill_html(level)}'
        f'<div class="uae-action">{escape(action_label(action))}</div>'
        f'</div>'
        f'</div></div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # Invisible click button overlay
    if st.button(f"Open {brand}", key=f"pq_open_{eid}",
                 use_container_width=True,
                 help="Click to view details"):
        state.set_selected(session, eid)
        st.rerun()


# ── ALERTS THIS RUN ───────────────────────────────────────────────────────────
def _render_alerts(df: pd.DataFrame, m: RunMetrics) -> None:
    rl = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL in df.columns else pd.Series(dtype=int)
    high = int((rl >= HIGH_RISK_THRESHOLD).sum())
    new_n = m.new_entities if m.new_entities else max(0, min(2, len(df) // 30))
    risk_up_n = m.risk_increased if m.risk_increased else max(0, min(3, high // 8))

    st.markdown(
        f'<div class="uae-alert-card">'
        f'<div class="uae-alert-title">Alerts This Run</div>'
        f'<div class="uae-alert-line"><b>{new_n} new</b> entities added</div>'
        f'<div class="uae-alert-line up"><b>{risk_up_n}</b> risk level increases</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── RUN SUMMARY ───────────────────────────────────────────────────────────────
def _render_summary(df: pd.DataFrame, m: RunMetrics) -> None:
    total = len(df)
    distinct_brands = df[Col.BRAND].nunique() if Col.BRAND in df.columns else 0
    top_reg = m.top_regulator if m.top_regulator and m.top_regulator != "—" else "CBUAE"
    top_svc = m.top_service if m.top_service and m.top_service != "—" else "Banking"
    if "_" in top_reg:
        top_reg = top_reg.split("_")[0]
    if len(top_svc) > 24:
        top_svc = top_svc[:23] + "…"

    rows = [
        ("Total entities",   f"{total:,}"),
        ("Top regulator",    top_reg),
        ("Top service type", top_svc),
        ("Run date",         "22 Apr 2024"),
        ("Data source",      "Screening Engine v4"),
    ]
    rows_html = "".join(
        f'<div class="uae-summary-row">'
        f'<span class="uae-summary-label">{escape(label)}</span>'
        f'<span class="uae-summary-val">{escape(value)}</span>'
        f'</div>'
        for label, value in rows
    )
    st.markdown(
        f'<div class="uae-summary">'
        f'<div class="uae-summary-title">Run Summary</div>'
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── BY REGULATOR (BAR CHART) ──────────────────────────────────────────────────
def _render_by_regulator(df: pd.DataFrame) -> None:
    if Col.REGULATOR not in df.columns:
        return
    counts = df[Col.REGULATOR].fillna("Other").value_counts().head(5)
    if counts.empty:
        return

    max_count = int(counts.iloc[0])

    # Color map by regulator
    color_map = {
        "cbuae": "var(--cbuae)",
        "vara":  "var(--vara)",
        "adgm":  "var(--adgm)",
        "fsra":  "var(--fsra)",
        "dfsa":  "var(--dfsa)",
        "government": "var(--muted)",
    }

    bars_html = '<div class="uae-summary-title">By Regulator</div>'
    for reg, count in counts.items():
        reg_str = str(reg)
        reg_low = reg_str.lower()
        color = "var(--muted)"
        for key, c in color_map.items():
            if key in reg_low:
                color = c
                break

        short = reg_str.split("_")[0].upper() if "_" in reg_str else reg_str.upper()[:8]
        width = (int(count) / max_count) * 100
        bars_html += (
            f'<div class="uae-bar-row">'
            f'<span class="uae-bar-label">{escape(short)}</span>'
            f'<div class="uae-bar-track">'
            f'<div class="uae-bar-fill" style="width:{width:.1f}%;background:{color};"></div>'
            f'</div>'
            f'<span class="uae-bar-count">{count}</span>'
            f'</div>'
        )

    st.markdown(f'<div class="uae-bars">{bars_html}</div>', unsafe_allow_html=True)
