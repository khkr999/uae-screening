"""Reusable data shaping and state helpers for the screening dashboard."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd


DEFAULT_SESSION_STATE: dict[str, Any] = {
    "theme": "light",
    "workflow_log": {},
    "active_chip": None,
    "page": 1,
    "risk_filter": [],
    "reg_filter": [],
}


def init_session_state(session_state) -> None:
    for key, value in DEFAULT_SESSION_STATE.items():
        session_state.setdefault(key, value)


def metric_delta(current: int, previous: int) -> str | None:
    diff = current - previous
    if previous == 0 and current == 0:
        return None
    if previous == 0 and current != 0:
        return f"+{current} vs prior run"
    prefix = "+" if diff > 0 else ""
    return f"{prefix}{diff} vs prior run"


def compute_metrics(df: pd.DataFrame) -> dict[str, int]:
    alert_series = df["Alert Status"] if "Alert Status" in df.columns else pd.Series(dtype=str)
    return {
        "total": len(df),
        "critical": int((df["Risk Level"] >= 5).sum()),
        "high": int((df["Risk Level"] == 4).sum()),
        "needs_review": int(((df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)).sum()),
        "licensed": int((df["Risk Level"] == 0).sum()),
        "new_entities": int((alert_series == "🆕 NEW").sum()),
        "risk_up": int((alert_series == "📈 RISK INCREASED").sum()),
    }


def build_filter_options(df: pd.DataFrame) -> dict[str, list]:
    return {
        "brands": sorted(df["Brand"].dropna().unique().tolist()),
        "risk_levels": sorted(df["Risk Level"].dropna().unique().tolist(), reverse=True),
        "regulators": sorted(df["Regulator Scope"].dropna().unique().tolist()) if "Regulator Scope" in df.columns else [],
    }


def apply_filters(
    df: pd.DataFrame,
    selected_brand: str | None,
    risk_filter: list[int],
    reg_filter: list[str],
    active_chip: str | None,
    sort_by: str,
) -> pd.DataFrame:
    filtered = df.copy()
    if selected_brand:
        filtered = filtered[filtered["Brand"] == selected_brand]
    if risk_filter:
        filtered = filtered[filtered["Risk Level"].isin(risk_filter)]
    if reg_filter:
        filtered = filtered[filtered["Regulator Scope"].isin(reg_filter)]

    if active_chip == "high":
        filtered = filtered[filtered["Risk Level"] >= 4]
    elif active_chip == "new" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "🆕 NEW"]
    elif active_chip == "riskup" and "Alert Status" in filtered.columns:
        filtered = filtered[filtered["Alert Status"] == "📈 RISK INCREASED"]
    elif active_chip == "licensed":
        filtered = filtered[filtered["Risk Level"] == 0]
    elif active_chip == "va":
        va_mask = filtered["Regulator Scope"].astype(str).str.contains("VA|VASP|CRYPTO", case=False, na=False)
        if "Service Type" in filtered.columns:
            va_mask |= filtered["Service Type"].astype(str).str.contains("crypto|virtual asset|token", case=False, na=False)
        filtered = filtered[va_mask]

    sort_map = {
        "Risk ↓": ("Risk Level", False),
        "Risk ↑": ("Risk Level", True),
        "Name A–Z": ("Brand", True),
        "Confidence ↓": ("Confidence", False),
    }
    column, ascending = sort_map.get(sort_by, ("Risk Level", False))
    if column in filtered.columns:
        filtered = filtered.sort_values(column, ascending=ascending, kind="stable")
    return filtered.reset_index(drop=True)


def paginate(df: pd.DataFrame, page: int, per_page: int = 25) -> tuple[pd.DataFrame, int]:
    total_pages = max(1, (len(df) + per_page - 1) // per_page)
    safe_page = min(max(page, 1), total_pages)
    start = (safe_page - 1) * per_page
    return df.iloc[start:start + per_page], total_pages


def build_active_filters(
    selected_brand: str | None,
    risk_filter: list[int],
    reg_filter: list[str],
    active_chip: str | None,
    risk_label_resolver,
    chip_label_resolver,
) -> list[str]:
    filters: list[str] = []
    if selected_brand:
        filters.append(f'"{selected_brand}"')
    if risk_filter:
        filters.extend(risk_label_resolver(value) for value in risk_filter)
    if reg_filter:
        filters.extend(reg_filter)
    if active_chip:
        filters.append(chip_label_resolver(active_chip))
    return filters


def dominant_value(df: pd.DataFrame, column: str, default: str = "N/A") -> str:
    if column not in df.columns:
        return default
    values = df[column].dropna()
    if values.empty:
        return default
    return str(values.value_counts().idxmax())


def build_trend_dataframe(files: list[dict], load_data_fn) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for file_info in files[:10]:
        try:
            df = load_data_fn(file_info["path"])
        except Exception:
            continue
        rows.append(
            {
                "Run": file_info["timestamp"].strftime("%m/%d %H:%M"),
                "High/Critical": int((df["Risk Level"] >= 4).sum()),
                "Needs Review": int(((df["Risk Level"] >= 2) & (df["Risk Level"] <= 3)).sum()),
                "Licensed": int((df["Risk Level"] == 0).sum()),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).iloc[::-1]


def classification_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if "Classification" not in df.columns:
        return pd.DataFrame()
    result = df["Classification"].value_counts().reset_index()
    result.columns = ["Classification", "Count"]
    result["% of Total"] = (result["Count"] / max(len(df), 1) * 100).round(1).astype(str) + "%"
    return result


def export_buffers(df: pd.DataFrame) -> tuple[bytes, bytes | None]:
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Filtered")
        excel_bytes = excel_buffer.getvalue()
    except Exception:
        excel_bytes = None
    return csv_bytes, excel_bytes


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
