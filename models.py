"""
Domain models.

Kept as plain dataclasses (no pydantic dependency required) but structured
so they can be swapped for pydantic BaseModel later when exposing a FastAPI
layer — field names align with Col.* and the Index.tsx ScreeningEntity shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


WorkflowStatus = Literal["Open", "In Review", "Escalated", "Cleared"]
AlertStatus = Literal["NEW", "RISK_INCREASED", "UNCHANGED", "RESOLVED"]


@dataclass
class ScreeningEntity:
    """A single row in the screening dataset."""
    id: str
    brand: str
    service_type: str
    classification: str
    risk_level: int
    regulator_scope: str
    group: str | None = None
    action: str | None = None
    confidence: str | None = None
    matched_entity: str | None = None
    register_category: str | None = None
    rationale: str | None = None
    uae_present: bool = False
    license_signal: bool = False
    unlicensed_signal: bool = False
    source_url: str | None = None
    snippet: str | None = None
    source: str | None = None

    # Mutable operational fields
    workflow_status: WorkflowStatus = "Open"
    alert_status: AlertStatus = "UNCHANGED"
    annotations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningRun:
    """Metadata for a single screening file/run."""
    path: Path
    name: str
    timestamp: datetime
    size_kb: int
    row_count: int = 0

    def display_label(self) -> str:
        return f"{self.timestamp.strftime('%d %b %Y, %H:%M')}  ·  {self.size_kb} KB"


@dataclass
class RunMetrics:
    """Aggregated KPIs for a run — mirrors Index.tsx KPI section."""
    total: int = 0
    licensed: int = 0
    low: int = 0
    monitor: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    needs_review: int = 0           # monitor + medium
    critical_high: int = 0          # high + critical
    new_entities: int = 0
    risk_increased: int = 0
    top_regulator: str = "—"
    top_service: str = "—"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    column: str | None = None


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


@dataclass
class FilterState:
    """Mirrors the FilterState in Index.tsx."""
    query: str = ""
    risk_levels: list[int] = field(default_factory=list)
    regulators: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    quick_chip: str | None = None           # "highCritical" | "new" | etc.
    sort_key: str = "risk_level"
    sort_dir: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = 12
