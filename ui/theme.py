"""Design system — Bloomberg-terminal aesthetic, navy + gold."""
from __future__ import annotations

import streamlit as st

from config import THEMES, Theme


def current_theme(session) -> Theme:
    name = session.get("theme", "dark")
    return THEMES.get(name, THEMES["dark"])


def inject_css(theme: Theme) -> None:
    is_dark = theme.name == "dark"

    # ── Color palette ─────────────────────────────────────────────────────────
    if is_dark:
        bg          = "#0A0E1F"   # deep navy/black
        card        = "#0F1530"   # slightly lighter card
        card_hover  = "#141B3A"
        border      = "rgba(255,255,255,0.06)"
        border_hi   = "rgba(255,255,255,0.12)"
        text        = "#E8ECF5"
        dim         = "#A0AABC"
        muted       = "#5A6478"
        gold        = "#E5B547"
        gold_soft   = "rgba(229,181,71,0.10)"
        accent      = gold
        accent_soft = gold_soft
        # Risk colours
        critical    = "#EF4444"
        high        = "#F87171"
        medium      = "#F59E0B"
        monitor     = "#818CF8"
        low         = "#3B82F6"
        licensed    = "#22C55E"
        # Regulator colours
        cbuae_c     = "#E5B547"
        vara_c      = "#A78BFA"
        adgm_c      = "#F59E0B"
        fsra_c      = "#22C55E"
        dfsa_c      = "#A78BFA"
    else:
        bg          = "#F1F5F9"
        card        = "#FFFFFF"
        card_hover  = "#F8FAFC"
        border      = "rgba(15,23,42,0.08)"
        border_hi   = "rgba(15,23,42,0.16)"
        text        = "#0F172A"
        dim         = "#334155"
        muted       = "#64748B"
        gold        = "#B8860B"
        gold_soft   = "rgba(184,134,11,0.10)"
        accent      = gold
        accent_soft = gold_soft
        critical    = "#DC2626"
        high        = "#EF4444"
        medium      = "#D97706"
        monitor     = "#6366F1"
        low         = "#2563EB"
        licensed    = "#16A34A"
        cbuae_c     = "#B8860B"
        vara_c      = "#7C3AED"
        adgm_c      = "#D97706"
        fsra_c      = "#16A34A"
        dfsa_c      = "#7C3AED"

    css = f"""
    <style>
    /* ── Fonts ──────────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {{
      --bg:         {bg};
      --card:       {card};
      --card-hover: {card_hover};
      --border:     {border};
      --border-hi:  {border_hi};
      --text:       {text};
      --dim:        {dim};
      --muted:      {muted};
      --accent:     {accent};
      --accent-s:   {accent_soft};
      --gold:       {gold};
      --critical:   {critical};
      --high:       {high};
      --medium:     {medium};
      --monitor:    {monitor};
      --low:        {low};
      --licensed:   {licensed};
      --cbuae:      {cbuae_c};
      --vara:       {vara_c};
      --adgm:       {adgm_c};
      --fsra:       {fsra_c};
      --dfsa:       {dfsa_c};
    }}

    /* ── App-level resets ───────────────────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"], .stApp {{
      background: var(--bg) !important;
      color: var(--text) !important;
      font-family: 'Inter', -apple-system, sans-serif !important;
    }}
    .block-container {{
      padding: 1rem 2rem 3rem 2rem !important;
      max-width: 100% !important;
    }}

    /* Hide Streamlit chrome */
    #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0 !important; }}
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}

    /* ── Top navigation bar ─────────────────────────────────────────────── */
    .uae-topnav {{
      display: flex;
      align-items: center;
      gap: 32px;
      padding: 14px 24px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      margin-bottom: 20px;
    }}
    .uae-brand {{
      display: flex; align-items: center; gap: 12px;
      flex-shrink: 0;
    }}
    .uae-brand-logo {{
      width: 42px; height: 42px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--gold), {("#B8860B" if not is_dark else "#A6822A")});
      display: flex; align-items: center; justify-content: center;
      font-size: 20px; color: #0A0E1F;
      box-shadow: 0 4px 12px rgba(229,181,71,0.25);
    }}
    .uae-brand-name {{
      font-size: 16px; font-weight: 700; color: var(--text);
      line-height: 1;
    }}
    .uae-brand-sub {{
      font-size: 9px; font-weight: 600; color: var(--muted);
      letter-spacing: 0.15em; text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace; margin-top: 4px;
    }}
    .uae-tabs {{
      display: flex; gap: 28px; flex: 1;
    }}
    .uae-tab {{
      font-size: 14px; font-weight: 500;
      color: var(--muted);
      padding: 8px 0;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s;
    }}
    .uae-tab:hover {{ color: var(--dim); }}
    .uae-tab-active {{
      color: var(--text);
      border-bottom-color: var(--gold);
      font-weight: 600;
    }}
    .uae-meta {{
      display: flex; align-items: center; gap: 16px;
      flex-shrink: 0;
    }}
    .uae-live {{
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 11px; font-weight: 600; color: var(--licensed);
      font-family: 'JetBrains Mono', monospace;
    }}
    .uae-live-dot {{
      width: 7px; height: 7px; border-radius: 999px;
      background: var(--licensed);
      box-shadow: 0 0 8px var(--licensed);
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%,100% {{opacity:1}} 50% {{opacity:0.5}} }}
    .uae-meta-text {{
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.06em;
    }}
    .uae-meta-text b {{ color: var(--dim); font-weight: 600; }}

    /* ── KPI Cards ──────────────────────────────────────────────────────── */
    .uae-kpi-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}
    .uae-kpi {{
      position: relative;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px 22px;
      overflow: hidden;
    }}
    .uae-kpi::before {{
      content: '';
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 3px;
    }}
    .uae-kpi.k-screened::before {{ background: var(--gold); }}
    .uae-kpi.k-high::before     {{ background: var(--critical); }}
    .uae-kpi.k-risk::before     {{ background: var(--medium); }}
    .uae-kpi.k-new::before      {{ background: var(--licensed); }}
    .uae-kpi.k-licensed::before {{ background: var(--licensed); }}

    .uae-kpi-label {{
      font-size: 10px; font-weight: 700; color: var(--muted);
      letter-spacing: 0.12em; text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
      display: flex; justify-content: space-between; align-items: center;
    }}
    .uae-kpi-trend {{
      font-size: 10px; font-weight: 700;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(245,158,11,0.15);
      color: var(--medium);
      font-family: 'JetBrains Mono', monospace;
    }}
    .uae-kpi-trend.up {{ background: rgba(245,158,11,0.15); color: var(--medium); }}
    .uae-kpi-trend.new {{ background: rgba(34,197,94,0.15); color: var(--licensed); }}
    .uae-kpi-value {{
      font-size: 42px; font-weight: 800; color: var(--text);
      line-height: 1.1; margin-top: 12px;
      font-family: 'Inter', sans-serif;
      letter-spacing: -0.02em;
    }}
    .uae-kpi-hint {{
      font-size: 11px; color: var(--muted);
      margin-top: 8px;
    }}

    /* ── Section Headers ───────────────────────────────────────────────── */
    .uae-section {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px;
    }}
    .uae-section-title {{
      font-size: 16px; font-weight: 700; color: var(--text);
    }}
    .uae-section-badge {{
      font-size: 10px; font-weight: 700;
      color: var(--gold); background: var(--accent-s);
      border: 1px solid rgba(229,181,71,0.25);
      padding: 5px 12px; border-radius: 999px;
      letter-spacing: 0.1em; text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Entity Cards (Priority Queue) ─────────────────────────────────── */
    .uae-entity {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px 22px;
      margin-bottom: 12px;
      transition: all 0.15s;
      cursor: pointer;
      position: relative;
    }}
    .uae-entity:hover {{
      background: var(--card-hover);
      border-color: var(--border-hi);
      transform: translateY(-1px);
    }}
    .uae-entity-row {{
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: 16px;
    }}
    .uae-entity-main {{ flex: 1; min-width: 0; }}
    .uae-entity-head {{
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      margin-bottom: 6px;
    }}
    .uae-entity-name {{
      font-size: 17px; font-weight: 700; color: var(--text);
    }}
    .uae-entity-meta {{
      font-size: 12px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 10px;
    }}
    .uae-entity-rationale {{
      font-size: 13px; color: var(--dim);
      line-height: 1.55;
    }}
    .uae-entity-side {{
      display: flex; flex-direction: column; align-items: flex-end;
      gap: 8px; flex-shrink: 0;
    }}

    /* Status pills */
    .uae-pill {{
      display: inline-flex; align-items: center; gap: 4px;
      font-size: 10px; font-weight: 700;
      padding: 4px 10px; border-radius: 999px;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.06em;
    }}
    .uae-pill.risk-up {{ background: rgba(245,158,11,0.12); color: var(--medium); border: 1px solid rgba(245,158,11,0.25); }}
    .uae-pill.new {{ background: rgba(34,197,94,0.12); color: var(--licensed); border: 1px solid rgba(34,197,94,0.25); }}
    .uae-pill.critical {{ background: rgba(239,68,68,0.12); color: var(--critical); border: 1px solid rgba(239,68,68,0.30); }}
    .uae-pill.high {{ background: rgba(248,113,113,0.12); color: var(--high); border: 1px solid rgba(248,113,113,0.30); }}
    .uae-pill.medium {{ background: rgba(245,158,11,0.12); color: var(--medium); border: 1px solid rgba(245,158,11,0.30); }}
    .uae-pill.monitor {{ background: rgba(129,140,248,0.12); color: var(--monitor); border: 1px solid rgba(129,140,248,0.30); }}
    .uae-pill.low {{ background: rgba(59,130,246,0.12); color: var(--low); border: 1px solid rgba(59,130,246,0.30); }}
    .uae-pill.licensed {{ background: rgba(34,197,94,0.12); color: var(--licensed); border: 1px solid rgba(34,197,94,0.30); }}

    /* Risk badge with dot */
    .uae-risk-badge {{
      display: inline-flex; align-items: center; gap: 5px;
      font-size: 11px; font-weight: 700;
      padding: 5px 12px; border-radius: 999px;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.06em; text-transform: uppercase;
    }}
    .uae-risk-dot {{ width: 6px; height: 6px; border-radius: 999px; }}

    /* Required action text */
    .uae-action {{
      font-size: 11px; color: var(--muted);
      max-width: 200px; text-align: right;
      line-height: 1.4;
    }}

    /* Regulator pill */
    .uae-reg {{
      display: inline-flex; align-items: center;
      font-size: 10px; font-weight: 700;
      padding: 4px 10px; border-radius: 6px;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.08em;
    }}
    .uae-reg.cbuae {{ background: rgba(229,181,71,0.12); color: var(--cbuae); border: 1px solid rgba(229,181,71,0.30); }}
    .uae-reg.vara  {{ background: rgba(167,139,250,0.12); color: var(--vara);  border: 1px solid rgba(167,139,250,0.30); }}
    .uae-reg.adgm  {{ background: rgba(245,158,11,0.12);  color: var(--adgm);  border: 1px solid rgba(245,158,11,0.30); }}
    .uae-reg.fsra  {{ background: rgba(34,197,94,0.12);   color: var(--fsra);  border: 1px solid rgba(34,197,94,0.30); }}
    .uae-reg.dfsa  {{ background: rgba(167,139,250,0.12); color: var(--dfsa);  border: 1px solid rgba(167,139,250,0.30); }}
    .uae-reg.gov   {{ background: rgba(90,100,120,0.20); color: var(--muted); border: 1px solid rgba(90,100,120,0.30); }}
    .uae-reg.other {{ background: rgba(90,100,120,0.20); color: var(--muted); border: 1px solid rgba(90,100,120,0.30); }}

    /* ── Right sidebar callouts ────────────────────────────────────────── */
    .uae-alert-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-left: 3px solid var(--medium);
      border-radius: 12px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }}
    .uae-alert-title {{
      font-size: 10px; font-weight: 700; color: var(--medium);
      letter-spacing: 0.12em; text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 12px;
    }}
    .uae-alert-line {{
      font-size: 13px; color: var(--dim);
      margin-bottom: 6px;
    }}
    .uae-alert-line b {{ color: var(--licensed); font-weight: 700; }}
    .uae-alert-line.up b {{ color: var(--medium); }}

    .uae-summary {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 16px;
    }}
    .uae-summary-title {{
      font-size: 13px; font-weight: 700; color: var(--text);
      margin-bottom: 14px;
    }}
    .uae-summary-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--border);
    }}
    .uae-summary-row:last-child {{ border-bottom: none; }}
    .uae-summary-label {{
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
    }}
    .uae-summary-val {{
      font-size: 12px; font-weight: 600; color: var(--dim);
      font-family: 'JetBrains Mono', monospace;
    }}

    .uae-bars {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
    }}
    .uae-bar-row {{
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 10px;
    }}
    .uae-bar-row:last-child {{ margin-bottom: 0; }}
    .uae-bar-label {{
      font-size: 10px; font-weight: 700; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      width: 56px; text-align: right; flex-shrink: 0;
    }}
    .uae-bar-track {{
      flex: 1; height: 8px;
      background: rgba(255,255,255,0.04);
      border-radius: 999px; overflow: hidden;
    }}
    .uae-bar-fill {{
      height: 100%; border-radius: 999px;
      transition: width 0.4s ease;
    }}
    .uae-bar-count {{
      font-size: 12px; font-weight: 700; color: var(--text);
      font-family: 'JetBrains Mono', monospace;
      width: 28px; flex-shrink: 0;
    }}

    /* ── Search & Filter table ─────────────────────────────────────────── */
    .uae-table-head {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 2fr 1fr;
      gap: 16px;
      padding: 12px 20px;
      font-size: 10px; font-weight: 700; color: var(--muted);
      letter-spacing: 0.12em; text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
      border-bottom: 1px solid var(--border);
    }}
    .uae-table-row {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 2fr 1fr;
      gap: 16px;
      padding: 18px 20px;
      align-items: center;
      border-bottom: 1px solid var(--border);
      transition: background 0.15s;
    }}
    .uae-table-row:hover {{ background: var(--card-hover); }}
    .uae-table-row:last-child {{ border-bottom: none; }}
    .uae-table-cell-name {{
      font-size: 14px; font-weight: 600; color: var(--text);
    }}
    .uae-table-cell-svc {{
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      margin-top: 2px;
    }}
    .uae-table-action {{
      font-size: 12px; color: var(--dim);
    }}
    .uae-table-status {{
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Search bar with autocomplete ──────────────────────────────────── */
    .uae-search-wrap {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 4px;
      margin-bottom: 12px;
    }}
    .uae-search-bar {{
      display: flex; align-items: center; gap: 10px;
      padding: 10px 16px;
    }}
    .uae-search-icon {{
      color: var(--muted); font-size: 14px;
    }}
    .uae-search-suggest {{
      background: rgba(229,181,71,0.06);
      border-top: 1px solid var(--border);
      padding: 12px 16px;
      display: flex; justify-content: space-between; align-items: center;
      font-family: 'JetBrains Mono', monospace;
    }}
    .uae-search-suggest-text {{
      font-size: 13px; color: var(--gold); font-weight: 600;
    }}
    .uae-search-suggest-hint {{
      font-size: 11px; color: var(--muted);
    }}

    /* ── Filter chip row ───────────────────────────────────────────────── */
    .uae-chip-row {{
      display: flex; gap: 8px; align-items: center;
      flex-wrap: wrap;
    }}
    .uae-chip {{
      font-size: 11px; font-weight: 600;
      padding: 8px 16px; border-radius: 999px;
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--dim);
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.06em;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .uae-chip:hover {{ border-color: var(--border-hi); color: var(--text); }}
    .uae-chip.active {{
      background: var(--accent-s);
      border-color: var(--gold);
      color: var(--gold);
    }}

    /* ── Streamlit widget overrides ─────────────────────────────────────── */
    /* Hide default tab styling — we use custom HTML nav */
    .stTabs [data-baseweb="tab-list"] {{ display: none; }}

    div[data-testid="stTextInput"] input {{
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
      border-radius: 12px !important;
      padding: 12px 16px !important;
      font-size: 14px !important;
      font-family: 'Inter', sans-serif !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
      border-color: var(--gold) !important;
      box-shadow: 0 0 0 2px rgba(229,181,71,0.2) !important;
    }}

    div[data-testid="stSelectbox"] > div {{
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      border-radius: 10px !important;
      color: var(--text) !important;
    }}

    button[kind="secondary"], button[kind="primary"] {{
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      color: var(--dim) !important;
      border-radius: 10px !important;
      font-weight: 500 !important;
      font-family: 'Inter', sans-serif !important;
      padding: 8px 16px !important;
      transition: all 0.15s !important;
    }}
    button[kind="secondary"]:hover, button[kind="primary"]:hover {{
      border-color: var(--gold) !important;
      color: var(--gold) !important;
      background: var(--accent-s) !important;
    }}

    /* Drawer / expander styling */
    div[data-testid="stExpander"] {{
      background: var(--card) !important;
      border: 1px solid var(--border) !important;
      border-radius: 14px !important;
      margin-top: 16px;
    }}
    div[data-testid="stExpander"] summary {{
      font-weight: 600 !important;
      color: var(--text) !important;
      padding: 16px 20px !important;
    }}

    /* Drawer panel for entity detail */
    .uae-drawer {{
      background: var(--card);
      border: 1px solid var(--border);
      border-left: 3px solid var(--gold);
      border-radius: 14px;
      padding: 24px;
      position: relative;
    }}
    .uae-drawer-head {{
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 20px;
    }}
    .uae-drawer-title {{
      font-size: 22px; font-weight: 800; color: var(--text);
      letter-spacing: -0.01em;
    }}
    .uae-drawer-pills {{
      display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;
    }}
    .uae-drawer-section {{
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px 18px;
      margin-bottom: 12px;
    }}
    .uae-drawer-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 6px 0;
    }}
    .uae-drawer-label {{
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.08em; text-transform: uppercase;
    }}
    .uae-drawer-val {{
      font-size: 13px; font-weight: 600; color: var(--dim);
    }}
    .uae-drawer-rationale {{
      font-size: 13px; color: var(--dim);
      line-height: 1.6;
    }}
    .uae-drawer-action {{
      background: rgba(229,181,71,0.06);
      border-left: 3px solid var(--gold);
      border-radius: 6px;
      padding: 14px 16px;
      font-size: 14px; font-weight: 600;
      color: var(--gold);
      margin-top: 8px;
    }}

    /* Empty state */
    .uae-empty {{
      background: var(--card);
      border: 1px dashed var(--border);
      border-radius: 14px;
      padding: 40px 24px;
      text-align: center;
    }}
    .uae-empty-icon {{ font-size: 32px; margin-bottom: 12px; }}
    .uae-empty-title {{ font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 4px; }}
    .uae-empty-desc  {{ font-size: 12px; color: var(--muted); }}

    /* Footer */
    .uae-footer {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 20px 0 12px 0;
      font-size: 11px; color: var(--muted);
      font-family: 'JetBrains Mono', monospace;
      border-top: 1px solid var(--border);
      margin-top: 32px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
