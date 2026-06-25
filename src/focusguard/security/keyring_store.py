"""Wrapper around python-keyring for secure secret storage.

All secrets (DB encryption key, GitHub tokens, API keys) go through this
module. Never stores secrets in plaintext config files.

Uses the OS-native credential store:
  - macOS: Keychain
  - Windows: Credential Locker
  - Linux: Secret Service (GNOME Keyring / KWallet)
"""

from __future__ import annotations

import keyring
from keyring.errors import PasswordDeleteError

SERVICE_NAME = "focusguard"


def store_secret(name: str, value: str) -> None:
    """Store a secret in the OS keyring.

    Args:
        name: Key name (e.g. 'db_key', 'github_token').
        value: The secret value to store.
    """
    keyring.set_password(SERVICE_NAME, name, value)


def get_secret(name: str) -> str | None:
    """Retrieve a secret from the OS keyring.

    Args:
        name: Key name to look up.

    Returns:
        The secret value, or None if not found.
    """
    return keyring.get_password(SERVICE_NAME, name)


def delete_secret(name: str) -> bool:
    """Delete a secret from the OS keyring.

    Args:
        name: Key name to delete.

    Returns:
        True if deleted, False if it didn't exist.
    """
    try:
        keyring.delete_password(SERVICE_NAME, name)
        return True
    except PasswordDeleteError:
        return False


def has_secret(name: str) -> bool:
    """Check if a secret exists in the keyring."""
    return get_secret(name) is not None
