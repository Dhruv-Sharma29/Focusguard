"""Static report views for multi-day summaries.

Used by `focusguard report --period week` and similar commands
that generate summaries over longer date ranges.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from focusguard.config import load_config
from focusguard.core.scorer import calculate_focus_score
from focusguard.db import queries
from focusguard.ui.themes import get_theme, score_style

console = Console()


def render_period_report(days: int = 7) -> None:
    """Render a multi-day summary report.

    Args:
        days: Number of days to include (default 7 for weekly).
    """
    config = load_config()
    theme = get_theme(config.personality.mode)

    now = datetime.now()
    period_start = now - timedelta(days=days)

    # Daily breakdown table
    table = Table(
        title=f"[bold {theme.primary}]📊 {days}-Day Report[/bold {theme.primary}]",
        show_header=True,
        header_style=f"bold {theme.primary}",
        border_style=theme.border,
        expand=True,
    )
    table.add_column("Date", style=theme.muted)
    table.add_column("Score", justify="center")
    table.add_column("Coding", justify="right", style=theme.success)
    table.add_column("Distract", justify="right", style=theme.danger)
    table.add_column("Total", justify="right")
    table.add_column("Commits", justify="center", style=theme.secondary)

    total_coding = 0.0
    total_distraction = 0.0
    total_tracked = 0.0
    total_commits = 0
    scores = []

    for i in range(days):
        day = now - timedelta(days=days - 1 - i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        day_score = calculate_focus_score(day_start, day_end, use_decay=False)
        coding = queries.get_coding_minutes(day_start, day_end)
        distraction = queries.get_distraction_minutes(day_start, day_end)
        total = queries.get_total_active_minutes(day_start, day_end)
        commits = queries.get_git_commits_today()  # TODO: parameterize by date

        total_coding += coding
        total_distraction += distraction
        total_tracked += total
        total_commits += commits
        scores.append(day_score)

        s_style = score_style(theme, day_score)
        table.add_row(
            day.strftime("%a %m/%d"),
            f"[{s_style}]{day_score:.0f}[/{s_style}]",
            _fmt_time(coding),
            _fmt_time(distraction),
            _fmt_time(total),
            str(commits),
        )

    # Summary row
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_style = score_style(theme, avg_score)
    table.add_section()
    table.add_row(
        f"[bold]Average[/bold]",
        f"[{avg_style}]{avg_score:.0f}[/{avg_style}]",
        f"[bold]{_fmt_time(total_coding / max(days, 1))}[/bold]/day",
        f"[bold]{_fmt_time(total_distraction / max(days, 1))}[/bold]/day",
        _fmt_time(total_tracked / max(days, 1)),
        f"{total_commits}",
    )

    console.print()
    console.print(table)
    console.print()


def _fmt_time(minutes: float) -> str:
    """Format minutes into a human-readable string."""
    if minutes < 1:
        return "<1m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"
