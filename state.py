"""Session state helpers — local UI state + Supabase shared persistence.

Performance strategy:
- All reads come from local session cache (instant)
- Supabase is queried ONCE on login (_pull_shared_state)
- Writes go to Supabase AND update local cache immediately
- A lightweight TTL refresh runs max once every 30 seconds
  so teammates' changes appear without slowing down clicks
"""
from __future__ import annotations
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any
from models import FilterState

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "theme": "dark", "active_tab": "overview", "selected_entity_id": None,
    "filter_state": None, "workflow_overrides": {}, "annotations": {},
    "watchlist": [], "file_upload_nonce": 0, "current_user": "",
}

_REFRESH_TTL = 30  # seconds between background Supabase refreshes


def _db():
    try:
        from db import get_client
        return get_client()
    except Exception:
        return None


def _fmt_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M")
    except Exception:
        return iso[:16]


# ── Init ──────────────────────────────────────────────────────────────────────
def init_state(session) -> None:
    for key, value in _DEFAULTS.items():
        if key not in session:
            session[key] = value
    if session.get("filter_state") is None:
        session["filter_state"] = FilterState()
    wl = session.get("watchlist", [])
    if isinstance(wl, set):
        session["watchlist"] = list(wl)

    if not session.get("_workspace_loaded"):
        _restore_login(session)
        _selected = session.get("selected_entity_id")
        _pull_shared_state(session)
        if _selected:
            session["selected_entity_id"] = _selected
        session["_workspace_loaded"] = True
        session["_last_refresh"] = time.time()
    else:
        # TTL-based background refresh — runs at most once per 30s
        _maybe_refresh(session)


def _maybe_refresh(session) -> None:
    """Silently refresh shared state from Supabase at most once per TTL."""
    last = session.get("_last_refresh", 0)
    if time.time() - last < _REFRESH_TTL:
        return
    try:
        db = _db()
        if db is None:
            return
        # Only refresh workflow and watchlist — annotations fetched on-demand
        rows = db.table("workflow_overrides").select("entity_id,status").execute()
        session["workflow_overrides"] = {r["entity_id"]: r["status"] for r in (rows.data or [])}
        rows = db.table("watchlist").select("entity_id").execute()
        session["watchlist"] = [r["entity_id"] for r in (rows.data or [])]
        session["_last_refresh"] = time.time()
    except Exception as exc:
        logger.warning("Background refresh failed: %s", exc)


def _restore_login(session) -> None:
    if session.get("current_user"):
        return
    db = _db()
    if db is None:
        return
    try:
        rows = db.table("sessions").select("username,is_owner") \
                 .order("last_seen", desc=True).limit(1).execute()
        if rows.data:
            r = rows.data[0]
            session["current_user"] = r["username"]
            session["is_owner"]     = bool(r["is_owner"])
    except Exception as exc:
        logger.warning("Could not restore login: %s", exc)


def _pull_shared_state(session) -> None:
    """Full pull from Supabase — only on first load."""
    db = _db()
    if db is None:
        return
    try:
        rows = db.table("workflow_overrides").select("entity_id,status").execute()
        session["workflow_overrides"] = {r["entity_id"]: r["status"] for r in (rows.data or [])}
        rows = db.table("watchlist").select("entity_id").execute()
        session["watchlist"] = [r["entity_id"] for r in (rows.data or [])]
        rows = db.table("annotations").select("*").order("created_at").execute()
        annotations: dict[str, list] = {}
        for r in (rows.data or []):
            eid = r["entity_id"]
            annotations.setdefault(eid, []).append({
                "text": r["text"], "ts": _fmt_ts(r["created_at"]), "author": r["author"],
            })
        session["annotations"] = annotations
    except Exception as exc:
        logger.warning("Could not pull shared state: %s", exc)


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


# ── Entity selection ──────────────────────────────────────────────────────────
def set_selected(session, entity_id) -> None:
    session["selected_entity_id"] = entity_id

def get_selected(session):
    return session.get("selected_entity_id")


