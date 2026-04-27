"""Insights tab — risk distribution, regulator breakdown, service mix."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import services
from ui.components import empty_state, section_header

_BG = "#111827"
_GRID = "#1F2937"
_TEXT = "#6B7280"
_LABEL = "#9CA3AF"


def _base_config(chart):
    return chart.configure_view(
        stroke=None,
        fill=_BG,
    ).configure_axis(
        gridColor=_GRID,
        labelColor=_LABEL,
        titleColor=_TEXT,
        labelFont="IBM Plex Mono",
        titleFont="IBM Plex Mono",
        labelFontSize=10,
        titleFontSize=10,
    ).configure_legend(
        labelColor=_LABEL,
        titleColor=_TEXT,
        labelFont="IBM Plex Mono",
        titleFont="IBM Plex Mono",
    )


def render(df: pd.DataFrame) -> None:
    if df.empty:
        empty_state("No data to visualise")
        return

    insights = services.get_insights(df)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _render_risk_chart(insights["risk_distribution"])
    with c2:
        _render_regulator_chart(insights["regulators"])

    st.write("")
    _render_service_chart(insights["services"])


def _render_risk_chart(dist: pd.DataFrame) -> None:
    section_header("Risk Distribution", "Entity counts per tier — current run")
    if dist["count"].sum() == 0:
        empty_state("No risk data")
        return

    chart = _base_config(
        alt.Chart(dist)
        .mark_bar(cornerRadiusEnd=4, size=22)
        .encode(
            y=alt.Y("label:N",
                    sort=alt.SortField("level", order="descending"),
                    title=None,
                    axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono")),
            x=alt.X("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[
                alt.Tooltip("label:N", title="Risk Tier"),
                alt.Tooltip("count:Q", title="Entities", format=","),
            ],
        )
        .properties(height=250, background=_BG)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_regulator_chart(regs: pd.DataFrame) -> None:
    section_header("Regulator Scope", "Top regulators by entity count")
    if regs.empty:
        empty_state("No regulator data")
        return

    chart = _base_config(
        alt.Chart(regs)
        .mark_bar(cornerRadiusEnd=4, size=20, color="#C9A84C")
        .encode(
            y=alt.Y("regulator:N", sort="-x", title=None,
                    axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono", labelLimit=160)),
            x=alt.X("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[
                alt.Tooltip("regulator:N", title="Regulator"),
                alt.Tooltip("count:Q",     title="Entities", format=","),
            ],
        )
        .properties(height=250, background=_BG)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_service_chart(services_df: pd.DataFrame) -> None:
    section_header("Service Mix", "Top service categories detected")
    if services_df.empty:
        empty_state("No service data")
        return

    chart = _base_config(
        alt.Chart(services_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#3DA5E0")
        .encode(
            x=alt.X("service:N", sort="-y", title=None,
                    axis=alt.Axis(labelAngle=-35, labelFontSize=10,
                                  labelFont="IBM Plex Mono", labelLimit=150)),
            y=alt.Y("count:Q", title="Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[
                alt.Tooltip("service:N", title="Service"),
                alt.Tooltip("count:Q",   title="Entities", format=","),
            ],
        )
        .properties(height=280, background=_BG)
    )
    st.altair_chart(chart, use_container_width=True)
