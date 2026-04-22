"""
UAE Regulatory Screening – Internal Search UI
==============================================
Streamlit app that lets the Market Conduct team search, filter,
and review the output of uae_screening_v5.py.

How to run:
    cd ~/Downloads/appdesign
    streamlit run app.py
"""

from __future__ import annotations

import glob
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RISK_LABELS = {
    5: "🔴 Critical",
    4: "🔴 High",
    3: "🟠 Medium",
    2: "🟡 Low",
    1: "⚪ Very Low",
    0: "🟢 Licensed",
}


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def list_screening_files() -> list[dict]:
    """Find all screening .xlsx files in the data folder, newest first."""
    files = []
    for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
        p = Path(path)
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})", p.name)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M")
            files.append({"path": path, "name": p.name,
                          "timestamp": ts, "size_kb": p.stat().st_size // 1024})
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)


@st.cache_data(show_spinner="Loading screening data...")
def load_data(path: str) -> pd.DataFrame:
    """Load the main screening results tab from an Excel file."""
    try:
        df = pd.read_excel(path, sheet_name="📋 All Results")
    except Exception:
        try:
            df = pd.read_excel(path, sheet_name=0)
        except Exception as e:
            st.error(f"Could not read Excel file: {e}")
            return pd.DataFrame()
    return df


def load_history(files: list[dict], brand: str) -> pd.DataFrame:
    """Load classification history for one brand across all runs."""
    rows = []
    for f in files:
        try:
            df = pd.read_excel(f["path"], sheet_name="📋 All Results")
            match = df[df["Brand"].astype(str).str.lower() == brand.lower()]
            if not match.empty:
                r = match.iloc[0]
                rows.append({
                    "Run date": f["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    "Classification": r.get("Classification", ""),
                    "Risk Level": r.get("Risk Level", ""),
                    "Confidence": r.get("Confidence", ""),
                    "Alert Status": r.get("Alert Status", ""),
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

st.sidebar.title("🛡️ UAE Screening")
st.sidebar.caption("Internal Market Conduct search tool")

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Data Source")

files = list_screening_files()

if files:
    options = {
        f"{f['timestamp'].strftime('%Y-%m-%d %H:%M')} ({f['size_kb']} KB)": f["path"]
        for f in files
    }
    choice = st.sidebar.selectbox(
        "Select screening run:",
        list(options.keys()),
        index=0,
        help="Newest runs appear first",
    )
    selected_path = options[choice]
else:
    selected_path = None

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Upload new run")

uploaded = st.sidebar.file_uploader(
    "Drop a UAE_Screening_*.xlsx file",
    type=["xlsx"],
    help="File will be saved to Downloads/UAE_Screening/",
)
if uploaded:
    save_path = DATA_DIR / uploaded.name
    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.sidebar.success(f"Saved: {uploaded.name}")
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"📁 Data folder:\n`{DATA_DIR}`")
st.sidebar.caption(f"📊 Total runs: **{len(files)}**")


# ---------------------------------------------------------------------------
# MAIN PAGE
# ---------------------------------------------------------------------------

st.title("UAE Regulatory Screening")
st.caption("Search, filter, and review UAE-facing financial services companies")

if selected_path is None:
    st.warning("⚠️ No screening files found yet.")
    st.markdown(f"""
    ### Getting started
    1. Run `uae_screening_v5.py` to generate a screening file
    2. The output will be saved to `{DATA_DIR}`
    3. Refresh this page and it will appear in the sidebar

    Or upload a file directly using the sidebar uploader.
    """)
    st.stop()

df = load_data(selected_path)
if df.empty:
    st.error("The selected file is empty or could not be read.")
    st.stop()


# ---------------------------------------------------------------------------
# KPI DASHBOARD
# ---------------------------------------------------------------------------

total = len(df)
unlicensed = len(df[df["Risk Level"] >= 4]) if "Risk Level" in df.columns else 0
needs_review = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)]) \
    if "Risk Level" in df.columns else 0
licensed = len(df[df["Risk Level"] == 0]) if "Risk Level" in df.columns else 0

new_this_run = len(df[df["Alert Status"] == "🆕 NEW"]) \
    if "Alert Status" in df.columns else 0
risk_up = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) \
    if "Alert Status" in df.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Screened", total)
