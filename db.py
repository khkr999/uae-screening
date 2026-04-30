"""Supabase client — single shared connection for the whole app."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_client = None

SUPABASE_URL = "https://lzlbiarbeepvgparmqar.supabase.co"
# Loaded from Streamlit secrets or environment variable
SUPABASE_KEY = None


def get_client():
    global _client, SUPABASE_KEY
    if _client is not None:
        return _client

    # Try Streamlit secrets first, then env var, then fallback
    key = SUPABASE_KEY
    if key is None:
        try:
            import streamlit as st
            key = st.secrets["SUPABASE_KEY"]
        except Exception:
            key = os.environ.get("SUPABASE_KEY", "")

    if not key:
        logger.error("SUPABASE_KEY not set — shared state will not work.")
        return None

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, key)
        logger.info("Supabase client connected.")
    except Exception as exc:
        logger.error("Could not connect to Supabase: %s", exc)
        return None

    return _client
