"""Smart procrastination detection engine.

Uses a weighted signal system (NOT ML) to detect procrastination patterns.
Deterministic, auditable, no training data, no false-positive black boxes.

Key insight: instead of "YouTube = bad", the engine reads compound patterns:
  goal set + 1h elapsed + 0 files modified + 0 git activity + app switching
  = procrastinating

This avoids false positives where research/reading docs in a browser
looks like distraction but isn't.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from focusguard.db import queries

logger = logging.getLogger(__name__)


@dataclass
class ActivityContext:
    """Snapshot of current activity state for pattern evaluation."""

    has_active_goal: bool = False
    goal_description: str = ""
    hours_since_goal_set: float = 0.0

    coding_minutes_last_hour: float = 0.0
    coding_minutes_today: float = 0.0
    distraction_minutes_last_hour: float = 0.0
    entertainment_minutes_last_hour: float = 0.0

    unique_apps_last_30min: int = 0
    git_commits_today: int = 0

    focus_score: float = 0.0
    current_hour: int = 0

    # Learned patterns (populated from historical data)
    avg_productive_hours: list[int] = field(default_factory=list)
    avg_slump_hours: list[int] = field(default_factory=list)


@dataclass
class ProcrastinationSignal:
    """A single signal that contributes to the procrastination score."""

    name: str
    description: str
    weight: float  # 0.0 to 1.0
    check: Callable[[ActivityContext], bool]


# ── Signal Definitions ───────────────────────────────────────────────────────

SIGNALS: list[ProcrastinationSignal] = [
    ProcrastinationSignal(
        name="goal_set_no_progress",
        description="Active goal exists but no coding in the last hour",
        weight=0.3,
        check=lambda ctx: ctx.has_active_goal and ctx.coding_minutes_last_hour == 0,
    ),
    ProcrastinationSignal(
        name="excessive_app_switching",
        description="More than 10 unique apps in the last 30 minutes",
        weight=0.2,
        check=lambda ctx: ctx.unique_apps_last_30min > 10,
    ),
    ProcrastinationSignal(
        name="long_entertainment",
        description="More than 30 minutes of entertainment in the last hour",
        weight=0.4,
        check=lambda ctx: ctx.entertainment_minutes_last_hour > 30,
    ),
    ProcrastinationSignal(
        name="zero_git_activity",
        description="No git commits today despite goal being set for 2+ hours",
        weight=0.1,
        check=lambda ctx: (
            ctx.git_commits_today == 0
            and ctx.has_active_goal
            and ctx.hours_since_goal_set > 2
        ),
    ),
    ProcrastinationSignal(
        name="high_distraction_ratio",
        description="Distraction time exceeds coding time in the last hour",
        weight=0.25,
        check=lambda ctx: (
            ctx.distraction_minutes_last_hour > ctx.coding_minutes_last_hour
            and ctx.distraction_minutes_last_hour > 15
        ),
    ),
    ProcrastinationSignal(
        name="known_slump_hour",
        description="Current hour is a historically low-productivity time",
        weight=0.1,
        check=lambda ctx: ctx.current_hour in ctx.avg_slump_hours,
    ),
    ProcrastinationSignal(
        name="long_idle_with_goal",
        description="Goal set but almost no activity at all in the last hour",
        weight=0.35,
        check=lambda ctx: (
            ctx.has_active_goal
            and ctx.coding_minutes_last_hour < 5
            and ctx.entertainment_minutes_last_hour < 5
            and ctx.hours_since_goal_set > 1
        ),
    ),
]


@dataclass
class DetectionResult:
    """Result of a procrastination detection check."""

    score: float  # 0.0 to 1.0 (weighted sum of triggered signals)
    is_procrastinating: bool  # True if score >= threshold
    triggered_signals: list[ProcrastinationSignal]
    context: ActivityContext


# ── Engine ───────────────────────────────────────────────────────────────────

PROCRASTINATION_THRESHOLD = 0.6


def build_context() -> ActivityContext:
    """Build an ActivityContext from the current database state.

    Returns:
        A populated ActivityContext snapshot.
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    one_hour_ago = now - timedelta(hours=1)
    thirty_min_ago = now - timedelta(minutes=30)

    # Goal info
    active_goals = queries.get_active_goals()
    has_goal = len(active_goals) > 0
    goal_desc = active_goals[0]["description"] if has_goal else ""

    hours_since_goal = 0.0
    if has_goal:
        try:
            created = datetime.fromisoformat(active_goals[0].get("created_at", ""))
            hours_since_goal = (now - created).total_seconds() / 3600
        except (ValueError, KeyError):
            pass

    # Activity stats
    coding_last_hour = queries.get_coding_minutes(one_hour_ago, now)
    coding_today = queries.get_coding_minutes(today_start, now)
    distraction_last_hour = queries.get_distraction_minutes(one_hour_ago, now)
    entertainment_last_hour = queries.get_entertainment_minutes_since(one_hour_ago)
    unique_apps = queries.get_unique_apps_since(thirty_min_ago)
    git_commits = queries.get_git_commits_today()

    # Focus score
    from focusguard.core.scorer import calculate_focus_score
    score = calculate_focus_score(today_start, now)

    # Learn hourly patterns from historical data
    avg_productive, avg_slump = _learn_hourly_patterns()

    return ActivityContext(
        has_active_goal=has_goal,
        goal_description=goal_desc,
        hours_since_goal_set=hours_since_goal,
        coding_minutes_last_hour=coding_last_hour,
        coding_minutes_today=coding_today,
        distraction_minutes_last_hour=distraction_last_hour,
        entertainment_minutes_last_hour=entertainment_last_hour,
        unique_apps_last_30min=unique_apps,
        git_commits_today=git_commits,
        focus_score=score,
        current_hour=now.hour,
        avg_productive_hours=avg_productive,
        avg_slump_hours=avg_slump,
    )


