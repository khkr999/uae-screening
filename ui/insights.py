"""Insights tab — theme-aware charts, richer storytelling."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import services
import state
from config import RISK_BY_LEVEL, Col
from ui.components import empty_state, section_header


def _chart_colors(session) -> dict:
    """Return chart colors matching current theme."""
    is_dark = session.get("theme", "dark") == "dark"
    return {
        "bg":    "#111827" if is_dark else "#FFFFFF",
        "grid":  "#1F2937" if is_dark else "#E2E8F0",
        "label": "#9CA3AF" if is_dark else "#6B7280",
        "title": "#6B7280" if is_dark else "#374151",
    }


def _cfg(chart, colors: dict):
    return (
        chart
        .configure_view(stroke=None, fill=colors["bg"])
        .configure_axis(
            gridColor=colors["grid"],
            labelColor=colors["label"],
            titleColor=colors["title"],
            labelFont="IBM Plex Mono",
            titleFont="IBM Plex Mono",
            labelFontSize=10,
            titleFontSize=10,
        )
        .configure_legend(
            labelColor=colors["label"],
            titleColor=colors["title"],
            labelFont="IBM Plex Mono",
            titleFont="IBM Plex Mono",
        )
    )


def render(df: pd.DataFrame) -> None:
    session = st.session_state
    if df.empty:
        empty_state("No data to visualise")
        return

    ins    = services.get_insights(df)
    total  = len(df)
    colors = _chart_colors(session)

    # ── Summary KPI strip ──
    _summary_strip(ins["risk_distribution"], total)
    st.write("")

    # ── Row 1: Risk + Regulator ──
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _risk_chart(ins["risk_distribution"], total, colors)
    with c2:
        _regulator_chart(ins["regulators"], colors)

    st.write("")

    # ── Row 2: Service mix ──
    _service_chart(ins["services"], colors)

    st.write("")

    # ── Row 3: Risk breakdown table ──
    _risk_breakdown_table(ins["risk_distribution"], total)


# ── SUMMARY STRIP ─────────────────────────────────────────────────────────────
def _summary_strip(dist: pd.DataFrame, total: int) -> None:
    critical = int(dist[dist["level"] == 5]["count"].sum())
    high     = int(dist[dist["level"] == 4]["count"].sum())
    medium   = int(dist[dist["level"] == 3]["count"].sum())
    licensed = int(dist[dist["level"] == 0]["count"].sum())
    high_pct = round((critical + high) / max(total, 1) * 100)

    cards = [
        ("#EF4444", "Critical",    critical,              f"{round(critical/max(total,1)*100)}% of run"),
        ("#F87171", "High Risk",   high,                  f"{round(high/max(total,1)*100)}% of run"),
        ("#FBBF24", "Medium",      medium,                f"{round(medium/max(total,1)*100)}% of run"),
        ("#34D399", "Licensed",    licensed,              f"{round(licensed/max(total,1)*100)}% of run"),
        ("#C9A84C", "High+Crit %", f"{high_pct}%",       f"{critical + high} entities need action"),
    ]

    cols = st.columns(5)
    for col, (color, label, value, hint) in zip(cols, cards):
        col.markdown(
            f'<div style="background:var(--card);border:1px solid var(--border);'
            f'border-top:2px solid {color};border-radius:12px;padding:12px 14px;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;">'
            f'{label}</div>'
            f'<div style="font-size:26px;font-weight:700;color:var(--text);margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;letter-spacing:-0.02em;">{value}</div>'
            f'<div style="font-size:10px;color:var(--muted);margin-top:4px;'
            f'font-family:\'IBM Plex Mono\',monospace;">{hint}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── RISK DISTRIBUTION CHART ───────────────────────────────────────────────────
def _risk_chart(dist: pd.DataFrame, total: int, colors: dict) -> None:
    high_count = int(dist[dist["level"] >= 4]["count"].sum())
    pct        = round(high_count / max(total, 1) * 100)
    section_header(
        "Risk Distribution",
        f"High-risk entities: {pct}% of this run ({high_count} of {total} entities)"
    )
    if dist["count"].sum() == 0:
        empty_state("No risk data")
        return

    chart = _cfg(
        alt.Chart(dist)
        .mark_bar(cornerRadiusEnd=5, size=24)
        .encode(
            y=alt.Y("label:N",
                    sort=alt.SortField("level", order="descending"),
                    title=None,
                    axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono", labelLimit=120)),
            x=alt.X("count:Q", title="Entity Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[
                alt.Tooltip("label:N",  title="Risk Tier"),
                alt.Tooltip("count:Q",  title="Entities", format=","),
            ],
        )
        .properties(height=260, background=colors["bg"]),
        colors,
    )
    st.altair_chart(chart, use_container_width=True)


# ── REGULATOR CHART ───────────────────────────────────────────────────────────
def _regulator_chart(regs: pd.DataFrame, colors: dict) -> None:
    top = regs.iloc[0]["regulator"] if not regs.empty else "—"
    section_header(
        "Regulator Scope",
        f"Dominant regulator: {top} — top 10 by entity count"
    )
    if regs.empty:
        empty_state("No regulator data")
        return

    chart = _cfg(
        alt.Chart(regs)
        .mark_bar(cornerRadiusEnd=5, size=22, color="#C9A84C")
        .encode(
            y=alt.Y("regulator:N", sort="-x", title=None,
                    axis=alt.Axis(labelFontSize=10, labelFont="IBM Plex Mono", labelLimit=160)),
            x=alt.X("count:Q", title="Entity Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[
                alt.Tooltip("regulator:N", title="Regulator"),
                alt.Tooltip("count:Q",     title="Entities", format=","),
            ],
        )
        .properties(height=260, background=colors["bg"]),
        colors,
    )
    st.altair_chart(chart, use_container_width=True)


# ── SERVICE MIX CHART ─────────────────────────────────────────────────────────
def _service_chart(svcs: pd.DataFrame, colors: dict) -> None:
    top = svcs.iloc[0]["service"] if not svcs.empty else "—"
    section_header(
        "Service Mix",
        f"Leading service category: {top} — showing top 10"
    )
    if svcs.empty:
        empty_state("No service data")
        return

    chart = _cfg(
        alt.Chart(svcs)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color="#3DA5E0")
        .encode(
            x=alt.X("service:N", sort="-y", title=None,
                    axis=alt.Axis(labelAngle=-35, labelFontSize=10,
                                  labelFont="IBM Plex Mono", labelLimit=140)),
            y=alt.Y("count:Q", title="Entity Count",
                    axis=alt.Axis(format=",", labelFont="IBM Plex Mono", tickCount=5)),
            tooltip=[
                alt.Tooltip("service:N", title="Service"),
                alt.Tooltip("count:Q",   title="Entities", format=","),
            ],
        )
        .properties(height=280, background=colors["bg"]),
        colors,
    )
    st.altair_chart(chart, use_container_width=True)


# ── RISK BREAKDOWN TABLE ──────────────────────────────────────────────────────
def _risk_breakdown_table(dist: pd.DataFrame, total: int) -> None:
    section_header("Risk Tier Breakdown", "Full breakdown by tier with percentage share")

    rows_html = ""
    for _, r in dist.sort_values("level", ascending=False).iterrows():
        count = int(r["count"])
        if count == 0:
            continue
        pct   = round(count / max(total, 1) * 100)
        color = r["color"]
        width = (count / max(dist["count"].max(), 1)) * 100

        rows_html += (
            f'<div style="display:grid;grid-template-columns:130px 1fr 60px 50px;'
            f'gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);">'
            f'<span style="font-size:11px;color:var(--dim);font-family:\'IBM Plex Mono\',monospace;">'
            f'{r["label"]}</span>'
            f'<div style="height:6px;border-radius:999px;background:rgba(128,128,128,0.10);overflow:hidden;">'
            f'<div style="height:100%;width:{width:.1f}%;background:{color};border-radius:999px;"></div>'
            f'</div>'
            f'<span style="font-size:11px;font-weight:700;color:var(--text);'
            f'font-family:\'IBM Plex Mono\',monospace;text-align:right;">{count}</span>'
            f'<span style="font-size:10px;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;'
            f'text-align:right;">{pct}%</span>'
            f'</div>'
        )

    header = (
        f'<div style="display:grid;grid-template-columns:130px 1fr 60px 50px;'
        f'gap:12px;padding:6px 0;border-bottom:2px solid var(--border);margin-bottom:2px;">'
        f'{"".join(f"<span style=\"font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted);font-family:\'IBM Plex Mono\',monospace;\">{h}</span>" for h in ["Tier", "Distribution", "Count", "Share"])}'
        f'</div>'
    )

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:12px;padding:12px 20px;">{header}{rows_html}</div>',
        unsafe_allow_html=True,
    )
