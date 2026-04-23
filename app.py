# =============================
# UAE Regulatory Screening (FINAL VERSION)
# =============================

from __future__ import annotations
import glob, io, re
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# ── CONFIG ─────────────────────────────────────────────
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DATA DIR (FIXED FOR CLOUD) ─────────────────────────
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── ADMIN ACCESS ───────────────────────────────────────
password = st.sidebar.text_input("Admin Access", type="password")
IS_ADMIN = password == "admin123"

# ── DARK MODE ──────────────────────────────────────────
dark_mode = st.sidebar.toggle("🌙 Dark Mode")

# ── CSS ────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.main-header {
    background: linear-gradient(135deg, #1F3864 0%, #2E5090 100%);
    color: white; padding: 1.5rem;
    border-radius: 12px; margin-bottom: 1rem;
}

.company-card {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:12px;
    padding:1rem;
    margin-bottom:0.75rem;
    box-shadow:0 2px 6px rgba(0,0,0,0.05);
}

.company-card:hover {
    transform: translateY(-2px);
    box-shadow:0 6px 20px rgba(0,0,0,0.1);
    transition:0.2s;
}
</style>
""", unsafe_allow_html=True)

if dark_mode:
    st.markdown("""
    <style>
    body { background-color: #0E1117; color: #E5E7EB; }
    .company-card { background:#1A1D24; color:white; border:1px solid #2A2E36; }
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
    color = {5:"#991B1B",4:"#B91C1C",3:"#92400E",2:"#1E40AF",0:"#065F46"}.get(risk)

    st.markdown(f"""
    <div class="company-card">
        <div style="display:flex;justify-content:space-between;">
            <div>
                <b>{row.get("Brand","")}</b><br>
                <span style="color:#6B7280;font-size:0.8rem;">
                    {row.get("Service Type","")} · {row.get("Regulator Scope","")}
                </span>
                <p style="font-size:0.85rem;margin-top:0.4rem;">
                    {str(row.get("Rationale",""))[:200]}
                </p>
            </div>
            <div style="text-align:right;">
                <span style="background:{color};color:white;padding:4px 10px;border-radius:10px;font-size:0.75rem;">
                    Risk {risk}
                </span>
                <br>
                <span style="font-size:0.75rem;color:#6B7280;">
                    {row.get("Action Required","")}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────
st.sidebar.markdown("### 🛡️ UAE Screening")

files = list_files()
selected_path = None

if files:
    options = {f["timestamp"].strftime("%Y-%m-%d %H:%M"): f["path"] for f in files}
    selected_path = st.sidebar.selectbox("Select Run:", list(options.keys()))
    selected_path = options[selected_path]

# ADMIN UPLOAD
if IS_ADMIN:
    st.sidebar.markdown("---")
    uploaded = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded:
        with open(DATA_DIR / uploaded.name, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success("Uploaded")
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
tab1, tab2 = st.tabs(["🏠 Home", "🔍 Search"])

# HOME
with tab1:
    st.subheader("Top High-Risk Entities")
    top = df[df["Risk Level"] >= 4].head(10) if safe(df,"Risk Level") else df.head(10)

    for _, row in top.iterrows():
        render_card(row)

# SEARCH
with tab2:
    query = st.text_input("Search company")

    filtered = df.copy()

    if query and safe(df,"Brand"):
        filtered = filtered[df["Brand"].str.contains(query, case=False, na=False)]

    st.dataframe(filtered, use_container_width=True)

# DOWNLOAD
csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("Download CSV", csv)

st.caption("Internal tool – not a legal determination")
