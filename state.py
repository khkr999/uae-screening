"""Session state helpers + persistent storage."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATA_DIR
from models import FilterState

logger = logging.getLogger(__name__)

_PERSIST_FILE: Path = DATA_DIR / ".screening_workspace.json"

# Use only JSON-serializable types in defaults (no set)
_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "active_tab": "overview",
    "selected_entity_id": None,
    "filter_state": None,
    "workflow_overrides": {},
    "annotations": {},
    "watchlist": [],          # stored as list, converted to set only when needed
    "file_upload_nonce": 0,
}


# ── Disk helpers ──────────────────────────────────────────────────────────────
def _load_persisted() -> dict:
    try:
        if _PERSIST_FILE.exists():
            return json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not load workspace: %s", exc)
    return {}


def _save_persisted(session) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        wl = session.get("watchlist", [])
        if isinstance(wl, set):
            wl = list(wl)
        payload = {
            "workflow_overrides": dict(session.get("workflow_overrides", {})),
            "annotations":        dict(session.get("annotations", {})),
            "watchlist":          wl,
            "theme":              session.get("theme", "dark"),
        }
        _PERSIST_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Could not save workspace: %s", exc)


# ── Init ──────────────────────────────────────────────────────────────────────
def init_state(session) -> None:
    for key, value in _DEFAULTS.items():
        if key not in session:
            session[key] = value
    if session.get("filter_state") is None:
        session["filter_state"] = FilterState()

    # Ensure watchlist is always a list (never a set in session)
    wl = session.get("watchlist", [])
    if isinstance(wl, set):
        session["watchlist"] = list(wl)

    # Load persisted data once per browser session
    if not session.get("_workspace_loaded"):
        persisted = _load_persisted()
        if persisted.get("workflow_overrides"):
            session["workflow_overrides"] = persisted["workflow_overrides"]
        if persisted.get("annotations"):
            session["annotations"] = persisted["annotations"]
        if persisted.get("watchlist"):
            wl = persisted["watchlist"]
            session["watchlist"] = list(wl) if not isinstance(wl, list) else wl
        if persisted.get("theme"):
            session["theme"] = persisted["theme"]
        session["_workspace_loaded"] = True


# ── Generic ───────────────────────────────────────────────────────────────────
def get(session, key: str, default=None):
    return session.get(key, default)


def set_(session, key: str, value) -> None:
    session[key] = value


# ── Filter ────────────────────────────────────────────────────────────────────
def get_filter(session) -> FilterState:
    fs = session.get("filter_state")
    if fs is None:
        fs = FilterState()
        session["filter_state"] = fs
    return fs


def update_filter(session, **changes) -> FilterState:
    current = get_filter(session)
    updated = FilterState(**{**asdict(current), **changes})
    if "page" not in changes:
        updated.page = 1
    session["filter_state"] = updated
    return updated


# ── Theme ─────────────────────────────────────────────────────────────────────
def toggle_theme(session) -> None:
    session["theme"] = "light" if session.get("theme") == "dark" else "dark"
    _save_persisted(session)


# ── Entity selection ──────────────────────────────────────────────────────────
def set_selected(session, entity_id) -> None:
    session["selected_entity_id"] = entity_id


def get_selected(session):
    return session.get("selected_entity_id")


# ── Workflow ──────────────────────────────────────────────────────────────────
def set_workflow(session, entity_id: str, status: str) -> None:
    overrides = dict(session.get("workflow_overrides", {}))
    overrides[entity_id] = status
    session["workflow_overrides"] = overrides
    _save_persisted(session)


def get_workflow(session, entity_id: str) -> str:
    return session.get("workflow_overrides", {}).get(entity_id, "Open")


# ── Watchlist (stored as list, exposed as set for lookups) ───────────────────
def toggle_watchlist(session, entity_id: str) -> bool:
    wl = list(session.get("watchlist", []))
    if entity_id in wl:
        wl.remove(entity_id)
        in_wl = False
    else:
        wl.append(entity_id)
        in_wl = True
    session["watchlist"] = wl
    _save_persisted(session)
    return in_wl


def in_watchlist(session, entity_id: str) -> bool:
    return entity_id in session.get("watchlist", [])


def get_watchlist(session) -> set:
    return set(session.get("watchlist", []))


# ── Annotations ───────────────────────────────────────────────────────────────
def add_annotation(session, entity_id: str, text: str) -> None:
    notes = dict(session.get("annotations", {}))
    entry = {"text": text, "ts": datetime.now().strftime("%d %b %H:%M")}
    notes[entity_id] = [*notes.get(entity_id, []), entry]
    session["annotations"] = notes
    _save_persisted(session)


def get_annotations(session, entity_id: str) -> list:
    return session.get("annotations", {}).get(entity_id, [])


def get_all_annotations(session) -> dict:
    return dict(session.get("annotations", {}))


# ── Legacy compatibility (used by original add_annotation calls) ──────────────
def get_review_stats(session) -> dict[str, int]:
    overrides = session.get("workflow_overrides", {})
    counts: dict[str, int] = {"Open": 0, "In Review": 0, "Escalated": 0, "Cleared": 0}
    for status in overrides.values():
        if status in counts:
            counts[status] += 1
    return counts
