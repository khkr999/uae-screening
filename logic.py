"""Business rules and normalization helpers for UAE regulatory screening."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


RISK_META = {
    5: {"label": "Critical", "color": "#E11D48", "bg": "rgba(225,29,72,0.12)", "border": "rgba(225,29,72,0.3)"},
    4: {"label": "High", "color": "#F97316", "bg": "rgba(249,115,22,0.12)", "border": "rgba(249,115,22,0.3)"},
    3: {"label": "Medium", "color": "#EAB308", "bg": "rgba(234,179,8,0.12)", "border": "rgba(234,179,8,0.3)"},
    2: {"label": "Monitor", "color": "#4A7FD4", "bg": "rgba(74,127,212,0.12)", "border": "rgba(74,127,212,0.3)"},
    1: {"label": "Low", "color": "#4A7FD4", "bg": "rgba(74,127,212,0.08)", "border": "rgba(74,127,212,0.2)"},
    0: {"label": "Licensed", "color": "#10B981", "bg": "rgba(16,185,129,0.12)", "border": "rgba(16,185,129,0.3)"},
}


@dataclass(frozen=True)
class RiskRule:
    """Transparent, configurable rule used to derive risk labels."""

    min_level: int
    max_level: int
    label: str


DEFAULT_RISK_RULES: tuple[RiskRule, ...] = (
    RiskRule(5, 5, "Critical"),
    RiskRule(4, 4, "High"),
    RiskRule(3, 3, "Medium"),
    RiskRule(2, 2, "Monitor"),
    RiskRule(1, 1, "Low"),
    RiskRule(0, 0, "Licensed"),
)

NOISE_BRANDS = {
    "rulebook", "the complete rulebook", "licensing", "centralbank",
    "globenewswire", "globe newswire", "cbuae rulebook",
    "insights for businesses", "insights", "businesses",
    "money transfers", "companies law amendments", "gccbusinesswatch",
    "financialit", "visamiddleeast", "khaleejtimes", "khaleej times",
    "gulfnews", "gulf news", "thenational", "the national",
    "arabianbusiness", "arabian business", "zawya", "wam",
    "reuters", "bloomberg", "ft.com", "cnbc", "forbes",
    "crunchbase", "techcrunch", "wikipedia", "medium",
    "page", "home", "about", "contact", "terms", "privacy",
    "fintech news", "press release", "media release", "news release",
    "blog", "white paper", "whitepaper", "report", "research", "survey",
    "study", "conference", "event", "webinar", "podcast",
    "linkedin", "twitter", "facebook", "instagram", "youtube",
    "warning", "vasps", "vasps licensing process",
    "rules", "guide", "overview", "trends", "plan", "news", "article",
    "introduction", "summary", "conclusion", "documentation", "docs",
    "help", "support", "faq", "faqs", "sitemap", "copyright",
}

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

REGULATOR_ALIASES = {
    "CBUAE_ONSHORE": "CBUAE",
    "CBUAE ONSHORE": "CBUAE",
    "VARA_ONSHORE": "VARA",
    "DFSA_ONSHORE": "DFSA",
    "ADGM_ONSHORE": "ADGM",
}

ALERT_ALIASES = {
    "NEW": "🆕 NEW",
    "RISK INCREASED": "📈 RISK INCREASED",
    "": "",
}


def is_noise_brand(brand: str) -> bool:
    """Filter obvious non-entity brand values before they hit the dashboard."""

    if not brand or not isinstance(brand, str):
        return True
    candidate = brand.strip().lower()
    if not candidate or len(candidate) < 3:
        return True
    if candidate in NOISE_BRANDS or NOISE_PATTERNS.match(candidate):
        return True
    if re.match(r"^[\s&'\"\-–—_\.,;:]", brand):
        return True
    if candidate[0].isdigit():
        return True
    if re.search(r"\.(com|ae|net|org|io|co|gov|edu)\b", candidate):
        return True
    words = candidate.split()
    if words and all(word in GENERIC_ONLY_WORDS for word in words):
        return True
    if len(words) > 5:
        return True
    if len(words) == 1 and candidate in GENERIC_ONLY_WORDS:
        return True
    if any(token in candidate for token in ("news", "blog", "press", "media", "review", "journal")):
        return True
    letters = sum(char.isalpha() for char in brand)
    return letters < len(brand) * 0.5


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("nan", "")


def normalize_frame_text(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    normalized = df.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(normalize_text)
    return normalized


def normalize_regulator(value: object) -> str:
    text = normalize_text(value).upper().replace("-", "_").replace(" ", "_")
    return REGULATOR_ALIASES.get(text, text.replace("_", " "))


def normalize_alert_status(value: object) -> str:
    text = normalize_text(value).upper().replace("📈", "").replace("🆕", "").strip()
    return ALERT_ALIASES.get(text, normalize_text(value))


def normalize_risk_level(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(2).clip(lower=0, upper=5).astype(int)


def risk_label(level: int, rules: Iterable[RiskRule] = DEFAULT_RISK_RULES) -> str:
    for rule in rules:
        if rule.min_level <= level <= rule.max_level:
            return rule.label
    return "Monitor"


def apply_risk_logic(
    df: pd.DataFrame,
    rules: Iterable[RiskRule] = DEFAULT_RISK_RULES,
) -> pd.DataFrame:
    """
    Standardize values and attach transparent risk outputs.

    The dashboard still honors the input Excel data, but this layer makes the
    resulting classification explicit, normalized, and reusable in APIs later.
    """

    processed = df.copy()
    if "Risk Level" not in processed.columns:
        processed["Risk Level"] = 2
    processed["Risk Level"] = normalize_risk_level(processed["Risk Level"])
    processed["Risk Label"] = processed["Risk Level"].map(lambda value: risk_label(int(value), rules))
    processed["Risk Bucket"] = processed["Risk Level"].map(
        lambda value: "Priority" if value >= 4 else ("Review" if value >= 2 else "Clear")
    )
    processed["Derived Rule"] = processed["Risk Level"].map(
        lambda value: f"risk_level_between_{value}_{value}"
    )

    if "Regulator Scope" in processed.columns:
        processed["Regulator Scope"] = processed["Regulator Scope"].map(normalize_regulator)
    if "Alert Status" in processed.columns:
        processed["Alert Status"] = processed["Alert Status"].map(normalize_alert_status)
    return processed