col2.metric("🔴 Unlicensed / High Risk", unlicensed,
            delta=f"{unlicensed/total*100:.0f}%" if total else "0%",
            delta_color="inverse")
col3.metric("🟠 Needs Review", needs_review)
col4.metric("🟢 Licensed", licensed)
col5.metric("🆕 New This Run", new_this_run,
            delta=f"📈 {risk_up} risk up" if risk_up else None,
            delta_color="inverse")

st.markdown("---")


# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------

tab_search, tab_flags, tab_alerts, tab_history, tab_summary = st.tabs([
    "🔍 Search & Filter",
    "🔴 Priority Flags",
    "🔔 Weekly Alerts",
    "📜 Company History",
    "📊 Summary",
])


# ── Tab 1: Search & Filter ───────────────────────────────────────────────
with tab_search:
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])

    with c1:
        search = st.text_input(
            "🔍 Search company name",
            placeholder="e.g. Tabby, Binance, Wise...",
        )

    with c2:
        risk_options = sorted(df["Risk Level"].dropna().unique().tolist(),
                               reverse=True) if "Risk Level" in df.columns else []
        risk_filter = st.multiselect(
            "Risk Level",
            options=risk_options,
            format_func=lambda x: RISK_LABELS.get(int(x), str(x)),
        )

    with c3:
        if "Regulator Scope" in df.columns:
            reg_options = sorted(df["Regulator Scope"].dropna().unique().tolist())
            reg_filter = st.multiselect("Regulator", options=reg_options)
        else:
            reg_filter = []

    with c4:
        if "Group" in df.columns:
            grp_options = sorted(df["Group"].dropna().unique().tolist())
            grp_filter = st.multiselect("Group", options=grp_options)
        else:
            grp_filter = []

    filtered = df.copy()
    if search:
        mask = filtered["Brand"].astype(str).str.lower().str.contains(
            search.lower(), na=False)
        if "Service Type" in filtered.columns:
            mask |= filtered["Service Type"].astype(str).str.lower().str.contains(
                search.lower(), na=False)
        filtered = filtered[mask]
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]
    if grp_filter:
        filtered = filtered[filtered["Group"].isin(grp_filter)]

    st.caption(f"Showing **{len(filtered)}** of **{total}** entities")

    display_cols = [c for c in [
        "Brand", "Classification", "Action Required", "Risk Level",
        "Confidence", "Regulator Scope", "Service Type",
        "Matched Entity (Register)", "Rationale", "Alert Status",
        "First Seen", "Top Source URL",
    ] if c in filtered.columns]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True, height=500, hide_index=True,
        column_config={
            "Top Source URL": st.column_config.LinkColumn("Source"),
            "Risk Level": st.column_config.NumberColumn(
                "Risk", format="%d", min_value=0, max_value=5),
        },
    )

    if not filtered.empty:
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download filtered view (CSV)",
            data=csv,
            file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
        )


# ── Tab 2: Priority Flags ────────────────────────────────────────────────
with tab_flags:
    st.subheader("🔴 Entities Requiring Action")
    st.caption("Risk level 4+ — investigate this week or escalate immediately")

    if "Risk Level" in df.columns:
        flagged = df[df["Risk Level"] >= 4].sort_values(
            "Risk Level", ascending=False)
    else:
        flagged = pd.DataFrame()

    if flagged.empty:
        st.success("✅ No high-risk entities in this run.")
    else:
        st.error(f"⚠️ **{len(flagged)} entities** require immediate attention")

        flag_cols = [c for c in [
            "Brand", "Classification", "Action Required", "Confidence",
            "Regulator Scope", "Service Type", "Rationale",
            "Top Source URL", "First Seen", "Days Seen",
        ] if c in flagged.columns]

        st.dataframe(
            flagged[flag_cols],
            use_container_width=True, height=500, hide_index=True,
            column_config={
                "Top Source URL": st.column_config.LinkColumn("Source"),
            },
        )

        csv = flagged.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download priority flags (CSV)",
            data=csv,
            file_name=f"priority_flags_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
        )