def detect_procrastination(
    context: ActivityContext | None = None,
    threshold: float = PROCRASTINATION_THRESHOLD,
) -> DetectionResult:
    """Run the procrastination detection engine.

    Args:
        context: Pre-built context, or None to build from current state.
        threshold: Score threshold for "is_procrastinating" (default 0.6).

    Returns:
        A DetectionResult with score, triggered signals, and context.
    """
    if context is None:
        context = build_context()

    triggered: list[ProcrastinationSignal] = []
    total_score = 0.0

    for signal in SIGNALS:
        try:
            if signal.check(context):
                triggered.append(signal)
                total_score += signal.weight
        except Exception as e:
            logger.debug(f"Signal {signal.name} evaluation failed: {e}")

    # Cap at 1.0
    total_score = min(1.0, total_score)

    return DetectionResult(
        score=total_score,
        is_procrastinating=total_score >= threshold,
        triggered_signals=triggered,
        context=context,
    )


def _learn_hourly_patterns() -> tuple[list[int], list[int]]:
    """Learn which hours are typically productive vs slump hours.

    Analyzes the last 30 days of hourly focus scores to identify patterns.

    Returns:
        Tuple of (productive_hours, slump_hours).
    """
    from focusguard.db.connection import query as db_query

    try:
        rows = db_query(
            """SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                      AVG(score) as avg_score
               FROM focus_scores
               WHERE timestamp >= datetime('now', '-30 days')
                 AND period = 'hourly'
               GROUP BY hour
               HAVING COUNT(*) >= 3
               ORDER BY hour""",
        )

        if not rows:
            return ([], [])

        overall_avg = sum(r["avg_score"] for r in rows) / len(rows)

        productive = [r["hour"] for r in rows if r["avg_score"] > overall_avg + 10]
        slump = [r["hour"] for r in rows if r["avg_score"] < overall_avg - 10]

        return (productive, slump)

    except Exception:
        return ([], [])


def get_detection_summary(result: DetectionResult) -> str:
    """Get a human-readable summary of detection results."""
    if not result.is_procrastinating:
        return "No procrastination patterns detected."

    signal_names = [s.description for s in result.triggered_signals]
    signals_str = "; ".join(signal_names)

    return (
        f"Procrastination score: {result.score:.0%} "
        f"(threshold: {PROCRASTINATION_THRESHOLD:.0%}). "
        f"Signals: {signals_str}"
    )
