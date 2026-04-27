"""
Rule-based risk classification engine.

Rules are declarative (see `config.DEFAULT_RULES`). The engine evaluates them
in priority order and assigns the first match to each row — fully vectorized,
no Python-level row loops. Safe for 100k+ rows.

Use `reclassify(df)` to overwrite existing Risk Level / Classification with
engine output, or `apply_rules(df, rules)` to compute without overwriting.
"""
from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd

from config import ClassificationRule, Col, DEFAULT_RULES, RISK_BY_LEVEL
from exceptions import ClassificationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Predicate evaluation (vectorized)
# ---------------------------------------------------------------------------
def _evaluate_predicate(df: pd.DataFrame,
                        column: str,
                        op: str,
                        value: object) -> pd.Series:
    """Return a boolean Series of the same length as df for one condition."""
    if column not in df.columns:
        # Missing column → predicate is vacuously False (except falsy which is True)
        return pd.Series(op == "falsy", index=df.index)

    col = df[column]

    if op == "truthy":
        if col.dtype == bool:
            return col
        return col.notna() & (col.astype(str).str.strip() != "")
    if op == "falsy":
        if col.dtype == bool:
            return ~col
        return col.isna() | (col.astype(str).str.strip() == "")
    if op == "eq":
        return col == value
    if op == "neq":
        return col != value
    if op == "in":
        return col.isin(list(value))  # type: ignore[arg-type]
    if op == "gte":
        return pd.to_numeric(col, errors="coerce") >= value  # type: ignore[operator]
    if op == "lte":
        return pd.to_numeric(col, errors="coerce") <= value  # type: ignore[operator]

    raise ClassificationError(f"Unknown predicate op: {op!r}")


def _match_rule(df: pd.DataFrame, rule: ClassificationRule) -> pd.Series:
    """Return a boolean mask of rows matching ALL conditions in `rule`."""
    if not rule.when:
        return pd.Series(True, index=df.index)  # unconditional / fallback
    mask = pd.Series(True, index=df.index)
    for column, (op, value) in rule.when.items():
        mask &= _evaluate_predicate(df, column, op, value)
    return mask


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def apply_rules(df: pd.DataFrame,
                rules: Iterable[ClassificationRule] = DEFAULT_RULES
                ) -> pd.DataFrame:
    """
    Evaluate rules and return a DataFrame with two new columns:
        `_rule_risk_level`, `_rule_classification`

    Does NOT modify existing Risk Level / Classification — use `reclassify`
    if you want to overwrite.
    """
    if df.empty:
        return df.assign(_rule_risk_level=pd.Series(dtype=int),
                         _rule_classification=pd.Series(dtype=str))

    sorted_rules = sorted(rules, key=lambda r: r.priority)

    # Initialize with the fallback
    result_level = np.full(len(df), -1, dtype=int)
    result_label = np.full(len(df), "", dtype=object)

    remaining = np.ones(len(df), dtype=bool)
    for rule in sorted_rules:
        if not remaining.any():
            break
        mask = _match_rule(df, rule).to_numpy() & remaining
        if not mask.any():
            continue
        result_level[mask] = rule.risk_level
        result_label[mask] = rule.label
        remaining &= ~mask

    # Anything unmatched gets the lowest priority fallback (should be rare)
    if remaining.any():
        fallback = min(sorted_rules, key=lambda r: r.priority)
        result_level[remaining] = fallback.risk_level
        result_label[remaining] = fallback.label

    out = df.copy()
    out["_rule_risk_level"] = result_level
    out["_rule_classification"] = result_label
    return out


def reclassify(df: pd.DataFrame,
               rules: Iterable[ClassificationRule] = DEFAULT_RULES,
               *, overwrite: bool = True) -> pd.DataFrame:
    """
    Run rules and (optionally) overwrite Risk Level / Classification.

    Rows where the source file already supplied a Risk Level are *preserved*
    when overwrite=False.
    """
    scored = apply_rules(df, rules)
    if overwrite:
        scored[Col.RISK_LEVEL] = scored["_rule_risk_level"]
        scored[Col.CLASSIFICATION] = scored["_rule_classification"]
    else:
        missing = scored[Col.RISK_LEVEL].isna() | (scored[Col.RISK_LEVEL] < 0)
        scored.loc[missing, Col.RISK_LEVEL] = scored.loc[missing, "_rule_risk_level"]
        missing_label = scored[Col.CLASSIFICATION].isna() | \
                        (scored[Col.CLASSIFICATION].astype(str).str.len() == 0)
        scored.loc[missing_label, Col.CLASSIFICATION] = \
            scored.loc[missing_label, "_rule_classification"]

    # Add human-readable tier label for downstream UI
    scored["_risk_tier"] = scored[Col.RISK_LEVEL].map(
        lambda lvl: RISK_BY_LEVEL.get(int(lvl), RISK_BY_LEVEL[1]).label
    )
    return scored.drop(columns=["_rule_risk_level", "_rule_classification"])