# ── Workflow — write-through cache ────────────────────────────────────────────
def set_workflow(session, entity_id: str, status: str) -> None:
    # Update local cache FIRST so UI reflects change immediately
    overrides = dict(session.get("workflow_overrides", {}))
    overrides[entity_id] = status
    session["workflow_overrides"] = overrides

    # Write to Supabase in background (non-blocking from user's perspective)
    db = _db()
    if db is None:
        return
    try:
        db.table("workflow_overrides").upsert({
            "entity_id":  entity_id,
            "status":     status,
            "updated_by": session.get("current_user", "Unknown"),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("Could not save workflow: %s", exc)

def get_workflow(session, entity_id: str) -> str:
    # Always reads from local cache — instant, no network call
    return session.get("workflow_overrides", {}).get(entity_id, "Open")


# ── Watchlist — write-through cache ──────────────────────────────────────────
def toggle_watchlist(session, entity_id: str) -> bool:
    wl = list(session.get("watchlist", []))
    db = _db()

    if entity_id in wl:
        wl.remove(entity_id)
        in_wl = False
        if db:
            try:
                db.table("watchlist").delete().eq("entity_id", entity_id).execute()
            except Exception as exc:
                logger.warning("Could not remove watchlist: %s", exc)
    else:
        wl.append(entity_id)
        in_wl = True
        if db:
            try:
                db.table("watchlist").upsert({
                    "entity_id": entity_id,
                    "added_by":  session.get("current_user", "Unknown"),
                    "added_at":  datetime.utcnow().isoformat(),
                }).execute()
            except Exception as exc:
                logger.warning("Could not add watchlist: %s", exc)

    session["watchlist"] = wl
    return in_wl

def in_watchlist(session, entity_id: str) -> bool:
    return entity_id in session.get("watchlist", [])

def get_watchlist(session) -> set:
    return set(session.get("watchlist", []))


# ── Annotations — write-through cache ────────────────────────────────────────
def add_annotation(session, entity_id: str, text: str) -> None:
    author = session.get("current_user", "Unknown")
    ts     = datetime.now().strftime("%d %b %H:%M")

    # Update local cache immediately
    notes = dict(session.get("annotations", {}))
    entry = {"text": text, "ts": ts, "author": author}
    notes[entity_id] = [*notes.get(entity_id, []), entry]
    session["annotations"] = notes

    db = _db()
    if db is None:
        return
    try:
        db.table("annotations").insert({
            "entity_id":  entity_id,
            "author":     author,
            "text":       text,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("Could not save annotation: %s", exc)


def delete_annotation(session, entity_id: str, index: int) -> None:
    # Delete from Supabase by UUID
    db = _db()
    if db:
        try:
            rows = db.table("annotations").select("id").eq("entity_id", entity_id) \
                     .order("created_at").execute()
            if rows.data and index < len(rows.data):
                db.table("annotations").delete().eq("id", rows.data[index]["id"]).execute()
        except Exception as exc:
            logger.warning("Could not delete annotation: %s", exc)

    # Update local cache
    notes = dict(session.get("annotations", {}))
    entries = list(notes.get(entity_id, []))
    if 0 <= index < len(entries):
        entries.pop(index)
    notes[entity_id] = entries
    session["annotations"] = notes


def get_annotations(session, entity_id: str) -> list:
    """Read from local cache — fast. Supabase sync happens via TTL refresh."""
    return session.get("annotations", {}).get(entity_id, [])


def get_all_annotations(session) -> dict:
    return dict(session.get("annotations", {}))


# ── Review stats — reads from local cache ─────────────────────────────────────
def get_review_stats(session) -> dict[str, int]:
    """Read workflow stats from local session cache — no Supabase call."""
    overrides = session.get("workflow_overrides", {})
    counts: dict[str, int] = {"Open": 0, "In Review": 0, "Escalated": 0, "Cleared": 0}
    for status in overrides.values():
        if status in counts:
            counts[status] += 1
    return counts
