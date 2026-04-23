from __future__ import annotations
import glob
import html
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Optional autocomplete
try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except Exception:
    HAS_SEARCHBOX = False


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ADMIN_PASSWORD = "admin123"


# =========================================================
# SESSION
# =========================================================
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "active_chip" not in st.session_state:
    st.session_state.active_chip = "all"

if "selected_run_label" not in st.session_state:
    st.session_state.selected_run_label = None


# =========================================================
# HELPERS
# =========================================================
def list_files() -> list[dict]:
    files = []
    for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
        p = Path(path)
        match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})", p.name)
        if match:
            ts = datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M")
        else:
            ts = datetime.fromtimestamp(p.stat().st_mtime)
        files.append({"path": str(p), "timestamp": ts, "name": p.name})
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)


def load_data(path: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name="📋 All Results")
    except Exception:
        return pd.read_excel(path)


def has_col(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def clean_text(value, default=""):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def int_or_default(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def risk_meta(risk: int) -> tuple[str, str, str]:
    mapping = {
        5: ("Critical", "#E11D48", "critical"),
        4: ("High", "#F97316", "high"),
        3: ("Medium", "#EAB308", "medium"),
        2: ("Monitor", "#3B82F6", "monitor"),
        1: ("Low", "#10B981", "low"),
        0: ("Licensed", "#059669", "licensed"),
    }
    return mapping.get(risk, ("Unknown", "#6B7280", "unknown"))


def theme_tokens() -> dict:
    if st.session_state.theme == "dark":
        return {
            "bg": "#071122",
            "bg2": "#0B1730",
            "surface": "#0E1B36",
            "surface_soft": "#122245",
            "text": "#F5F7FF",
            "muted": "#A8B3CF",
            "border": "rgba(255,255,255,0.08)",
            "accent": "#4F7CFF",
            "accent2": "#7C4DFF",
            "success": "#10B981",
            "shadow": "0 12px 30px rgba(0,0,0,0.24)",
            "hero1": "#2457D6",
            "hero2": "#0C8C8C",
            "hero3": "#7C4DFF",
            "sidebar": "#0B1530",
        }
    return {
        "bg": "#F3F7FC",
        "bg2": "#EAF1FB",
        "surface": "#FFFFFF",
        "surface_soft": "#F9FBFF",
        "text": "#142033",
        "muted": "#66738A",
        "border": "rgba(20,32,51,0.08)",
        "accent": "#2563EB",
        "accent2": "#7C3AED",
        "success": "#059669",
        "shadow": "0 12px 26px rgba(15,23,42,0.08)",
        "hero1": "#2563EB",
        "hero2": "#0891B2",
        "hero3": "#7C3AED",
        "sidebar": "#F7FAFF",
    }


def inject_css():
    t = theme_tokens()
    st.markdown(
        f"""
        <style>
        #MainMenu, footer, header {{
            visibility: hidden;
        }}

        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(124,77,255,0.12), transparent 24%),
                radial-gradient(circle at top left, rgba(37,99,235,0.10), transparent 22%),
                linear-gradient(180deg, {t["bg"]} 0%, {t["bg2"]} 100%);
            color: {t["text"]};
        }}

        .block-container {{
            max-width: 1450px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }}

        [data-testid="stSidebar"] {{
            background: {t["sidebar"]};
            border-right: 1px solid {t["border"]};
        }}

        [data-testid="stMetric"] {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 20px;
            padding: 0.75rem 0.9rem;
            box-shadow: {t["shadow"]};
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        .stTextInput > div > div,
        .stMultiSelect > div > div {{
            border-radius: 14px !important;
        }}

        .hero {{
            border-radius: 28px;
            padding: 1.7rem;
            background:
                radial-gradient(circle at 88% 20%, rgba(255,255,255,0.16), transparent 16%),
                linear-gradient(135deg, {t["hero1"]} 0%, {t["hero2"]} 48%, {t["hero3"]} 100%);
            color: white;
            box-shadow: {t["shadow"]};
            margin-bottom: 1rem;
            border: 1px solid rgba(255,255,255,0.12);
        }}

        .hero-title {{
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.45rem;
            letter-spacing: -0.02em;
        }}

        .hero-sub {{
            font-size: 1rem;
            line-height: 1.55;
            color: rgba(255,255,255,0.94);
        }}

        .hero-badge {{
            display: inline-block;
            margin-top: 0.9rem;
            padding: 0.42rem 0.82rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.18);
            font-size: 0.82rem;
            font-weight: 700;
        }}

        .section-title {{
            font-size: 1.05rem;
            font-weight: 800;
            color: {t["text"]};
            margin: 0 0 0.85rem 0;
        }}

        .summary-card {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 22px;
            box-shadow: {t["shadow"]};
            padding: 1rem;
        }}

        .soft-card {{
            background: {t["surface_soft"]};
            border: 1px solid {t["border"]};
            border-radius: 18px;
            padding: 0.95rem;
        }}

        .entity-card {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 22px;
            box-shadow: {t["shadow"]};
            padding: 1rem;
            margin-bottom: 0.9rem;
        }}

        .entity-title {{
            font-size: 1.1rem;
            font-weight: 800;
            color: {t["text"]};
            margin-bottom: 0.35rem;
        }}

        .entity-meta {{
            color: {t["muted"]};
            font-size: 0.9rem;
            line-height: 1.45;
            margin-bottom: 0.75rem;
        }}

        .entity-text {{
            color: {t["text"]};
            font-size: 0.94rem;
            line-height: 1.65;
        }}

        .muted {{
            color: {t["muted"]};
            font-size: 0.84rem;
        }}

        .risk-pill {{
            display: inline-block;
            padding: 0.42rem 0.75rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 800;
        }}

        .risk-critical {{
            background: rgba(225,29,72,0.12);
            color: #E11D48;
            border: 1px solid rgba(225,29,72,0.35);
        }}

        .risk-high {{
            background: rgba(249,115,22,0.12);
            color: #F97316;
            border: 1px solid rgba(249,115,22,0.35);
        }}

        .risk-medium {{
            background: rgba(234,179,8,0.14);
            color: #CA8A04;
            border: 1px solid rgba(234,179,8,0.35);
        }}

        .risk-monitor {{
            background: rgba(59,130,246,0.12);
            color: #3B82F6;
            border: 1px solid rgba(59,130,246,0.35);
        }}

        .risk-low {{
            background: rgba(16,185,129,0.12);
            color: #10B981;
            border: 1px solid rgba(16,185,129,0.35);
        }}

        .risk-licensed {{
            background: rgba(5,150,105,0.12);
            color: #059669;
            border: 1px solid rgba(5,150,105,0.35);
        }}

        .risk-unknown {{
            background: rgba(107,114,128,0.12);
            color: #6B7280;
            border: 1px solid rgba(107,114,128,0.35);
        }}

        div.stButton > button,
        .stDownloadButton button {{
            border-radius: 14px !important;
            padding: 0.52rem 0.9rem !important;
            font-weight: 700 !important;
        }}

        button[kind="primary"] {{
            background: linear-gradient(135deg, {t["accent"]}, {t["accent2"]}) !important;
            color: white !important;
            border: none !important;
        }}

        .chip-note {{
            color: {t["muted"]};
            font-size: 0.84rem;
            margin-top: 0.25rem;
            margin-bottom: 0.6rem;
        }}

        .empty-state {{
            background: {t["surface"]};
            border: 1px dashed {t["border"]};
            border-radius: 22px;
            padding: 1.8rem;
            text-align: center;
            color: {t["muted"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">🛡️ UAE Regulatory Screening</div>
            <div class="hero-sub">
                A cleaner review workspace for screening, triage, search, and quick insight discovery across UAE financial entities.
            </div>
            <div class="hero-badge">Modern UI · Better usability · Safer rendering</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_entity_card(row: pd.Series):
    risk = int_or_default(row.get("Risk Level", 2), 2)
    risk_label, _, risk_class = risk_meta(risk)

    brand = html.escape(clean_text(row.get("Brand"), "Unknown entity"))
    service = html.escape(clean_text(row.get("Service Type"), "Service type not provided"))
    regulator = html.escape(clean_text(row.get("Regulator Scope"), "Scope not provided"))
    rationale = html.escape(clean_text(row.get("Rationale"), "No rationale provided."))
    action_required = html.escape(clean_text(row.get("Action Required"), "Review details"))
    alert_status = html.escape(clean_text(row.get("Alert Status"), ""))

    right_col = f"""
        <div style="text-align:right;">
            <div class="risk-pill risk-{risk_class}">{risk_label} · Risk {risk}</div>
            <div class="muted" style="margin-top:0.55rem;">{action_required}</div>
        </div>
    """

    status_html = f'<div class="muted" style="margin-top:0.6rem;">Status: {alert_status}</div>' if alert_status else ""

    st.markdown(
        f"""
        <div class="entity-card">
            <div style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap;">
                <div style="flex:1; min-width:260px;">
                    <div class="entity-title">{brand}</div>
                    <div class="entity-meta">{service} · {regulator}</div>
                    <div class="entity-text">{rationale[:340]}</div>
                    {status_html}
                </div>
                <div style="min-width:170px;">
                    {right_col}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_dataframe(df: pd.DataFrame, selected_brand, risk_filter, reg_filter, chip) -> pd.DataFrame:
    filtered = df.copy()

    if selected_brand and has_col(filtered, "Brand"):
        filtered = filtered[filtered["Brand"].astype(str) == str(selected_brand)]

    if risk_filter and has_col(filtered, "Risk Level"):
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]

    if reg_filter and has_col(filtered, "Regulator Scope"):
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]

    if chip == "high" and has_col(filtered, "Risk Level"):
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "medium" and has_col(filtered, "Risk Level"):
        filtered = filtered[filtered["Risk Level"] == 3]
    elif chip == "licensed" and has_col(filtered, "Risk Level"):
        filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "new" and has_col(filtered, "Alert Status"):
        filtered = filtered[filtered["Alert Status"].astype(str) == "🆕 NEW"]
    elif chip == "up" and has_col(filtered, "Alert Status"):
        filtered = filtered[filtered["Alert Status"].astype(str) == "📈 RISK INCREASED"]
    elif chip == "crypto" and has_col(filtered, "Service Type"):
        filtered = filtered[
            filtered["Service Type"].astype(str).str.contains("crypto", case=False, na=False)
        ]
    elif chip == "clear" and has_col(filtered, "Action Required"):
        filtered = filtered[
            filtered["Action Required"].astype(str).str.contains("clear|none|no action", case=False, na=False)
        ]

    return filtered


def search_func_factory(brands: list[str]):
    def search_func(query: str) -> list[str]:
        if not query:
            return brands[:10]
        return [b for b in brands if query.lower() in b.lower()][:12]
    return search_func


# =========================================================
# UI START
# =========================================================
inject_css()

with st.sidebar:
    st.markdown("### Control Center")
    st.caption("Manage runs, theme, filters, and admin access.")

    run_files = list_files()
    selected_path = None

    if run_files:
        options = {
            f'{item["timestamp"].strftime("%Y-%m-%d %H:%M")} · {item["name"]}': item["path"]
            for item in run_files
        }
        labels = list(options.keys())

        if st.session_state.selected_run_label not in labels:
            st.session_state.selected_run_label = labels[0]

        selected_label = st.selectbox(
            "Select screening run",
            labels,
            index=labels.index(st.session_state.selected_run_label),
        )
        st.session_state.selected_run_label = selected_label
        selected_path = options[selected_label]
    else:
        st.info("No screening files found.")

    dark_mode = st.toggle("Dark mode", value=st.session_state.theme == "dark")
    st.session_state.theme = "dark" if dark_mode else "light"

    with st.expander("Admin access", expanded=False):
        if not st.session_state.is_admin:
            admin_password = st.text_input("Enter admin password", type="password")
            if st.button("Unlock admin tools", use_container_width=True):
                if admin_password == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.success("Admin tools unlocked.")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            st.success("Admin mode enabled.")
            if st.button("Lock admin tools", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()

        if st.session_state.is_admin:
            uploaded = st.file_uploader("Upload Excel run", type=["xlsx"])
            if uploaded is not None:
                save_path = DATA_DIR / uploaded.name
                with open(save_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                st.success(f"Uploaded: {uploaded.name}")
                st.rerun()

render_hero()

if not selected_path:
    st.markdown(
        """
        <div class="empty-state">
            <h3 style="margin-bottom:0.4rem;">No data available</h3>
            <div>Upload an Excel file from the admin section to start.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

df = load_data(selected_path)

if has_col(df, "Risk Level"):
    df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(0).astype(int)

total_entities = len(df)
high_risk = len(df[df["Risk Level"] >= 4]) if has_col(df, "Risk Level") else 0
risk_up = len(df[df["Alert Status"].astype(str) == "📈 RISK INCREASED"]) if has_col(df, "Alert Status") else 0
licensed = len(df[df["Risk Level"] == 0]) if has_col(df, "Risk Level") else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Entities screened", f"{total_entities:,}")
with m2:
    st.metric("High risk", f"{high_risk:,}")
with m3:
    st.metric("Risk increased", f"{risk_up:,}")
with m4:
    st.metric("Licensed / clear", f"{licensed:,}")

tab1, tab2, tab3, tab4 = st.tabs(["🏠 Overview", "🔍 Search & Filter", "📊 Insights", "🗂️ Dataset"])

with tab1:
    left, right = st.columns([1.9, 1])

    with left:
        st.markdown('<div class="section-title">Priority review queue</div>', unsafe_allow_html=True)
        if has_col(df, "Risk Level"):
            top_entities = df.sort_values("Risk Level", ascending=False).head(10)
        else:
            top_entities = df.head(10)

        if len(top_entities) == 0:
            st.markdown('<div class="empty-state">No entities found in this run.</div>', unsafe_allow_html=True)
        else:
            for _, row in top_entities.iterrows():
                render_entity_card(row)

    with right:
        st.markdown('<div class="section-title">Quick summary</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="summary-card">', unsafe_allow_html=True)
            st.write(f"**Selected run**")
            st.code(Path(selected_path).name, language=None)

            dominant_regulator = "N/A"
            if has_col(df, "Regulator Scope") and not df["Regulator Scope"].dropna().empty:
                dominant_regulator = df["Regulator Scope"].astype(str).value_counts().idxmax()

            dominant_service = "N/A"
            if has_col(df, "Service Type") and not df["Service Type"].dropna().empty:
                dominant_service = df["Service Type"].astype(str).value_counts().idxmax()

            st.write(f"**Top regulator scope**  \n{dominant_regulator}")
            st.write(f"**Most frequent service type**  \n{dominant_service}")
            st.write(f"**Rows available**  \n{total_entities:,}")
            st.caption("Use Search & Filter for detailed review.")
            st.markdown("</div>", unsafe_allow_html=True)

        if has_col(df, "Risk Level"):
            st.markdown("")
            st.markdown('<div class="section-title">Risk distribution</div>', unsafe_allow_html=True)
            st.bar_chart(df["Risk Level"].value_counts().sort_index(), use_container_width=True)

with tab2:
    brands = sorted(df["Brand"].dropna().astype(str).unique().tolist()) if has_col(df, "Brand") else []

    top1, top2 = st.columns([1.2, 1])

    with top1:
        st.markdown('<div class="section-title">Entity search</div>', unsafe_allow_html=True)
        if HAS_SEARCHBOX and brands:
            selected_brand = st_searchbox(
                search_func_factory(brands),
                placeholder="Search company or brand...",
                key="brand_searchbox",
            )
        else:
            selected_brand = st.selectbox("Brand", [""] + brands)
            selected_brand = selected_brand or None

    with top2:
        st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        with f1:
            risk_filter = st.multiselect(
                "Risk level",
                sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True) if has_col(df, "Risk Level") else []
            )
        with f2:
            reg_filter = st.multiselect(
                "Regulator scope",
                sorted(df["Regulator Scope"].dropna().astype(str).unique().tolist()) if has_col(df, "Regulator Scope") else []
            )

    st.markdown('<div class="section-title">Quick filters</div>', unsafe_allow_html=True)
    st.markdown('<div class="chip-note">Use one quick filter at a time.</div>', unsafe_allow_html=True)

    chip_items = [
        ("all", "All"),
        ("high", "High risk"),
        ("medium", "Medium"),
        ("new", "New"),
        ("up", "Risk increased"),
        ("licensed", "Licensed"),
        ("crypto", "Crypto"),
        ("clear", "Clear"),
    ]
    chip_cols = st.columns(len(chip_items))
    for i, (chip_key, chip_label) in enumerate(chip_items):
        with chip_cols[i]:
            is_primary = st.session_state.active_chip == chip_key
            if st.button(chip_label, key=f"chip_{chip_key}", type="primary" if is_primary else "secondary", use_container_width=True):
                st.session_state.active_chip = chip_key

    filtered_df = filter_dataframe(
        df=df,
        selected_brand=selected_brand,
        risk_filter=risk_filter,
        reg_filter=reg_filter,
        chip=st.session_state.active_chip,
    )

    left, right = st.columns([1.45, 1])

    with left:
        st.markdown('<div class="section-title">Filtered results</div>', unsafe_allow_html=True)
        st.caption(f"{len(filtered_df):,} matching entities")
        st.dataframe(filtered_df, use_container_width=True, height=520)

    with right:
        st.markdown('<div class="section-title">Preview cards</div>', unsafe_allow_html=True)
        if len(filtered_df) == 0:
            st.markdown('<div class="empty-state">No matching entities found.</div>', unsafe_allow_html=True)
        else:
            for _, row in filtered_df.head(5).iterrows():
                render_entity_card(row)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Risk level breakdown</div>', unsafe_allow_html=True)
        if has_col(df, "Risk Level"):
            st.bar_chart(df["Risk Level"].value_counts().sort_index(), use_container_width=True)
        else:
            st.info("Risk Level column is not available.")

    with c2:
        st.markdown('<div class="section-title">Top regulator scopes</div>', unsafe_allow_html=True)
        if has_col(df, "Regulator Scope"):
            st.bar_chart(df["Regulator Scope"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Regulator Scope column is not available.")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="section-title">Service type mix</div>', unsafe_allow_html=True)
        if has_col(df, "Service Type"):
            st.bar_chart(df["Service Type"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Service Type column is not available.")

    with c4:
        st.markdown('<div class="section-title">Alert status mix</div>', unsafe_allow_html=True)
        if has_col(df, "Alert Status"):
            st.bar_chart(df["Alert Status"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Alert Status column is not available.")

with tab4:
    left, right = st.columns([1.1, 1])

    with left:
        st.markdown('<div class="section-title">Dataset details</div>', unsafe_allow_html=True)
        st.write(f"**File name:** {Path(selected_path).name}")
        st.write(f"**Rows:** {len(df):,}")
        st.write(f"**Columns:** {len(df.columns):,}")

        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Download CSV",
            data=csv_data,
            file_name=f"{Path(selected_path).stem}.csv",
            mime="text/csv",
        )

    with right:
        st.markdown('<div class="section-title">Columns</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Column": df.columns}), use_container_width=True, height=320)

st.caption("Internal tool — for monitoring and review support only, not a legal determination.")
