from __future__ import annotations
import glob, io, re
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# Optional autocomplete
try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except:
    HAS_SEARCHBOX = False

# ── CONFIG ─────────────────────────────────────────────
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── SIDEBAR ────────────────────────────────────────────
password = st.sidebar.text_input("Admin Access", type="password")
IS_ADMIN = password == "admin123"
dark_mode = st.sidebar.toggle("🌙 Dark Mode")

# ── CSS ────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.main-header {
    background: linear-gradient(135deg, #1F3864, #2E5090);
    color:white;
    padding:1.5rem;
    border-radius:12px;
    margin-bottom:1rem;
}

/* 🔥 CARDS */
.card {
    background:white;
    border-radius:14px;
    padding:1.2rem;
    margin-bottom:0.8rem;
    border:1px solid #E5E7EB;
    box-shadow:0 4px 10px rgba(0,0,0,0.05);
    transition:0.2s;
}
.card:hover {
    transform: translateY(-3px);
    box-shadow:0 10px 25px rgba(0,0,0,0.1);
}
.card-title {
    font-size:1.1rem;
    font-weight:700;
    color:#111827;
}
.card-meta {
    font-size:0.8rem;
    color:#6B7280;
}
.card-text {
    font-size:0.9rem;
    margin-top:0.4rem;
    color:#374151;
}
.risk-pill {
    padding:4px 10px;
    border-radius:10px;
    color:white;
    font-size:0.75rem;
}
</style>
""", unsafe_allow_html=True)

if dark_mode:
    st.markdown("""
    <style>
    body { background:#0E1117; color:#E5E7EB; }
    .card { background:#1A1D24; border:1px solid #2A2E36; }
    </style>
    """, unsafe_allow_html=True)

# ── HELPERS ────────────────────────────────────────────
def list_files():
    files = []
    for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
        p = Path(path)
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})", p.name)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M")
            files.append({"path": path, "timestamp": ts})
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)

def load_data(path):
    try:
        return pd.read_excel(path, sheet_name="📋 All Results")
    except:
        return pd.read_excel(path)

def safe(df, col):
    return col in df.columns

def render_card(row):
    risk = int(row.get("Risk Level", 2))
    color = {5:"#991B1B",4:"#DC2626",3:"#F59E0B",2:"#2563EB",0:"#059669"}.get(risk)

    st.markdown(f"""
    <div class="card">
        <div style="display:flex;justify-content:space-between;">
            <div>
                <div class="card-title">{row.get("Brand","")}</div>
                <div class="card-meta">
                    {row.get("Service Type","")} · {row.get("Regulator Scope","")}
                </div>
                <div class="card-text">
                    {str(row.get("Rationale",""))[:240]}
                </div>
            </div>
            <div style="text-align:right;">
                <div class="risk-pill" style="background:{color};">
                    Risk {risk}
                </div>
                <div style="font-size:0.75rem;margin-top:5px;color:#6B7280;">
                    {row.get("Action Required","")}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── FILE SELECT ────────────────────────────────────────
files = list_files()
selected_path = None

if files:
    options = {f["timestamp"].strftime("%Y-%m-%d %H:%M"): f["path"] for f in files}
    selected_path = st.sidebar.selectbox("Select Run:", list(options.keys()))
    selected_path = options[selected_path]

# Upload (admin only)
if IS_ADMIN:
    uploaded = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded:
        with open(DATA_DIR / uploaded.name, "wb") as f:
            f.write(uploaded.getbuffer())
        st.rerun()

# ── HEADER ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
<h2>🛡️ UAE Regulatory Screening</h2>
<p>Monitor and flag UAE financial entities</p>
</div>
""", unsafe_allow_html=True)

if not selected_path:
    st.warning("Upload a file to start.")
    st.stop()

df = load_data(selected_path)

# ── KPIs ───────────────────────────────────────────────
total = len(df)
high_risk = len(df[df["Risk Level"] >= 4]) if safe(df,"Risk Level") else 0
risk_up = len(df[df["Alert Status"]=="📈 RISK INCREASED"]) if safe(df,"Alert Status") else 0

st.info(f"⚠️ {high_risk} high-risk entities detected | {risk_up} increasing risk")

c1,c2 = st.columns(2)
c1.metric("Total", total)
c2.metric("High Risk", high_risk)

# ── TABS ───────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🏠 Home", "🔍 Search", "📊 Insights"])

# HOME
with tab1:
    top = df[df["Risk Level"] >= 4].head(10) if safe(df,"Risk Level") else df.head(10)
    for _, row in top.iterrows():
        render_card(row)

# SEARCH
with tab2:
    brands = df["Brand"].dropna().unique().tolist() if safe(df,"Brand") else []

    def search_func(q):
        return [b for b in brands if q.lower() in b.lower()][:10]

    if HAS_SEARCHBOX:
        selected = st_searchbox(search_func, placeholder="Search company...")
    else:
        selected = st.selectbox("Search", [""] + brands)

    c1,c2 = st.columns(2)

    with c1:
        risk_filter = st.multiselect("Risk Level", sorted(df["Risk Level"].unique(), reverse=True))

    with c2:
        reg_filter = st.multiselect("Regulator", df["Regulator Scope"].unique() if safe(df,"Regulator Scope") else [])

    chip_cols = st.columns(6)
    chips = ["high","new","up","licensed","crypto","clear"]

    for i,key in enumerate(chips):
        if chip_cols[i].button(key):
            st.session_state["chip"] = key

    filtered = df.copy()

    if selected:
        filtered = filtered[filtered["Brand"] == selected]

    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]

    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]

    chip = st.session_state.get("chip")

    if chip == "high":
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "new" and safe(df,"Alert Status"):
        filtered = filtered[filtered["Alert Status"]=="🆕 NEW"]
    elif chip == "up" and safe(df,"Alert Status"):
        filtered = filtered[filtered["Alert Status"]=="📈 RISK INCREASED"]
    elif chip == "licensed":
        filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "crypto":
        filtered = filtered[df["Service Type"].str.contains("crypto", case=False, na=False)]

    st.dataframe(filtered, use_container_width=True)

# INSIGHTS
with tab3:
    if safe(df,"Risk Level"):
        st.bar_chart(df["Risk Level"].value_counts())

    if safe(df,"Regulator Scope"):
        st.bar_chart(df["Regulator Scope"].value_counts().head(10))

    if safe(df,"Service Type"):
        st.bar_chart(df["Service Type"].value_counts().head(10))

# DOWNLOAD
csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("Download CSV", csv)

st.caption("Internal tool – not a legal determination")
