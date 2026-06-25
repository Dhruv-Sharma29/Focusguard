"""Database schema definitions and migrations for FocusGuard.

All table creation and schema upgrades happen here.
Uses a simple version-based migration strategy.
"""

from __future__ import annotations

from focusguard.db.connection import execute, query_one

SCHEMA_VERSION = 1

# ── Schema SQL ───────────────────────────────────────────────────────────────

SCHEMA_V1 = """
-- Activity log: one row per poll tick (every 60 seconds)
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    app_name TEXT NOT NULL,
    window_title TEXT,
    category TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 60,
    is_idle BOOLEAN NOT NULL DEFAULT 0
);

-- Focus scores: periodic snapshots of productivity metrics
CREATE TABLE IF NOT EXISTS focus_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    score REAL NOT NULL,
    coding_minutes REAL NOT NULL DEFAULT 0,
    distraction_minutes REAL NOT NULL DEFAULT 0,
    total_minutes REAL NOT NULL DEFAULT 0,
    period TEXT NOT NULL
);

-- Goals: user-defined tasks to work on
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT 1
);

-- Git activity: commits, PRs, issues from local repos + GitHub
CREATE TABLE IF NOT EXISTS git_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    repo_name TEXT,
    event_type TEXT NOT NULL,
    details TEXT
);

-- Daily summaries: aggregated data for retention policy
CREATE TABLE IF NOT EXISTS daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    total_minutes REAL NOT NULL DEFAULT 0,
    coding_minutes REAL NOT NULL DEFAULT 0,
    distraction_minutes REAL NOT NULL DEFAULT 0,
    avg_focus_score REAL,
    top_apps TEXT,
    git_commits INTEGER NOT NULL DEFAULT 0
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Indices for fast queries
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_category ON activity_log(category);
CREATE INDEX IF NOT EXISTS idx_scores_timestamp ON focus_scores(timestamp);
CREATE INDEX IF NOT EXISTS idx_scores_period ON focus_scores(period);
CREATE INDEX IF NOT EXISTS idx_goals_active ON goals(is_active);
CREATE INDEX IF NOT EXISTS idx_git_timestamp ON git_activity(timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_summaries(date);
"""


def init_db() -> None:
    """Initialize the database schema.

    Creates all tables if they don't exist and runs any pending migrations.
    Safe to call multiple times (idempotent).
    """
    # Execute full schema (CREATE IF NOT EXISTS is safe to repeat)
    for statement in SCHEMA_V1.split(";"):
        statement = statement.strip()
        if statement:
            execute(statement + ";")

    # Set schema version if not already set
    row = query_one("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    if row is None:
        execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))


def get_schema_version() -> int:
    """Get the current schema version.

    Returns:
        The version number, or 0 if the schema hasn't been initialized.
    """
    try:
        row = query_one("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        return int(row["version"]) if row else 0
    except Exception:
        return 0
