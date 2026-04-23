"""
UAE Regulatory Screening – Internal Search UI (v2)
====================================================
Polished, interactive, mobile-friendly dashboard for the Market Conduct team.

How to run locally:
    cd ~/Downloads/appdesign
    streamlit run app.py
"""

from __future__ import annotations

import glob
import io
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLING
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #1F3864 0%, #2E5090 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(31, 56, 100, 0.15);
    }
    .main-header h1 {
        margin: 0; color: white;
        font-size: 1.8rem; font-weight: 700;
    }
    .main-header p {
        margin: 0.25rem 0 0 0;
        color: rgba(255, 255, 255, 0.85);
        font-size: 0.95rem;
    }

    [data-testid="stMetric"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #6B7280 !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }

    .pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .pill-critical { background: #FEE2E2; color: #991B1B; }
    .pill-high     { background: #FED7AA; color: #9A3412; }
    .pill-medium   { background: #FEF3C7; color: #92400E; }
    .pill-low      { background: #DBEAFE; color: #1E40AF; }
    .pill-licensed { background: #D1FAE5; color: #065F46; }

    .callout-danger {
        background: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 1rem 1.25rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    .callout-warn {
        background: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 1rem 1.25rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    .callout-ok {
        background: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 1rem 1.25rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
    .callout-info {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 1rem 1.25rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }

    .company-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .company-card h4 {
        margin: 0 0 0.25rem 0;
        color: #1F2937;
        font-size: 1.1rem;
    }
    .company-card .meta {
        color: #6B7280;
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
    }

    [data-baseweb="tab-list"] { gap: 0.5rem; }
    [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        background: #1F3864 !important;
        color: white !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    @media (max-width: 768px) {
        [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
        .main-header h1 { font-size: 1.4rem !important; }
        [data-testid="stDataFrame"] { font-size: 0.85rem; }
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RISK_META = {
    5: {"label": "🔴 Critical",  "pill": "pill-critical"},
    4: {"label": "🔴 High",      "pill": "pill-high"},
    3: {"label": "🟠 Medium",    "pill": "pill-high"},
    2: {"label": "🟡 Low",       "pill": "pill-medium"},
    1: {"label": "⚪ Very Low",  "pill": "pill-low"},
    0: {"label": "🟢 Licensed",  "pill": "pill-licensed"},
}


def risk_pill(level) -> str:
    try:
        level = int(level)
    except (ValueError, TypeError):
        return '<span class="pill pill-low">Unknown</span>'
    meta = RISK_META.get(level, RISK_META[2])
    return f'<span class="pill {meta["pill"]}">{meta["label"]}</span>'


def render_card(row):
    pill_html = risk_pill(row.get("Risk Level", 2))
    url = row.get("Top Source URL", "")
    link_html = (f'<a href="{url}" target="_blank">🔗 Source</a>'
                 if url and str(url).startswith("http") else "")
    st.markdown(f"""
    <div class="company-card">
      <div style="display:flex; justify-content:space-between; align-items:start; gap:1rem;">
        <div style="flex:1; min-width:0;">
          <h4>{row.get('Brand', '')}</h4>
          <div class="meta">{row.get('Service Type', '')} · {row.get('Regulator Scope', '')}</div>
          <div style="font-size:0.9rem; color:#374151; margin-top:0.5rem;">
            {str(row.get('Rationale', ''))[:260]}
          </div>
        </div>
        <div style="text-align:right; min-width:140px;">
          {pill_html}<br/>
          <div style="font-size:0.8rem; color:#6B7280; margin-top:0.5rem;">
            {row.get('Action Required', '')}
          </div>
          <div style="font-size:0.8rem; margin-top:0.3rem;">{link_html}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def list_screening_files() -> list[dict]:
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
    try:
        df = pd.read_excel(path, sheet_name="📋 All Results")
    except Exception:
        try:
            df = pd.read_excel(path, sheet_name=0)
        except Exception as e:
            st.error(f"Could not read Excel file: {e}")
            return pd.DataFrame()
    for col in ["Brand", "Classification", "Group", "Service Type",
                "Regulator Scope", "Alert Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    if "Risk Level" in df.columns:
        df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(2).astype(int)
    return df


def load_history(files: list[dict], brand: str) -> pd.DataFrame:
    rows = []
    for f in files:
        try:
            d = pd.read_excel(f["path"], sheet_name="📋 All Results")
            match = d[d["Brand"].astype(str).str.lower() == brand.lower()]
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


def fuzzy_score(q: str, t: str) -> float:
    q, t = q.lower().strip(), str(t).lower()
    if not q or not t:
        return 0.0
    if q in t:
        return 1.0
    return SequenceMatcher(None, q, t).ratio()


def fuzzy_filter(df: pd.DataFrame, query: str, threshold: float = 0.45) -> pd.DataFrame:
    if not query:
        return df
    q = query.lower().strip()
    mask = df["Brand"].astype(str).str.lower().str.contains(q, na=False, regex=False)
    if "Service Type" in df.columns:
        mask |= df["Service Type"].astype(str).str.lower().str.contains(q, na=False, regex=False)
    result = df[mask]
    if result.empty and len(q) >= 3:
        scores = df["Brand"].astype(str).apply(lambda b: fuzzy_score(q, b))
        result = df[scores >= threshold]
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

st.sidebar.markdown("### 🛡️ UAE Screening")
st.sidebar.caption("Market Conduct search tool")
st.sidebar.markdown("---")

files = list_screening_files()

st.sidebar.subheader("📂 Data Source")
if files:
    options = {
        f"🗓️ {f['timestamp'].strftime('%d %b %Y, %H:%M')}  ·  {f['size_kb']} KB": f["path"]
        for f in files
    }
    choice = st.sidebar.selectbox(
        "Select screening run:",
        list(options.keys()),
        index=0,
        label_visibility="collapsed",
    )
    selected_path = options[choice]
else:
    selected_path = None

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Upload new run")
uploaded = st.sidebar.file_uploader(
    "Drop a UAE_Screening_*.xlsx file",
    type=["xlsx"],
    label_visibility="collapsed",
)
if uploaded:
    save_path = DATA_DIR / uploaded.name
    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.sidebar.success(f"✅ Saved: {uploaded.name}")
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"📊 Total runs archived: **{len(files)}**")
st.sidebar.caption(f"📁 `{DATA_DIR}`")


# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🛡️ UAE Regulatory Screening</h1>
    <p>Market Conduct · Search, monitor, and flag UAE-facing financial services companies</p>
</div>
""", unsafe_allow_html=True)

if selected_path is None:
    st.markdown("""
    <div class="callout-warn">
    ⚠️ <b>No screening files found yet.</b><br/>
    Run <code>uae_screening_v5.py</code> first, or upload a file via the sidebar.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df = load_data(selected_path)
if df.empty:
    st.error("The selected file is empty or could not be read.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════════════════════

total = len(df)
unlicensed = len(df[df["Risk Level"] >= 4])
needs_review = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)])
licensed = len(df[df["Risk Level"] == 0])
new_this_run = len(df[df["Alert Status"] == "🆕 NEW"]) if "Alert Status" in df.columns else 0
risk_up = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) if "Alert Status" in df.columns else 0

kcol1, kcol2, kcol3, kcol4, kcol5 = st.columns(5)
kcol1.metric("📊 Total Screened", f"{total:,}")
kcol2.metric(
    "🔴 High Risk", unlicensed,
    delta=f"{unlicensed/total*100:.0f}% of total" if total else None,
    delta_color="inverse",
)
kcol3.metric("🟠 Needs Review", needs_review)
kcol4.metric("🟢 Licensed", licensed)
kcol5.metric(
    "🆕 New", new_this_run,
    delta=f"📈 {risk_up} risk ↑" if risk_up else None,
    delta_color="inverse",
)


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-GENERATED SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

def generate_summary() -> str:
    parts = [f"**{total} entities** screened in this run."]
    if unlicensed > 0:
        pct = unlicensed / total * 100
        parts.append(
            f"🔴 **{unlicensed} ({pct:.0f}%) flagged as unlicensed or high risk** — "
            f"requires team action this week."
        )
    else:
        parts.append("✅ No high-risk entities detected.")

    if new_this_run > 0:
        parts.append(f"🆕 **{new_this_run} new entities** discovered since the last run.")
    if risk_up > 0:
        parts.append(f"📈 **{risk_up} entities** had their risk level increase.")

    if "Alert Status" in df.columns:
        new_high = df[
            (df["Alert Status"] == "🆕 NEW") & (df["Risk Level"] >= 4)
        ].sort_values("Risk Level", ascending=False).head(3)
        if not new_high.empty:
            names = ", ".join(f"**{b}**" for b in new_high["Brand"].head(3))
            parts.append(f"🎯 Most urgent new discoveries: {names}")

    if "Regulator Scope" in df.columns:
        top_reg = df[df["Risk Level"] >= 4]["Regulator Scope"].value_counts().head(1)
        if not top_reg.empty:
            parts.append(
                f"📍 Most flags fall under **{top_reg.index[0]}** "
                f"({top_reg.iloc[0]} entities)."
            )
    return "  \n".join(parts)


st.markdown("#### 💡 This Week's Summary")
st.markdown(f'<div class="callout-info">{generate_summary()}</div>',
            unsafe_allow_html=True)
st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════

tab_home, tab_search, tab_flags, tab_alerts, tab_history, tab_insights = st.tabs([
    "🏠 Home",
    "🔍 Search",
    "🔴 Priority Flags",
    "🔔 Changes",
    "📜 Company Profile",
    "📊 Insights",
])


# ── Tab 1: Home ──────────────────────────────────────────────────────────
with tab_home:
    st.subheader("⚠️ Top entities needing attention")
    st.caption("Ranked by risk level — focus here first")

    top_risk = df[df["Risk Level"] >= 4].sort_values(
        "Risk Level", ascending=False).head(10)

    if top_risk.empty:
        st.markdown(
            '<div class="callout-ok">✅ No high-risk entities to review this run.</div>',
            unsafe_allow_html=True)
    else:
        for _, row in top_risk.iterrows():
            render_card(row)


# ── Tab 2: Search ────────────────────────────────────────────────────────
with tab_search:
    st.subheader("🔍 Search & Filter")

    # Chip filters
    if "chip_filter" not in st.session_state:
        st.session_state.chip_filter = {}

    chip_cols = st.columns(6)
    chips = [
        ("🔴 High Risk", {"risk": [4, 5]}),
        ("🆕 New",        {"alert": "🆕 NEW"}),
        ("📈 Risk Up",    {"alert": "📈 RISK INCREASED"}),
        ("🟢 Licensed",   {"risk": [0]}),
        ("₿ Crypto/VA",   {"va": True}),
        ("🗑️ Clear",      {"clear": True}),
    ]
    for i, (label, action) in enumerate(chips):
        if chip_cols[i].button(label, use_container_width=True, key=f"chip_{i}"):
            if action.get("clear"):
                st.session_state.chip_filter = {}
            else:
                st.session_state.chip_filter = action
            st.rerun()

    # Filter row
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        search = st.text_input(
            "Search",
            placeholder="🔍 Try: Tabby, Binance, crypto, BNPL...",
            label_visibility="collapsed",
        )
    with c2:
        risk_opts = sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True)
        default_risk = st.session_state.chip_filter.get("risk", [])
        risk_filter = st.multiselect(
            "Risk Level",
            options=risk_opts,
            default=default_risk,
            format_func=lambda x: RISK_META.get(int(x), {}).get("label", str(x)),
        )
    with c3:
        reg_opts = sorted(df["Regulator Scope"].dropna().unique().tolist()) \
            if "Regulator Scope" in df.columns else []
        reg_filter = st.multiselect("Regulator", options=reg_opts)
    with c4:
        grp_opts = sorted(df["Group"].dropna().unique().tolist()) \
            if "Group" in df.columns else []
        grp_filter = st.multiselect("Group", options=grp_opts)

    # Apply filters
    filtered = df.copy()
    if search:
        filtered = fuzzy_filter(filtered, search)
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]
    if grp_filter:
        filtered = filtered[filtered["Group"].isin(grp_filter)]

    if st.session_state.chip_filter.get("alert") and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == st.session_state.chip_filter["alert"]]
    if st.session_state.chip_filter.get("va"):
        va_mask = filtered["Regulator Scope"].astype(str).str.contains(
            "VA|VASP|CRYPTO", case=False, na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains(
                "crypto|virtual asset|token", case=False, na=False)
        filtered = filtered[va_mask]

    # Pagination
    per_page = 25
    total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
    if "page" not in st.session_state or st.session_state.page > total_pages:
        st.session_state.page = 1

    rcol1, rcol2 = st.columns([3, 1])
    rcol1.caption(f"Showing **{len(filtered):,}** of **{total:,}** entities")
    rcol2.caption(f"Page **{st.session_state.page}** of **{total_pages}**")

    display_cols = [c for c in [
        "Brand", "Classification", "Risk Level", "Action Required",
        "Confidence", "Regulator Scope", "Service Type",
        "Matched Entity (Register)", "Rationale", "Alert Status",
        "Top Source URL",
    ] if c in filtered.columns]

    start = (st.session_state.page - 1) * per_page
    page_df = filtered.iloc[start:start + per_page]

    st.dataframe(
        page_df[display_cols],
        use_container_width=True,
        height=min(600, 60 + len(page_df) * 38),
        hide_index=True,
        column_config={
            "Top Source URL": st.column_config.LinkColumn("🔗 Source", width="small"),
            "Risk Level": st.column_config.NumberColumn(
                "Risk", format="%d", min_value=0, max_value=5, width="small"),
        },
    )

    # Pagination buttons
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([1, 1, 3, 1, 1])
    if pcol1.button("⏮️", use_container_width=True,
                    disabled=st.session_state.page <= 1, key="pg_first"):
        st.session_state.page = 1
        st.rerun()
    if pcol2.button("◀️", use_container_width=True,
                    disabled=st.session_state.page <= 1, key="pg_prev"):
        st.session_state.page -= 1
        st.rerun()
    pcol3.markdown(
        f"<div style='text-align:center; padding-top:0.5rem;'>Page <b>{st.session_state.page}</b> of {total_pages}</div>",
        unsafe_allow_html=True)
    if pcol4.button("▶️", use_container_width=True,
                    disabled=st.session_state.page >= total_pages, key="pg_next"):
        st.session_state.page += 1
        st.rerun()
    if pcol5.button("⏭️", use_container_width=True,
                    disabled=st.session_state.page >= total_pages, key="pg_last"):
        st.session_state.page = total_pages
        st.rerun()

    # Downloads
    if not filtered.empty:
        dcol1, dcol2 = st.columns(2)
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        dcol1.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                filtered.to_excel(writer, index=False, sheet_name="Filtered")
            dcol2.download_button(
                "⬇️ Download Excel",
                data=buf.getvalue(),
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            pass


# ── Tab 3: Priority Flags ────────────────────────────────────────────────
with tab_flags:
    st.subheader("🔴 Entities Requiring Action")
    flagged = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False)

    if flagged.empty:
        st.markdown(
            '<div class="callout-ok">✅ No high-risk entities in this run.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="callout-danger">⚠️ <b>{len(flagged)} entities</b> need review this week</div>',
            unsafe_allow_html=True)

        critical = flagged[flagged["Risk Level"] == 5]
        high = flagged[flagged["Risk Level"] == 4]

        if not critical.empty:
            st.markdown(f"#### 🚨 Critical ({len(critical)})")
            for _, row in critical.iterrows():
                render_card(row)
        if not high.empty:
            st.markdown(f"#### 🔴 High ({len(high)})")
            for _, row in high.iterrows():
                render_card(row)

        csv = flagged.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Export priority flags (CSV)",
            data=csv,
            file_name=f"priority_flags_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
        )


# ── Tab 4: Changes ───────────────────────────────────────────────────────
with tab_alerts:
    st.subheader("🔔 Changes Since Last Run")

    alert_statuses = {"🆕 NEW", "📈 RISK INCREASED",
                      "🔄 STATUS CHANGED", "🚨 PERSISTING HIGH RISK"}
    alerts = df[df["Alert Status"].isin(alert_statuses)] \
        if "Alert Status" in df.columns else pd.DataFrame()

    if alerts.empty:
        st.markdown(
            '<div class="callout-info">ℹ️ No alerts — either this is the first run or nothing changed.</div>',
            unsafe_allow_html=True)
    else:
        alerts = alerts.sort_values("Risk Level", ascending=False)
        counts = alerts["Alert Status"].value_counts()
        cols = st.columns(min(len(counts), 4))
        for i, (status, cnt) in enumerate(counts.items()):
            cols[i % len(cols)].metric(status, cnt)

        st.markdown("---")

        alert_cols = [c for c in [
            "Brand", "Alert Status", "Classification",
            "Previous Classification", "Risk Level", "Days Seen",
            "Service Type", "Rationale",
        ] if c in alerts.columns]

        st.dataframe(
            alerts[alert_cols],
            use_container_width=True,
            height=500,
            hide_index=True,
        )


# ── Tab 5: Company Profile ───────────────────────────────────────────────
with tab_history:
    st.subheader("📜 Company Profile")

    brands = sorted(df["Brand"].dropna().unique().tolist())
    if not brands:
        st.info("No brands available.")
    else:
        brand = st.selectbox("Search and select a company:", brands, index=0)
        current = df[df["Brand"] == brand].iloc[0]

        pill_html = risk_pill(current.get("Risk Level", 2))
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
                    padding:1.5rem; border-radius:10px; border:1px solid #E5E7EB;">
          <h2 style="margin:0 0 0.5rem 0; color:#111827;">{brand}</h2>
          <div style="display:flex; gap:1rem; flex-wrap:wrap; align-items:center;">
            {pill_html}
            <span style="color:#6B7280; font-size:0.9rem;">
              <b>{current.get('Regulator Scope', '')}</b> · {current.get('Service Type', '')}
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")

        kf1, kf2, kf3 = st.columns(3)
        kf1.metric("Classification", str(current.get("Classification", ""))[:25])
        kf2.metric("Confidence", str(current.get("Confidence", "")))
        kf3.metric("Days Seen", str(current.get("Days Seen", "1")))

        st.markdown("#### 📝 Rationale")
        st.info(str(current.get("Rationale", "")))

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            st.markdown("#### 🔎 Evidence Indicators")
            for field, label in [
                ("UAE Present?", "UAE Presence"),
                ("License Signal?", "License Signal"),
                ("Unlicensed Signal?", "Unlicensed Signal"),
            ]:
                val = current.get(field, "No")
                icon = "✅" if val == "Yes" else "❌"
                st.markdown(f"- {icon} **{label}:** {val}")
        with ecol2:
            st.markdown("#### 🔗 Source")
            url = current.get("Top Source URL", "")
            if url and str(url).startswith("http"):
                st.markdown(f"[Open source page ↗]({url})")
            snippet = current.get("Key Snippet", "")
            if snippet:
                st.caption(str(snippet)[:300])

        st.markdown("---")
        st.markdown("#### 📈 Classification History")
        hist = load_history(files, brand)
        if len(hist) < 2:
            st.caption("Only one run archived — history appears after more runs.")
        else:
            st.dataframe(hist, use_container_width=True, hide_index=True)
            st.markdown("##### Risk Level Over Time")
            hist_plot = hist.copy()
            hist_plot["Run"] = range(1, len(hist_plot) + 1)
            st.line_chart(hist_plot.set_index("Run")["Risk Level"], height=220)


# ── Tab 6: Insights ──────────────────────────────────────────────────────
with tab_insights:
    st.subheader("📊 Insights Dashboard")

    ic1, ic2 = st.columns(2)
    with ic1:
        st.markdown("#### Risk Level Distribution")
        if "Risk Level" in df.columns:
            rc = df["Risk Level"].value_counts().sort_index(ascending=False)
            rc.index = [RISK_META.get(int(i), {}).get("label", str(i)) for i in rc.index]
            st.bar_chart(rc, height=280)
    with ic2:
        st.markdown("#### Classification Groups")
        if "Group" in df.columns:
            st.bar_chart(df["Group"].value_counts(), height=280)

    ic3, ic4 = st.columns(2)
    with ic3:
        st.markdown("#### Top 10 Regulator Scopes")
        if "Regulator Scope" in df.columns:
            st.bar_chart(df["Regulator Scope"].value_counts().head(10), height=280)
    with ic4:
        st.markdown("#### Top 10 Service Types")
        if "Service Type" in df.columns:
            st.bar_chart(df["Service Type"].value_counts().head(10), height=280)

    st.markdown("---")
    st.markdown("#### 📈 Trend Across All Runs")
    if len(files) >= 2:
        trend_rows = []
        for f in files[:10]:
            try:
                d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                trend_rows.append({
                    "Run": f["timestamp"].strftime("%m/%d %H:%M"),
                    "Unlicensed (4+)": int(len(d[d["Risk Level"] >= 4])),
                    "Needs Review (2-3)": int(len(d[(d["Risk Level"] >= 2) & (d["Risk Level"] <= 3)])),
                    "Licensed (0)": int(len(d[d["Risk Level"] == 0])),
                })
            except Exception:
                continue
        if trend_rows:
            trend_df = pd.DataFrame(trend_rows).set_index("Run").iloc[::-1]
            st.line_chart(trend_df, height=300)
    else:
        st.caption(f"Only {len(files)} run archived — trend chart needs 2+ runs.")

    st.markdown("---")
    st.markdown("#### Full Classification Breakdown")
    if "Classification" in df.columns:
        cls = df["Classification"].value_counts().reset_index()
        cls.columns = ["Classification", "Count"]
        cls["% of total"] = (cls["Count"] / total * 100).round(1).astype(str) + "%"
        st.dataframe(cls, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption(
    f"📁 Data: `{Path(selected_path).name}`  ·  "
    f"🕐 Loaded: {datetime.now():%Y-%m-%d %H:%M}  ·  "
    f"ℹ️ Automated first-pass screening — not a legal determination"
)
