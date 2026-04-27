"""
Centralized configuration: column schema, risk rules, theme, paths.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR: Final[Path] = Path.home() / "Downloads" / "UAE_Screening"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILE_GLOB: Final[str] = "UAE_Screening_*.xlsx"
DEFAULT_SHEET: Final[str] = "📋 All Results"


# ---------------------------------------------------------------------------
# Column schema
# ---------------------------------------------------------------------------
class Col:
    BRAND = "Brand"
    SERVICE = "Service Type"
    CLASSIFICATION = "Classification"
    GROUP = "Group"
    RISK_LEVEL = "Risk Level"
    ACTION = "Action Required"
    CONFIDENCE = "Confidence"
    REGULATOR = "Regulator Scope"
    MATCHED_ENTITY = "Matched Entity (Register)"
    REGISTER_CATEGORY = "Register Category"
    RATIONALE = "Rationale"
    UAE_PRESENT = "UAE Present?"
    LICENSE_SIGNAL = "License Signal?"
    UNLICENSED_SIGNAL = "Unlicensed Signal?"
    SOURCE_URL = "Top Source URL"
    SNIPPET = "Key Snippet"
    SEARCH_PROVIDER = "Search Provider"
    SOURCE = "Source"
    DISCOVERY_QUERY = "Discovery Query"


REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    Col.BRAND, Col.SERVICE, Col.CLASSIFICATION, Col.RISK_LEVEL, Col.REGULATOR,
)

OPTIONAL_COLUMNS: Final[tuple[str, ...]] = (
    Col.GROUP, Col.ACTION, Col.CONFIDENCE, Col.MATCHED_ENTITY,
    Col.REGISTER_CATEGORY, Col.RATIONALE, Col.UAE_PRESENT,
    Col.LICENSE_SIGNAL, Col.UNLICENSED_SIGNAL, Col.SOURCE_URL,
    Col.SNIPPET, Col.SEARCH_PROVIDER, Col.SOURCE, Col.DISCOVERY_QUERY,
)

COLUMN_ALIASES: Final[dict[str, str]] = {
    "brand_name": Col.BRAND, "entity": Col.BRAND, "name": Col.BRAND,
    "service": Col.SERVICE, "service type": Col.SERVICE,
    "regulator": Col.REGULATOR, "regulator_scope": Col.REGULATOR,
    "risk": Col.RISK_LEVEL, "risk_level": Col.RISK_LEVEL,
    "action": Col.ACTION, "top_source_url": Col.SOURCE_URL, "url": Col.SOURCE_URL,
}

NULL_TOKENS: Final[frozenset[str]] = frozenset({
    "", "nan", "n/a", "na", "none", "null", "-", "—",
})


# ---------------------------------------------------------------------------
# Risk taxonomy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RiskTier:
    level: int
    key: str
    label: str
    color: str
    accent_bg: str
    description: str


RISK_TIERS: Final[tuple[RiskTier, ...]] = (
    RiskTier(0, "licensed", "Licensed / Clear", "#50C88A", "rgba(80,200,138,0.12)", "Authorized and on an official register."),
    RiskTier(1, "low", "Low", "#3DA5E0", "rgba(61,165,224,0.12)", "No red flags; routine monitoring."),
    RiskTier(2, "monitor", "Monitor", "#7AA4E6", "rgba(122,164,230,0.12)", "Weak signals; keep under watch."),
    RiskTier(3, "medium", "Medium", "#C9A84C", "rgba(201,168,76,0.12)", "Material gaps; investigate."),
    RiskTier(4, "high", "High", "#E0884C", "rgba(224,136,76,0.12)", "Likely unlicensed; prioritize."),
    RiskTier(5, "critical", "Critical", "#D63C54", "rgba(214,60,84,0.14)", "Active enforcement concern."),
)

RISK_BY_LEVEL: Final[dict[int, RiskTier]] = {t.level: t for t in RISK_TIERS}
HIGH_RISK_THRESHOLD: Final[int] = 4
REVIEW_MIN, REVIEW_MAX = 2, 3


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificationRule:
    name: str
    when: dict[str, tuple[str, object]]
    risk_level: int
    label: str
    priority: int = 100


DEFAULT_RULES: Final[tuple[ClassificationRule, ...]] = (
    ClassificationRule("licensed_on_register",
        when={Col.LICENSE_SIGNAL: ("truthy", None), Col.MATCHED_ENTITY: ("truthy", None)},
        risk_level=0, label="✅ LICENSED – ON REGISTER", priority=10),
    ClassificationRule("unlicensed_signal_uae",
        when={Col.UNLICENSED_SIGNAL: ("truthy", None), Col.UAE_PRESENT: ("truthy", None)},
        risk_level=5, label="🚨 CRITICAL – CONFIRMED UNLICENSED", priority=20),
    ClassificationRule("uae_present_no_license",
        when={Col.UAE_PRESENT: ("truthy", None), Col.LICENSE_SIGNAL: ("falsy", None)},
        risk_level=4, label="🔴 NOT FOUND – POSSIBLE UNLICENSED", priority=30),
    ClassificationRule("partial_signals",
        when={Col.UAE_PRESENT: ("truthy", None)},
        risk_level=3, label="🟡 MEDIUM – PARTIAL SIGNALS", priority=40),
    ClassificationRule("weak_presence",
        when={}, risk_level=1, label="🟢 LOW – NO UAE FOOTPRINT", priority=999),
)


# ---------------------------------------------------------------------------
# Pagination & UI defaults
# ---------------------------------------------------------------------------
PAGE_SIZE_DEFAULT: Final[int] = 12
PAGE_SIZE_OPTIONS: Final[tuple[int, ...]] = (12, 24, 48, 96)


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Theme:
    name: str
    app_bg: str
    card_bg: str
    text: str
    text_dim: str
    text_muted: str
    border: str
    accent: str
    accent_soft: str


THEMES: Final[dict[str, Theme]] = {
    "dark": Theme(name="dark", app_bg="#07091C", card_bg="#0C1228",
        text="#D8E1F2", text_dim="#8896B4", text_muted="#4E5E7A",
        border="rgba(255,255,255,0.08)", accent="#C9A84C",
        accent_soft="rgba(201,168,76,0.12)"),
    "light": Theme(name="light", app_bg="#F5F7FB", card_bg="#FFFFFF",
        text="#0F172A", text_dim="#334155", text_muted="#64748B",
        border="rgba(15,23,42,0.10)", accent="#8A6012",
        accent_soft="rgba(138,96,18,0.12)"),
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ValidationConfig:
    max_rows: int = 50_000
    max_file_size_mb: int = 25
    warn_missing_optional: bool = True


VALIDATION: Final[ValidationConfig] = ValidationConfig()