# ── Tab 3: Weekly Alerts ─────────────────────────────────────────────────
with tab_alerts:
    st.subheader("🔔 Changes Since Last Run")
    st.caption("New entities and status changes detected this run")

    alert_statuses = {"🆕 NEW", "📈 RISK INCREASED",
                      "🔄 STATUS CHANGED", "🚨 PERSISTING HIGH RISK"}

    if "Alert Status" in df.columns:
        alerts = df[df["Alert Status"].isin(alert_statuses)].sort_values(
            "Risk Level", ascending=False)
    else:
        alerts = pd.DataFrame()

    if alerts.empty:
        st.info("No alerts to show — either this is the first run or nothing changed.")
    else:
        counts = alerts["Alert Status"].value_counts()
        cols = st.columns(min(len(counts), 4))
        for i, (status, cnt) in enumerate(counts.items()):
            cols[i % len(cols)].metric(status, cnt)

        alert_cols = [c for c in [
            "Brand", "Alert Status", "Classification",
            "Previous Classification", "Risk Level", "Days Seen",
            "Service Type", "Rationale",
        ] if c in alerts.columns]

        st.dataframe(
            alerts[alert_cols],
            use_container_width=True, height=450, hide_index=True,
        )


# ── Tab 4: Company History ───────────────────────────────────────────────
with tab_history:
    st.subheader("📜 Classification History")
    st.caption("Track how a company's classification has changed over time")

    brands = sorted(df["Brand"].dropna().unique().tolist()) \
        if "Brand" in df.columns else []

    if not brands:
        st.info("No brands available.")
    else:
        brand = st.selectbox("Select company:", brands)

        if brand and len(files) >= 1:
            hist = load_history(files, brand)

            if hist.empty:
                st.info("No history found for this company.")
            else:
                st.markdown(f"### {brand}")
                st.caption(f"Found in {len(hist)} of {len(files)} runs")

                current = df[df["Brand"] == brand].iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric("Current Classification",
                          str(current.get("Classification", ""))[:30])
                c2.metric("Risk Level",
                          RISK_LABELS.get(
                              int(current.get("Risk Level", 0)), "N/A"))
                c3.metric("Confidence",
                          str(current.get("Confidence", "")))

                st.markdown("#### Timeline")
                st.dataframe(hist, use_container_width=True, hide_index=True)

                if len(hist) > 1:
                    hist_plot = hist.copy()
                    hist_plot["Run"] = range(1, len(hist_plot) + 1)
                    st.markdown("#### Risk Level Over Time")
                    st.line_chart(
                        hist_plot.set_index("Run")["Risk Level"],
                        height=200,
                    )

                st.markdown("#### Current Run Details")
                detail_dict = {k: v for k, v in current.to_dict().items()
                               if pd.notna(v) and str(v) and not k.startswith("_")}
                st.json(detail_dict)


# ── Tab 5: Summary ───────────────────────────────────────────────────────
with tab_summary:
    st.subheader("📊 Run Summary")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### By Classification Group")
        if "Group" in df.columns:
            grp_counts = df["Group"].value_counts()
            st.bar_chart(grp_counts, height=300)

    with c2:
        st.markdown("#### By Risk Level")
        if "Risk Level" in df.columns:
            risk_counts = df["Risk Level"].value_counts().sort_index(
                ascending=False)
            risk_counts.index = [RISK_LABELS.get(int(i), str(i))
                                  for i in risk_counts.index]
            st.bar_chart(risk_counts, height=300)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown("#### By Regulator Scope")
        if "Regulator Scope" in df.columns:
            reg_counts = df["Regulator Scope"].value_counts().head(10)
            st.bar_chart(reg_counts, height=300)

    with c4:
        st.markdown("#### By Source")
        if "Source" in df.columns:
            src_counts = df["Source"].value_counts().head(10)
            st.bar_chart(src_counts, height=300)

    st.markdown("---")
    st.markdown("#### Full Classification Breakdown")
    if "Classification" in df.columns:
        cls_counts = df["Classification"].value_counts().reset_index()
        cls_counts.columns = ["Classification", "Count"]
        st.dataframe(cls_counts, use_container_width=True, hide_index=True)


st.markdown("---")
st.caption(
    f"Data source: `{Path(selected_path).name}` | "
    f"Last refreshed: {datetime.now():%Y-%m-%d %H:%M} | "
    "Automated first-pass screening — not a legal determination"
)
