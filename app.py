"""
UAE Regulatory Screening – Internal Search UI (v5 · Full redesign)
Improvements:
  - Night/day mode toggle with fully implemented light theme
  - Clickable table rows → entity detail dialog panel
  - Workflow actions: review, escalate, clear, annotate
  - Proper filter system with active chips + clear all
  - Autocomplete search with suggestions (streamlit-searchbox)
  - Improved table: truncated text, sorting, better layout
  - Loading, empty, and error states
  - Trust indicators: last updated, data source, run status
  - Improved chart clarity: titles, insights, axis labels
  - Accessibility improvements: contrast, labels, aria roles
"""
from __future__ import annotations

import glob
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from streamlit_searchbox import st_searchbox
    HAS_SEARCHBOX = True
except ImportError:
    HAS_SEARCHBOX = False

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UAE Regulatory Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SESSION STATE DEFAULTS ────────────────────────────────────────────────
def _init():
    defaults = {
        "theme":          "dark",
        "workflow_log":   {},   # {brand: {action, note, ts}}
        "selected_brand": None,
        "active_chip":    None,
        "page":           1,
        "sort_col":       "Risk Level",
        "sort_asc":       False,
        "risk_filter":    [],
        "reg_filter":     [],
        "search_query":   None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

dark = st.session_state.theme == "dark"

# ── THEME TOKENS ──────────────────────────────────────────────────────────
T = {
    "dark": {
        "app_bg":        "#07091C",
        "sidebar_bg":    "#040610",
        "card_bg":       "#0C1228",
        "raised_bg":     "#111830",
        "text":          "#D8E1F2",
        "text_dim":      "#8896B4",
        "text_muted":    "#4E5E7A",
        "gold":          "#C9A84C",
        "gold_dim":      "rgba(201,168,76,0.12)",
        "gold_border":   "rgba(201,168,76,0.22)",
        "border":        "rgba(255,255,255,0.06)",
        "input_bg":      "#0C1228",
    },
    "light": {
        "app_bg":        "#EBF0FB",
        "sidebar_bg":    "#DDE5F5",
        "card_bg":       "#FFFFFF",
        "raised_bg":     "#F0F4FF",
        "text":          "#0F172A",
        "text_dim":      "#475569",
        "text_muted":    "#94A3B8",
        "gold":          "#8A6012",
        "gold_dim":      "rgba(138,96,18,0.09)",
        "gold_border":   "rgba(138,96,18,0.28)",
        "border":        "rgba(0,0,0,0.08)",
        "input_bg":      "#FFFFFF",
    },
}
c = T[st.session_state.theme]

# ── RISK METADATA ─────────────────────────────────────────────────────────
RISK_META = {
    5: {"label":"Critical",  "color":"#E11D48", "bg":"rgba(225,29,72,0.12)",  "border":"rgba(225,29,72,0.3)"},
    4: {"label":"High",      "color":"#F97316", "bg":"rgba(249,115,22,0.12)", "border":"rgba(249,115,22,0.3)"},
    3: {"label":"Medium",    "color":"#EAB308", "bg":"rgba(234,179,8,0.12)",  "border":"rgba(234,179,8,0.3)"},
    2: {"label":"Monitor",   "color":"#4A7FD4", "bg":"rgba(74,127,212,0.12)", "border":"rgba(74,127,212,0.3)"},
    1: {"label":"Low",       "color":"#4A7FD4", "bg":"rgba(74,127,212,0.08)", "border":"rgba(74,127,212,0.2)"},
    0: {"label":"Licensed",  "color":"#10B981", "bg":"rgba(16,185,129,0.12)", "border":"rgba(16,185,129,0.3)"},
}

def risk_badge_html(level: int) -> str:
    m = RISK_META.get(level, RISK_META[2])
    dot = f'<span style="width:5px;height:5px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:5px;"></span>'
    return (f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;'
            f'background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};'
            f'font-size:10px;font-weight:800;white-space:nowrap;">{dot}{m["label"]} {level}</span>')

def alert_badge_html(status: str) -> str:
    if "NEW" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,0.12);color:#22C55E;border:1px solid rgba(34,197,94,0.3);font-size:9px;font-weight:800;">NEW</span>'
    if "INCREASED" in str(status):
        return '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(249,115,22,0.12);color:#F97316;border:1px solid rgba(249,115,22,0.3);font-size:9px;font-weight:800;">↑ RISK UP</span>'
    return ""

# ── CSS INJECTION ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: {c['app_bg']} !important;
    color: {c['text']} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {c['app_bg']} !important; }}
.block-container {{ padding-top: 0.8rem !important; padding-bottom: 2rem !important; max-width: 1480px !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: {c['sidebar_bg']} !important; border-right: 1px solid {c['border']} !important; }}
[data-testid="stSidebar"] * {{ color: {c['text_dim']} !important; }}
[data-testid="stSidebar"] h3 {{ color: {c['gold']} !important; }}
[data-testid="stSidebar"] .stCaption {{ color: {c['text_muted']} !important; font-size: 0.78rem !important; }}

/* Inputs */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-baseweb="input"] input, .stTextInput input,
[data-testid="stSelectbox"] > div > div > div {{
    background: {c['input_bg']} !important;
    border-color: {c['gold_border']} !important;
    border-radius: 10px !important;
    color: {c['text']} !important;
}}
div[data-baseweb="select"] svg {{ fill: {c['gold']} !important; }}
ul[data-baseweb="menu"] {{ background: {c['raised_bg']} !important; border: 1px solid {c['gold_border']} !important; border-radius: 10px !important; }}
[data-baseweb="option"]:hover {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; }}
.stMultiSelect > div > div {{ background: {c['input_bg']} !important; border-color: {c['gold_border']} !important; border-radius: 10px !important; }}
[data-baseweb="tag"] {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; }}

