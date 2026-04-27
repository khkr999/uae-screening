from __future__ import annotations
import hashlib, logging, re
from datetime import datetime
from pathlib import Path
from typing import IO
import pandas as pd
from config import (COLUMN_ALIASES, Col, DATA_DIR, DEFAULT_SHEET, FILE_GLOB, NULL_TOKENS, OPTIONAL_COLUMNS, REQUIRED_COLUMNS, VALIDATION)
from exceptions import DataLoadError, ValidationError
from models import ScreeningRun, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)

try:
    import streamlit as st
    _cache_data = st.cache_data
except ImportError:
    def _cache_data(*args, **kwargs):
        def decorator(fn): return fn
        return decorator if not callable(args[0] if args else None) else args[0]

_TIMESTAMP_RX = re.compile(r"(\d{4}-\d{2}-\d{2}[_\-\s]\d{2}[-:]\d{2})")

def list_screening_files(directory: Path = DATA_DIR) -> list[ScreeningRun]:
    if not directory.exists(): return []
    runs = []
    for p in directory.glob(FILE_GLOB):
        try:
            stat = p.stat()
            runs.append(ScreeningRun(path=p, name=p.name, timestamp=_parse_timestamp(p.name, stat.st_mtime), size_kb=max(1, stat.st_size // 1024)))
        except OSError as err:
            logger.warning("Skipping %s: %s", p, err)
    runs.sort(key=lambda r: r.timestamp, reverse=True)
    return runs

def _parse_timestamp(filename: str, fallback: float) -> datetime:
    m = _TIMESTAMP_RX.search(filename)
    if m:
        raw = m.group(1).replace("_", " ").replace("-", ":", 2)
        for fmt in ("%Y:%m:%d %H:%M", "%Y:%m:%d %H-%M"):
            try: return datetime.strptime(raw, fmt)
            except ValueError: continue
    return datetime.fromtimestamp(fallback)

def save_uploaded_file(file_obj: IO[bytes], *, directory: Path = DATA_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    name = getattr(file_obj, "name", f"upload_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    if not name.lower().endswith(".xlsx"):
        raise DataLoadError("Only .xlsx files are supported.", user_message="Only Excel (.xlsx) files are supported.")
    dest = directory / Path(name).name
    data = file_obj.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > VALIDATION.max_file_size_mb:
        raise DataLoadError(f"Upload too large: {size_mb:.1f} MB", user_message=f"File is too large ({size_mb:.1f} MB). Max is {VALIDATION.max_file_size_mb} MB.")
    dest.write_bytes(data)
    return dest

def _file_signature(path: Path) -> str:
    stat = path.stat()
    return hashlib.md5(f"{path}|{stat.st_mtime}|{stat.st_size}".encode()).hexdigest()

@_cache_data(show_spinner=False)
def _read_excel_cached(path_str: str, signature: str) -> pd.DataFrame:
    del signature
    path = Path(path_str)
    try:
        xl = pd.ExcelFile(path)
        sheet = DEFAULT_SHEET if DEFAULT_SHEET in xl.sheet_names else xl.sheet_names[0]
        return pd.read_excel(xl, sheet_name=sheet, dtype=object)
    except Exception as exc:
        raise DataLoadError(f"Could not read {path.name}: {exc}", user_message=f"Could not read file '{path.name}'.") from exc

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for c in df.columns:
        key = str(c).strip().lower().replace("  ", " ")
        if key in COLUMN_ALIASES: rename_map[c] = COLUMN_ALIASES[key]
    if rename_map: df = df.rename(columns=rename_map)
    return df

def _coerce_bool(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    return s.isin({"yes", "y", "true", "t", "1"})

def _coerce_risk_level(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(1).clip(lower=0, upper=5).astype(int)

def _clean_strings(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns: continue
        s = df[c].astype(str).str.strip()
        df[c] = s.mask(s.str.lower().isin(NULL_TOKENS), other=None)
    return df

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_columns(df).copy()
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns: df[col] = None
    string_cols = [c for c in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS) if c in df.columns and c != Col.RISK_LEVEL]
    df = _clean_strings(df, string_cols)
    df[Col.RISK_LEVEL] = _coerce_risk_level(df[Col.RISK_LEVEL])
    for bool_col in (Col.UAE_PRESENT, Col.LICENSE_SIGNAL, Col.UNLICENSED_SIGNAL):
        df[bool_col] = _coerce_bool(df[bool_col])
    df = df[df[Col.BRAND].notna() & (df[Col.BRAND].astype(str).str.len() > 0)]
    df = (df.sort_values(Col.RISK_LEVEL, ascending=False)
            .drop_duplicates(subset=[Col.BRAND, Col.REGULATOR], keep="first")
            .reset_index(drop=True))
    df["id"] = df[Col.BRAND].astype(str) + "|" + df[Col.REGULATOR].fillna("").astype(str)
    return df

def validate(df: pd.DataFrame) -> ValidationResult:
    issues = []
    for c in REQUIRED_COLUMNS:
        if c not in df.columns:
            issues.append(ValidationIssue(severity="error", code="missing_required_column", message=f"Required column missing: '{c}'", column=c))
    if len(df) == 0:
        issues.append(ValidationIssue(severity="error", code="empty_file", message="File contains no data rows."))
    return ValidationResult(ok=not any(i.severity == "error" for i in issues), issues=issues)

def load_screening_data(path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise DataLoadError("File does not exist.", user_message="The selected screening file is no longer available.")
    raw = _read_excel_cached(str(path), _file_signature(path))
    raw = _normalize_columns(raw)
    result = validate(raw)
    if not result.ok:
        err_msgs = "; ".join(i.message for i in result.errors)
        raise ValidationError(err_msgs, user_message=f"This file cannot be used: {err_msgs}")
    return normalize(raw)
