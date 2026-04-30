"""Session state helpers — local UI state + Supabase shared persistence."""
from __future__ import annotations
import logging
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
        # Restore login first so the user doesn't get logged out on refresh
        _restore_login(session)
        # Preserve UI-only state that must survive the Supabase pull
        _selected = session.get("selected_entity_id")
        _pull_shared_state(session)
        if _selected:
            session["selected_entity_id"] = _selected
        session["_workspace_loaded"] = True

def _restore_login(session) -> None:
    """
    Streamlit has no native cookies, so we store the last active session
    in Supabase. On refresh we restore whoever was last seen — suitable
    for a single-user-per-browser internal tool.
    """
    if session.get("current_user"):
        return  # already logged in this session
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
        logger.warning("Could not pull shared state from Supabase: %s", exc)

def get(session, key: str, default=None):
    return session.get(key, default)

def set_(session, key: str, value) -> None:
    session[key] = value

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

def toggle_theme(session) -> None:
    session["theme"] = "light" if session.get("theme") == "dark" else "dark"

def set_selected(session, entity_id) -> None:
    session["selected_entity_id"] = entity_id

def get_selected(session):
    return session.get("selected_entity_id")

def set_workflow(session, entity_id: str, status: str) -> None:
    overrides = dict(session.get("workflow_overrides", {}))
    overrides[entity_id] = status
    session["workflow_overrides"] = overrides
    db = _db()
    if db is None:
        return
    try:
        db.table("workflow_overrides").upsert({
            "entity_id": entity_id, "status": status,
            "updated_by": session.get("current_user", "Unknown"),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("Could not save workflow to Supabase: %s", exc)

def get_workflow(session, entity_id: str) -> str:
    return session.get("workflow_overrides", {}).get(entity_id, "Open")

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
                logger.warning("Could not remove from watchlist: %s", exc)
    else:
        wl.append(entity_id)
        in_wl = True
        if db:
            try:
                db.table("watchlist").upsert({
                    "entity_id": entity_id,
                    "added_by": session.get("current_user", "Unknown"),
                    "added_at": datetime.utcnow().isoformat(),
                }).execute()
            except Exception as exc:
                logger.warning("Could not add to watchlist: %s", exc)
    session["watchlist"] = wl
    return in_wl

def in_watchlist(session, entity_id: str) -> bool:
    return entity_id in session.get("watchlist", [])

def get_watchlist(session) -> set:
    return set(session.get("watchlist", []))

def add_annotation(session, entity_id: str, text: str) -> None:
    author = session.get("current_user", "Unknown")
    ts = datetime.now().strftime("%d %b %H:%M")
    notes = dict(session.get("annotations", {}))
    entry = {"text": text, "ts": ts, "author": author}
    notes[entity_id] = [*notes.get(entity_id, []), entry]
    session["annotations"] = notes
    db = _db()
    if db is None:
        return
    try:
        db.table("annotations").insert({
            "entity_id": entity_id, "author": author, "text": text,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("Could not save annotation to Supabase: %s", exc)

def delete_annotation(session, entity_id: str, index: int) -> None:
    """Delete a comment by index — removes from Supabase and local cache."""
    # Get fresh list from Supabase to get the correct row id
    db = _db()
    if db:
        try:
            rows = db.table("annotations").select("id").eq("entity_id", entity_id)                      .order("created_at").execute()
            if rows.data and index < len(rows.data):
                row_id = rows.data[index]["id"]
                db.table("annotations").delete().eq("id", row_id).execute()
        except Exception as exc:
            logger.warning("Could not delete annotation from Supabase: %s", exc)

    # Update local session cache
    notes = dict(session.get("annotations", {}))
    entries = list(notes.get(entity_id, []))
    if 0 <= index < len(entries):
        entries.pop(index)
    notes[entity_id] = entries
    session["annotations"] = notes


def get_annotations(session, entity_id: str) -> list:
    db = _db()
    if db:
        try:
            rows = db.table("annotations").select("*").eq("entity_id", entity_id).order("created_at").execute()
            return [{"text": r["text"], "ts": _fmt_ts(r["created_at"]), "author": r["author"]} for r in (rows.data or [])]
        except Exception as exc:
            logger.warning("Could not fetch annotations: %s", exc)
    return session.get("annotations", {}).get(entity_id, [])

def get_all_annotations(session) -> dict:
    return dict(session.get("annotations", {}))

def get_review_stats(session) -> dict[str, int]:
    db = _db()
    if db:
        try:
            rows = db.table("workflow_overrides").select("entity_id,status").execute()
            counts: dict[str, int] = {"Open": 0, "In Review": 0, "Escalated": 0, "Cleared": 0}
            overrides = {}
            for r in (rows.data or []):
                overrides[r["entity_id"]] = r["status"]
                if r["status"] in counts:
                    counts[r["status"]] += 1
            session["workflow_overrides"] = overrides
            return counts
        except Exception as exc:
            logger.warning("Could not fetch review stats: %s", exc)
    overrides = session.get("workflow_overrides", {})
    counts = {"Open": 0, "In Review": 0, "Escalated": 0, "Cleared": 0}
    for status in overrides.values():
        if status in counts:
            counts[status] += 1
    return counts
