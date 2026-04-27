"""
Business-logic orchestration layer.

This is the ONLY layer that UI code (and, later, FastAPI endpoints) should
import for data operations. It composes data_loader, classification, and
processing into coherent use-cases.

Every function here takes primitives or dataclasses and returns primitives
or dataclasses — no Streamlit objects — so the same code powers both the
dashboard and a future REST API.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

from classification import reclassify
from config import Col
from data_loader import (
    list_screening_files, load_screening_data, save_uploaded_file,
)
from exceptions import DataLoadError, ValidationError
from models import FilterState, RunMetrics, ScreeningRun
from processing import (
    apply_filters, build_filter_options, compute_metrics, paginate,
    priority_queue, regulator_breakdown, risk_distribution, service_mix,
    to_csv_bytes, to_excel_bytes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def list_runs() -> list[ScreeningRun]:
    return list_screening_files()


def load_run(path: Path | str, *, run_classifier: bool = False) -> pd.DataFrame:
    """
    Load a single run. If `run_classifier` is True, the rule-based engine
    overwrites the file's Risk Level / Classification columns. Otherwise
    the file values are preserved (engine output is still available via
    the `_risk_tier` column).
    """
    df = load_screening_data(path)
    df = reclassify(df, overwrite=run_classifier)
    return df


def save_upload(file_obj) -> Path:
    return save_uploaded_file(file_obj)


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------
def get_metrics(df: pd.DataFrame,
                previous: pd.DataFrame | None = None) -> RunMetrics:
    return compute_metrics(df, previous=previous)


def get_page(df: pd.DataFrame, state: FilterState) -> tuple[pd.DataFrame, int]:
    """Return (page_slice, total_matching_rows)."""
    filtered = apply_filters(df, state)
    total = len(filtered)
    return paginate(filtered, state.page, state.page_size), total


def get_filter_options(df: pd.DataFrame) -> dict:
    return build_filter_options(df)


def get_entity(df: pd.DataFrame, entity_id: str) -> pd.Series | None:
    if "id" not in df.columns:
        return None
    hits = df[df["id"] == entity_id]
    return None if hits.empty else hits.iloc[0]


# ---------------------------------------------------------------------------
# Insights (thin pass-through but centralized so callers have one import)
# ---------------------------------------------------------------------------
def get_insights(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "risk_distribution": risk_distribution(df),
        "regulators": regulator_breakdown(df),
        "services": service_mix(df),
        "priority": priority_queue(df),
    }


# ---------------------------------------------------------------------------
# Deltas against previous run
# ---------------------------------------------------------------------------
def find_previous_run(runs: list[ScreeningRun],
                      current: Path) -> ScreeningRun | None:
    """Return the run immediately older than `current`."""
    current = Path(current)
    older = [r for r in runs if r.path != current and r.timestamp]
    older.sort(key=lambda r: r.timestamp, reverse=True)
    # `runs` is newest-first; find current and return the next one
    try:
        idx = next(i for i, r in enumerate(runs) if r.path == current)
    except StopIteration:
        return None
    return runs[idx + 1] if idx + 1 < len(runs) else None


def load_previous_df(runs: list[ScreeningRun],
                     current: Path) -> pd.DataFrame | None:
    prev = find_previous_run(runs, current)
    if prev is None:
        return None
    try:
        return load_screening_data(prev.path)
    except (DataLoadError, ValidationError) as exc:
        logger.warning("Could not load previous run %s: %s", prev.name, exc)
        return None


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
def export(df: pd.DataFrame, fmt: str = "csv") -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime_type)."""
    if fmt == "csv":
        return to_csv_bytes(df), "screening_export.csv", "text/csv"
    if fmt == "xlsx":
        return (to_excel_bytes(df), "screening_export.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    raise ValueError(f"Unsupported export format: {fmt}")
