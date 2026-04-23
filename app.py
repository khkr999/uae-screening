from __future__ import annotations
import glob
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
# PAGE CONFIG
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
# SESSION STATE
# =========================================================
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "active_chip" not in st.session_state:
    st.session_state.active_chip = "all"

if "search_value" not in st.session_state:
    st.session_state.search_value = ""

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


def safe_series(df: pd.DataFrame, col: str, default="") -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def int_or_default(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def risk_meta(risk: int) -> tuple[str, str]:
    mapping = {
        5: ("Critical", "#E11D48"),
        4: ("High", "#F97316"),
        3: ("Medium", "#EAB308"),
        2: ("Monitor", "#3B82F6"),
        1: ("Low", "#10B981"),
        0: ("Licensed", "#059669"),
    }
    return mapping.get(risk, ("Unknown", "#6B7280"))


def theme_tokens() -> dict:
    if st.session_state.theme == "dark":
        return {
            "bg": "#0B1020",
            "bg_soft": "#121933",
            "surface": "rgba(18, 25, 51, 0.80)",
            "surface_2": "#18213F",
            "text": "#F3F6FF",
            "muted": "#A7B0C5",
            "border": "rgba(255,255,255,0.08)",
            "accent": "#5B8CFF",
            "accent_2": "#22C55E",
            "shadow": "0 12px 32px rgba(0,0,0,0.22)",
            "hero_1": "#1D4ED8",
            "hero_2": "#0F766E",
            "hero_3": "#7C3AED",
        }
    return {
        "bg": "#F5F7FB",
        "bg_soft": "#ECF2FF",
        "surface": "rgba(255,255,255,0.88)",
        "surface_2": "#FFFFFF",
        "text": "#111827",
        "muted": "#6B7280",
        "border": "rgba(17,24,39,0.08)",
        "accent": "#2563EB",
        "accent_2": "#059669",
        "shadow": "0 12px 30px rgba(15,23,42,0.08)",
        "hero_1": "#2563EB",
        "hero_2": "#0EA5E9",
        "hero_3": "#7C3AED",
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
                radial-gradient(circle at top right, rgba(124,58,237,0.14), transparent 24%),
                radial-gradient(circle at top left, rgba(37,99,235,0.14), transparent 26%),
                linear-gradient(180deg, {t["bg"]} 0%, {t["bg_soft"]} 100%);
            color: {t["text"]};
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1450px;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {t["surface_2"]} 0%, {t["bg"]} 100%);
            border-right: 1px solid {t["border"]};
        }}

        [data-testid="stMetric"] {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 20px;
            padding: 0.8rem 1rem;
            box-shadow: {t["shadow"]};
            backdrop-filter: blur(10px);
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        .stTextInput > div > div,
        .stMultiSelect > div > div,
        .stDateInput > div > div {{
            border-radius: 14px !important;
        }}

        .hero {{
            position: relative;
            overflow: hidden;
            border-radius: 28px;
            padding: 1.6rem 1.6rem 1.25rem 1.6rem;
            background:
                radial-gradient(circle at 85% 15%, rgba(255,255,255,0.18), transparent 18%),
                linear-gradient(135deg, {t["hero_1"]} 0%, {t["hero_2"]} 50%, {t["hero_3"]} 100%);
            color: white;
            box-shadow: {t["shadow"]};
            margin-bottom: 1rem;
            border: 1px solid rgba(255,255,255,0.12);
        }}

        .hero h1 {{
            margin: 0 0 0.25rem 0;
            font-size: 2rem;
            line-height: 1.15;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .hero p {{
            margin: 0;
            font-size: 0.98rem;
            color: rgba(255,255,255,0.92);
        }}

        .glass-card {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 22px;
            box-shadow: {t["shadow"]};
            backdrop-filter: blur(12px);
            padding: 1rem 1rem 0.9rem 1rem;
        }}

        .section-title {{
            font-size: 1.05rem;
            font-weight: 800;
            color: {t["text"]};
            margin: 0 0 0.75rem 0;
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 0.8rem 0 1rem 0;
        }}

        .stat-card {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 20px;
            box-shadow: {t["shadow"]};
            padding: 1rem;
            min-height: 110px;
        }}

        .stat-label {{
            color: {t["muted"]};
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.55rem;
        }}

        .stat-value {{
            color: {t["text"]};
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: -0.03em;
        }}

        .stat-sub {{
            color: {t["muted"]};
            font-size: 0.84rem;
            margin-top: 0.55rem;
        }}

        .toolbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 0.4rem;
        }}

        .toolbar-badge {{
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 999px;
            padding: 0.42rem 0.75rem;
            font-size: 0.82rem;
            font-weight: 600;
            color: white;
        }}

        .screening-card {{
            background: {t["surface"]};
            border: 1px solid {t["border"]};
            border-radius: 22px;
            box-shadow: {t["shadow"]};
            padding: 1rem;
            margin-bottom: 0.9rem;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }}

        .screening-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(91, 140, 255, 0.45);
            box-shadow: 0 16px 36px rgba(0,0,0,0.12);
        }}

        .screening-head {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
        }}

        .screening-brand {{
            color: {t["text"]};
            font-size: 1.08rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }}

        .screening-meta {{
            color: {t["muted"]};
            font-size: 0.88rem;
            line-height: 1.5;
        }}

        .screening-rationale {{
            color: {t["text"]};
            opacity: 0.92;
            font-size: 0.93rem;
            margin-top: 0.8rem;
            line-height: 1.6;
        }}

        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 0.38rem 0.72rem;
            font-size: 0.78rem;
            font-weight: 800;
            white-space: nowrap;
        }}

        .action-text {{
            color: {t["muted"]};
            font-size: 0.8rem;
            margin-top: 0.45rem;
            text-align: right;
            max-width: 210px;
        }}

        .subtle-note {{
            color: {t["muted"]};
            font-size: 0.84rem;
            margin-top: 0.35rem;
        }}

        .empty-state {{
            text-align: center;
            padding: 2rem 1rem;
            background: {t["surface"]};
            border: 1px dashed {t["border"]};
            border-radius: 22px;
            color: {t["muted"]};
        }}

        div.stButton > button,
        .stDownloadButton button {{
            border-radius: 14px !important;
            padding: 0.55rem 1rem !important;
            border: 1px solid {t["border"]} !important;
            background: {t["surface_2"]} !important;
            color: {t["text"]} !important;
            font-weight: 700 !important;
        }}

        div.stButton > button:hover,
        .stDownloadButton button:hover {{
            border-color: rgba(91, 140, 255, 0.5) !important;
            transform: translateY(-1px);
        }}

        button[kind="primary"] {{
            background: linear-gradient(135deg, {t["accent"]}, {t["hero_3"]}) !important;
            color: white !important;
            border: none !important;
        }}

        [data-testid="stTabs"] button {{
            font-weight: 700;
        }}

        [data-testid="stDataFrame"] {{
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid {t["border"]};
            box-shadow: {t["shadow"]};
        }}

        @media (max-width: 1100px) {{
            .stat-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 700px) {{
            .stat-grid {{
                grid-template-columns: 1fr;
            }}
            .hero h1 {{
                font-size: 1.6rem;
            }}
            .screening-head {{
                flex-direction: column;
            }}
            .action-text {{
                text-align: left;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label: str, value: str, sub: str):
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_entity_card(row: pd.Series):
    risk = int_or_default(row.get("Risk Level", 2), 2)
    risk_label, risk_color = risk_meta(risk)

    brand = row.get("Brand", "Unknown Entity")
    service = row.get("Service Type", "Service type not provided")
    regulator = row.get("Regulator Scope", "Scope not provided")
    rationale = str(row.get("Rationale", "")).strip() or "No rationale provided."
    action_required = str(row.get("Action Required", "")).strip() or "Review details"
    alert_status = str(row.get("Alert Status", "")).strip()

    badge_style = (
        f"background: {risk_color}22; color: {risk_color}; "
        f"border: 1px solid {risk_color}55;"
    )

    alert_html = ""
    if alert_status:
        alert_html = f'<div class="subtle-note">Status: {alert_status}</div>'

    st.markdown(
        f"""
        <div class="screening-card">
            <div class="screening-head">
                <div style="flex:1;">
                    <div class="screening-brand">{brand}</div>
                    <div class="screening-meta">
                        {service} · {regulator}
                    </div>
                    <div class="screening-rationale">
                        {rationale[:320]}
                    </div>
                    {alert_html}
                </div>
                <div>
                    <div class="pill" style="{badge_style}">
                        {risk_label} · Risk {risk}
                    </div>
                    <div class="action-text">{action_required}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_dataframe(df: pd.DataFrame, selected_brand, risk_filter, reg_filter, chip) -> pd.DataFrame:
    filtered = df.copy()

    if selected_brand:
        filtered = filtered[safe_series(filtered, "Brand").astype(str) == str(selected_brand)]

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
            filtered["Action Required"].astype(str).str.contains("no action|clear|none", case=False, na=False)
        ]

    return filtered


def search_func_factory(brands: list[str]):
    def search_func(query: str) -> list[str]:
        if not query:
            return brands[:8]
        return [b for b in brands if query.lower() in b.lower()][:12]
    return search_func


# =========================================================
# UI
# =========================================================
inject_css()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### Control Center")
    st.caption("Manage runs, theme, filters, and admin access.")

    run_files = list_files()
    selected_path = None

    if run_files:
        run_options = {
            f'{item["timestamp"].strftime("%Y-%m-%d %H:%M")} · {item["name"]}': item["path"]
            for item in run_files
        }
        labels = list(run_options.keys())

        if st.session_state.selected_run_label not in labels:
            st.session_state.selected_run_label = labels[0]

        chosen_label = st.selectbox(
            "Select screening run",
            labels,
            index=labels.index(st.session_state.selected_run_label),
        )
        st.session_state.selected_run_label = chosen_label
        selected_path = run_options[chosen_label]
    else:
        st.info("No screening files found yet in the data folder.")

    st.toggle(
        "Dark mode",
        value=st.session_state.theme == "dark",
        key="theme_toggle",
    )
    st.session_state.theme = "dark" if st.session_state.theme_toggle else "light"

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

    st.markdown("---")
    st.caption("Tip: The app keeps normal users focused on analysis, while admin tools stay hidden until unlocked.")

# ---------------- Main ----------------
st.markdown(
    """
    <div class="hero">
        <div class="toolbar">
            <div>
                <h1>🛡️ UAE Regulatory Screening</h1>
                <p>Modernized review workspace for risk monitoring, search, and insight discovery across UAE financial entities.</p>
            </div>
            <div class="toolbar-badge">Responsive UI · Faster review flow</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not selected_path:
    st.markdown(
        """
        <div class="empty-state">
            <h3 style="margin-bottom:0.3rem;">No screening run available</h3>
            <div>Upload an Excel file from the Admin access section to get started.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

df = load_data(selected_path)

# Clean common numeric column
if has_col(df, "Risk Level"):
    df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(0).astype(int)

# ---------------- Top summary ----------------
total_entities = len(df)

high_risk = len(df[df["Risk Level"] >= 4]) if has_col(df, "Risk Level") else 0
licensed = len(df[df["Risk Level"] == 0]) if has_col(df, "Risk Level") else 0
risk_up = len(df[df["Alert Status"].astype(str) == "📈 RISK INCREASED"]) if has_col(df, "Alert Status") else 0
new_entities = len(df[df["Alert Status"].astype(str) == "🆕 NEW"]) if has_col(df, "Alert Status") else 0

st.markdown('<div class="stat-grid">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_stat_card("Entities screened", f"{total_entities:,}", "Total rows in the selected run")
with col2:
    render_stat_card("High risk", f"{high_risk:,}", "Entities with risk level 4 or 5")
with col3:
    render_stat_card("Risk increased", f"{risk_up:,}", "Entities marked as increased risk")
with col4:
    render_stat_card("Licensed / clear", f"{licensed:,}", "Entities with risk level 0")
st.markdown('</div>', unsafe_allow_html=True)

if new_entities > 0 or risk_up > 0:
    st.info(f"🧭 This run includes {new_entities} new entities and {risk_up} entities with increasing risk.")

# ---------------- Tabs ----------------
tab_home, tab_search, tab_insights, tab_dataset = st.tabs(
    ["🏠 Overview", "🔍 Search & Filter", "📊 Insights", "🗂️ Dataset"]
)

# =========================================================
# TAB 1: OVERVIEW
# =========================================================
with tab_home:
    left, right = st.columns([1.7, 1])

    with left:
        st.markdown('<div class="section-title">Priority review queue</div>', unsafe_allow_html=True)
        if has_col(df, "Risk Level"):
            top_entities = df.sort_values(["Risk Level"], ascending=False).head(10)
        else:
            top_entities = df.head(10)

        if len(top_entities) == 0:
            st.markdown('<div class="empty-state">No entities found in this run.</div>', unsafe_allow_html=True)
        else:
            for _, row in top_entities.iterrows():
                render_entity_card(row)

    with right:
        st.markdown('<div class="section-title">Quick summary</div>', unsafe_allow_html=True)
        with st.container(border=False):
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)

            dominant_regulator = "N/A"
            if has_col(df, "Regulator Scope") and not df["Regulator Scope"].dropna().empty:
                dominant_regulator = df["Regulator Scope"].astype(str).value_counts().idxmax()

            dominant_service = "N/A"
            if has_col(df, "Service Type") and not df["Service Type"].dropna().empty:
                dominant_service = df["Service Type"].astype(str).value_counts().idxmax()

            st.markdown(f"**Selected run**  \n`{Path(selected_path).name}`")
            st.markdown(f"**Top regulator scope**  \n{dominant_regulator}")
            st.markdown(f"**Most frequent service type**  \n{dominant_service}")
            st.markdown(f"**Rows available**  \n{total_entities:,}")
            st.markdown(
                '<div class="subtle-note">Use the Search & Filter tab for targeted review, then export the filtered results if needed.</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("")
        if has_col(df, "Risk Level"):
            st.markdown('<div class="section-title">Risk distribution</div>', unsafe_allow_html=True)
            risk_counts = df["Risk Level"].value_counts().sort_index()
            st.bar_chart(risk_counts, use_container_width=True)

# =========================================================
# TAB 2: SEARCH & FILTER
# =========================================================
with tab_search:
    search_col, filters_col = st.columns([1.15, 1])

    brands = []
    if has_col(df, "Brand"):
        brands = sorted(df["Brand"].dropna().astype(str).unique().tolist())

    with search_col:
        st.markdown('<div class="section-title">Entity search</div>', unsafe_allow_html=True)
        if HAS_SEARCHBOX and brands:
            selected_brand = st_searchbox(
                search_func_factory(brands),
                placeholder="Search for a company or brand...",
                key="brand_searchbox",
            )
        else:
            selected_brand = st.selectbox(
                "Brand",
                options=[""] + brands,
                help="Autocomplete package not installed. Using standard dropdown.",
            )
            selected_brand = selected_brand or None

    with filters_col:
        st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
        filter_left, filter_right = st.columns(2)

        with filter_left:
            risk_filter = (
                st.multiselect(
                    "Risk level",
                    options=sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True),
                )
                if has_col(df, "Risk Level")
                else []
            )

        with filter_right:
            reg_filter = (
                st.multiselect(
                    "Regulator scope",
                    options=sorted(df["Regulator Scope"].dropna().astype(str).unique().tolist()),
                )
                if has_col(df, "Regulator Scope")
                else []
            )

    st.markdown('<div class="section-title">Quick filters</div>', unsafe_allow_html=True)
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
            if st.button(chip_label, key=f"chip_{chip_key}", use_container_width=True, type="primary" if is_primary else "secondary"):
                st.session_state.active_chip = chip_key

    filtered_df = filter_dataframe(
        df=df,
        selected_brand=selected_brand,
        risk_filter=risk_filter,
        reg_filter=reg_filter,
        chip=st.session_state.active_chip,
    )

    result_col, preview_col = st.columns([1.5, 1])

    with result_col:
        st.markdown('<div class="section-title">Filtered results</div>', unsafe_allow_html=True)
        st.caption(f"{len(filtered_df):,} entities match the current search and filters.")
        st.dataframe(filtered_df, use_container_width=True, height=520)

    with preview_col:
        st.markdown('<div class="section-title">Preview cards</div>', unsafe_allow_html=True)
        if len(filtered_df) == 0:
            st.markdown('<div class="empty-state">No matching entities found.</div>', unsafe_allow_html=True)
        else:
            for _, row in filtered_df.head(5).iterrows():
                render_entity_card(row)

# =========================================================
# TAB 3: INSIGHTS
# =========================================================
with tab_insights:
    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown('<div class="section-title">Risk level breakdown</div>', unsafe_allow_html=True)
        if has_col(df, "Risk Level"):
            st.bar_chart(df["Risk Level"].value_counts().sort_index(), use_container_width=True)
        else:
            st.info("Risk Level column is not available.")

    with chart2:
        st.markdown('<div class="section-title">Top regulator scopes</div>', unsafe_allow_html=True)
        if has_col(df, "Regulator Scope"):
            st.bar_chart(df["Regulator Scope"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Regulator Scope column is not available.")

    chart3, chart4 = st.columns(2)

    with chart3:
        st.markdown('<div class="section-title">Service type mix</div>', unsafe_allow_html=True)
        if has_col(df, "Service Type"):
            st.bar_chart(df["Service Type"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Service Type column is not available.")

    with chart4:
        st.markdown('<div class="section-title">Alert status mix</div>', unsafe_allow_html=True)
        if has_col(df, "Alert Status"):
            st.bar_chart(df["Alert Status"].astype(str).value_counts().head(10), use_container_width=True)
        else:
            st.info("Alert Status column is not available.")

# =========================================================
# TAB 4: DATASET
# =========================================================
with tab_dataset:
    info_left, info_right = st.columns([1.2, 1])

    with info_left:
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
            use_container_width=False,
        )

    with info_right:
        st.markdown('<div class="section-title">Column list</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Column": df.columns}), use_container_width=True, height=300)

st.caption("Internal tool — for monitoring and review support only, not a legal determination.")
