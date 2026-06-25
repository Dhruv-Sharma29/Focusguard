"""Shared fixtures for FocusGuard tests.

Uses an in-memory unencrypted SQLite database for all tests
to avoid touching the real database or requiring sqlcipher.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_db(tmp_path):
    """Replace the database with a temporary unencrypted SQLite file.

    This fixture patches the connection module so tests never touch
    the real database or require sqlcipher.
    """
    db_path = tmp_path / "test_focus.db"
    _local = threading.local()

    def _get_test_connection() -> sqlite3.Connection:
        if hasattr(_local, "connection") and _local.connection is not None:
            return _local.connection
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        _local.connection = conn
        return conn

    with patch("focusguard.db.connection._get_connection", _get_test_connection):
        # Initialize schema
        from focusguard.db.models import init_db
        init_db()
        yield db_path

    # Cleanup
    if hasattr(_local, "connection") and _local.connection:
        _local.connection.close()


@pytest.fixture
def sample_activity(mock_db):
    """Insert sample activity data for testing."""
    from focusguard.db.queries import log_activity

    entries = [
        ("VS Code", "main.py — project", "coding", 60, False),
        ("VS Code", "utils.py — project", "coding", 60, False),
        ("VS Code", "test_main.py — project", "coding", 60, False),
        ("Chrome", "Stack Overflow", "browser", 60, False),
        ("Chrome", "YouTube - Music", "entertainment", 60, False),
        ("Chrome", "YouTube - Tutorial", "entertainment", 60, False),
        ("Slack", "team-general", "communication", 60, False),
        ("Terminal", "zsh", "coding", 60, False),
        ("Unknown", None, "other", 60, True),  # idle
    ]

    ids = []
    for app, title, cat, dur, idle in entries:
        row_id = log_activity(app, title, cat, dur, idle)
        ids.append(row_id)

    return ids


@pytest.fixture
def sample_goals(mock_db):
    """Insert sample goals for testing."""
    from focusguard.db.queries import add_goal

    g1 = add_goal("Build authentication system")
    g2 = add_goal("Write unit tests")
    return [g1, g2]
