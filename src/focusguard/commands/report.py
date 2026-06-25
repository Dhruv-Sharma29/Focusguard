"""focusguard report — Show the productivity dashboard."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from focusguard.db.models import init_db

console = Console()


def report(
    period: Annotated[
        Optional[str],
        typer.Option("--period", "-p",
                     help="Report period: 'today' (default), 'week', or 'month'."),
    ] = "today",
) -> None:
    """📊 Show the productivity dashboard.

    Displays focus score, coding time, distractions, and activity timeline.
    """
    init_db()

    if period == "today":
        from focusguard.ui.dashboard import render_dashboard
        render_dashboard()
    elif period == "week":
        from focusguard.ui.report_view import render_period_report
        render_period_report(days=7)
    elif period == "month":
        from focusguard.ui.report_view import render_period_report
        render_period_report(days=30)
    else:
        console.print(f"[red]✗ Unknown period: {period}[/red]")
        console.print("[dim]Valid periods: today, week, month[/dim]")
        raise typer.Exit(1)
