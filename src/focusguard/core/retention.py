"""Log retention and auto-deletion policy.

Prevents activity logs from accumulating forever:
- Raw activity_log entries older than retention_days → aggregate into
  daily summaries, then delete raw rows
- Hourly focus_scores older than 30 days → delete (daily scores kept)

Runs automatically once per day when the daemon detects a new calendar day.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from focusguard.config import load_config
from focusguard.db import queries

logger = logging.getLogger(__name__)


def run_retention_policy() -> dict[str, int]:
    """Execute the retention policy.

    Returns:
        Dict with counts of rows affected:
        - 'days_summarized': number of days aggregated
        - 'activity_rows_deleted': raw rows deleted
        - 'score_rows_deleted': hourly score rows deleted
    """
    config = load_config()
    retention_days = config.security.retention_days

    now = datetime.now()
    cutoff = now - timedelta(days=retention_days)
    score_cutoff = now - timedelta(days=30)

    results = {
        "days_summarized": 0,
        "activity_rows_deleted": 0,
        "score_rows_deleted": 0,
    }

    # Step 1: Aggregate old activity into daily summaries
    old_count = queries.get_activity_count_before(cutoff)
    if old_count > 0:
        results["days_summarized"] = _aggregate_to_daily_summaries(cutoff)
        results["activity_rows_deleted"] = queries.delete_activity_before(cutoff)
        logger.info(
            f"Retention: aggregated {results['days_summarized']} days, "
            f"deleted {results['activity_rows_deleted']} raw activity rows"
        )

    # Step 2: Delete old hourly scores
    results["score_rows_deleted"] = queries.delete_hourly_scores_before(score_cutoff)
    if results["score_rows_deleted"] > 0:
        logger.info(
            f"Retention: deleted {results['score_rows_deleted']} old hourly scores"
        )

    return results


def _aggregate_to_daily_summaries(cutoff: datetime) -> int:
    """Aggregate raw activity into daily summaries before cutoff.

    Returns:
        Number of days summarized.
    """
    from focusguard.db.connection import query

    # Get distinct dates with old activity
    rows = query(
        """SELECT DISTINCT date(timestamp) as day
           FROM activity_log
           WHERE timestamp < ?
           ORDER BY day ASC""",
        (cutoff.isoformat(),),
    )

    days_processed = 0

    for row in rows:
        day_str = row["day"]
        day_start = datetime.fromisoformat(f"{day_str}T00:00:00")
        day_end = datetime.fromisoformat(f"{day_str}T23:59:59")

        total_min = queries.get_total_active_minutes(day_start, day_end)
        coding_min = queries.get_coding_minutes(day_start, day_end)
        distraction_min = queries.get_distraction_minutes(day_start, day_end)

        # Get average focus score for the day
        score_row = query(
            """SELECT AVG(score) as avg_score
               FROM focus_scores
               WHERE timestamp BETWEEN ? AND ?
                 AND period IN ('hourly', 'daily')""",
            (day_start.isoformat(), day_end.isoformat()),
        )
        avg_score = float(score_row[0]["avg_score"]) if score_row and score_row[0]["avg_score"] else None

        # Get top apps for the day
        top_apps_rows = queries.get_top_distractions(5, day_start, day_end)
        top_apps = [r["app_name"] for r in top_apps_rows] if top_apps_rows else None

        git_commits_row = query(
            """SELECT COUNT(*) as count FROM git_activity
               WHERE timestamp BETWEEN ? AND ? AND event_type = 'commit'""",
            (day_start.isoformat(), day_end.isoformat()),
        )
        git_commits = int(git_commits_row[0]["count"]) if git_commits_row else 0

        queries.save_daily_summary(
            date=day_str,
            total_min=total_min,
            coding_min=coding_min,
            distraction_min=distraction_min,
            avg_score=avg_score,
            top_apps=top_apps,
            git_commits=git_commits,
        )
        days_processed += 1

    return days_processed