/* Metrics */
[data-testid="stMetric"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-top: 3px solid {c['gold']} !important;
    border-radius: 12px !important;
    padding: 1rem 1.1rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
}}
[data-testid="stMetricLabel"] {{ color: {c['text_muted']} !important; font-size: 0.77rem !important; font-weight: 700 !important; letter-spacing: 0.07em !important; text-transform: uppercase !important; }}
[data-testid="stMetricValue"] {{ color: {c['text']} !important; font-size: 1.9rem !important; font-weight: 800 !important; letter-spacing: -0.03em !important; }}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ background: {c['card_bg']} !important; border-radius: 10px !important; padding: 4px !important; gap: 4px !important; border: 1px solid {c['border']} !important; }}
[data-testid="stTabs"] [data-baseweb="tab"] {{ background: transparent !important; color: {c['text_dim']} !important; font-weight: 600 !important; font-size: 0.88rem !important; padding: 0.5rem 1.1rem !important; border-radius: 8px !important; transition: all 0.15s; }}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{ background: {c['gold_dim']} !important; color: {c['gold']} !important; font-weight: 800 !important; border: 1px solid {c['gold_border']} !important; }}
[data-baseweb="tab-highlight"] {{ display: none !important; }}
[data-baseweb="tab-border"] {{ background-color: {c['border']} !important; }}

/* Buttons */
div.stButton > button, .stDownloadButton button {{
    background: {c['gold_dim']} !important;
    border: 1px solid {c['gold_border']} !important;
    border-radius: 10px !important;
    color: {c['gold']} !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    transition: all 0.15s !important;
}}
div.stButton > button:hover {{ background: rgba(201,168,76,0.2) !important; transform: translateY(-1px) !important; }}
div.stButton > button:disabled {{ opacity: 0.3 !important; transform: none !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 10px !important; border: 1px solid {c['border']} !important; overflow: hidden !important; box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important; }}
[data-testid="stDataFrame"] table {{ background: {c['card_bg']} !important; }}
[data-testid="stDataFrame"] th {{ background: {c['raised_bg']} !important; color: {c['text_muted']} !important; font-size: 0.77rem !important; font-weight: 700 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; border-bottom: 1px solid {c['border']} !important; padding: 8px 10px !important; }}
[data-testid="stDataFrame"] td {{ color: {c['text']} !important; font-size: 0.84rem !important; border-bottom: 1px solid {c['border']} !important; padding: 7px 10px !important; }}
[data-testid="stDataFrame"] tr:hover td {{ background: {c['raised_bg']} !important; }}

/* Vega charts */
[data-testid="stVegaLiteChart"] {{ border-radius: 10px !important; }}

/* Alerts */
[data-testid="stAlert"] {{ border-radius: 10px !important; border-left-width: 3px !important; background: {c['card_bg']} !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {c['gold_border']}; border-radius: 99px; }}

/* Chip buttons */
div[data-testid="stHorizontalBlock"] .stButton button {{
    height: 34px !important; min-height: 34px !important;
    white-space: nowrap !important; font-size: 0.79rem !important;
    padding: 0 0.7rem !important;
}}

