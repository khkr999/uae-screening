"""
Session state management.

Single place where Streamlit's session_state is mutated. Keeps defaults,
getters, and setters in one layer so UI code doesn't sprinkle
`st.session_state.*` everywhere.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from models import FilterState


_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "active_tab": "overview",
    "selected_entity_id": None,
    "filter_state": None,                  # FilterState
    "workflow_overrides": {},              # id → WorkflowStatus
    "annotations": {},                     # id → list[str]
    "file_upload_nonce": 0,
}


def init_state(session) -> None:
    """Populate defaults on first run. Idempotent."""
    for key, value in _DEFAULTS.items():
        if key not in session:
            session[key] = value
    if session.get("filter_state") is None:
        session["filter_state"] = FilterState()


# ---------------------------------------------------------------------------
# Generic getters / setters
# ---------------------------------------------------------------------------
def get(session, key: str, default: Any = None) -> Any:
    return session.get(key, default)


def set_(session, key: str, value: Any) -> None:
    session[key] = value


# ---------------------------------------------------------------------------
# Typed helpers
# ---------------------------------------------------------------------------
def get_filter(session) -> FilterState:
    fs = session.get("filter_state")
    if fs is None:
        fs = FilterState()
        session["filter_state"] = fs
    return fs


def update_filter(session, **changes: Any) -> FilterState:
    current = get_filter(session)
    updated = FilterState(**{**asdict(current), **changes})
    # Any filter change resets to page 1 unless explicitly asked
    if "page" not in changes:
        updated.page = 1
    session["filter_state"] = updated
    return updated


def toggle_theme(session) -> None:
    session["theme"] = "light" if session.get("theme") == "dark" else "dark"


def set_selected(session, entity_id: str | None) -> None:
    session["selected_entity_id"] = entity_id


def get_selected(session) -> str | None:
    return session.get("selected_entity_id")


def set_workflow(session, entity_id: str, status: str) -> None:
    overrides = dict(session.get("workflow_overrides", {}))
    overrides[entity_id] = status
    session["workflow_overrides"] = overrides


def add_annotation(session, entity_id: str, note: str) -> None:
    notes = dict(session.get("annotations", {}))
    notes.setdefault(entity_id, [])
    notes[entity_id] = [*notes[entity_id], note]
    session["annotations"] = notes
