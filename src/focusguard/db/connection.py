"""Encrypted SQLite database connection manager.

Uses sqlcipher3 for transparent AES-256 encryption at rest.
The encryption key is stored in the OS keyring (never on disk).
Falls back to standard sqlite3 if sqlcipher3 is not available
(with a warning — unencrypted mode is for development only).
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from collections.abc import Generator
from typing import Any

from rich.console import Console

from focusguard.config import DB_FILE, ensure_dirs
from focusguard.security.crypto import get_or_create_db_key

console = Console(stderr=True)

# Try to use sqlcipher for encrypted database
try:
    from sqlcipher3 import dbapi2 as sqlcipher  # type: ignore[import-untyped]

    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False

# Thread-local storage for connections (one connection per thread)
_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Get or create a database connection for the current thread.

    Returns:
        A sqlite3-compatible connection object.
    """
    if hasattr(_local, "connection") and _local.connection is not None:
        return _local.connection  # type: ignore[no-any-return]

    ensure_dirs()
    db_path = str(DB_FILE)

    if HAS_SQLCIPHER:
        conn = sqlcipher.connect(db_path)
        key = get_or_create_db_key()
        conn.execute(f"PRAGMA key = '{key}';")
    else:
        console.print(
            "[yellow]⚠ sqlcipher3 not installed — database is NOT encrypted.[/yellow]"
        )
        console.print(
            "[dim]Install with: pip install sqlcipher3-binary[/dim]"
        )
        conn = sqlite3.connect(db_path)

    # Enable WAL mode for concurrent reads during report generation
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    # Return rows as sqlite3.Row for dict-like access
    conn.row_factory = sqlite3.Row

    _local.connection = conn
    return conn


@contextlib.contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database access.

    Yields:
        An active database connection. Auto-commits on success,
        rolls back on exception.

    Usage:
        with get_db() as db:
            db.execute("INSERT INTO ...")
    """
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    """Execute a SQL statement and commit.

    Args:
        sql: SQL string (use ? placeholders for params).
        params: Tuple of parameters for the query.

    Returns:
        The cursor after execution.
    """
    conn = _get_connection()
    cursor = conn.execute(sql, params)
    conn.commit()
    return cursor


def query(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    """Execute a SELECT query and return all rows.

    Args:
        sql: SQL SELECT string.
        params: Tuple of parameters.

    Returns:
        List of sqlite3.Row objects (dict-like access).
    """
    conn = _get_connection()
    return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    """Execute a SELECT query and return the first row.

    Args:
        sql: SQL SELECT string.
        params: Tuple of parameters.

    Returns:
        A single sqlite3.Row, or None if no results.
    """
    conn = _get_connection()
    return conn.execute(sql, params).fetchone()


def close() -> None:
    """Close the database connection for the current thread."""
    if hasattr(_local, "connection") and _local.connection is not None:
        _local.connection.close()
        _local.connection = None