/* Compact top bar */
.topbar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 0 14px 0; margin-bottom: 4px;
    border-bottom: 1px solid {c['border']};
}}
.topbar-logo {{ display:flex; align-items:center; gap:10px; }}
.topbar-icon {{
    width:32px; height:32px; border-radius:9px;
    background:linear-gradient(135deg,{c['gold']},#7A5B10);
    display:flex; align-items:center; justify-content:center;
    font-size:16px; box-shadow:0 4px 12px rgba(201,168,76,0.25);
    flex-shrink:0;
}}
.topbar-title {{ color:{c['text']}; font-size:14px; font-weight:800; line-height:1.2; }}
.topbar-sub {{ color:{c['text_muted']}; font-size:9px; font-weight:600; letter-spacing:0.08em; }}
.topbar-meta {{ text-align:right; }}
.topbar-meta .run {{ color:{c['text_dim']}; font-size:10px; }}
.topbar-meta .run b {{ color:{c['text']}; }}
.topbar-meta .src {{ color:{c['text_muted']}; font-size:9px; }}
.live-badge {{
    display:inline-flex; align-items:center; gap:5px; padding:4px 10px;
    border-radius:999px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25);
}}
.live-dot {{ width:5px; height:5px; border-radius:50%; background:#10B981; display:inline-block; }}
.live-txt {{ color:#10B981; font-size:10px; font-weight:800; letter-spacing:0.06em; }}

/* Pill */
.pill {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:10px; font-weight:800; white-space:nowrap; letter-spacing:0.04em; }}
.pill-critical {{ background:rgba(225,29,72,0.12); color:#E11D48; border:1px solid rgba(225,29,72,0.3); }}
.pill-high     {{ background:rgba(249,115,22,0.12); color:#F97316; border:1px solid rgba(249,115,22,0.3); }}
.pill-medium   {{ background:rgba(234,179,8,0.12);  color:#EAB308; border:1px solid rgba(234,179,8,0.3); }}
.pill-low      {{ background:rgba(74,127,212,0.12); color:#4A7FD4; border:1px solid rgba(74,127,212,0.3); }}
.pill-licensed {{ background:rgba(16,185,129,0.12); color:#10B981; border:1px solid rgba(16,185,129,0.3); }}

/* Cards */
.entity-card {{
    background:{c['card_bg']}; border:1px solid {c['border']};
    border-radius:12px; padding:14px 16px; margin-bottom:8px;
    transition:border-color 0.2s, box-shadow 0.2s;
}}
.entity-card:hover {{ border-color:{c['gold_border']}; box-shadow:0 4px 16px rgba(0,0,0,0.2); }}
.entity-card h4 {{ margin:0 0 3px 0; color:{c['text']}; font-size:0.97rem; font-weight:800; }}
.entity-card .meta {{ color:{c['text_muted']}; font-size:0.8rem; margin-bottom:0.3rem; }}
.entity-card .rationale {{ color:{c['text_dim']}; font-size:0.84rem; line-height:1.55; }}
.entity-card .action-note {{ color:{c['text_muted']}; font-size:0.76rem; border-left:2px solid {c['gold_border']}; padding-left:7px; margin-top:6px; }}

/* Section titles */
.section-title {{ color:{c['text']}; font-size:11px; font-weight:800; letter-spacing:0.07em; text-transform:uppercase; margin:0 0 0.6rem 0; }}

/* Trust bar */
.trust-bar {{
    display:flex; gap:16px; flex-wrap:wrap; align-items:center;
    padding:8px 0; border-top:1px solid {c['border']};
    color:{c['text_muted']}; font-size:10px;
}}
.trust-bar b {{ color:{c['text_dim']}; }}

/* Detail panel */
.detail-panel {{
    background:{c['card_bg']}; border:1px solid {c['border']};
    border-radius:14px; padding:18px; margin-top:12px;
    box-shadow:0 4px 24px rgba(0,0,0,0.25);
}}
.detail-header {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:16px; padding-bottom:14px; border-bottom:1px solid {c['border']}; }}

/* Workflow action badge */
.wf-badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:9px; font-weight:800; background:{c['gold_dim']}; color:{c['gold']}; border:1px solid {c['gold_border']}; margin-left:6px; }}

/* Empty state */
.empty-state {{ text-align:center; padding:40px 20px; }}
.empty-state .icon {{ font-size:36px; margin-bottom:12px; }}
.empty-state .title {{ color:{c['text']}; font-size:14px; font-weight:700; margin-bottom:6px; }}
.empty-state .desc {{ color:{c['text_muted']}; font-size:12px; }}

/* Error state */
.error-state {{ background:rgba(225,29,72,0.07); border:1px solid rgba(225,29,72,0.2); border-radius:10px; padding:16px; }}

/* Active filter chip */
.filter-chip {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:999px; background:{c['gold_dim']}; border:1px solid {c['gold_border']}; color:{c['gold']}; font-size:10px; font-weight:700; margin-right:4px; }}

hr {{ border-color: {c['border']} !important; }}
</style>
""", unsafe_allow_html=True)

# ── NOISE FILTER ──────────────────────────────────────────────────────────
NOISE_BRANDS = {
    "rulebook","the complete rulebook","licensing","centralbank",
    "globenewswire","globe newswire","cbuae rulebook",
    "insights for businesses","insights","businesses",
    "money transfers","companies law amendments","gccbusinesswatch",
    "financialit","visamiddleeast","khaleejtimes","khaleej times",
    "gulfnews","gulf news","thenational","the national",
    "arabianbusiness","arabian business","zawya","wam",
    "reuters","bloomberg","ft.com","cnbc","forbes",
    "crunchbase","techcrunch","wikipedia","medium",
    "page","home","about","contact","terms","privacy",
    "fintech news","press release","media release","news release",
    "blog","white paper","whitepaper","report","research","survey",
    "study","conference","event","webinar","podcast",
    "linkedin","twitter","facebook","instagram","youtube",
    "warning","vasps","vasps licensing process",
    "rules","guide","overview","trends","plan","news","article",
    "introduction","summary","conclusion","documentation","docs",
    "help","support","faq","faqs","sitemap","copyright",
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
    re.I,
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
    if b.rstrip(".").split()[-1] in {"the","a","an","of","in","on","for","to","and","or","by","with","from","at","as"}: return True
    letters = sum(c.isalpha() for c in brand)
    if letters < len(brand) * 0.5: return True
    if len(words) == 1 and b in GENERIC_ONLY_WORDS: return True
    if any(ind in b for ind in ["news","times","watch","magazine","blog","gazette","tribune","herald","daily","weekly","journal","newsletter","review","press","media"]): return True
    return False

# ── DATA PATHS ────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

@st.cache_data(show_spinner=False)
def load_data(path: str) -> tuple[pd.DataFrame, str | None]:
    try:
        try:    df = pd.read_excel(path, sheet_name="📋 All Results")
        except Exception: df = pd.read_excel(path, sheet_name=0)
    except Exception as e:
        return pd.DataFrame(), str(e)

    for col in ["Brand","Classification","Group","Service Type","Regulator Scope","Alert Status","Rationale","Action Required","Top Source URL"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("nan","")
    if "Risk Level" in df.columns:
        df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(2).astype(int)
    if "Brand" in df.columns:
        df = df[~df["Brand"].apply(is_noise_brand)].reset_index(drop=True)
    return df, None


def save_uploaded_run(uploaded_file) -> str:
    save_path = DATA_DIR / uploaded_file.name
    with open(save_path, "wb") as handle:
        handle.write(uploaded_file.getbuffer())
    st.cache_data.clear()
    return str(save_path)

def render_card(row: pd.Series):
    level = int(row.get("Risk Level", 2))
    m     = RISK_META.get(level, RISK_META[2])
    dot   = f'<span style="width:5px;height:5px;border-radius:50%;background:{m["color"]};display:inline-block;margin-right:5px;flex-shrink:0;"></span>'
    pill  = f'<span style="display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;background:{m["bg"]};border:1px solid {m["border"]};color:{m["color"]};font-size:10px;font-weight:800;">{dot}{m["label"]} · {level}</span>'

    alert = str(row.get("Alert Status",""))
    alert_html = alert_badge_html(alert)

    svc  = str(row.get("Service Type",""))
    reg  = str(row.get("Regulator Scope",""))
    rat  = str(row.get("Rationale",""))[:300]
    act  = str(row.get("Action Required",""))
    url  = str(row.get("Top Source URL",""))
    brand = str(row.get("Brand",""))
    conf  = str(row.get("Confidence",""))

    wf = st.session_state.workflow_log.get(brand)
    wf_html = f'<span class="wf-badge">{wf["action"].upper()}</span>' if wf else ""

    link = f'<a href="{url}" target="_blank" style="font-size:11px;color:#4A7FD4;text-decoration:none;">↗ Source</a>' if url.startswith("http") else ""
    conf_html = f'<div style="color:{c["text_muted"]};font-size:9px;margin-top:4px;">CONF {conf}%</div>' if conf else ""

    tag_style = f'display:inline-block;padding:2px 8px;border-radius:4px;background:{c["gold_dim"]};color:{c["gold"]};font-size:10px;font-weight:600;margin-right:4px;'

    st.markdown(f"""
    <div class="entity-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
        <div style="flex:1;min-width:0;">
          <h4>{brand} {alert_html} {wf_html}</h4>
          <div class="meta">
            <span style="{tag_style}">{svc}</span>
            <span style="{tag_style}">{reg}</span>
          </div>
          <div class="rationale">{rat}</div>
          {f'<div class="action-note">{act}</div>' if act else ''}
        </div>
        <div style="text-align:right;min-width:110px;flex-shrink:0;">
          {pill}
          {conf_html}
          <div style="margin-top:6px;">{link}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── ENTITY DETAIL DIALOG ──────────────────────────────────────────────────
@st.dialog("Entity Detail", width="large")
def show_entity_detail(row: pd.Series):
    brand = str(row.get("Brand",""))
    level = int(row.get("Risk Level", 2))
    m     = RISK_META.get(level, RISK_META[2])

    # Header
    st.markdown(f"""
    <div class="detail-header">
      <div style="flex:1;">
        {risk_badge_html(level)}
        {alert_badge_html(str(row.get("Alert Status","")))}
        <h3 style="color:{c['text']};font-size:18px;font-weight:800;margin:8px 0 4px 0;">{brand}</h3>
        <div style="color:{c['text_muted']};font-size:11px;">{row.get('Classification','')}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Workflow actions
    st.markdown(f'<div class="section-title">Workflow Actions</div>', unsafe_allow_html=True)
    wf = st.session_state.workflow_log.get(brand)

    wa1, wa2, wa3, wa4 = st.columns(4)
    actions = [
        (wa1, "✓ Mark Reviewed", "reviewed", "#10B981"),
        (wa2, "↑ Escalate",      "escalated", "#F97316"),
        (wa3, "✕ Clear",         "cleared",   "#4A7FD4"),
        (wa4, "✎ Annotate",      "annotate",  c["gold"]),
    ]
    for col, label, action_id, color in actions:
        is_active = wf and wf.get("action") == action_id
        btn_label = f"{'✓ ' if is_active else ''}{label}"
        if col.button(btn_label, key=f"wf_{action_id}_{brand}", use_container_width=True):
            if action_id == "annotate":
                st.session_state[f"show_note_{brand}"] = True
            elif is_active:
                del st.session_state.workflow_log[brand]
                st.rerun()
            else:
                st.session_state.workflow_log[brand] = {
                    "action": action_id, "note": None,
                    "ts": datetime.now().strftime("%H:%M:%S")
                }
                st.rerun()

    if st.session_state.get(f"show_note_{brand}"):
        note = st.text_area("Annotation note", placeholder="Enter your note…", key=f"note_{brand}")
        if st.button("Save note", key=f"save_note_{brand}"):
            st.session_state.workflow_log[brand] = {
                "action": "annotated", "note": note,
                "ts": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state[f"show_note_{brand}"] = False
            st.rerun()

    if wf:
        note_text = f' — "{wf["note"]}"' if wf.get("note") else ""
        st.success(f"✓ Logged as **{wf['action']}** at {wf['ts']}{note_text}")

    st.divider()

    # Metadata grid
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        for label, key in [("Service Type","Service Type"),("Regulator Scope","Regulator Scope"),("Classification","Classification")]:
            val = str(row.get(key,"")) or "—"
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">{label}</div>
              <div style="color:{c['text']};font-size:12px;">{val}</div>
            </div>""", unsafe_allow_html=True)
    with meta_col2:
        conf = str(row.get("Confidence",""))
        matched = str(row.get("Matched Entity (Register)","")) or "—"
        url = str(row.get("Top Source URL",""))
        st.markdown(f"""
        <div style="margin-bottom:12px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">Confidence</div>
          <div style="height:8px;background:{c['border']};border-radius:99px;overflow:hidden;margin-bottom:4px;">
            <div style="width:{conf}%;height:100%;background:#10B981;border-radius:99px;"></div>
          </div>
          <div style="color:{c['text_dim']};font-size:11px;font-weight:700;">{conf}%</div>
        </div>
        <div style="margin-bottom:12px;">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:3px;">Matched Entity</div>
          <div style="color:{c['text']};font-size:12px;">{matched}</div>
        </div>""", unsafe_allow_html=True)
        if url.startswith("http"):
            st.link_button("↗ View Source", url)

    st.divider()
    rat = str(row.get("Rationale",""))
    act = str(row.get("Action Required",""))
    st.markdown(f"""
    <div style="margin-bottom:14px;">
      <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Rationale</div>
      <div style="color:{c['text_dim']};font-size:12px;line-height:1.7;">{rat}</div>
    </div>""", unsafe_allow_html=True)
    if act:
        st.markdown(f"""
        <div style="background:{c['gold_dim']};border:1px solid {c['gold_border']};border-radius:8px;padding:10px 14px;">
          <div style="color:{c['gold']};font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Action Required</div>
          <div style="color:{c['text']};font-size:12px;line-height:1.65;">{act}</div>
        </div>""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 14px 0;border-bottom:1px solid {c['border']};margin-bottom:14px;">
        <div class="topbar-icon">🛡️</div>
        <div>
            <div class="topbar-title">UAE Screening</div>
            <div class="topbar-sub">RISK MONITORING</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Theme toggle
    theme_label = "☀ Switch to Light Mode" if dark else "☾ Switch to Dark Mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state.theme = "light" if dark else "dark"
        st.rerun()

    st.markdown("---")

    files = list_screening_files()
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Screening Run</div>', unsafe_allow_html=True)
    selected_path = None
    if files:
        options = {
            f'{f["timestamp"].strftime("%d %b %Y, %H:%M")}  ·  {f["size_kb"]} KB': f["path"]
            for f in files
        }
        choice = st.selectbox("Run", list(options.keys()), index=0, label_visibility="collapsed")
        selected_path = options[choice]
    else:
        st.markdown(f"""
        <div class="empty-state">
          <div class="icon">📭</div>
          <div class="title">No screening files</div>
          <div class="desc">Upload a UAE_Screening_*.xlsx file below</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text_muted"]};font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Upload New Run</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Drop a UAE_Screening_*.xlsx file", type=["xlsx"], label_visibility="collapsed")
    if uploaded:
        save_uploaded_run(uploaded)
        st.success(f"Saved: {uploaded.name}")
        st.rerun()

    st.markdown("---")
    st.caption(f"Runs archived: **{len(files)}**")
    st.caption(f"`{DATA_DIR}`")
    st.caption("Internal tool — not a legal determination.")

# ── HEADER (compact top bar) ──────────────────────────────────────────────
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
file_label = Path(selected_path).name if selected_path else "No file loaded"

st.markdown(f"""
<div class="topbar">
  <div class="topbar-logo">
    <div class="topbar-icon">🛡️</div>
    <div>
      <div class="topbar-title">UAE Regulatory Screening</div>
      <div class="topbar-sub">INTERNAL RISK MONITORING PLATFORM</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="topbar-meta">
      <div class="run">Run: <b>{now_str}</b></div>
      <div class="src">VARA · CBUAE · DFSA · ADGM · SCA</div>
    </div>
    <div class="live-badge">
      <span class="live-dot"></span>
      <span class="live-txt">LIVE</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

if selected_path is None:
    st.markdown(f"""
    <div style="max-width:760px;margin:40px auto 0 auto;background:{c['card_bg']};border:1px solid {c['gold_border']};
                border-radius:18px;padding:28px 28px 24px 28px;box-shadow:0 14px 34px rgba(0,0,0,0.18);">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <div style="width:42px;height:42px;border-radius:12px;background:{c['gold_dim']};border:1px solid {c['gold_border']};
                    display:flex;align-items:center;justify-content:center;font-size:18px;">📂</div>
        <div>
          <div style="color:{c['text']};font-size:20px;font-weight:800;line-height:1.15;">Upload a screening run to get started</div>
          <div style="color:{c['text_muted']};font-size:12px;margin-top:4px;">This app is built for <code>UAE_Screening_*.xlsx</code> files exported from your screening process.</div>
        </div>
      </div>
      <div style="background:{c['raised_bg']};border:1px solid {c['border']};border-radius:14px;padding:14px 16px;margin-bottom:18px;">
        <div style="color:{c['text_dim']};font-size:12px;line-height:1.7;">
          No local screening file is available on this Streamlit deployment yet.
          Upload the latest Excel file here and the dashboard will load immediately.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded_main = st.file_uploader(
        "Upload a UAE_Screening_*.xlsx file",
        type=["xlsx"],
        key="main_empty_state_uploader",
        help="Use the screening Excel export you want to review in the dashboard.",
    )
    if uploaded_main:
        save_uploaded_run(uploaded_main)
        st.success(f"Uploaded: {uploaded_main.name}")
        st.rerun()
    st.stop()

# ── LOAD DATA ─────────────────────────────────────────────────────────────
with st.spinner("Loading screening data…"):
    df, load_error = load_data(selected_path)

if load_error:
    st.markdown(f"""
    <div class="error-state">
      <div style="color:#E11D48;font-size:13px;font-weight:700;margin-bottom:4px;">⚠ Failed to load data</div>
      <div style="color:#8896B4;font-size:11px;">{load_error}</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

if df.empty:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">📭</div>
      <div class="title">Empty dataset</div>
      <div class="desc">The selected file contains no valid entities after filtering.</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────
total     = len(df)
critical  = len(df[df["Risk Level"] >= 5])
high      = len(df[df["Risk Level"] == 4])
needs_rev = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)])
licensed  = len(df[df["Risk Level"] == 0])
new_ents  = len(df[df["Alert Status"] == "🆕 NEW"])   if "Alert Status" in df.columns else 0
risk_up   = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) if "Alert Status" in df.columns else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Entities Screened", f"{total:,}", help="Total entities after noise filtering")
k2.metric("Critical / High",   critical + high,
          delta=f"{(critical+high)/total*100:.0f}% of total" if total else None,
          delta_color="inverse", help="Risk levels 4–5 requiring immediate attention")
k3.metric("Needs Review",      needs_rev, help="Risk levels 2–3, monitor or review")
k4.metric("Licensed / Clear",  licensed, help="Risk level 0, no action required")
k5.metric("New Entities",      new_ents,
          delta=f"↑ {risk_up} risk increased" if risk_up else None,
          delta_color="inverse", help="Entities not seen in prior run")

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────
tab_home, tab_search, tab_insights = st.tabs(["🏠  Overview", "🔍  Search & Filter", "📊  Insights"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tab_home:
    left_col, right_col = st.columns([1.7, 1])

    with left_col:
        st.markdown('<div class="section-title">Priority Review Queue</div>', unsafe_allow_html=True)
        st.caption("High and Critical entities — click 'Detail' to open full view with workflow actions")

        top_risk = (df[df["Risk Level"] >= 4]
                    .sort_values("Risk Level", ascending=False).head(10))

        if top_risk.empty:
            st.markdown("""
            <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:20px;text-align:center;">
              <div style="color:#10B981;font-size:13px;font-weight:700;">✓ No high-risk entities this run</div>
            </div>""", unsafe_allow_html=True)
        else:
            for _, row in top_risk.iterrows():
                render_card(row)
                if st.button(f"Open detail →  {row['Brand'][:30]}", key=f"det_{row.name}",
                             use_container_width=False):
                    show_entity_detail(row)

    with right_col:
        if new_ents > 0 or risk_up > 0:
            st.markdown(f"""
            <div style="background:rgba(249,115,22,0.07);border:1px solid rgba(249,115,22,0.2);border-radius:10px;padding:12px 14px;margin-bottom:14px;">
              <div style="color:#F97316;font-size:9px;font-weight:800;letter-spacing:0.09em;margin-bottom:6px;">ALERTS THIS RUN</div>
              {"<div style='color:"+c["text_dim"]+";font-size:11px;margin-bottom:3px;'><span style='color:#22C55E;font-weight:700;'>"+str(new_ents)+" new</span> entities added</div>" if new_ents else ""}
              {"<div style='color:"+c["text_dim"]+";font-size:11px;'><span style='color:#F97316;font-weight:700;'>"+str(risk_up)+"</span> risk level increases</div>" if risk_up else ""}
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-title">Run Summary</div>', unsafe_allow_html=True)
        dominant_reg = df["Regulator Scope"].value_counts().idxmax() if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty else "N/A"
        dominant_svc = df["Service Type"].value_counts().idxmax()    if "Service Type"    in df.columns and not df["Service Type"].dropna().empty    else "N/A"

        for label, value in [
            ("File",          Path(selected_path).name[:40]),
            ("Top Regulator", dominant_reg),
            ("Top Service",   dominant_svc),
            ("Total Rows",    f"{total:,}"),
            ("Last Updated",  now_str),
        ]:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {c['border']};gap:8px;">
              <span style="color:{c['text_muted']};font-size:10px;">{label}</span>
              <span style="color:{c['text']};font-size:10px;font-weight:700;text-align:right;word-break:break-word;max-width:160px;">{value}</span>
            </div>""", unsafe_allow_html=True)

        if "Risk Level" in df.columns:
            import altair as alt
            st.markdown(f'<div class="section-title" style="margin-top:16px;">Risk Distribution</div>', unsafe_allow_html=True)
            _RCOL = {"Critical":"#E11D48","High":"#F97316","Medium":"#EAB308","Monitor":"#4A7FD4","Low":"#4A7FD4","Licensed":"#10B981"}
            _rc = df["Risk Level"].value_counts().reset_index()
            _rc.columns = ["level","count"]
            _rc["label"] = _rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
            _chart = (alt.Chart(_rc)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
                .encode(
                    x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"),
                            axis=alt.Axis(labelColor=c["text_dim"], tickColor="transparent",
                                          domainColor=c["border"], labelFont="DM Sans,sans-serif", labelAngle=0)),
                    y=alt.Y("count:Q", axis=alt.Axis(labelColor=c["text_dim"], gridColor=c["border"],
                                                      domainColor="transparent", tickColor="transparent",
                                                      labelFont="DM Sans,sans-serif")),
                    color=alt.Color("label:N", scale=alt.Scale(domain=list(_RCOL.keys()), range=list(_RCOL.values())), legend=None),
                    tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
                )
                .properties(height=200, title=alt.TitleParams("Entity count by risk level", color=c["text_dim"], fontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"]))
            st.altair_chart(_chart, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – SEARCH & FILTER
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    if "page" not in st.session_state: st.session_state.page = 1

    all_brands = sorted(df["Brand"].dropna().unique().tolist())

    def search_brands(q: str) -> list[str]:
        if not q: return []
        q = q.lower().strip()
        starts   = [b for b in all_brands if b.lower().startswith(q)]
        contains = [b for b in all_brands if q in b.lower() and b not in starts]
        return (starts + contains)[:12]

    # ── Filter toolbar ────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([1.4, 1, 1])

    with fc1:
        if HAS_SEARCHBOX:
            selected_brand = st_searchbox(search_brands, placeholder="Search entity or brand…",
                                          key="brand_searchbox", clear_on_submit=False)
        else:
            raw = st.selectbox("Brand", ["— All —"] + all_brands, index=0, label_visibility="collapsed")
            selected_brand = None if raw == "— All —" else raw

    with fc2:
        risk_opts   = sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True)
        risk_filter = st.multiselect("Risk Level", options=risk_opts,
                                     format_func=lambda x: RISK_META.get(int(x),{}).get("label", str(x)),
                                     placeholder="All risk levels", label_visibility="collapsed",
                                     key="risk_filter")

    with fc3:
        reg_opts   = sorted(df["Regulator Scope"].dropna().unique().tolist()) if "Regulator Scope" in df.columns else []
        reg_filter = st.multiselect("Regulator", options=reg_opts,
                                    placeholder="All regulators", label_visibility="collapsed",
                                    key="reg_filter")

    # ── Quick-filter chips ────────────────────────────────────────────────
    CHIPS = [
        ("Critical / High", "high"),
        ("New Entities",    "new"),
        ("Risk Up",         "riskup"),
        ("Licensed",        "licensed"),
        ("VASP / Crypto",   "va"),
    ]
    chip_cols = st.columns(len(CHIPS) + 1)
    for i, (label, key) in enumerate(CHIPS):
        active = st.session_state.active_chip == key
        btn_label = f"✓ {label}" if active else label
        if chip_cols[i].button(btn_label, key=f"chip_{key}", use_container_width=True):
            st.session_state.active_chip = None if active else key
            st.session_state.page = 1
            st.rerun()
    if chip_cols[-1].button("✕ Clear", key="chip_clear", use_container_width=True):
        st.session_state.active_chip = None
        st.session_state.page = 1
        st.rerun()

    # ── Active filter summary ─────────────────────────────────────────────
    active_filters = []
    if selected_brand:   active_filters.append(f'"{selected_brand}"')
    if risk_filter:      active_filters.extend([RISK_META.get(int(r),{}).get("label",str(r)) for r in risk_filter])
    if reg_filter:       active_filters.extend(reg_filter)
    if st.session_state.active_chip:
        chip_label = next((l for l,k in CHIPS if k==st.session_state.active_chip), "")
        active_filters.append(chip_label)

    if active_filters:
        chips_html = " ".join(f'<span class="filter-chip">{f} ×</span>' for f in active_filters)
        clear_all_note = f'<span style="color:#E11D48;font-size:10px;font-weight:700;cursor:pointer;margin-left:6px;">✕ Clear all ({len(active_filters)})</span>'
        st.markdown(f'<div style="margin:6px 0 10px 0;">{chips_html}{clear_all_note}</div>', unsafe_allow_html=True)

    # ── Sorting ───────────────────────────────────────────────────────────
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col2:
        sort_by = st.selectbox("Sort by", ["Risk ↓","Risk ↑","Name A–Z","Confidence ↓"],
                               label_visibility="collapsed", key="sort_sel")

    # ── Apply filters ─────────────────────────────────────────────────────
    filtered = df.copy()
    if selected_brand:
        filtered = filtered[filtered["Brand"] == selected_brand]
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]

    chip = st.session_state.active_chip
    if chip == "high":
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "new" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "🆕 NEW"]
    elif chip == "riskup" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "📈 RISK INCREASED"]
    elif chip == "licensed":
        filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "va":
        va_mask = filtered["Regulator Scope"].astype(str).str.contains("VA|VASP|CRYPTO", case=False, na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains("crypto|virtual asset|token", case=False, na=False)
        filtered = filtered[va_mask]

    # Sort
    sort_map = {"Risk ↓":("Risk Level",False),"Risk ↑":("Risk Level",True),"Name A–Z":("Brand",True),"Confidence ↓":("Confidence",False)}
    scol, sasc = sort_map.get(sort_by, ("Risk Level", False))
    if scol in filtered.columns:
        filtered = filtered.sort_values(scol, ascending=sasc)

    # Empty state
    if filtered.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🔍</div>
          <div class="title">No entities found</div>
          <div class="desc">Try adjusting your search query or clearing some filters.</div>
        </div>""", unsafe_allow_html=True)
    else:
        # ── Pagination ────────────────────────────────────────────────────
        per_page    = 25
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        if st.session_state.page > total_pages: st.session_state.page = 1

        rc_l, rc_r = st.columns([3, 1])
        rc_l.caption(f"**{len(filtered):,}** of **{total:,}** entities")
        rc_r.caption(f"Page **{st.session_state.page}** / **{total_pages}**")

        # ── Table ─────────────────────────────────────────────────────────
        display_cols = [c_ for c_ in [
            "Brand","Classification","Risk Level","Action Required",
            "Confidence","Regulator Scope","Service Type",
            "Matched Entity (Register)","Rationale","Top Source URL",
        ] if c_ in filtered.columns]

        start   = (st.session_state.page - 1) * per_page
        page_df = filtered.iloc[start: start + per_page]

        col_config = {
            "Top Source URL": st.column_config.LinkColumn("↗ Source", width="small"),
            "Risk Level":     st.column_config.NumberColumn("Risk", format="%d", min_value=0, max_value=5, width="small"),
            "Brand":          st.column_config.TextColumn("Brand", width="medium"),
            "Rationale":      st.column_config.TextColumn("Rationale", width="large"),
            "Action Required":st.column_config.TextColumn("Action Required", width="large"),
            "Confidence":     st.column_config.ProgressColumn("Conf.", min_value=0, max_value=100, format="%d%%", width="small"),
        }

        event = st.dataframe(
            page_df[display_cols],
            use_container_width=True,
            height=min(540, 60 + len(page_df) * 38),
            hide_index=True,
            column_config=col_config,
            selection_mode="single-row",
            on_select="rerun",
            key="entity_table",
        )

        # ── Row click → detail panel ──────────────────────────────────────
        if event.selection.rows:
            idx = event.selection.rows[0]
            selected_row = page_df.iloc[idx]
            show_entity_detail(selected_row)

        # ── Pagination controls ───────────────────────────────────────────
        pc1,pc2,pc3,pc4,pc5 = st.columns([1,1,4,1,1])
        if pc1.button("⏮", use_container_width=True, disabled=st.session_state.page<=1, key="p_first"):
            st.session_state.page=1; st.rerun()
        if pc2.button("◀", use_container_width=True, disabled=st.session_state.page<=1, key="p_prev"):
            st.session_state.page-=1; st.rerun()
        pc3.markdown(f"<div style='text-align:center;padding-top:0.5rem;color:{c['text_muted']};font-size:12px;'>Page <b style='color:{c['text']}'>{st.session_state.page}</b> of {total_pages}</div>", unsafe_allow_html=True)
        if pc4.button("▶", use_container_width=True, disabled=st.session_state.page>=total_pages, key="p_next"):
            st.session_state.page+=1; st.rerun()
        if pc5.button("⏭", use_container_width=True, disabled=st.session_state.page>=total_pages, key="p_last"):
            st.session_state.page=total_pages; st.rerun()

        # ── Downloads ─────────────────────────────────────────────────────
        d1, d2 = st.columns(2)
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        d1.download_button("↓ Download CSV", data=csv,
            file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv", use_container_width=True)
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                filtered.to_excel(w, index=False, sheet_name="Filtered")
            d2.download_button("↓ Download Excel", data=buf.getvalue(),
                file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with tab_insights:
    import altair as alt

    RISK_COLORS = {"Critical":"#E11D48","High":"#F97316","Medium":"#EAB308",
                   "Monitor":"#4A7FD4","Low":"#4A7FD4","Licensed":"#10B981"}

    def _chart_base(height=240):
        return dict(
            axis_x=dict(
                labelColor=c["text_dim"],
                tickColor="transparent",
                domainColor=c["border"],
                labelFont="DM Sans,sans-serif",
            ),
            axis_y=dict(
                labelColor=c["text_dim"],
                gridColor=c["border"],
                domainColor="transparent",
                tickColor="transparent",
                labelFont="DM Sans,sans-serif",
            ),
            height=height,
        )

    def bar_chart(series, title, subtitle, color="#C9A84C", rotate=-30, height=240):
        if series.empty:
            st.markdown(f'<div class="empty-state"><div class="icon">📊</div><div class="title">{title}</div><div class="desc">No data available</div></div>', unsafe_allow_html=True)
            return
        df_c = series.reset_index(); df_c.columns = ["label","value"]
        b = _chart_base(height)
        chart = (alt.Chart(df_c)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
            .encode(
                x=alt.X("label:N", sort="-y", axis=alt.Axis(**b["axis_x"], labelAngle=rotate, title=None)),
                y=alt.Y("value:Q", axis=alt.Axis(**b["axis_y"], title="Count")),
                color=alt.value(color),
                tooltip=["label:N", alt.Tooltip("value:Q", title="Count")],
            )
            .properties(height=b["height"],
                        title=alt.TitleParams(title, subtitle=[subtitle],
                                              color=c["text"], fontSize=12,
                                              subtitleColor=c["text_dim"], subtitleFontSize=10))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"]))
        st.altair_chart(chart, use_container_width=True)

    def risk_bar(height=240):
        if "Risk Level" not in df.columns: return
        rc = df["Risk Level"].value_counts().reset_index(); rc.columns = ["level","count"]
        rc["label"] = rc["level"].apply(lambda x: RISK_META.get(int(x),{}).get("label","Unknown"))
        rc["color"] = rc["label"].map(RISK_COLORS).fillna("#7E8FAD")
        b = _chart_base(height)
        chart = (alt.Chart(rc)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, opacity=0.9)
            .encode(
                x=alt.X("label:N", sort=alt.EncodingSortField("level", order="descending"),
                        axis=alt.Axis(**b["axis_x"], title=None, labelAngle=0)),
                y=alt.Y("count:Q", axis=alt.Axis(**b["axis_y"], title="Entity Count")),
                color=alt.Color("label:N", scale=alt.Scale(domain=list(RISK_COLORS.keys()), range=list(RISK_COLORS.values())), legend=None),
                tooltip=["label:N", alt.Tooltip("count:Q", title="Entities")],
            )
            .properties(height=b["height"],
                        title=alt.TitleParams("Risk Level Distribution",
                                              subtitle=["Entity count per risk category"],
                                              color=c["text"], fontSize=12,
                                              subtitleColor=c["text_dim"], subtitleFontSize=10))
            .configure_view(strokeOpacity=0, fill=c["card_bg"])
            .configure(background=c["card_bg"]))
        st.altair_chart(chart, use_container_width=True)

    # Insight summary row
    top_risk_label = df["Risk Level"].map(lambda x: RISK_META.get(int(x),{}).get("label","")).value_counts().idxmax() if "Risk Level" in df.columns and not df.empty else "—"
    top_reg = df["Regulator Scope"].value_counts().idxmax() if "Regulator Scope" in df.columns and not df["Regulator Scope"].dropna().empty else "—"
    top_svc = df["Service Type"].value_counts().idxmax()    if "Service Type"    in df.columns and not df["Service Type"].dropna().empty    else "—"

    si1, si2, si3, si4 = st.columns(4)
    for col, label, value, color_ in [
        (si1, "Most Common Risk",  top_risk_label, "#E11D48"),
        (si2, "Top Regulator",     top_reg,        "#4A7FD4"),
        (si3, "Top Service Type",  top_svc,        c["gold"]),
        (si4, "New This Run",      f"+{new_ents}",  "#22C55E"),
    ]:
        col.markdown(f"""
        <div style="background:{c['card_bg']};border-radius:8px;padding:10px 14px;border:1px solid {c['border']};">
          <div style="color:{c['text_muted']};font-size:9px;font-weight:800;letter-spacing:0.09em;text-transform:uppercase;margin-bottom:4px;">{label}</div>
          <div style="color:{color_};font-size:14px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    ic1, ic2 = st.columns(2)
    with ic1: risk_bar()
    with ic2:
        if "Regulator Scope" in df.columns:
            bar_chart(df["Regulator Scope"].value_counts().head(10),
                      "Regulator Scope", "Entities per regulatory body", "#4A7FD4")

    ic3, ic4 = st.columns(2)
    with ic3:
        if "Service Type" in df.columns:
            bar_chart(df["Service Type"].value_counts().head(10),
                      "Service Type Mix", "Top service categories identified", c["gold"])
    with ic4:
        if "Alert Status" in df.columns and df["Alert Status"].replace("","nan").dropna().replace("nan","").any():
            bar_chart(df["Alert Status"].replace("","nan").dropna().replace("nan","").value_counts().head(10),
                      "Alert Status Mix", "Changes detected vs. prior run", "#F97316")
        else:
            st.markdown(f"""
            <div class="empty-state">
              <div class="icon">📭</div>
              <div class="title">No Alert Data</div>
              <div class="desc">Alert Status column not present or empty in this run.</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:4px;">Trend Across Runs</div>', unsafe_allow_html=True)
    files_list = list_screening_files()
    if len(files_list) >= 2:
        trend_rows = []
        for f in files_list[:10]:
            try:
                d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                trend_rows.append({
                    "Run":           f["timestamp"].strftime("%m/%d %H:%M"),
                    "High/Critical": int(len(d[d["Risk Level"] >= 4])),
                    "Needs Review":  int(len(d[(d["Risk Level"]>=2)&(d["Risk Level"]<=3)])),
                    "Licensed":      int(len(d[d["Risk Level"]==0])),
                })
            except Exception:
                continue
        if trend_rows:
            _trend = pd.DataFrame(trend_rows).iloc[::-1]
            _trend_long = _trend.melt("Run", var_name="Category", value_name="Count")
            _tcolors = {"High/Critical":"#E11D48","Needs Review":"#EAB308","Licensed":"#10B981"}
            b = _chart_base(260)
            _tchart = (alt.Chart(_trend_long)
                .mark_line(point=True, strokeWidth=2)
                .encode(
                    x=alt.X("Run:N", axis=alt.Axis(**b["axis_x"].__dict__, title=None)),
                    y=alt.Y("Count:Q", axis=alt.Axis(**b["axis_y"].__dict__, title="Entity Count")),
                    color=alt.Color("Category:N", scale=alt.Scale(
                        domain=list(_tcolors.keys()), range=list(_tcolors.values())),
                        legend=alt.Legend(labelColor=c["text_dim"], titleColor=c["text_dim"])),
                    tooltip=["Run:N","Category:N", alt.Tooltip("Count:Q", title="Entities")],
                )
                .properties(height=b["height"],
                            title=alt.TitleParams("Risk Trend Across Runs",
                                                  subtitle=["Historical view of risk category counts per run"],
                                                  color=c["text"], fontSize=12,
                                                  subtitleColor=c["text_dim"], subtitleFontSize=10))
                .configure_view(strokeOpacity=0, fill=c["card_bg"])
                .configure(background=c["card_bg"],
                           legend=alt.LegendConfig(labelColor=c["text_dim"], titleColor=c["text_dim"])))
            st.altair_chart(_tchart, use_container_width=True)
    else:
        st.caption(f"Only {len(files_list)} run archived — trend chart requires 2+ runs.")

    st.markdown("---")
    st.markdown(f'<div style="color:{c["text"]};font-size:12px;font-weight:800;margin-bottom:8px;">Classification Breakdown</div>', unsafe_allow_html=True)
    if "Classification" in df.columns:
        cls = df["Classification"].value_counts().reset_index()
        cls.columns = ["Classification","Count"]
        cls["% of Total"] = (cls["Count"]/total*100).round(1).astype(str)+"%"
        st.dataframe(cls, use_container_width=True, hide_index=True,
                     column_config={"Count": st.column_config.ProgressColumn("Count", min_value=0, max_value=int(cls["Count"].max()), format="%d")})

# ── FOOTER / TRUST INDICATORS ─────────────────────────────────────────────
st.markdown("---")
wf_count = len(st.session_state.workflow_log)
st.markdown(f"""
<div class="trust-bar">
  <span>📁 {Path(selected_path).name}</span>
  <span>🕐 Last updated: <b>{now_str}</b></span>
  <span>🗃 Sources: <b>VARA · CBUAE · DFSA · ADGM · SCA</b></span>
  {"<span>✓ <b>"+str(wf_count)+"</b> workflow actions logged this session</span>" if wf_count else ""}
  <span>ℹ️ Automated first-pass — not a legal determination</span>
</div>""", unsafe_allow_html=True)
