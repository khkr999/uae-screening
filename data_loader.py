"""Data ingestion and validation for UAE screening Excel files."""

from __future__ import annotations

import glob
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from logic import apply_risk_logic, is_noise_brand, normalize_frame_text

try:
    import streamlit as st
except ImportError:  # pragma: no cover - enables reuse outside Streamlit
    st = None


logger = logging.getLogger(__name__)


def _identity_cache(*_args, **_kwargs):
    def decorator(func: Callable):
        return func

    return decorator


cache_data = st.cache_data if st else _identity_cache

DATA_DIR = Path(os.getenv("SCREENING_DATA_DIR", str(Path.home() / "Downloads" / "UAE_Screening")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {"Brand"}
TEXT_COLUMNS = [
    "Brand",
    "Classification",
    "Group",
    "Service Type",
    "Regulator Scope",
    "Alert Status",
    "Rationale",
    "Action Required",
    "Top Source URL",
    "Matched Entity (Register)",
    "Confidence",
]

FILE_TS_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2})")


class ScreeningDataError(Exception):
    """Raised when a screening file cannot be loaded safely."""


@dataclass(frozen=True)
class ScreeningFile:
    path: str
    name: str
    timestamp: datetime
    size_kb: int


@cache_data(show_spinner=False)
def list_screening_files() -> list[dict]:
    files: list[ScreeningFile] = []
    for path in glob.glob(str(DATA_DIR / "UAE_Screening_*.xlsx")):
        candidate = Path(path)
        match = FILE_TS_PATTERN.search(candidate.name)
        if not match:
            continue
        ts = datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M")
        files.append(
            ScreeningFile(
                path=str(candidate),
                name=candidate.name,
                timestamp=ts,
                size_kb=max(1, candidate.stat().st_size // 1024),
            )
        )
    ordered = sorted(files, key=lambda item: item.timestamp, reverse=True)
    return [item.__dict__ for item in ordered]


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ScreeningDataError(
            f"The uploaded file is missing required columns: {', '.join(sorted(missing))}."
        )


def _read_excel(path: str) -> pd.DataFrame:
    try:
        try:
            return pd.read_excel(path, sheet_name="📋 All Results")
        except ValueError:
            return pd.read_excel(path, sheet_name=0)
    except Exception as exc:  # pragma: no cover - defensive I/O error path
        logger.exception("Failed to read Excel file: %s", path)
        raise ScreeningDataError(f"Unable to read Excel file: {exc}") from exc


def standardize_screening_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df)
    cleaned = normalize_frame_text(df, TEXT_COLUMNS)
    cleaned = apply_risk_logic(cleaned)
    cleaned = cleaned[~cleaned["Brand"].map(is_noise_brand)].reset_index(drop=True)
    return cleaned


@cache_data(show_spinner=False)
def load_screening_data(path: str) -> pd.DataFrame:
    raw = _read_excel(path)
    return standardize_screening_dataframe(raw)


@cache_data(show_spinner=False)
def load_run_summary(path: str) -> dict:
    df = load_screening_data(path)
    return {
        "total": len(df),
        "critical_high": int((df["Risk Level"] >= 4).sum()) if "Risk Level" in df.columns else 0,
        "needs_review": int(((df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)).sum()) if "Risk Level" in df.columns else 0,
        "licensed": int((df["Risk Level"] == 0).sum()) if "Risk Level" in df.columns else 0,
        "new_entities": int((df.get("Alert Status", pd.Series(dtype=str)) == "🆕 NEW").sum()),
    }


def save_uploaded_file(uploaded_file) -> str:
    save_path = DATA_DIR / uploaded_file.name
    with open(save_path, "wb") as handle:
        handle.write(uploaded_file.getbuffer())
    logger.info("Saved uploaded file to %s", save_path)
    if st:
        st.cache_data.clear()
    return str(save_path)
