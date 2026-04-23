from __future__ import annotations
import altair as alt
import pandas as pd
import streamlit as st
import services
from ui.components import empty_state, section_header

def render(df: pd.DataFrame) -> None:
    if df.empty:
        empty_state("No data to visualise"); return
    insights = services.get_insights(df)
    c1, c2 = st.columns(2, gap="medium")
    with c1: _render_risk_chart(insights["risk_distribution"])
    with c2: _render_regulator_chart(insights["regulators"])
    st.write("")
    _render_service_chart(insights["services"])

def _render_risk_chart(dist: pd.DataFrame) -> None:
    section_header("Risk Distribution", "Counts per tier across the current run")
    if dist["count"].sum() == 0:
        empty_state("No risk data"); return
    chart = alt.Chart(dist).mark_bar(cornerRadiusEnd=6, size=30).encode(y=alt.Y("label:N", sort=alt.SortField("level", order="descending"), title=None), x=alt.X("count:Q", title="Count"), color=alt.Color("color:N", scale=None, legend=None), tooltip=["label:N","count:Q"]).properties(height=240).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

def _render_regulator_chart(regs: pd.DataFrame) -> None:
    section_header("Regulator Scope", "Top regulators by entity count")
    if regs.empty:
        empty_state("No regulator data"); return
    chart = alt.Chart(regs).mark_bar(cornerRadiusEnd=6, size=24).encode(y=alt.Y("regulator:N", sort="-x", title=None), x=alt.X("count:Q", title="Count"), color=alt.value("#C9A84C"), tooltip=["regulator:N","count:Q"]).properties(height=240).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

def _render_service_chart(services_df: pd.DataFrame) -> None:
    section_header("Service Mix", "Top service categories detected")
    if services_df.empty:
        empty_state("No service data"); return
    chart = alt.Chart(services_df).mark_bar(cornerRadiusEnd=6).encode(x=alt.X("service:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-30, labelFontSize=10, labelLimit=140)), y=alt.Y("count:Q", title="Count"), color=alt.value("#3DA5E0"), tooltip=["service:N","count:Q"]).properties(height=260).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)
