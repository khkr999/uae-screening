"""Insights tab — risk distribution, regulator breakdown, service mix."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import services
from ui.components import empty_state, section_header

_CARD_BG = "#111827"
_GRID    = "#1F2937"
_LABEL   = "#9CA3AF"
_TITLE   = "#6B7280"


def _cfg(chart):
    return (chart
            .configure_view(stroke=None, fill=_CARD_BG)
            .configure_axis(
                gridColor=_GRID, labelColor=_LABEL, titleColor=_TITLE,
                labelFont="IBM Plex Mono", titleFont="IBM Plex Mono",
                labelFontSize=10, titleFontSize=10,
            )
            .configure_legend(labelColor=_LABEL, titleColor=_TITLE,
                               labelFont="IBM Plex Mono", titleFont="IBM Plex Mono"))


def render(df: pd.DataFrame) -> None:
    if df.empty:
        empty_state("No data to visualise")
        return

    ins = services.get_insights(df)
    total = len(df)

    # ── Row 1 ──
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _risk_chart(ins["risk_distribution"], total)
    with c2:
        _regulator_chart(ins["regulators"])

    st.write("")

    # ── Row 2 ──
    _service_chart(ins["services"])


def _risk_chart(dist: pd.DataFrame, total: int) -> None:
    high_count = int(dist[dist["level"] >= 4]["count"].sum())
    pct = round(high_count / max(total, 1) * 100)
    section_header(
        "Risk Distribution",
        f"High-risk entities represent {pct}% of this run ({high_count} of {total})"
    )
    if dist["count"].sum() == 0:
        empty_state("No risk data")
        return

    chart = _cfg(
        alt.Chart(dist)
        .mark_bar(cornerRadiusEnd=4, size=22)
        .encode(
            y=alt.Y("label:N", sort=alt.SortField("level", order="descending"),
                    title=None, axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono")),
            x=alt.X("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("label:N", title="Risk Tier"),
                     alt.Tooltip("count:Q", title="Entities", format=",")],
        )
        .properties(height=250, background=_CARD_BG)
    )
    st.altair_chart(chart, use_container_width=True)


def _regulator_chart(regs: pd.DataFrame) -> None:
    top = regs.iloc[0]["regulator"] if not regs.empty else "—"
    section_header(
        "Regulator Scope",
        f"Top regulator: {top} — showing top 10 by entity count"
    )
    if regs.empty:
        empty_state("No regulator data")
        return

    chart = _cfg(
        alt.Chart(regs)
        .mark_bar(cornerRadiusEnd=4, size=20, color="#C9A84C")
        .encode(
            y=alt.Y("regulator:N", sort="-x", title=None,
                    axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono", labelLimit=160)),
            x=alt.X("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[alt.Tooltip("regulator:N", title="Regulator"),
                     alt.Tooltip("count:Q",     title="Entities", format=",")],
        )
        .properties(height=250, background=_CARD_BG)
    )
    st.altair_chart(chart, use_container_width=True)


def _service_chart(svcs: pd.DataFrame) -> None:
    top = svcs.iloc[0]["service"] if not svcs.empty else "—"
    section_header(
        "Service Mix",
        f"Most common service type: {top} — showing top 10 categories"
    )
    if svcs.empty:
        empty_state("No service data")
        return

    chart = _cfg(
        alt.Chart(svcs)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#3DA5E0")
        .encode(
            x=alt.X("service:N", sort="-y", title=None,
                    axis=alt.Axis(labelAngle=-35, labelFontSize=10,
                                  labelFont="IBM Plex Mono", labelLimit=150)),
            y=alt.Y("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[alt.Tooltip("service:N", title="Service"),
                     alt.Tooltip("count:Q",   title="Entities", format=",")],
        )
        .properties(height=280, background=_CARD_BG)
    )
    st.altair_chart(chart, use_container_width=True)
