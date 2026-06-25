"""focusguard goal — Manage focus goals."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from focusguard.db.models import init_db
from focusguard.db import queries
from focusguard.config import load_config
from focusguard.ui.themes import get_theme

console = Console()
goal_app = typer.Typer(no_args_is_help=True)


@goal_app.command("add")
def add_goal(
    description: Annotated[str, typer.Argument(help="What you're working on.")],
) -> None:
    """Set a new focus goal.

    Example: focusguard goal add "Build authentication system"
    """
    init_db()
    goal_id = queries.add_goal(description)
    theme = get_theme(load_config().personality.mode)

    console.print(f"\n  [green]✓[/green] Goal #{goal_id} created:")
    console.print(f"  [{theme.primary}]→ {description}[/{theme.primary}]\n")


@goal_app.command("list")
def list_goals(
    all_goals: Annotated[
        bool,
        typer.Option("--all", "-a", help="Include completed and dropped goals."),
    ] = False,
) -> None:
    """List your goals."""
    init_db()
    theme = get_theme(load_config().personality.mode)
    goals = queries.get_all_goals(include_inactive=all_goals)

    if not goals:
        console.print(f"\n  [{theme.muted}]No goals set. Create one with:[/{theme.muted}]")
        console.print(f"  [{theme.primary}]focusguard goal add \"...\"[/{theme.primary}]\n")
        return

    table = Table(
        title=f"[bold {theme.primary}]🎯 Goals[/bold {theme.primary}]",
        show_header=True,
        header_style=f"bold {theme.primary}",
        border_style=theme.border,
    )
    table.add_column("#", style=theme.muted, width=4)
    table.add_column("Goal", style=theme.primary)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Created", style=theme.muted, width=18)

    for g in goals:
        goal_id = g["id"]
        desc = g["description"]
        created = g.get("created_at", "")

        if g.get("completed_at"):
            status = f"[green]✓ Done[/green]"
        elif g.get("is_active"):
            status = f"[{theme.warning}]● Active[/{theme.warning}]"
        else:
            status = f"[{theme.muted}]✗ Dropped[/{theme.muted}]"

        # Format created time
        created_short = created[:16] if len(created) > 16 else created

        table.add_row(str(goal_id), desc, status, created_short)

    console.print()
    console.print(table)
    console.print()


@goal_app.command("complete")
def complete_goal(
    goal_id: Annotated[int, typer.Argument(help="Goal ID to mark as complete.")],
) -> None:
    """Mark a goal as completed."""
    init_db()

    if queries.complete_goal(goal_id):
        console.print(f"\n  [green]✓[/green] Goal #{goal_id} completed! Nice work. 🎉\n")
    else:
        console.print(f"\n  [red]✗[/red] Goal #{goal_id} not found or already completed.\n")
        raise typer.Exit(1)


@goal_app.command("drop")
def drop_goal(
    goal_id: Annotated[int, typer.Argument(help="Goal ID to drop.")],
) -> None:
    """Drop a goal without completing it."""
    init_db()

    if queries.drop_goal(goal_id):
        console.print(f"\n  [yellow]■[/yellow] Goal #{goal_id} dropped.\n")
    else:
        console.print(f"\n  [red]✗[/red] Goal #{goal_id} not found or already inactive.\n")
        raise typer.Exit(1)
