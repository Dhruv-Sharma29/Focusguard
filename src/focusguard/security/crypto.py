"""Database encryption key management.

On first run, generates a random 32-byte hex key and stores it
in the OS keyring via python-keyring. On subsequent runs, retrieves
the existing key. The key is never written to disk in plaintext.
"""

from __future__ import annotations

import secrets

from focusguard.security.keyring_store import get_secret, store_secret

DB_KEY_NAME = "db_encryption_key"


def get_or_create_db_key() -> str:
    """Get the database encryption key, creating one if it doesn't exist.

    Returns:
        A 64-character hex string (32 bytes of entropy).
    """
    existing = get_secret(DB_KEY_NAME)
    if existing is not None:
        return existing

    # Generate a cryptographically secure random key
    key = secrets.token_hex(32)
    store_secret(DB_KEY_NAME, key)
    return key


def export_db_key() -> str | None:
    """Export the current database key for backup purposes.

    Returns:
        The key string, or None if no key exists.
    """
    return get_secret(DB_KEY_NAME)
