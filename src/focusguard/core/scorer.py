"""Focus score computation engine.

Calculates a 0–100 focus score based on activity categories,
with time-decay weighting so recent activity matters more.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from focusguard.db import queries

# Category weights for focus score calculation
PRODUCTIVE_CATEGORIES = {"coding", "documentation", "terminal"}
DISTRACTION_CATEGORIES = {"entertainment"}
NEUTRAL_CATEGORIES = {"browser", "communication", "other"}

# Time decay weights: more recent activity counts more
DECAY_WINDOWS = [
    (timedelta(hours=2), 2.0),   # Last 2 hours: 2× weight
    (timedelta(hours=4), 1.5),   # 2–4 hours ago: 1.5× weight
    (timedelta(hours=24), 1.0),  # 4–24 hours ago: 1× weight
]


def calculate_focus_score(
    start: datetime | None = None,
    end: datetime | None = None,
    use_decay: bool = True,
) -> float:
    """Calculate the focus score for a given time range.

    The score is a weighted ratio of productive time to total active time.

    Args:
        start: Start of the scoring window. Defaults to start of today.
        end: End of the scoring window. Defaults to now.
        use_decay: Whether to apply time-decay weighting.

    Returns:
        A focus score between 0.0 and 100.0.
    """
    if start is None:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = datetime.now()

    activity = queries.get_activity_range(start, end)

    if not activity:
        return 0.0

    productive_weighted = 0.0
    distraction_weighted = 0.0
    total_weighted = 0.0

    now = datetime.now()

    for entry in activity:
        if entry.get("is_idle"):
            continue

        duration = entry.get("duration_seconds", 60) / 60.0  # Convert to minutes
        category = entry.get("category", "other")

        # Calculate time-decay weight
        try:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            age = now - entry_time
        except (ValueError, KeyError):
            age = timedelta(hours=12)

        weight = 1.0
        if use_decay:
            weight = _get_decay_weight(age)

        weighted_duration = duration * weight
        total_weighted += weighted_duration

        if category in PRODUCTIVE_CATEGORIES:
            productive_weighted += weighted_duration
        elif category in DISTRACTION_CATEGORIES:
            distraction_weighted += weighted_duration
        # Neutral categories count toward total but not productive or distraction

    if total_weighted == 0:
        return 0.0

    # Score = productive ratio with distraction penalty
    productive_ratio = productive_weighted / total_weighted
    distraction_ratio = distraction_weighted / total_weighted

    # Base score from productive ratio, penalized by distractions
    score = (productive_ratio * 100) - (distraction_ratio * 25)

    return max(0.0, min(100.0, score))


def _get_decay_weight(age: timedelta) -> float:
    """Get the time-decay weight for an activity entry.

    More recent entries get higher weight.
    """
    for threshold, weight in DECAY_WINDOWS:
        if age <= threshold:
            return weight
    return 0.5  # Very old entries get minimum weight


def get_score_emoji(score: float) -> str:
    """Get a color-coded emoji for a focus score."""
    if score >= 80:
        return "🟢"
    elif score >= 50:
        return "🟡"
    else:
        return "🔴"


def get_score_label(score: float) -> str:
    """Get a descriptive label for a focus score."""
    if score >= 90:
        return "Exceptional"
    elif score >= 80:
        return "Focused"
    elif score >= 65:
        return "Productive"
    elif score >= 50:
        return "Average"
    elif score >= 30:
        return "Distracted"
    else:
        return "Off Track"


def get_trend(hours: int = 8) -> str:
    """Calculate whether focus is trending up, down, or stable.

    Returns:
        "↑" (improving), "↓" (declining), or "→" (stable).
    """
    scores = queries.get_score_trend(hours)

    if len(scores) < 2:
        return "→"

    # Compare first half average to second half average
    mid = len(scores) // 2
    first_half = sum(s["score"] for s in scores[:mid]) / mid
    second_half = sum(s["score"] for s in scores[mid:]) / (len(scores) - mid)

    diff = second_half - first_half

    if diff > 5:
        return "↑"
    elif diff < -5:
        return "↓"
    else:
        return "→"


def snapshot_score(period: str = "session") -> float:
    """Calculate and save a focus score snapshot.

    Args:
        period: One of 'session', 'hourly', 'daily'.

    Returns:
        The calculated score.
    """
    now = datetime.now()

    if period == "hourly":
        start = now - timedelta(hours=1)
    elif period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    score = calculate_focus_score(start, now)
    coding_min = queries.get_coding_minutes(start, now)
    distraction_min = queries.get_distraction_minutes(start, now)
    total_min = queries.get_total_active_minutes(start, now)

    queries.save_focus_score(score, coding_min, distraction_min, total_min, period)

    return score
