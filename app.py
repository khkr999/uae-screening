"""
UAE Regulatory Screening – Internal Search UI (v3)
"""
from __future__ import annotations
import glob, io, re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd
import streamlit as st

# Google-style autocomplete search box
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

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1F3864 0%, #2E5090 100%);
        color: white; padding: 1.5rem 2rem; border-radius: 12px;
        margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(31,56,100,0.15);
    }
    .main-header h1 { margin:0; color:white; font-size:1.8rem; font-weight:700; }
    .main-header p  { margin:0.25rem 0 0 0; color:rgba(255,255,255,0.85); font-size:0.95rem; }

    [data-testid="stMetric"] {
        background:white; padding:1rem; border-radius:10px;
        border:1px solid #E5E7EB; box-shadow:0 1px 3px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"]  { font-size:0.85rem !important; color:#6B7280 !important; font-weight:500 !important; }
    [data-testid="stMetricValue"]  { font-size:1.8rem !important; font-weight:700 !important; }

    .pill { display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:600; white-space:nowrap; }
    .pill-critical { background:#FEE2E2; color:#991B1B; }
    .pill-high     { background:#FED7AA; color:#9A3412; }
    .pill-medium   { background:#FEF3C7; color:#92400E; }
    .pill-low      { background:#DBEAFE; color:#1E40AF; }
    .pill-licensed { background:#D1FAE5; color:#065F46; }

    .company-card {
        background:white; border:1px solid #E5E7EB; border-radius:10px;
        padding:1.25rem; margin-bottom:0.75rem; box-shadow:0 1px 3px rgba(0,0,0,0.04);
    }
    .company-card h4 { margin:0 0 0.25rem 0; color:#1F2937; font-size:1.05rem; }
    .company-card .meta { color:#6B7280; font-size:0.82rem; margin-bottom:0.4rem; }

    /* Chip buttons — active state via CSS class */
    .chip-active button { background:#1F3864 !important; color:white !important; border-color:#1F3864 !important; }

    /* Force uniform button heights in horizontal rows (prevents chip misalignment) */
    div[data-testid="stHorizontalBlock"] .stButton button {
        height: 38px !important;
        min-height: 38px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 0.82rem !important;
        padding: 0 0.75rem !important;
    }

    [data-baseweb="tab-list"] { gap:0.5rem; }
    [data-baseweb="tab"] { padding:0.5rem 1rem; border-radius:8px; font-weight:500; }
    [data-baseweb="tab"][aria-selected="true"] { background:#1F3864 !important; color:white !important; }

    /* Tighter dataframe rows */
    [data-testid="stDataFrame"] td { padding: 6px 8px !important; font-size:0.88rem; }
    [data-testid="stDataFrame"] th { padding: 8px 8px !important; font-size:0.88rem; background:#F9FAFB; }

    /* Autocomplete dropdown styling */
    .suggestion-box {
        background:white; border:1px solid #E5E7EB; border-radius:8px;
        box-shadow:0 4px 12px rgba(0,0,0,0.08); margin-top:-0.5rem;
        max-height:200px; overflow-y:auto;
    }
    .suggestion-item {
        padding:0.5rem 1rem; cursor:pointer; font-size:0.9rem; color:#374151;
        border-bottom:1px solid #F3F4F6;
    }
    .suggestion-item:hover { background:#EFF6FF; color:#1E40AF; }

    #MainMenu {visibility:hidden;} footer {visibility:hidden;} header {visibility:hidden;}

    @media (max-width:768px) {
        [data-testid="stMetricValue"] { font-size:1.4rem !important; }
        .main-header h1 { font-size:1.4rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── CONFIG ───────────────────────────────────────────────────────────────
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

# ── NOISE FILTER (aggressive) ────────────────────────────────────────────
# Exact brand names to strip (lowercased)
NOISE_BRANDS = {
    # from your screenshots
    "rulebook", "the complete rulebook", "licensing", "centralbank",
    "globenewswire", "globe newswire", "cbuae rulebook",
    "insights for businesses", "insights", "businesses",
    "2025 mobile development", "transforming payments",
    "mobile development", "2026 business plan", "2026 rules",
    "10 leaves", "10leaves", "aafs",
    "money transfers", "companies law amendments", "gccbusinesswatch",
    "financialit", "visamiddleeast", "khaleejtimes", "khaleej times",
    "tekrevol", "trriple payments", "hwala", "aundigital",
    "gulfnews", "gulf news", "thenational", "the national",
    "arabianbusiness", "arabian business", "zawya", "wam",
    "reuters", "bloomberg", "ft.com", "cnbc", "forbes",
    "crunchbase", "techcrunch", "wikipedia", "medium",
    # navigation / web boilerplate
    "page", "home", "about", "contact", "terms", "privacy",
    "privacy policy", "cookie policy", "cookies",
    "fintech news", "press release", "media release", "news release",
    "blog", "blog post", "white paper", "whitepaper", "report",
    "research", "survey", "study", "conference", "event",
    "webinar", "podcast", "linkedin", "twitter", "facebook",
    "instagram", "youtube", "warning", "'s warning",
    "vasps licensing process", "licensing process",
    "& vasps licensing process in", "& vasps licensing process",
    "& vasps", "vasps", "rules", "guide", "overview",
    "trends", "plan", "leaves", "news", "article", "articles",
    "introduction", "summary", "conclusion", "references",
    "documentation", "docs", "help", "support", "faq", "faqs",
    "sitemap", "copyright", "company", "companies", "law",
    "amendments", "amendment", "watch", "magazine", "journal",
    "newsletter", "directory", "list", "index", "database",
    "agency", "institute", "association", "council", "authority",
    "commission", "committee", "task force",
}

# Regex patterns that indicate noise
NOISE_PATTERNS = re.compile(
    r"^(\s*[&'\"\-–—]|\s*\d+[\.\)\s]|top \d+|best \d+|leading \d+|"
    r"guide to|how to|what is|list of|complete list|overview|"
    r"introduction|insights for|transforming|mobile development|"
    r"press release|whitepaper|business plan|licensing process|"
    r"warning|\d{4}\s|"
    # domain-like fragments
    r".*\.(com|ae|net|org|io|co)$|"
    # news/magazine/media sites
    r".*(news|times|watch|magazine|journal|newsletter|review|"
    r"press|media|blog|gazette|tribune|post|herald|daily|weekly)$)",
    re.I
)

# Generic financial/business words that on their own aren't real brand names
GENERIC_ONLY_WORDS = {
    "bank", "banks", "banking", "payment", "payments", "finance",
    "financial", "wallet", "wallets", "exchange", "exchanges",
    "crypto", "cryptocurrency", "trading", "investment", "investments",
    "fintech", "regulation", "regulations", "regulatory",
    "compliance", "license", "licenses", "licensing",
    "money", "transfer", "transfers", "remittance", "remittances",
    "loan", "loans", "lending", "credit", "debit", "card", "cards",
    "digital", "mobile", "online", "virtual", "electronic",
    "service", "services", "solution", "solutions", "platform",
    "technology", "technologies", "app", "apps", "application",
    "company", "companies", "corporation", "corp", "limited", "ltd",
    "uae", "dubai", "abu", "dhabi", "emirates", "gulf", "middle",
    "east", "gcc", "regional", "international", "global", "local",
}

# Known news/media/blog domains that shouldn't be brands
NEWS_MEDIA_HOSTS = {
    "khaleejtimes", "gulfnews", "thenational", "arabianbusiness",
    "zawya", "wam", "gccbusinesswatch", "globenewswire",
    "financialit", "tekrevol", "visamiddleeast", "reuters",
    "bloomberg", "ftcom", "cnbc", "forbes", "crunchbase",
    "techcrunch", "wikipedia", "medium",
}


def is_noise_brand(brand: str) -> bool:
    """Aggressive check — returns True if this brand looks like junk."""
    if not brand or not isinstance(brand, str):
        return True
    b = brand.strip().lower()

    # Empty or too short
    if not b or len(b) < 3:
        return True

    # In noise blocklist
    if b in NOISE_BRANDS:
        return True

    # Pattern match (numbers, domains, news sites)
    if NOISE_PATTERNS.match(b):
        return True

    # Starts with special char
    if re.match(r"^[\s&'\"\-–—_\.,;:]", brand):
        return True

    # Starts with digit
    if b[0].isdigit():
        return True

    # Domain-like (contains a dot with tld-looking suffix)
    if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", b):
        return True

    # Known news/media host (stripped of spaces/punct)
    b_compact = re.sub(r"[^a-z0-9]", "", b)
    if b_compact in NEWS_MEDIA_HOSTS:
        return True

    # Only generic words
    words = b.split()
    if all(w in GENERIC_ONLY_WORDS for w in words):
        return True

    # Sentence-like (more than 5 words)
    if len(words) > 5:
        return True

    # Contains sentence connectors (sentence-like phrase)
    if re.search(
        r"\b(and|or|the|in|on|of|for|with|to|by)\b.*"
        r"\b(and|or|the|in|on|of|for|with|to|by)\b", b
    ):
        return True

    # Ends with an article (incomplete phrase)
    if b.rstrip('.').split()[-1] in {
        "the", "a", "an", "of", "in", "on", "for", "to", "and", "or",
        "by", "with", "from", "at", "as",
    }:
        return True

    # Too many special chars (ratio of letters to total)
    letters = sum(c.isalpha() for c in brand)
    if letters < len(brand) * 0.5:
        return True

    # Single generic word (e.g. "Bank", "Payments", "Finance")
    if len(words) == 1 and b in GENERIC_ONLY_WORDS:
        return True

    # Contains "news", "times", "watch", "blog" — likely a publication
    if any(indicator in b for indicator in [
        "news", "times", "watch", "magazine", "blog", "gazette",
        "tribune", "herald", "daily", "weekly", "journal",
        "newsletter", "review", "press", "media",
    ]):
        return True

    return False

# ── HELPERS ───────────────────────────────────────────────────────────────
def risk_pill(level) -> str:
    try: level = int(level)
    except: return '<span class="pill pill-low">Unknown</span>'
    m = RISK_META.get(level, RISK_META[2])
    return f'<span class="pill {m["pill"]}">{m["label"]}</span>'

def render_card(row):
    pill_html = risk_pill(row.get("Risk Level", 2))
    url = row.get("Top Source URL", "")
    link = f'<a href="{url}" target="_blank" style="font-size:0.8rem;">🔗 Source</a>' \
           if url and str(url).startswith("http") else ""
    svc  = str(row.get("Service Type", ""))
    reg  = str(row.get("Regulator Scope", ""))
    rat  = str(row.get("Rationale", ""))[:260]
    act  = str(row.get("Action Required", ""))
    st.markdown(f"""
    <div class="company-card">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:1rem;">
        <div style="flex:1;min-width:0;">
          <h4>{row.get('Brand','')}</h4>
          <div class="meta">{svc} · {reg}</div>
          <div style="font-size:0.88rem;color:#374151;margin-top:0.4rem;">{rat}</div>
        </div>
        <div style="text-align:right;min-width:130px;flex-shrink:0;">
          {pill_html}
          <div style="font-size:0.78rem;color:#6B7280;margin-top:0.4rem;">{act}</div>
          <div style="margin-top:0.3rem;">{link}</div>
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

@st.cache_data(show_spinner="Loading data...")
def load_data(path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name="📋 All Results")
    except Exception:
        try:    df = pd.read_excel(path, sheet_name=0)
        except Exception as e:
            st.error(f"Could not read file: {e}"); return pd.DataFrame()

    for col in ["Brand","Classification","Group","Service Type",
                "Regulator Scope","Alert Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    if "Risk Level" in df.columns:
        df["Risk Level"] = pd.to_numeric(df["Risk Level"], errors="coerce").fillna(2).astype(int)

    # ── Apply noise filter ──
    if "Brand" in df.columns:
        df = df[~df["Brand"].apply(is_noise_brand)].reset_index(drop=True)
    return df

def fuzzy_filter(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Kept for potential future use; currently unused."""
    if not query: return df
    q = query.lower().strip()
    mask = df["Brand"].astype(str).str.lower().str.contains(q, na=False, regex=False)
    if "Service Type" in df.columns:
        mask |= df["Service Type"].astype(str).str.lower().str.contains(q, na=False, regex=False)
    result = df[mask]
    if result.empty and len(q) >= 3:
        scores = df["Brand"].astype(str).apply(
            lambda b: SequenceMatcher(None, q, b.lower()).ratio())
        result = df[scores >= 0.45]
    return result

# ── SIDEBAR ───────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🛡️ UAE Screening")
st.sidebar.caption("Market Conduct search tool")
st.sidebar.markdown("---")

files = list_screening_files()

st.sidebar.subheader("📂 Data Source")
selected_path = None
if files:
    options = {
        f"🗓️ {f['timestamp'].strftime('%d %b %Y, %H:%M')}  ·  {f['size_kb']} KB": f["path"]
        for f in files
    }
    choice = st.sidebar.selectbox("Run:", list(options.keys()), index=0,
                                   label_visibility="collapsed")
    selected_path = options[choice]

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Upload new run")
uploaded = st.sidebar.file_uploader("Drop a UAE_Screening_*.xlsx file",
                                     type=["xlsx"], label_visibility="collapsed")
if uploaded:
    save_path = DATA_DIR / uploaded.name
    with open(save_path, "wb") as f: f.write(uploaded.getbuffer())
    st.sidebar.success(f"✅ Saved: {uploaded.name}")
    st.cache_data.clear(); st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"📊 Total runs archived: **{len(files)}**")
st.sidebar.caption(f"📁 `{DATA_DIR}`")

# ── HEADER ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛡️ UAE Regulatory Screening</h1>
    <p>Market Conduct · Search, monitor, and flag UAE-facing financial services companies</p>
</div>""", unsafe_allow_html=True)

if selected_path is None:
    st.warning("⚠️ No screening files found yet. Run `uae_screening_v5.py` or upload a file.")
    st.stop()

df = load_data(selected_path)
if df.empty:
    st.error("The selected file is empty or could not be read."); st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────
total       = len(df)
unlicensed  = len(df[df["Risk Level"] >= 4])
needs_rev   = len(df[(df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)])
licensed    = len(df[df["Risk Level"] == 0])
new_run     = len(df[df["Alert Status"] == "🆕 NEW"]) if "Alert Status" in df.columns else 0
risk_up     = len(df[df["Alert Status"] == "📈 RISK INCREASED"]) if "Alert Status" in df.columns else 0

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("📊 Total Screened",   f"{total:,}")
k2.metric("🔴 High Risk",        unlicensed,
          delta=f"{unlicensed/total*100:.0f}% of total" if total else None,
          delta_color="inverse")
k3.metric("🟠 Needs Review",     needs_rev)
k4.metric("🟢 Licensed",         licensed)
k5.metric("🆕 New",              new_run,
          delta=f"📈 {risk_up} risk ↑" if risk_up else None,
          delta_color="inverse")

st.markdown("---")

# ── TABS (3 only) ─────────────────────────────────────────────────────────
tab_home, tab_search, tab_insights = st.tabs(["🏠 Home", "🔍 Search", "📊 Insights"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – HOME
# ════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.subheader("⚠️ Top entities needing attention")
    st.caption("Ranked by risk level — focus here first")

    top_risk = df[df["Risk Level"] >= 4].sort_values("Risk Level", ascending=False).head(10)

    if top_risk.empty:
        st.success("✅ No high-risk entities to review this run.")
    else:
        for _, row in top_risk.iterrows():
            render_card(row)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – SEARCH
# ════════════════════════════════════════════════════════════════════════════
with tab_search:
    st.subheader("🔍 Search & Filter")

    # ── session state ────────────────────────────────────────────────────
    if "active_chip" not in st.session_state:
        st.session_state.active_chip = None
    if "page" not in st.session_state:
        st.session_state.page = 1

    # ── Google-style autocomplete search box ─────────────────────────────
    all_brands = sorted(df["Brand"].dropna().unique().tolist())

    def search_brands(searchterm: str) -> list[str]:
        """Called as user types — returns matching brand names."""
        if not searchterm:
            return []
        q = searchterm.lower().strip()
        # Starts-with matches first (better UX)
        starts = [b for b in all_brands if b.lower().startswith(q)]
        # Then contains matches
        contains = [b for b in all_brands if q in b.lower() and b not in starts]
        return (starts + contains)[:15]

    if HAS_SEARCHBOX:
        selected_brand = st_searchbox(
            search_brands,
            placeholder="🔍 Start typing a company name (e.g. Cash, Tabby, Binance...)",
            key="brand_searchbox",
            clear_on_submit=False,
        )
    else:
        # Fallback if component isn't installed
        st.warning("⚠️ For a better search experience, add `streamlit-searchbox` to requirements.txt")
        selected_brand_raw = st.selectbox(
            "🔍 Search for a company",
            options=["— All companies —"] + all_brands,
            index=0,
        )
        selected_brand = None if selected_brand_raw == "— All companies —" else selected_brand_raw

    # Reset to page 1 when selection changes
    if selected_brand != st.session_state.get("_last_selected_brand"):
        st.session_state.page = 1
        st.session_state._last_selected_brand = selected_brand

    # ── Filter row: Risk Level + Regulator ───────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        risk_opts = sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True)
        risk_filter = st.multiselect(
            "Risk Level", options=risk_opts,
            format_func=lambda x: RISK_META.get(int(x), {}).get("label", str(x)),
        )
    with fc2:
        reg_opts = sorted(df["Regulator Scope"].dropna().unique().tolist()) \
            if "Regulator Scope" in df.columns else []
        reg_filter = st.multiselect("Regulator", options=reg_opts)

    # ── Quick-filter chip buttons (uniform width, single row) ────────────
    st.markdown(
        "<div style='margin:0.5rem 0 0.3rem 0; font-size:0.82rem; color:#6B7280;'>"
        "Quick filters:</div>",
        unsafe_allow_html=True,
    )
    chips = [
        ("🔴 High Risk", "high_risk"),
        ("🆕 New",       "new"),
        ("📈 Risk Up",   "risk_up"),
        ("🟢 Licensed",  "licensed"),
        ("₿ Crypto",     "va"),
        ("🗑️ Clear",     "clear"),
    ]
    chip_cols = st.columns(len(chips))
    for i, (label, key) in enumerate(chips):
        is_active = (st.session_state.active_chip == key)
        btn_label = f"✓ {label}" if is_active else label
        if chip_cols[i].button(btn_label, key=f"chip_{key}", use_container_width=True):
            if key == "clear":
                st.session_state.active_chip = None
            else:
                st.session_state.active_chip = None if is_active else key
            st.session_state.page = 1
            st.rerun()

    # ── Apply all filters ────────────────────────────────────────────────
    filtered = df.copy()

    # Brand filter (from autocomplete searchbox)
    if selected_brand:
        filtered = filtered[filtered["Brand"] == selected_brand]

    # Dropdown filters
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]

    # Chip filter
    chip = st.session_state.active_chip
    if chip == "high_risk":
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif chip == "new" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "🆕 NEW"]
    elif chip == "risk_up" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "📈 RISK INCREASED"]
    elif chip == "licensed":
        filtered = filtered[filtered["Risk Level"] == 0]
    elif chip == "va":
        va_mask = filtered["Regulator Scope"].astype(str).str.contains(
            "VA|VASP|CRYPTO", case=False, na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains(
                "crypto|virtual asset|token", case=False, na=False)
        filtered = filtered[va_mask]

    # Sort by risk descending
    filtered = filtered.sort_values("Risk Level", ascending=False)

    # ── Pagination ────────────────────────────────────────────────────────
    per_page    = 25
    total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
    if st.session_state.page > total_pages:
        st.session_state.page = 1

    rc1, rc2 = st.columns([3, 1])
    rc1.caption(f"Showing **{len(filtered):,}** of **{total:,}** entities")
    rc2.caption(f"Page **{st.session_state.page}** of **{total_pages}**")

    display_cols = [c for c in [
        "Brand", "Classification", "Risk Level", "Action Required",
        "Confidence", "Regulator Scope", "Service Type",
        "Matched Entity (Register)", "Rationale", "Top Source URL",
    ] if c in filtered.columns]

    start    = (st.session_state.page - 1) * per_page
    page_df  = filtered.iloc[start: start + per_page]

    st.dataframe(
        page_df[display_cols],
        use_container_width=True,
        height=min(550, 60 + len(page_df) * 38),
        hide_index=True,
        column_config={
            "Top Source URL": st.column_config.LinkColumn("🔗 Source", width="small"),
            "Risk Level":     st.column_config.NumberColumn("Risk", format="%d",
                                                            min_value=0, max_value=5,
                                                            width="small"),
            "Brand":          st.column_config.TextColumn("Brand", width="medium"),
            "Rationale":      st.column_config.TextColumn("Rationale", width="large"),
        },
    )

    # Pagination buttons
    pc1, pc2, pc3, pc4, pc5 = st.columns([1,1,4,1,1])
    if pc1.button("⏮️", use_container_width=True,
                  disabled=st.session_state.page<=1, key="p_first"):
        st.session_state.page=1; st.rerun()
    if pc2.button("◀️", use_container_width=True,
                  disabled=st.session_state.page<=1, key="p_prev"):
        st.session_state.page-=1; st.rerun()
    pc3.markdown(f"<div style='text-align:center;padding-top:0.5rem;'>"
                 f"Page <b>{st.session_state.page}</b> of {total_pages}</div>",
                 unsafe_allow_html=True)
    if pc4.button("▶️", use_container_width=True,
                  disabled=st.session_state.page>=total_pages, key="p_next"):
        st.session_state.page+=1; st.rerun()
    if pc5.button("⏭️", use_container_width=True,
                  disabled=st.session_state.page>=total_pages, key="p_last"):
        st.session_state.page=total_pages; st.rerun()

    # ── Downloads ─────────────────────────────────────────────────────────
    if not filtered.empty:
        d1, d2 = st.columns(2)
        csv = filtered.to_csv(index=False).encode("utf-8-sig")
        d1.download_button("⬇️ Download CSV", data=csv,
                           file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.csv",
                           mime="text/csv", use_container_width=True)
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                filtered.to_excel(writer, index=False, sheet_name="Filtered")
            d2.download_button("⬇️ Download Excel", data=buf.getvalue(),
                               file_name=f"filtered_{datetime.now():%Y%m%d_%H%M}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with tab_insights:
    st.subheader("📊 Insights Dashboard")

    ic1, ic2 = st.columns(2)
    with ic1:
        st.markdown("#### Risk Level Distribution")
        if "Risk Level" in df.columns:
            rc = df["Risk Level"].value_counts().sort_index(ascending=False)
            rc.index = [RISK_META.get(int(i),{}).get("label", str(i)) for i in rc.index]
            st.bar_chart(rc, height=260)
    with ic2:
        st.markdown("#### Classification Groups")
        if "Group" in df.columns:
            st.bar_chart(df["Group"].value_counts(), height=260)

    ic3, ic4 = st.columns(2)
    with ic3:
        st.markdown("#### Top 10 Regulator Scopes")
        if "Regulator Scope" in df.columns:
            st.bar_chart(df["Regulator Scope"].value_counts().head(10), height=260)
    with ic4:
        st.markdown("#### Top 10 Service Types")
        if "Service Type" in df.columns:
            st.bar_chart(df["Service Type"].value_counts().head(10), height=260)

    st.markdown("---")
    st.markdown("#### 📈 Trend Across Runs")
    if len(files) >= 2:
        trend_rows = []
        for f in files[:10]:
            try:
                d = pd.read_excel(f["path"], sheet_name="📋 All Results")
                d["Risk Level"] = pd.to_numeric(d["Risk Level"], errors="coerce").fillna(2).astype(int)
                trend_rows.append({
                    "Run":               f["timestamp"].strftime("%m/%d %H:%M"),
                    "Unlicensed (4+)":   int(len(d[d["Risk Level"] >= 4])),
                    "Needs Review (2-3)":int(len(d[(d["Risk Level"]>=2)&(d["Risk Level"]<=3)])),
                    "Licensed (0)":      int(len(d[d["Risk Level"]==0])),
                })
            except Exception: continue
        if trend_rows:
            st.line_chart(pd.DataFrame(trend_rows).set_index("Run").iloc[::-1], height=280)
    else:
        st.caption(f"Only {len(files)} run archived — trend chart needs 2+ runs.")

    st.markdown("---")
    st.markdown("#### Full Classification Breakdown")
    if "Classification" in df.columns:
        cls = df["Classification"].value_counts().reset_index()
        cls.columns = ["Classification","Count"]
        cls["% of total"] = (cls["Count"]/total*100).round(1).astype(str)+"%"
        st.dataframe(cls, use_container_width=True, hide_index=True)

# ── FOOTER ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"📁 `{Path(selected_path).name}`  ·  "
    f"🕐 {datetime.now():%Y-%m-%d %H:%M}  ·  "
    f"ℹ️ Automated first-pass screening — not a legal determination"
)
