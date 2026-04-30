"""
Pure DataFrame transforms: metrics, filtering, sorting, aggregation, export.

All functions are pure (no session state, no Streamlit) so they are trivial
to unit test and can be called directly from a FastAPI endpoint.
"""
from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Iterable

import pandas as pd

from config import (
    Col, HIGH_RISK_THRESHOLD, REVIEW_MAX, REVIEW_MIN, RISK_BY_LEVEL,
)
from models import FilterState, RunMetrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(df: pd.DataFrame,
                    previous: pd.DataFrame | None = None) -> RunMetrics:
    """
    Aggregate KPIs for a run. If `previous` is provided, computes
    new_entities / risk_increased deltas against it.
    """
    if df.empty:
        return RunMetrics()

    risk = df[Col.RISK_LEVEL]
    counts = risk.value_counts()
    get = lambda lvl: int(counts.get(lvl, 0))

    metrics = RunMetrics(
        total=len(df),
        licensed=get(0),
        low=get(1),
        monitor=get(2),
        medium=get(3),
        high=get(4),
        critical=get(5),
        needs_review=int(((risk >= REVIEW_MIN) & (risk <= REVIEW_MAX)).sum()),
        critical_high=int((risk >= HIGH_RISK_THRESHOLD).sum()),
        top_regulator=_mode_or_dash(df[Col.REGULATOR]),
        top_service=_mode_or_dash(df[Col.SERVICE]),
    )

    if previous is not None and not previous.empty:
        prev_brands = set(previous[Col.BRAND].dropna().astype(str))
        curr_brands = set(df[Col.BRAND].dropna().astype(str))
        metrics.new_entities = len(curr_brands - prev_brands)

        # Risk increased: same brand, higher level than before
        prev_risk = (previous.groupby(Col.BRAND)[Col.RISK_LEVEL]
                     .max().to_dict())
        curr_risk = (df.groupby(Col.BRAND)[Col.RISK_LEVEL]
                     .max().to_dict())
        metrics.risk_increased = sum(
            1 for b, r in curr_risk.items()
            if b in prev_risk and r > prev_risk[b]
        )

    return metrics


def _mode_or_dash(series: pd.Series) -> str:
    clean = series.dropna()
    if clean.empty:
        return "—"
    return str(clean.mode().iloc[0])


# ---------------------------------------------------------------------------
# Filtering & sorting (vectorized)
# ---------------------------------------------------------------------------
_QUICK_CHIP_FILTERS = {
    "highCritical": lambda df: df[Col.RISK_LEVEL] >= HIGH_RISK_THRESHOLD,
    "needsReview":  lambda df: df[Col.RISK_LEVEL].between(REVIEW_MIN, REVIEW_MAX),
    "licensed":     lambda df: df[Col.RISK_LEVEL] == 0,
    "crypto":       lambda df: df[Col.SERVICE].fillna("")
                                  .str.contains(r"crypto|virtual asset|token|stable",
                                                case=False, regex=True),
    "uaePresent":   lambda df: df[Col.UAE_PRESENT] == True,  # noqa: E712
    "unlicensed":   lambda df: (df[Col.UNLICENSED_SIGNAL] == True) & (df[Col.LICENSE_SIGNAL] != True),  # noqa: E712 — exclude entities that are also confirmed licensed
}


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    """Apply a FilterState to a DataFrame. Returns a new frame."""
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if state.query:
        q = state.query.strip().lower()
        if q:
            searchable = [Col.BRAND, Col.SERVICE, Col.CLASSIFICATION,
                          Col.REGULATOR, Col.MATCHED_ENTITY]
            available = [c for c in searchable if c in df.columns]
            # Vectorized case-insensitive OR across all searchable columns
            text_mask = pd.Series(False, index=df.index)
            for c in available:
                text_mask |= df[c].fillna("").astype(str).str.lower().str.contains(
                    q, regex=False, na=False
                )
            mask &= text_mask

    if state.risk_levels:
        mask &= df[Col.RISK_LEVEL].isin(state.risk_levels)

    if state.regulators:
        mask &= df[Col.REGULATOR].isin(state.regulators)

    if state.services:
        mask &= df[Col.SERVICE].isin(state.services)

    if state.quick_chip and state.quick_chip in _QUICK_CHIP_FILTERS:
        mask &= _QUICK_CHIP_FILTERS[state.quick_chip](df)

    filtered = df.loc[mask]

    # Map friendly sort keys → column names
    sort_col = _resolve_sort_key(state.sort_key)
    if sort_col in filtered.columns:
        filtered = filtered.sort_values(
            by=sort_col,
            ascending=(state.sort_dir == "asc"),
            na_position="last",
            kind="stable",
        )

    return filtered


def _resolve_sort_key(key: str) -> str:
    aliases = {
        "risk_level": Col.RISK_LEVEL,
        "riskLevel": Col.RISK_LEVEL,
        "brand": Col.BRAND,
        "regulator": Col.REGULATOR,
        "service": Col.SERVICE,
    }
    return aliases.get(key, key)


def paginate(df: pd.DataFrame, page: int, page_size: int) -> pd.DataFrame:
    """Return a slice for page `page` (1-indexed)."""
    if df.empty:
        return df
    start = max(0, (page - 1) * page_size)
    return df.iloc[start:start + page_size]


# ---------------------------------------------------------------------------
# Filter option discovery
# ---------------------------------------------------------------------------
def build_filter_options(df: pd.DataFrame) -> dict[str, list]:
    """Unique sorted values for each filterable column."""
    def unique(col: str) -> list[str]:
        if col not in df.columns:
            return []
        return sorted(df[col].dropna().astype(str).unique().tolist())

    risk_levels = sorted(df[Col.RISK_LEVEL].dropna().astype(int).unique().tolist(),
                         reverse=True)

    return {
        "regulators": unique(Col.REGULATOR),
        "services":   unique(Col.SERVICE),
        "brands":     unique(Col.BRAND),
        "risk_levels": risk_levels,
    }


# ---------------------------------------------------------------------------
# Aggregations for insights charts
# ---------------------------------------------------------------------------
def risk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count per risk level, including zero-rows for missing tiers."""
    counts = df[Col.RISK_LEVEL].value_counts()
    rows = []
    for tier in RISK_BY_LEVEL.values():
        rows.append({
            "level": tier.level,
            "label": tier.label,
            "count": int(counts.get(tier.level, 0)),
            "color": tier.color,
        })
    return pd.DataFrame(rows).sort_values("level", ascending=False)


def regulator_breakdown(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Count per regulator, top N."""
    if df.empty or Col.REGULATOR not in df.columns:
        return pd.DataFrame(columns=["regulator", "count"])
    s = df[Col.REGULATOR].fillna("Unknown").value_counts().head(top_n)
    return s.reset_index().rename(columns={"index": "regulator",
                                           Col.REGULATOR: "regulator",
                                           "count": "count"})


def service_mix(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Count per service type, top N."""
    if df.empty or Col.SERVICE not in df.columns:
        return pd.DataFrame(columns=["service", "count"])
    s = df[Col.SERVICE].fillna("Unknown").value_counts().head(top_n)
    return s.reset_index().rename(columns={"index": "service",
                                           Col.SERVICE: "service",
                                           "count": "count"})


def priority_queue(df: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    """Top-risk rows for the overview 'Priority Review' section."""
    if df.empty:
        return df
    return (df[df[Col.RISK_LEVEL] >= HIGH_RISK_THRESHOLD]
            .sort_values(Col.RISK_LEVEL, ascending=False)
            .head(limit))


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Screening", index=False)
    return buffer.getvalue()
