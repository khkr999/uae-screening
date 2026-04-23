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

# ── DATA DIRECTORY ─────────────────────────────────────
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
    background: linear-gradient(135deg, #1F3864, #2E5090);
    color: white;
    padding: 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}

.company-card {
    background:white;
    border:1px solid #E5E7EB;
    border-radius:10px;
    padding:1rem;
    margin-bottom:0.5rem;
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
        df = pd.read_excel(path, sheet_name="📋 All Results")
    except:
        try:
            df = pd.read_excel(path)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return pd.DataFrame()
    return df

def safe_col(df, col):
    return col in df.columns

# ── SIDEBAR ────────────────────────────────────────────
st.sidebar.markdown("### 🛡️ UAE Screening")

files = list_files()
selected_path = None

if files:
    options = {f["timestamp"].strftime("%Y-%m-%d %H:%M"): f["path"] for f in files}
    choice = st.sidebar.selectbox("Select Run:", list(options.keys()))
    selected_path = options[choice]

# ADMIN UPLOAD
if IS_ADMIN:
    st.sidebar.markdown("---")
    uploaded = st.sidebar.file_uploader("Upload Excel", type=["xlsx"])
    if uploaded:
        save_path = DATA_DIR / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success("Uploaded successfully")
        st.rerun()

# ── HEADER ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
<h2>🛡️ UAE Regulatory Screening</h2>
<p>Monitor and flag UAE financial entities</p>
</div>
""", unsafe_allow_html=True)

if selected_path is None:
    st.warning("Upload a file to start.")
    st.stop()

df = load_data(selected_path)

if df.empty:
    st.error("File is empty or invalid.")
    st.stop()

# ── SAFE KPI CALCULATIONS ──────────────────────────────
total = len(df)

if safe_col(df, "Risk Level"):
    high_risk = len(df[df["Risk Level"] >= 4])
else:
    high_risk = 0

if safe_col(df, "Alert Status"):
    risk_up = len(df[df["Alert Status"] == "📈 RISK INCREASED"])
else:
    risk_up = 0

# ── SMART SUMMARY ──────────────────────────────────────
st.info(f"⚠️ {high_risk} high-risk entities detected | {risk_up} increasing risk")

# ── KPI DISPLAY ────────────────────────────────────────
k1, k2 = st.columns(2)
k1.metric("Total Entities", total)
k2.metric("High Risk", high_risk)

# ── QUICK FILTERS ──────────────────────────────────────
c1, c2, c3 = st.columns(3)

if c1.button("🔴 High Risk"):
    if safe_col(df, "Risk Level"):
        df = df[df["Risk Level"] >= 4]

if c2.button("🆕 New"):
    if safe_col(df, "Alert Status"):
        df = df[df["Alert Status"] == "🆕 NEW"]

if c3.button("₿ Crypto"):
    if safe_col(df, "Service Type"):
        df = df[df["Service Type"].astype(str).str.contains("crypto", case=False, na=False)]

# ── SEARCH ─────────────────────────────────────────────
query = st.text_input("🔍 Search company")

if query and safe_col(df, "Brand"):
    df = df[df["Brand"].astype(str).str.contains(query, case=False, na=False)]

# ── TABLE (SAFE DISPLAY) ───────────────────────────────
def highlight(row):
    if "Risk Level" in row and row["Risk Level"] >= 4:
        return ["background-color: #fee2e2"] * len(row)
    return [""] * len(row)

try:
    styled_df = df.style.apply(highlight, axis=1)
    st.dataframe(styled_df, use_container_width=True)
except:
    st.dataframe(df, use_container_width=True)

# ── DOWNLOAD ───────────────────────────────────────────
try:
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Download CSV", csv)
except:
    pass

# ── FOOTER ─────────────────────────────────────────────
st.caption("Internal tool – not a legal determination")
