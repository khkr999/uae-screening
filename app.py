from __future__ import annotations
import glob, io, re
from datetime import datetime
from difflib import SequenceMatcher
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
    background:white; border:1px solid #E5E7EB;
    border-radius:10px; padding:1rem; margin-bottom:0.5rem;
    transition:0.2s;
}
.company-card:hover {
    transform: translateY(-2px);
    box-shadow:0 6px 20px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# 🌙 DARK MODE CSS
if dark_mode:
    st.markdown("""
    <style>
    body { background-color: #0E1117; color: #E5E7EB; }
    .company-card { background:#1A1D24; color:white; border:1px solid #2A2E36; }
    .main-header { background: linear-gradient(135deg, #0F172A, #1E293B); }
    </style>
    """, unsafe_allow_html=True)

# ── DATA DIR FIXED ─────────────────────────────────────
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── HELPERS ────────────────────────────────────────────
def list_screening_files():
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

# ── SIDEBAR ────────────────────────────────────────────
st.sidebar.markdown("### 🛡️ UAE Screening")

files = list_screening_files()

selected_path = None
if files:
    options = {f["timestamp"].strftime("%Y-%m-%d %H:%M"): f["path"] for f in files}
    choice = st.sidebar.selectbox("Select Run:", list(options.keys()))
    selected_path = options[choice]

# ✅ ADMIN ONLY UPLOAD
if IS_ADMIN:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📤 Upload")
    uploaded = st.sidebar.file_uploader("", type=["xlsx"])
    if uploaded:
        save_path = DATA_DIR / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.sidebar.success("Uploaded")
        st.rerun()

# ── HEADER ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
<h2>🛡️ UAE Regulatory Screening</h2>
<p>Monitor and flag UAE financial entities</p>
</div>
""", unsafe_allow_html=True)

# ── MAIN ───────────────────────────────────────────────
if selected_path is None:
    st.warning("Upload a file to start.")
    st.stop()

df = load_data(selected_path)
if df.empty:
    st.error("File is empty or invalid.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────
total = len(df)
high_risk = len(df[df["Risk Level"] >= 4])
risk_up = len(df[df.get("Alert Status", "") == "📈 RISK INCREASED"])

st.info(f"⚠️ {high_risk} high-risk entities detected. {risk_up} increasing risk.")

k1, k2 = st.columns(2)
k1.metric("Total", total)
k2.metric("High Risk", high_risk)

# ── QUICK ACTIONS ──────────────────────────────────────
c1, c2, c3 = st.columns(3)
if c1.button("🔴 High Risk"):
    df = df[df["Risk Level"] >= 4]
if c2.button("🆕 New"):
    df = df[df.get("Alert Status", "") == "🆕 NEW"]
if c3.button("₿ Crypto"):
    df = df[df["Service Type"].astype(str).str.contains("crypto", case=False, na=False)]

# ── SEARCH ─────────────────────────────────────────────
query = st.text_input("🔍 Search company")

if query:
    df = df[df["Brand"].astype(str).str.contains(query, case=False, na=False)]

# ── TABLE ──────────────────────────────────────────────
def highlight(row):
    if row["Risk Level"] >= 4:
        return ["background-color: #fee2e2"] * len(row)
    return [""] * len(row)

st.dataframe(
    df.style.apply(highlight, axis=1),
    use_container_width=True
)

# ── DOWNLOAD ───────────────────────────────────────────
csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("Download CSV", csv)

# ── FOOTER ─────────────────────────────────────────────
st.caption("Internal tool – not a legal determination")
