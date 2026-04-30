"""Supabase client — single shared connection for the whole app."""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)
_client = None

SUPABASE_URL = "https://lzlbiarbeepvgparmqar.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6bGJpYXJiZWVwdmdwYXJtcWFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NTA0NzIsImV4cCI6MjA5MzAyNjQ3Mn0.sYisU80vBgOP_ZCP5czaGPQ8OZ9CWo6lu14na31BtNE"


def get_client():
    global _client
    if _client is not None:
        return _client

    # Key order: Streamlit secrets → env var → hardcoded fallback
    key = None
    try:
        import streamlit as st
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass
    if not key:
        key = os.environ.get("SUPABASE_KEY")
    if not key:
        key = SUPABASE_ANON_KEY

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, key)
        logger.info("Supabase connected.")
    except Exception as exc:
        logger.error("Supabase connection failed: %s", exc)
        return None

    return _client
