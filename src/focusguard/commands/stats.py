"""focusguard stats — Quick one-line stats summary."""

from __future__ import annotations

import typer

from focusguard.db.models import init_db


def stats() -> None:
    """Quick one-line productivity summary.

    Shows focus score, coding time, and distraction time for today.
    """
    init_db()

    from focusguard.ui.dashboard import render_quick_stats
    render_quick_stats()
