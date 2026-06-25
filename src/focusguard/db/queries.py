"""Query helpers for FocusGuard database operations.

Provides a clean API for CRUD operations on all tables.
All functions use the connection manager from db.connection.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from focusguard.db.connection import execute, query, query_one


def _ts(dt: datetime) -> str:
    """Format a datetime for SQLite comparison.

    SQLite's datetime('now', 'localtime') uses space separator: '2026-06-24 11:00:00'
    Python's isoformat() uses T separator: '2026-06-24T11:00:00'
    This helper ensures consistency.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ── Activity Log ─────────────────────────────────────────────────────────────


def log_activity(
    app_name: str,
    window_title: str | None,
    category: str,
    duration_seconds: int = 60,
    is_idle: bool = False,
) -> int:
    """Log a single activity entry.

    Returns:
        The ID of the inserted row.
    """
    cursor = execute(
        """INSERT INTO activity_log (app_name, window_title, category, duration_seconds, is_idle)
           VALUES (?, ?, ?, ?, ?)""",
        (app_name, window_title, category, duration_seconds, is_idle),
    )
    return cursor.lastrowid or 0


def get_activity_range(
    start: datetime, end: datetime | None = None
) -> list[dict[str, Any]]:
    """Get activity entries within a time range.

    Args:
        start: Start of the range (inclusive).
        end: End of the range (inclusive). Defaults to now.

    Returns:
        List of activity dicts.
    """
    if end is None:
        end = datetime.now()

    rows = query(
        """SELECT * FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
           ORDER BY timestamp ASC""",
        (_ts(start), _ts(end)),
    )
    return [dict(row) for row in rows]


def get_today_activity() -> list[dict[str, Any]]:
    """Get all activity entries for today."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return get_activity_range(today_start)


def get_coding_minutes(start: datetime, end: datetime | None = None) -> float:
    """Get total coding minutes in a time range."""
    if end is None:
        end = datetime.now()

    row = query_one(
        """SELECT COALESCE(SUM(duration_seconds), 0) / 60.0 as minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND category IN ('coding', 'documentation')
             AND is_idle = 0""",
        (_ts(start), _ts(end)),
    )
    return float(row["minutes"]) if row else 0.0


def get_distraction_minutes(start: datetime, end: datetime | None = None) -> float:
    """Get total distraction minutes in a time range."""
    if end is None:
        end = datetime.now()

    row = query_one(
        """SELECT COALESCE(SUM(duration_seconds), 0) / 60.0 as minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND category = 'entertainment'
             AND is_idle = 0""",
        (_ts(start), _ts(end)),
    )
    return float(row["minutes"]) if row else 0.0


def get_total_active_minutes(start: datetime, end: datetime | None = None) -> float:
    """Get total non-idle tracked minutes in a time range."""
    if end is None:
        end = datetime.now()

    row = query_one(
        """SELECT COALESCE(SUM(duration_seconds), 0) / 60.0 as minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND is_idle = 0""",
        (_ts(start), _ts(end)),
    )
    return float(row["minutes"]) if row else 0.0


def get_top_distractions(
    n: int = 5,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get the top N most time-consuming distraction apps.

    Returns:
        List of dicts with 'app_name' and 'total_minutes' keys.
    """
    if start is None:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = datetime.now()

    rows = query(
        """SELECT app_name, window_title, SUM(duration_seconds) / 60.0 as total_minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND category = 'entertainment'
             AND is_idle = 0
           GROUP BY app_name, window_title
           ORDER BY total_minutes DESC
           LIMIT ?""",
        (_ts(start), _ts(end), n),
    )
    return [dict(row) for row in rows]


