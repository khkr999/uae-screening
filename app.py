"""
UAE Regulatory Screening – Internal Search UI (v4 · Gold/Navy redesign)
"""
from __future__ import annotations
import glob, io, re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd
import streamlit as st

try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False

st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DESIGN SYSTEM ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap');

/* Base */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #07091C !important;
    color: #D8E1F2 !important;
}

#MainMenu, footer, header { visibility: hidden; }

/* App background */
.stApp {
    background: #07091C !important;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1480px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #040610 !important;
    border-right: 1px solid rgba(201,168,76,0.15) !important;
}
[data-testid="stSidebar"] * { color: #8896B4 !important; }
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stSubheader { color: #C9A84C !important; }
[data-testid="stSidebar"] .stCaption { color: #4E5E7A !important; font-size: 0.78rem !important; }

/* Selectbox / inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div,
div[data-baseweb="input"],
div[data-baseweb="input"] > div,
div[data-baseweb="input"] input,
.stTextInput > div > div,
.stTextInput input,
[data-testid="stSelectbox"] > div > div,
[data-testid="stSelectbox"] > div > div > div {
    background: #0C1228 !important;
    background-color: #0C1228 !important;
    border-color: rgba(201,168,76,0.2) !important;
    border-radius: 10px !important;
    color: #D8E1F2 !important;
}
div[data-baseweb="select"] svg { fill: #C9A84C !important; }

/* streamlit-searchbox override */
[data-testid="stForm"] input,
.stSearchbox input,
input[type="text"],
input[type="search"] {
    background: #0C1228 !important;
    background-color: #0C1228 !important;
    color: #D8E1F2 !important;
    border-color: rgba(201,168,76,0.2) !important;
}
/* Dropdown menu */
ul[data-baseweb="menu"],
[data-baseweb="popover"] ul {
    background: #111830 !important;
    border: 1px solid rgba(201,168,76,0.15) !important;
    border-radius: 10px !important;
}
[data-baseweb="menu"] li:hover,
[data-baseweb="option"]:hover {
    background: rgba(201,168,76,0.08) !important;
    color: #C9A84C !important;
}

/* Multiselect */
.stMultiSelect > div > div {
    background: #0C1228 !important;
    border-color: rgba(201,168,76,0.2) !important;
    border-radius: 10px !important;
}
[data-baseweb="tag"] {
    background: rgba(201,168,76,0.15) !important;
    color: #C9A84C !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #0C1228 !important;
    border: 1px solid rgba(201,168,76,0.13) !important;
    border-top: 2px solid #C9A84C !important;
    border-radius: 12px !important;
    padding: 1rem 1.1rem !important;
}
[data-testid="stMetricLabel"] {
    color: #7E8FAD !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: #D8E1F2 !important;
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; font-weight: 700 !important; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: #7E8FAD !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.1rem !important;
    border-radius: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {
    color: #C9A84C !important;
    font-weight: 800 !important;
    background: transparent !important;
}
/* This is the actual sliding underline element in baseui */
[data-baseweb="tab-highlight"] {
    background-color: #C9A84C !important;
}
[data-baseweb="tab-border"] {
    background-color: rgba(255,255,255,0.05) !important;
}

/* Buttons */
div.stButton > button,
.stDownloadButton button {
    background: rgba(201,168,76,0.08) !important;
    border: 1px solid rgba(201,168,76,0.25) !important;
    border-radius: 10px !important;
    color: #C9A84C !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s !important;
}
div.stButton > button:hover,
.stDownloadButton button:hover {
    background: rgba(201,168,76,0.16) !important;
    border-color: rgba(201,168,76,0.5) !important;
    transform: translateY(-1px) !important;
}
div.stButton > button:disabled {
    opacity: 0.3 !important;
    transform: none !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    border: 1px solid rgba(201,168,76,0.13) !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] table {
    background: #0C1228 !important;
}
[data-testid="stDataFrame"] th {
    background: #111830 !important;
    color: #7E8FAD !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid rgba(201,168,76,0.13) !important;
    padding: 8px 10px !important;
}
[data-testid="stDataFrame"] td {
    color: #D8E1F2 !important;
    font-size: 0.84rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    padding: 7px 10px !important;
}

/* Bar chart */
[data-testid="stVegaLiteChart"] { border-radius: 10px !important; }

/* Info / warning / success */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 3px !important;
}

/* Horizontal rule */
hr { border-color: rgba(201,168,76,0.12) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(201,168,76,0.2); border-radius: 99px; }

/* Uniform chip-button heights */
div[data-testid="stHorizontalBlock"] .stButton button {
    height: 36px !important;
    min-height: 36px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 0.8rem !important;
    padding: 0 0.7rem !important;
}

/* Main-header card */
.main-header {
    background: linear-gradient(135deg, #0E1A3A 0%, #0C1228 60%, #111830 100%);
    border: 1px solid rgba(201,168,76,0.18);
    border-left: 3px solid #C9A84C;
    color: #D8E1F2;
    padding: 1.2rem 1.6rem;
    border-radius: 14px;
    margin-bottom: 1.4rem;
}
.main-header h1 { margin:0; color:#D8E1F2; font-size:1.6rem; font-weight:800; letter-spacing:-0.02em; }
.main-header p  { margin:0.2rem 0 0; color:#7E8FAD; font-size:0.9rem; }
.main-header .badge {
    display:inline-block; background:rgba(201,168,76,0.12);
    color:#C9A84C; border:1px solid rgba(201,168,76,0.3);
    border-radius:999px; padding:3px 10px; font-size:0.72rem; font-weight:800;
    letter-spacing:0.08em; margin-top:0.5rem;
}

/* Risk pills */
.pill { display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.75rem; font-weight:800; white-space:nowrap; letter-spacing:0.04em; }
.pill-critical { background:rgba(225,29,72,0.12);  color:#E11D48; border:1px solid rgba(225,29,72,0.3); }
.pill-high     { background:rgba(249,115,22,0.12); color:#F97316; border:1px solid rgba(249,115,22,0.3); }
.pill-medium   { background:rgba(212,160,23,0.12); color:#D4A017; border:1px solid rgba(212,160,23,0.3); }
.pill-low      { background:rgba(74,127,212,0.12); color:#4A7FD4; border:1px solid rgba(74,127,212,0.3); }
.pill-licensed { background:rgba(16,185,129,0.12); color:#10B981; border:1px solid rgba(16,185,129,0.3); }

/* Entity cards */
.company-card {
    background: #0C1228;
    border: 1px solid rgba(201,168,76,0.12);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
}
.company-card:hover { border-color: rgba(201,168,76,0.35); }
.company-card h4 { margin:0 0 3px 0; color:#D8E1F2; font-size:0.98rem; font-weight:800; }
.company-card .meta { color:#7E8FAD; font-size:0.8rem; margin-bottom:0.3rem; }
.company-card .rationale { color:#8896B4; font-size:0.84rem; line-height:1.55; }
.company-card .action-note {
    color:#4E5E7A; font-size:0.76rem; margin-top:3px;
    border-left:2px solid rgba(201,168,76,0.3); padding-left:7px; margin-top:6px;
}

/* Section titles */
.section-title {
    color: #D8E1F2;
    font-size: 0.95rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    margin: 0 0 0.6rem 0;
}

@media (max-width: 768px) {
    [data-testid="stMetricValue"] { font-size:1.5rem !important; }
    .main-header h1 { font-size:1.3rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RISK_META = {
    5: {"label": "Critical",  "pill": "pill-critical"},
    4: {"label": "High",      "pill": "pill-high"},
    3: {"label": "Medium",    "pill": "pill-medium"},
    2: {"label": "Monitor",   "pill": "pill-low"},
    1: {"label": "Low",       "pill": "pill-low"},
    0: {"label": "Licensed",  "pill": "pill-licensed"},
}

# ── NOISE FILTER ──────────────────────────────────────────────────────────
NOISE_BRANDS = {
    "rulebook","the complete rulebook","licensing","centralbank",
    "globenewswire","globe newswire","cbuae rulebook",
    "insights for businesses","insights","businesses",
    "2025 mobile development","transforming payments",
    "mobile development","2026 business plan","2026 rules",
    "10 leaves","10leaves","aafs",
    "money transfers","companies law amendments","gccbusinesswatch",
    "financialit","visamiddleeast","khaleejtimes","khaleej times",
    "tekrevol","trriple payments","hwala","aundigital",
    "gulfnews","gulf news","thenational","the national",
    "arabianbusiness","arabian business","zawya","wam",
    "reuters","bloomberg","ft.com","cnbc","forbes",
    "crunchbase","techcrunch","wikipedia","medium",
    "page","home","about","contact","terms","privacy",
    "privacy policy","cookie policy","cookies",
    "fintech news","press release","media release","news release",
    "blog","blog post","white paper","whitepaper","report",
    "research","survey","study","conference","event",
    "webinar","podcast","linkedin","twitter","facebook",
    "instagram","youtube","warning","'s warning",
    "vasps licensing process","licensing process",
    "& vasps licensing process in","& vasps licensing process",
    "& vasps","vasps","rules","guide","overview",
    "trends","plan","leaves","news","article","articles",
    "introduction","summary","conclusion","references",
    "documentation","docs","help","support","faq","faqs",
    "sitemap","copyright","company","companies","law",
    "amendments","amendment","watch","magazine","journal",
    "newsletter","directory","list","index","database",
    "agency","institute","association","council","authority",
    "commission","committee","task force",
}

NOISE_PATTERNS = re.compile(
    r"^(\s*[&'\"\-–—]|\s*\d+[\.\)\s]|top \d+|best \d+|leading \d+|"
    r"guide to|how to|what is|list of|complete list|overview|"
    r"introduction|insights for|transforming|mobile development|"
    r"press release|whitepaper|business plan|licensing process|"
    r"warning|\d{4}\s|"
    r".*\.(com|ae|net|org|io|co)$|"
    r".*(news|times|watch|magazine|journal|newsletter|review|"
    r"press|media|blog|gazette|tribune|post|herald|daily|weekly)$)",
    re.I
)

GENERIC_ONLY_WORDS = {
    "bank","banks","banking","payment","payments","finance",
    "financial","wallet","wallets","exchange","exchanges",
    "crypto","cryptocurrency","trading","investment","investments",
    "fintech","regulation","regulations","regulatory",
    "compliance","license","licenses","licensing",
    "money","transfer","transfers","remittance","remittances",
    "loan","loans","lending","credit","debit","card","cards",
    "digital","mobile","online","virtual","electronic",
    "service","services","solution","solutions","platform",
    "technology","technologies","app","apps","application",
    "company","companies","corporation","corp","limited","ltd",
    "uae","dubai","abu","dhabi","emirates","gulf","middle",
    "east","gcc","regional","international","global","local",
}

NEWS_MEDIA_HOSTS = {
    "khaleejtimes","gulfnews","thenational","arabianbusiness",
    "zawya","wam","gccbusinesswatch","globenewswire",
    "financialit","tekrevol","visamiddleeast","reuters",
    "bloomberg","ftcom","cnbc","forbes","crunchbase",
    "techcrunch","wikipedia","medium",
}

def is_noise_brand(brand: str) -> bool:
    if not brand or not isinstance(brand, str): return True
    b = brand.strip().lower()
    if not b or len(b) < 3: return True
    if b in NOISE_BRANDS: return True
    if NOISE_PATTERNS.match(b): return True
    if re.match(r"^[\s&'\"\-–—_\.,;:]", brand): return True
    if b[0].isdigit(): return True
    if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", b): return True
    b_compact = re.sub(r"[^a-z0-9]", "", b)
    if b_compact in NEWS_MEDIA_HOSTS: return True
    words = b.split()
    if all(w in GENERIC_ONLY_WORDS for w in words): return True
    if len(words) > 5: return True
    if re.search(r"\b(and|or|the|in|on|of|for|with|to|by)\b.*\b(and|or|the|in|on|of|for|with|to|by)\b", b): return True
    if b.rstrip('.').split()[-1] in {"the","a","an","of","in","on","for","to","and","or","by","with","from","at","as"}: return True
    letters = sum(c.isalpha() for c in brand)
    if letters < len(brand) * 0.5: return True
    if len(words) == 1 and b in GENERIC_ONLY_WORDS: return True
    if any(ind in b for ind in ["news","times","watch","magazine","blog","gazette","tribune","herald","daily","weekly","journal","newsletter","review","press","media"]): return True
    return False

# ── HELPERS ───────────────────────────────────────────────────────────────
def risk_pill(level) -> str:
    try: level = int(level)
    except: return '<span class="pill pill-low">Unknown</span>'
    m = RISK_META.get(level, RISK_META[2])
    return f'<span class="pill {m["pill"]}">{m["label"]} · {level}</span>'

def render_card(row):
    pill_html = risk_pill(row.get("Risk Level", 2))
    url  = row.get("Top Source URL", "")
    link = f'<a href="{url}" target="_blank" style="font-size:0.76rem;color:#4A7FD4;text-decoration:none;">↗ Source</a>' \
           if url and str(url).startswith("http") else ""
    svc  = str(row.get("Service Type", ""))
    reg  = str(row.get("Regulator Scope", ""))
    rat  = str(row.get("Rationale", ""))[:280]
    act  = str(row.get("Action Required", ""))
    alert = str(row.get("Alert Status", ""))
    alert_html = ""
    if "NEW" in alert:
        alert_html = '<span style="background:rgba(34,197,94,0.1);color:#22C55E;border:1px solid rgba(34,197,94,0.3);border-radius:999px;padding:2px 8px;font-size:0.7rem;font-weight:800;margin-left:6px;">+ NEW</span>'
    elif "INCREASED" in alert:
        alert_html = '<span style="background:rgba(249,115,22,0.1);color:#F97316;border:1px solid rgba(249,115,22,0.3);border-radius:999px;padding:2px 8px;font-size:0.7rem;font-weight:800;margin-left:6px;">↑ RISK UP</span>'
    st.markdown(f"""
    <div class="company-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
        <div style="flex:1;min-width:0;">
          <h4>{row.get('Brand','')} {alert_html}</h4>
          <div class="meta">{svc} · {reg}</div>
          <div class="rationale">{rat}</div>
          {f'<div class="action-note">{act}</div>' if act else ''}
        </div>
        <div style="text-align:right;min-width:120px;flex-shrink:0;">
          {pill_html}
          <div style="margin-top:6px;">{link}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── DATA LOADING ──────────────────────────────────────────────────────────
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

@st.cache_data(show_spinner="Loading screening data…")
def load_data(path: str) -> pd.DataFrame:
    try:    df = pd.read_excel(path, sheet_name="📋 All Results")
    except Exception:
        try:    df = pd.read_excel(path, sheet_name=0)
        except Exception as e:
            st.error(f"Could not read file: {e}"); return pd.DataFrame()
    for col in ["Brand","Classification","Group","Service Type","Regulator Scope","Alert Status"]:
        if col in df.columns: df[col] = df[col].astype(str)
    if "Risk Level" in df.columns:
        df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(2).astype(int)
    if "Brand" in df.columns:
        df = df[~df["Brand"].apply(is_noise_brand)].reset_index(drop=True)
    return df

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px 0;border-bottom:1px solid rgba(201,168,76,0.15);margin-bottom:12px;">
        <div style="width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#C9A84C,#7A5B10);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;box-shadow:0 4px 12px rgba(201,168,76,0.3);">🛡️</div>
        <div>
            <div style="color:#D8E1F2;font-size:13px;font-weight:800;line-height:1.2;">UAE Screening</div>
            <div style="color:#4E5E7A;font-size:9px;font-weight:600;letter-spacing:0.07em;">RISK MONITORING PLATFORM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    files = list_screening_files()

    st.markdown('<div style="color:#7E8FAD;font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Screening Run</div>', unsafe_allow_html=True)
    selected_path = None
    if files:
        options = {
            f'{f["timestamp"].strftime("%d %b %Y, %H:%M")}  ·  {f["size_kb"]} KB': f["path"]
            for f in files
        }
        choice = st.selectbox("Run", list(options.keys()), index=0, label_visibility="collapsed")
        selected_path = options[choice]
    else:
        st.info("No screening files found. Upload one below.")

    st.markdown("---")
    st.markdown('<div style="color:#7E8FAD;font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Upload New Run</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Drop a UAE_Screening_*.xlsx file", type=["xlsx"], label_visibility="collapsed")
    if uploaded:
        save_path = DATA_DIR / uploaded.name
        with open(save_path, "wb") as f: f.write(uploaded.getbuffer())
        st.success(f"Saved: {uploaded.name}")
        st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.caption(f"Runs archived: **{len(files)}**")
    st.caption(f"`{DATA_DIR}`")
    st.markdown("")
    st.caption("Internal tool — not a legal determination.")

# ── HEADER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
            <h1>🛡️ UAE Regulatory Screening</h1>
            <p>Risk monitoring, search, and insight discovery across UAE financial entities</p>
        </div>
        <span class="badge">LIVE RUN</span>
    </div>
</div>""", unsafe_allow_html=True)

if selected_path is None:
    st.warning("No screening files found. Run the screening script or upload a file via the sidebar.")
    st.stop()

df = load_data(selected_path)
if df.empty:
    st.error("The selected file is empty or could not be read."); st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────
total      = len(df)
high_risk  = len(df[df["Risk Level"] >= 4])
needs_rev  = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)])
licensed   = len(df[df["Risk Level"] == 0])
new_ents   = len(df[df["Alert Status"] == "🆕 NEW"])   if "Alert Status" in df.columns else 0
risk_up    = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) if "Alert Status" in df.columns else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Entities Screened", f"{total:,}")
k2.metric("High / Critical",   high_risk,
          delta=f"{high_risk/total*100:.0f}% of total" if total else None,
          delta_color="inverse")
k3.metric("Needs Review",      needs_rev)
k4.metric("Licensed / Clear",  licensed)
k5.metric("New Entities",      new_ents,
          delta=f"↑ {risk_up} risk increased" if risk_up else None,
          delta_color="inverse")

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────
tab_home, tab_search, tab_insights = st.tabs(["🏠 Overview", "🔍 Search & Filter", "📊 Insights"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tab_home:
    left_col, right_col = st.columns([1.7, 1])

    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.caption("Top entities by risk level — focus here first")
        top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)
        if top_risk.empty:
            st.success("✅ No high-risk entities to review this run.")
        else:
            for _, row in top_risk.iterrows():
                render_card(row)

    with right_col:
        # Alert banner
        if new_ents > 0 or risk_up > 0:
            st.markdown(f"""
            <div style="background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.22);border-radius:12px;padding:12px 14px;margin-bottom:14px;">
                <div style="color:#F97316;font-size:10px;font-weight:800;letter-spacing:0.08em;margin-bottom:6px;">ALERTS THIS RUN</div>
                {"<div style='color:#8896B4;font-size:12px;margin-bottom:3px;'><span style='color:#22C55E;font-weight:700;'>"+str(new_ents)+" new</span> entities added</div>" if new_ents else ""}
                {"<div style='color:#8896B4;font-size:12px;'><span style='color:#F97316;font-weight:700;'>"+str(risk_up)+"</span> risk level increases</div>" if risk_up else ""}
            </div>""", unsafe_allow_html=True)

        # Summary
        st.markdown('<div class="section-title">Run Summary</div>', unsafe_allow_html=True)
        dominant_reg = "N/A"
        dominant_svc = "N/A"
        if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty:
            dominant_reg = df["Regulator Scope"].astype(str).value_counts().idxmax()
        if "Service Type" in df.columns and not df["Service Type"].dropna().empty:
            dominant_svc = df["Service Type"].astype(str).value_counts().idxmax()

        for label, value in [
            ("Selected file",  Path(selected_path).name),
            ("Top regulator",  dominant_reg),
            ("Top service",    dominant_svc),
            ("Total rows",     f"{total:,}"),
        ]:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04);gap:8px;">
                <span style="color:#4E5E7A;font-size:11px;">{label}</span>
                <span style="color:#D8E1F2;font-size:11px;font-weight:700;text-align:right;word-break:break-word;max-width:160px;">{value}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("")
        if "Risk Level" in df.columns:
            import altair as alt
            st.markdown('<div class="section-title" style="margin-top:14px;">Risk Distribution</div>', unsafe_allow_html=True)
            _RCOL = {"Critical":"#E11D48","High":"#F97316","Medium":"#D4A017","Monitor":"#4A7FD4","Low":"#22C55E","Licensed":"#10B981"}
            _rc = df["Risk Level"].value_counts().reset_index()
            _rc.columns = ["level","count"]
            _rc["label"] = _rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
            _chart = alt.Chart(_rc).mark_bar(cornerRadiusTopLeft=4,cornerRadiusTopRight=4,opacity=0.9).encode(
                x=alt.X("label:N",sort=alt.EncodingSortField("level",order="descending"),axis=alt.Axis(labelColor="#7E8FAD",tickColor="transparent",domainColor="rgba(255,255,255,0.06)",labelFont="DM Sans,sans-serif",labelAngle=0)),
                y=alt.Y("count:Q",axis=alt.Axis(labelColor="#7E8FAD",gridColor="rgba(255,255,255,0.04)",domainColor="transparent",tickColor="transparent",labelFont="DM Sans,sans-serif")),
                color=alt.Color("label:N",scale=alt.Scale(domain=list(_RCOL.keys()),range=list(_RCOL.values())),legend=None),
                tooltip=["label:N","count:Q"]
            ).properties(height=200).configure_view(strokeOpacity=0,fill="#0C1228").configure(background="#0C1228")
            st.altair_chart(_chart, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – SEARCH & FILTER
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    if "active_chip" not in st.session_state: st.session_state.active_chip = None
    if "page"        not in st.session_state: st.session_state.page = 1

    all_brands = sorted(df["Brand"].dropna().unique().tolist())

    def search_brands(searchterm: str) -> list[str]:
        if not searchterm: return []
        q = searchterm.lower().strip()
        starts   = [b for b in all_brands if b.lower().startswith(q)]
        contains = [b for b in all_brands if q in b.lower() and b not in starts]
        return (starts + contains)[:15]

    sc1, sc2 = st.columns([1.2, 1])
    with sc1:
        st.markdown('<div class="section-title">Entity Search</div>', unsafe_allow_html=True)
        if HAS_SEARCHBOX:
            selected_brand = st_searchbox(search_brands,
                placeholder="Search company or brand…",
                key="brand_searchbox", clear_on_submit=False)
        else:
            st.warning("Add `streamlit-searchbox` for autocomplete.")
            raw = st.selectbox("Brand", ["— All —"] + all_brands, index=0)
            selected_brand = None if raw == "— All —" else raw
    with sc2:
        st.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
        fc1, fc2 = st.columns(2)
        with fc1:
            risk_opts   = sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True)
            risk_filter = st.multiselect("Risk Level", options=risk_opts,
                format_func=lambda x: RISK_META.get(int(x),{}).get("label",str(x)))
        with fc2:
            reg_opts   = sorted(df["Regulator Scope"].dropna().unique().tolist()) \
                if "Regulator Scope" in df.columns else []
            reg_filter = st.multiselect("Regulator", options=reg_opts)

    if selected_brand != st.session_state.get("_last_brand"):
        st.session_state.page = 1
        st.session_state._last_brand = selected_brand

    # Quick-filter chips
    st.markdown('<div style="color:#7E8FAD;font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin:10px 0 6px;">Quick Filters</div>', unsafe_allow_html=True)
    chips = [("High / Critical","high"),("New","new"),("Risk Up","riskup"),("Licensed","licensed"),("Crypto","va"),("Clear","clear")]
    chip_cols = st.columns(len(chips))
    for i, (label, key) in enumerate(chips):
        is_active = st.session_state.active_chip == key
        btn_label = f"✓ {label}" if is_active else label
        if chip_cols[i].button(btn_label, key=f"chip_{key}", use_container_width=True):
            st.session_state.active_chip = None if key == "clear" or is_active else key
            st.session_state.page = 1
            st.rerun()

    # Apply filters
    filtered = df.copy()
    if selected_brand:
        filtered = filtered[filtered["Brand"] == selected_brand]
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]
    chip = st.session_state.active_chip
    if chip == "high":     filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "new"     and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "🆕 NEW"]
    elif chip == "riskup"  and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "📈 RISK INCREASED"]
    elif chip == "licensed": filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "va":
        va_mask = filtered["Regulator Scope"].astype(str).str.contains("VA|VASP|CRYPTO",case=False,na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains("crypto|virtual asset|token",case=False,na=False)
        filtered = filtered[va_mask]
    filtered = filtered.sort_values("Risk Level", ascending=False)

    # Pagination
    per_page    = 25
    total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
    if st.session_state.page > total_pages: st.session_state.page = 1

    rc_left, rc_right = st.columns([3,1])
    rc_left.caption(f"**{len(filtered):,}** of **{total:,}** entities")
    rc_right.caption(f"Page **{st.session_state.page}** / **{total_pages}**")

    display_cols = [c for c in ["Brand","Classification","Risk Level","Action Required",
        "Confidence","Regulator Scope","Service Type","Matched Entity (Register)",
        "Rationale","Top Source URL"] if c in filtered.columns]

    start   = (st.session_state.page - 1) * per_page
    page_df = filtered.iloc[start: start + per_page]

    st.dataframe(page_df[display_cols], use_container_width=True,
        height=min(540, 60 + len(page_df) * 38), hide_index=True,
        column_config={
            "Top Source URL": st.column_config.LinkColumn("↗ Source", width="small"),
            "Risk Level":     st.column_config.NumberColumn("Risk", format="%d", min_value=0, max_value=5, width="small"),
            "Brand":          st.column_config.TextColumn("Brand", width="medium"),
            "Rationale":      st.column_config.TextColumn("Rationale", width="large"),
        })

    pc1,pc2,pc3,pc4,pc5 = st.columns([1,1,4,1,1])
    if pc1.button("⏮", use_container_width=True, disabled=st.session_state.page<=1, key="p_first"):
        st.session_state.page=1; st.rerun()
    if pc2.button("◀", use_container_width=True, disabled=st.session_state.page<=1, key="p_prev"):
        st.session_state.page-=1; st.rerun()
    pc3.markdown(f"<div style='text-align:center;padding-top:0.5rem;color:#7E8FAD;font-size:12px;'>Page <b style='color:#D8E1F2'>{st.session_state.page}</b> of {total_pages}</div>", unsafe_allow_html=True)
    if pc4.button("▶", use_container_width=True, disabled=st.session_state.page>=total_pages, key="p_next"):
        st.session_state.page+=1; st.rerun()
    if pc5.button("⏭", use_container_width=True, disabled=st.session_state.page>=total_pages, key="p_last"):
        st.session_state.page=total_pages; st.rerun()

    if not filtered.empty:
        d1, d2 = st.columns(2)
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        d1.download_button("↓ Download CSV", data=csv,
            file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv", use_container_width=True)
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w: filtered.to_excel(w, index=False, sheet_name="Filtered")
            d2.download_button("↓ Download Excel", data=buf.getvalue(),
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        except Exception: pass


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with tab_insights:
    import altair as alt
    st.markdown('<div class="section-title">Insights Dashboard</div>', unsafe_allow_html=True)

    RISK_COLORS = {"Critical":"#E11D48","High":"#F97316","Medium":"#D4A017",
                   "Monitor":"#4A7FD4","Low":"#22C55E","Licensed":"#10B981"}

    def gold_bar(data_series, title, color="#C9A84C", height=240):
        df_chart = data_series.reset_index()
        df_chart.columns = ["label","value"]
        chart = alt.Chart(df_chart).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9
        ).encode(
            x=alt.X("label:N", sort="-y", axis=alt.Axis(
                labelColor="#7E8FAD", tickColor="transparent",
                domainColor="rgba(255,255,255,0.06)", labelAngle=-35,
                labelFontSize=11, labelFont="DM Sans, sans-serif")),
            y=alt.Y("value:Q", axis=alt.Axis(
                labelColor="#7E8FAD", gridColor="rgba(255,255,255,0.04)",
                domainColor="transparent", tickColor="transparent",
                labelFont="DM Sans, sans-serif")),
            color=alt.value(color),
            tooltip=["label:N","value:Q"]
        ).properties(height=height).configure_view(
            strokeOpacity=0, fill="#0C1228"
        ).configure(background="#0C1228")
        st.altair_chart(chart, use_container_width=True)

    def risk_colored_bar(df_in, height=240):
        rc = df_in["Risk Level"].value_counts().reset_index()
        rc.columns = ["level","count"]
        rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
        rc["color"] = rc["label"].map(RISK_COLORS).fillna("#7E8FAD")
        chart = alt.Chart(rc).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9
        ).encode(
            x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"),
                    axis=alt.Axis(labelColor="#7E8FAD", tickColor="transparent",
                                  domainColor="rgba(255,255,255,0.06)",
                                  labelFont="DM Sans, sans-serif")),
            y=alt.Y("count:Q", axis=alt.Axis(labelColor="#7E8FAD",
                    gridColor="rgba(255,255,255,0.04)", domainColor="transparent",
                    tickColor="transparent", labelFont="DM Sans, sans-serif")),
            color=alt.Color("label:N", scale=alt.Scale(
                domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())
            ), legend=None),
            tooltip=["label:N","count:Q"]
        ).properties(height=height).configure_view(
            strokeOpacity=0, fill="#0C1228"
        ).configure(background="#0C1228")
        st.altair_chart(chart, use_container_width=True)

    ic1, ic2 = st.columns(2)
    with ic1:
        st.markdown("#### Risk Level Distribution")
        if "Risk Level" in df.columns:
            risk_colored_bar(df)
    with ic2:
        st.markdown("#### Top Regulator Scopes")
        if "Regulator Scope" in df.columns:
            gold_bar(df["Regulator Scope"].value_counts().head(10), "Regulators", "#4A7FD4")

    ic3, ic4 = st.columns(2)
    with ic3:
        st.markdown("#### Service Type Mix")
        if "Service Type" in df.columns:
            gold_bar(df["Service Type"].value_counts().head(10), "Services", "#C9A84C")
    with ic4:
        st.markdown("#### Alert Status Mix")
        if "Alert Status" in df.columns:
            gold_bar(df["Alert Status"].value_counts().head(10), "Alerts", "#F97316")

    st.markdown("---")
    st.markdown("#### Trend Across Runs")
    if len(files) >= 2:
        trend_rows = []
        for f in files[:10]:
            try:
                d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                trend_rows.append({
                    "Run":             f["timestamp"].strftime("%m/%d %H:%M"),
                    "High / Critical": int(len(d[d["Risk Level"] >= 4])),
                    "Needs Review":    int(len(d[(d["Risk Level"]>=2)&(d["Risk Level"]<=3)])),
                    "Licensed":        int(len(d[d["Risk Level"]==0])),
                })
            except Exception: continue
        if trend_rows:
            import altair as alt
            _trend = pd.DataFrame(trend_rows).iloc[::-1]
            _trend_long = _trend.melt("Run", var_name="Category", value_name="Count")
            _tcolors = {"High / Critical":"#E11D48","Needs Review":"#D4A017","Licensed":"#10B981"}
            _tchart = alt.Chart(_trend_long).mark_line(point=True,strokeWidth=2).encode(
                x=alt.X("Run:N",axis=alt.Axis(labelColor="#7E8FAD",domainColor="rgba(255,255,255,0.06)",tickColor="transparent",labelFont="DM Sans,sans-serif")),
                y=alt.Y("Count:Q",axis=alt.Axis(labelColor="#7E8FAD",gridColor="rgba(255,255,255,0.04)",domainColor="transparent",tickColor="transparent",labelFont="DM Sans,sans-serif")),
                color=alt.Color("Category:N",scale=alt.Scale(domain=list(_tcolors.keys()),range=list(_tcolors.values()))),
                tooltip=["Run:N","Category:N","Count:Q"]
            ).properties(height=260).configure_view(strokeOpacity=0,fill="#0C1228").configure(background="#0C1228",legend=alt.LegendConfig(labelColor="#7E8FAD",titleColor="#7E8FAD"))
            st.altair_chart(_tchart, use_container_width=True)
    else:
        st.caption(f"Only {len(files)} run archived — trend chart requires 2+ runs.")

    st.markdown("---")
    st.markdown("#### Full Classification Breakdown")
    if "Classification" in df.columns:
        cls = df["Classification"].value_counts().reset_index()
        cls.columns = ["Classification","Count"]
        cls["% of total"] = (cls["Count"]/total*100).round(1).astype(str)+"%"
        st.dataframe(cls, use_container_width=True, hide_index=True)

# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="color:#4E5E7A;font-size:11px;display:flex;gap:16px;flex-wrap:wrap;">
    <span>📁 {Path(selected_path).name}</span>
    <span>🕐 {datetime.now():%Y-%m-%d %H:%M}</span>
    <span>ℹ️ Automated first-pass screening — not a legal determination</span>
</div>""", unsafe_allow_html=True)
