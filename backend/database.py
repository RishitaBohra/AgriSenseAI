"""
database.py  —  MongoDB connection, isolated from FastAPI app
═════════════════════════════════════════════════════════════

WHY THIS IS A SEPARATE FILE:
  Old code mixed MongoClient() directly inside main.py.
  Problems:
    1. Credentials were next to route handlers — easy to accidentally log them
    2. Can't mock the DB in unit tests without importing the whole app
    3. Connection was made at import time with no error handling

  New design:
    - Credentials come from env vars only (never hardcoded)
    - get_db() is called lazily (first real request, not at import)
    - If Mongo is unreachable we log a warning but don't crash the API

Interview talking points:
  - Lazy initialisation: the DB client is created once on first call,
    then reused (MongoDB driver is thread-safe, connection-pooled)
  - Graceful degradation: API still returns decisions even if DB is down;
    we just skip the write and log a warning
  - Separation of concerns: database logic is testable independently
"""

import os
import logging

log = logging.getLogger(__name__)

# Module-level cache — created once, reused forever
_client = None
_db     = None


def get_db():
    """
    Return the agrisense_ai database handle.
    Returns None if MONGO_URL is not set or connection fails.
    Callers should handle None gracefully (skip write, log warning).
    """
    global _client, _db
    if _db is not None:
        return _db

    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        log.warning("MONGO_URL not set — running without database persistence.")
        return None

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure

        _client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")   # fast connectivity check
        _db = _client["agrisense_ai"]
        log.info("MongoDB connected.")
        return _db

    except Exception as e:
        log.error("MongoDB connection failed (%s) — running without DB.", e)
        return None


def save_decision(commodity: str, state: str, result: dict) -> bool:
    """
    Persist a decision result to the 'decisions' collection.
    Returns True on success, False on any failure.
    """
    db = get_db()
    if db is None:
        return False

    try:
        db["decisions"].insert_one({
            "commodity": commodity,
            "state"    : state,
            **result,
        })
        return True
    except Exception as e:
        log.error("Failed to save decision to MongoDB: %s", e)
        return False