"""Sensitive site / title blocklist for privacy protection.

When the active window title matches a blocklist pattern, FocusGuard
records only a generic label instead of the actual title. This prevents
banking sites, health portals, and private browsing from being logged.
"""

from __future__ import annotations

from focusguard.config import load_config

# Sentinel value used when a title is blocklisted
REDACTED_TITLE = "[private]"


def get_blocklist() -> list[str]:
    """Get the current blocklist from config."""
    config = load_config()
    return config.security.blocklist


def is_sensitive(title: str, blocklist: list[str] | None = None) -> bool:
    """Check if a window title matches any blocklist pattern.

    Args:
        title: The window title to check.
        blocklist: Optional explicit blocklist. Uses config default if None.

    Returns:
        True if the title should be redacted.
    """
    if not title:
        return False

    if blocklist is None:
        blocklist = get_blocklist()

    title_lower = title.lower()
    return any(pattern.lower() in title_lower for pattern in blocklist)


def sanitize_title(title: str | None, blocklist: list[str] | None = None) -> str | None:
    """Sanitize a window title, replacing sensitive content.

    Args:
        title: The raw window title (may be None).
        blocklist: Optional explicit blocklist.

    Returns:
        The original title if safe, REDACTED_TITLE if sensitive, None if input was None.
    """
    if title is None:
        return None

    if is_sensitive(title, blocklist):
        return REDACTED_TITLE

    return title
