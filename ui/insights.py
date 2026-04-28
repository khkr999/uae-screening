"""Insights tab — fixed KPI strip, plain number axes, correct licensed count."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from config import Col, HIGH_RISK_THRESHOLD, REVIEW_MIN, REVIEW_MAX, RISK_BY_LEVEL
import services
from ui.components import section_header, empty_state


def render(df: pd.DataFrame) -> None:
    if df.empty:
        empty_state("No data", "Upload a screening file to see insights.")
        return

    _kpi_strip(df)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        _risk_chart(df)
    with right:
        _regulator_chart(df)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    _service_chart(df)

    st.markdown(
        '<div style="text-align:center;font-size:10px;color:var(--muted);'
        'padding:16px 0 4px 0;font-family:\'IBM Plex Mono\',monospace;">'
        'CBUAE Register — February 2026 snapshot</div>',
        unsafe_allow_html=True,
    )


# ── KPI STRIP ─────────────────────────────────────────────────────────────────
def _kpi_strip(df: pd.DataFrame) -> None:
    rl  = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL    in df.columns else pd.Series([99] * len(df))
    clf = df[Col.CLASSIFICATION].fillna("").astype(str) if Col.CLASSIFICATION in df.columns else pd.Series([""] * len(df))

    critical  = int((rl >= 5).sum())
    high      = int(((rl >= HIGH_RISK_THRESHOLD) & (rl < 5)).sum())
    medium    = int((rl == 3).sum())
    monitor   = int((rl == 2).sum())
    low       = int((rl == 1).sum())
    # Licensed = Risk Level 0 OR classification contains LICENSED
    licensed  = int(((rl == 0) | clf.str.contains("LICENSED", case=False, na=False)).sum())
    total     = len(df)

    high_pct = round((high + critical) / max(total, 1) * 100)

    kpis = [
        ("Critical",    critical,  "#DC2626", f"{round(critical/max(total,1)*100)}% of run"),
        ("High Risk",   high,      "#EF4444", f"{high_pct}% of run"),
        ("Medium",      medium,    "#F59E0B", f"{round(medium/max(total,1)*100)}% of run"),
        ("Monitor",     monitor,   "#818CF8", f"{round(monitor/max(total,1)*100)}% of run"),
        ("Low",         low,       "#3DA5E0", f"{round(low/max(total,1)*100)}% of run"),
        ("Licensed",    licensed,  "#059669", f"{round(licensed/max(total,1)*100)}% of run"),
        ("High+Crit %", f"{high_pct}%", "#C9A84C", f"{critical + high} entities need action"),
    ]

    cols = st.columns(len(kpis))
    for col, (label, value, color, hint) in zip(cols, kpis):
        with col:
            col.markdown(
                f'<div style="background:var(--card);border:1px solid var(--border);'
                f'border-top:2px solid {color};border-radius:10px;'
                f'padding:12px 14px;text-align:center;">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;'
                f'text-transform:uppercase;color:var(--muted);'
                f'font-family:\'IBM Plex Mono\',monospace;margin-bottom:4px;">'
                f'{escape(label)}</div>'
                f'<div style="font-size:24px;font-weight:800;color:{color};'
                f'font-family:\'IBM Plex Mono\',monospace;line-height:1;">'
                f'{escape(str(value))}</div>'
                f'<div style="font-size:9px;color:var(--muted);margin-top:4px;'
                f'font-family:\'IBM Plex Mono\',monospace;">{escape(hint)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── RISK DISTRIBUTION CHART ───────────────────────────────────────────────────
def _risk_chart(df: pd.DataFrame) -> None:
    section_header("Risk Distribution",
                   f"High-risk entities: {int((df[Col.RISK_LEVEL].fillna(0).astype(int) >= HIGH_RISK_THRESHOLD).sum())} "
                   f"of {len(df)} total" if Col.RISK_LEVEL in df.columns else "")

    rl = df[Col.RISK_LEVEL].fillna(99).astype(int) if Col.RISK_LEVEL in df.columns else pd.Series(dtype=int)
    clf = df[Col.CLASSIFICATION].fillna("").astype(str) if Col.CLASSIFICATION in df.columns else pd.Series([""] * len(df))

    rows = []
    for tier in sorted(RISK_BY_LEVEL.values(), key=lambda t: t.level, reverse=True):
        count = int((rl == tier.level).sum())
        # Licensed row: use max of risk==0 count vs classification match
        if tier.level == 0:
            count = max(count, int(clf.str.contains("LICENSED", case=False, na=False).sum()))
        rows.append({"label": tier.label, "count": count, "color": tier.color})

    # Filter empty tiers
    rows = [r for r in rows if r["count"] > 0]
    if not rows:
        empty_state("No data", ""); return

    max_count = max(r["count"] for r in rows)

    bars_html = ""
    for r in rows:
        width = (r["count"] / max_count) * 100
        short = r["label"].split("/")[0].strip()
        bars_html += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:var(--muted);width:80px;text-align:right;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;">{escape(short)}</span>'
            f'<div style="flex:1;height:18px;background:rgba(128,128,128,0.08);border-radius:4px;overflow:hidden;">'
            f'<div style="height:100%;width:{width:.1f}%;background:{r["color"]};border-radius:4px;'
            f'transition:width 0.4s ease;"></div></div>'
            f'<span style="font-size:11px;font-weight:700;color:var(--dim);width:36px;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;">{r["count"]}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:12px;padding:16px 20px;">{bars_html}</div>',
        unsafe_allow_html=True,
    )


# ── REGULATOR CHART ───────────────────────────────────────────────────────────
def _regulator_chart(df: pd.DataFrame) -> None:
    regs = services.get_insights(df)["regulators"]
    if regs.empty:
        section_header("Regulator Scope")
        empty_state("No regulator data", ""); return

    dominant = regs.iloc[0]["regulator"] if not regs.empty else "—"
    section_header("Regulator Scope", f"Dominant: {dominant} — top 10 by entity count")

    max_count = int(regs["count"].max()) if not regs.empty else 1
    bars_html = ""
    colors = ["#C9A84C", "#3DA5E0", "#818CF8", "#34D399", "#F87171",
              "#FBBF24", "#60A5FA", "#A78BFA", "#4ADE80", "#F472B6"]

    for i, (_, row) in enumerate(regs.iterrows()):
        width = (int(row["count"]) / max_count) * 100
        color = colors[i % len(colors)]
        label = str(row["regulator"])[:22]
        count = int(row["count"])
        bars_html += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:var(--muted);width:110px;text-align:right;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{escape(label)}</span>'
            f'<div style="flex:1;height:18px;background:rgba(128,128,128,0.08);border-radius:4px;overflow:hidden;">'
            f'<div style="height:100%;width:{width:.1f}%;background:{color};border-radius:4px;'
            f'transition:width 0.4s ease;"></div></div>'
            f'<span style="font-size:11px;font-weight:700;color:var(--dim);width:36px;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;">{count}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:12px;padding:16px 20px;">{bars_html}</div>',
        unsafe_allow_html=True,
    )


# ── SERVICE MIX CHART ─────────────────────────────────────────────────────────
def _service_chart(df: pd.DataFrame) -> None:
    svcs = services.get_insights(df)["services"]
    if svcs.empty:
        section_header("Service Mix")
        empty_state("No service data", ""); return

    leading = svcs.iloc[0]["service"] if not svcs.empty else "—"
    section_header("Service Mix", f"Leading: {leading[:40]} — top 10")

    max_count = int(svcs["count"].max()) if not svcs.empty else 1
    colors = ["#3DA5E0", "#C9A84C", "#818CF8", "#34D399", "#F87171",
              "#FBBF24", "#60A5FA", "#A78BFA", "#4ADE80", "#F472B6"]

    bars_html = ""
    for i, (_, row) in enumerate(svcs.iterrows()):
        width = (int(row["count"]) / max_count) * 100
        color = colors[i % len(colors)]
        label = str(row["service"])[:35]
        count = int(row["count"])
        bars_html += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:var(--muted);width:200px;text-align:right;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{escape(label)}</span>'
            f'<div style="flex:1;height:18px;background:rgba(128,128,128,0.08);border-radius:4px;overflow:hidden;">'
            f'<div style="height:100%;width:{width:.1f}%;background:{color};border-radius:4px;'
            f'transition:width 0.4s ease;"></div></div>'
            f'<span style="font-size:11px;font-weight:700;color:var(--dim);width:36px;'
            f'font-family:\'IBM Plex Mono\',monospace;flex-shrink:0;">{count}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:var(--card);border:1px solid var(--border);'
        f'border-radius:12px;padding:16px 20px;">{bars_html}</div>',
        unsafe_allow_html=True,
    )
