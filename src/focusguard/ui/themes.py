"""Color themes for FocusGuard terminal UI.

Each personality mode gets its own visual theme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Visual theme for the terminal dashboard."""

    name: str
    primary: str        # Main accent color
    secondary: str      # Secondary accent
    success: str        # Good/productive
    warning: str        # Moderate concern
    danger: str         # Bad/distraction
    muted: str          # Dimmed text
    border: str         # Panel borders
    header_bg: str      # Header background style
    score_high: str     # Score ≥ 80
    score_mid: str      # Score 50–79
    score_low: str      # Score < 50


# ── Theme Definitions ────────────────────────────────────────────────────────

COACH_THEME = Theme(
    name="coach",
    primary="cyan",
    secondary="blue",
    success="green",
    warning="yellow",
    danger="red",
    muted="dim white",
    border="cyan",
    header_bg="on dark_blue",
    score_high="bold green",
    score_mid="bold yellow",
    score_low="bold red",
)

STRICT_THEME = Theme(
    name="strict",
    primary="white",
    secondary="bright_white",
    success="green",
    warning="bright_yellow",
    danger="bright_red",
    muted="dim",
    border="white",
    header_bg="on grey23",
    score_high="bold bright_green",
    score_mid="bold bright_yellow",
    score_low="bold bright_red",
)

FRIEND_THEME = Theme(
    name="friend",
    primary="bright_magenta",
    secondary="magenta",
    success="bright_green",
    warning="bright_yellow",
    danger="bright_red",
    muted="dim magenta",
    border="bright_magenta",
    header_bg="on purple4",
    score_high="bold bright_green",
    score_mid="bold bright_yellow",
    score_low="bold bright_red",
)

ROAST_THEME = Theme(
    name="roast",
    primary="bright_red",
    secondary="dark_orange",
    success="green",
    warning="bright_yellow",
    danger="bright_red",
    muted="dim red",
    border="bright_red",
    header_bg="on dark_red",
    score_high="bold green",
    score_mid="bold dark_orange",
    score_low="bold bright_red blink",
)

THEMES: dict[str, Theme] = {
    "coach": COACH_THEME,
    "strict": STRICT_THEME,
    "friend": FRIEND_THEME,
    "roast": ROAST_THEME,
}


def get_theme(mode: str = "coach") -> Theme:
    """Get the theme for a personality mode.

    Args:
        mode: One of 'coach', 'strict', 'friend', 'roast'.

    Returns:
        The corresponding Theme, defaulting to coach.
    """
    return THEMES.get(mode, COACH_THEME)


def score_style(theme: Theme, score: float) -> str:
    """Get the Rich style string for a given focus score."""
    if score >= 80:
        return theme.score_high
    elif score >= 50:
        return theme.score_mid
    else:
        return theme.score_low