def get_app_breakdown(
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get time breakdown by app category.

    Returns:
        List of dicts with 'category' and 'total_minutes' keys.
    """
    if start is None:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = datetime.now()

    rows = query(
        """SELECT category, SUM(duration_seconds) / 60.0 as total_minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND is_idle = 0
           GROUP BY category
           ORDER BY total_minutes DESC""",
        (_ts(start), _ts(end)),
    )
    return [dict(row) for row in rows]


def get_hourly_activity(
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Get activity grouped by hour for timeline display.

    Returns:
        List of dicts with 'hour', 'category', 'total_minutes'.
    """
    if start is None:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = datetime.now()

    rows = query(
        """SELECT strftime('%H', timestamp) as hour,
                  category,
                  SUM(duration_seconds) / 60.0 as total_minutes
           FROM activity_log
           WHERE timestamp BETWEEN ? AND ?
             AND is_idle = 0
           GROUP BY hour, category
           ORDER BY hour ASC""",
        (_ts(start), _ts(end)),
    )
    return [dict(row) for row in rows]


def get_unique_apps_since(since: datetime) -> int:
    """Count unique apps used since a given time."""
    row = query_one(
        """SELECT COUNT(DISTINCT app_name) as count
           FROM activity_log
           WHERE timestamp >= ? AND is_idle = 0""",
        (_ts(since),),
    )
    return int(row["count"]) if row else 0


def get_entertainment_minutes_since(since: datetime) -> float:
    """Get entertainment minutes since a given time."""
    row = query_one(
        """SELECT COALESCE(SUM(duration_seconds), 0) / 60.0 as minutes
           FROM activity_log
           WHERE timestamp >= ?
             AND category = 'entertainment'
             AND is_idle = 0""",
        (_ts(since),),
    )
    return float(row["minutes"]) if row else 0.0


# ── Focus Scores ─────────────────────────────────────────────────────────────


def save_focus_score(
    score: float,
    coding_min: float,
    distraction_min: float,
    total_min: float,
    period: str,
) -> int:
    """Save a focus score snapshot.

    Args:
        score: Focus score (0.0 to 100.0).
        coding_min: Total coding minutes in the period.
        distraction_min: Total distraction minutes in the period.
        total_min: Total tracked minutes in the period.
        period: One of 'session', 'hourly', 'daily'.

    Returns:
        The ID of the inserted row.
    """
    cursor = execute(
        """INSERT INTO focus_scores (score, coding_minutes, distraction_minutes, total_minutes, period)
           VALUES (?, ?, ?, ?, ?)""",
        (score, coding_min, distraction_min, total_min, period),
    )
    return cursor.lastrowid or 0


def get_latest_score(period: str = "session") -> dict[str, Any] | None:
    """Get the most recent focus score for a given period.

    Returns:
        Dict with score data, or None if no scores exist.
    """
    row = query_one(
        """SELECT * FROM focus_scores
           WHERE period = ?
           ORDER BY timestamp DESC
           LIMIT 1""",
        (period,),
    )
    return dict(row) if row else None


def get_score_trend(hours: int = 8) -> list[dict[str, Any]]:
    """Get focus score history for trend calculation.

    Returns:
        List of score dicts ordered by time.
    """
    since = datetime.now() - timedelta(hours=hours)
    rows = query(
        """SELECT * FROM focus_scores
           WHERE timestamp >= ? AND period = 'hourly'
           ORDER BY timestamp ASC""",
        (_ts(since),),
    )
    return [dict(row) for row in rows]


# ── Goals ────────────────────────────────────────────────────────────────────


def add_goal(description: str) -> int:
    """Add a new goal.

    Returns:
        The ID of the new goal.
    """
    cursor = execute(
        "INSERT INTO goals (description) VALUES (?)",
        (description,),
    )
    return cursor.lastrowid or 0


def get_active_goals() -> list[dict[str, Any]]:
    """Get all active (uncompleted) goals."""
    rows = query(
        """SELECT * FROM goals
           WHERE is_active = 1
           ORDER BY created_at DESC"""
    )
    return [dict(row) for row in rows]


def complete_goal(goal_id: int) -> bool:
    """Mark a goal as completed.

    Returns:
        True if the goal was found and updated.
    """
    cursor = execute(
        """UPDATE goals
           SET completed_at = datetime('now', 'localtime'), is_active = 0
           WHERE id = ? AND is_active = 1""",
        (goal_id,),
    )
    return (cursor.rowcount or 0) > 0


def drop_goal(goal_id: int) -> bool:
    """Deactivate a goal without completing it.

    Returns:
        True if the goal was found and updated.
    """
    cursor = execute(
        "UPDATE goals SET is_active = 0 WHERE id = ? AND is_active = 1",
        (goal_id,),
    )
    return (cursor.rowcount or 0) > 0


def get_all_goals(include_inactive: bool = False) -> list[dict[str, Any]]:
    """Get all goals, optionally including inactive ones."""
    if include_inactive:
        rows = query("SELECT * FROM goals ORDER BY created_at DESC")
    else:
        rows = query(
            "SELECT * FROM goals WHERE is_active = 1 ORDER BY created_at DESC"
        )
    return [dict(row) for row in rows]


# ── Git Activity ─────────────────────────────────────────────────────────────


def log_git_event(
    event_type: str,
    repo_name: str | None = None,
    details: dict[str, Any] | None = None,
) -> int:
    """Log a git activity event.

    Args:
        event_type: One of 'commit', 'push', 'pr_open', 'pr_merge', 'issue'.
        repo_name: Name of the repository.
        details: Optional dict with extra info (serialized to JSON).

    Returns:
        The ID of the inserted row.
    """
    details_json = json.dumps(details) if details else None
    cursor = execute(
        """INSERT INTO git_activity (repo_name, event_type, details)
           VALUES (?, ?, ?)""",
        (repo_name, event_type, details_json),
    )
    return cursor.lastrowid or 0


def get_git_commits_today() -> int:
    """Count git commits logged today."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    row = query_one(
        """SELECT COUNT(*) as count FROM git_activity
           WHERE timestamp >= ? AND event_type = 'commit'""",
        (_ts(today_start),),
    )
    return int(row["count"]) if row else 0


def get_recent_git_activity(n: int = 10) -> list[dict[str, Any]]:
    """Get the N most recent git events."""
    rows = query(
        """SELECT * FROM git_activity
           ORDER BY timestamp DESC
           LIMIT ?""",
        (n,),
    )
    return [dict(row) for row in rows]


# ── Daily Summaries ──────────────────────────────────────────────────────────


def save_daily_summary(
    date: str,
    total_min: float,
    coding_min: float,
    distraction_min: float,
    avg_score: float | None,
    top_apps: list[str] | None,
    git_commits: int,
) -> None:
    """Save or update a daily summary (for retention policy)."""
    apps_json = json.dumps(top_apps) if top_apps else None
    execute(
        """INSERT OR REPLACE INTO daily_summaries
           (date, total_minutes, coding_minutes, distraction_minutes,
            avg_focus_score, top_apps, git_commits)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (date, total_min, coding_min, distraction_min, avg_score, apps_json, git_commits),
    )


def get_activity_count_before(before: datetime) -> int:
    """Count activity log entries older than a given date."""
    row = query_one(
        "SELECT COUNT(*) as count FROM activity_log WHERE timestamp < ?",
        (_ts(before),),
    )
    return int(row["count"]) if row else 0


def delete_activity_before(before: datetime) -> int:
    """Delete activity log entries older than a given date.

    Returns:
        Number of rows deleted.
    """
    cursor = execute(
        "DELETE FROM activity_log WHERE timestamp < ?",
        (_ts(before),),
    )
    return cursor.rowcount or 0


def delete_hourly_scores_before(before: datetime) -> int:
    """Delete hourly focus score entries older than a given date.

    Returns:
        Number of rows deleted.
    """
    cursor = execute(
        "DELETE FROM focus_scores WHERE timestamp < ? AND period = 'hourly'",
        (_ts(before),),
    )
    return cursor.rowcount or 0
