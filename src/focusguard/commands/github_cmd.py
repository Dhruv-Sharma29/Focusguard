"""focusguard github — GitHub integration commands."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from focusguard.config import load_config
from focusguard.ui.themes import get_theme

console = Console()
github_app = typer.Typer(no_args_is_help=True)


@github_app.command("setup")
def setup() -> None:
    """Configure GitHub personal access token.

    Token is stored securely in the OS keyring — never in a config file.
    """
    from focusguard.integrations.github_api import setup_token

    console.print()
    console.print("  [dim]Create a token at: https://github.com/settings/tokens[/dim]")
    console.print("  [dim]Required scopes: repo (read-only is fine)[/dim]")
    console.print()

    token = typer.prompt("  GitHub PAT", hide_input=True)
    setup_token(token)
    console.print("\n  [green]✓[/green] Token stored securely in OS keyring.\n")


@github_app.command("summary")
def summary(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to summarize."),
    ] = 7,
) -> None:
    """Show GitHub activity summary."""
    theme = get_theme(load_config().personality.mode)

    from focusguard.integrations.github_api import get_weekly_summary, is_configured

    if not is_configured():
        console.print("\n  [yellow]⚠ GitHub not configured.[/yellow]")
        console.print("  [dim]Run: focusguard github setup[/dim]\n")
        raise typer.Exit(1)

    console.print(f"\n  [dim]Fetching GitHub activity for the last {days} days...[/dim]")
    result = get_weekly_summary(days)

    if result is None:
        console.print("  [red]✗ Failed to fetch GitHub data.[/red]\n")
        raise typer.Exit(1)

    # Render summary
    table = Table(
        title=f"[bold {theme.primary}]🐙 GitHub — {days}-Day Summary[/bold {theme.primary}]",
        show_header=False,
        border_style=theme.border,
        padding=(0, 2),
    )
    table.add_column("Metric", style=theme.muted)
    table.add_column("Value", style=theme.primary)

    table.add_row("User", f"@{result.username}")
    table.add_row("Commits", f"[{theme.success}]{result.total_commits}[/{theme.success}]")
    table.add_row("PRs Opened", str(result.total_prs_opened))
    table.add_row("PRs Merged", f"[{theme.success}]{result.total_prs_merged}[/{theme.success}]")
    table.add_row("Issues Opened", str(result.total_issues_opened))
    table.add_row("Issues Closed", f"[{theme.success}]{result.total_issues_closed}[/{theme.success}]")
    table.add_row("Most Active Repo", result.most_active_repo or "—")
    table.add_row(
        "Repos Contributed",
        ", ".join(result.repos_contributed[:5]) or "—",
    )

    console.print()
    console.print(table)
    console.print()


@github_app.command("repos")
def scan_local(
    path: Annotated[
        str,
        typer.Argument(help="Directory to scan for git repos."),
    ] = "~/Code",
) -> None:
    """Scan a directory for local git repos and show activity."""
    theme = get_theme(load_config().personality.mode)

    from focusguard.integrations.git_tracker import find_git_repos, scan_all_repos

    console.print(f"\n  [dim]Scanning {path} for git repos...[/dim]")

    repo_paths = find_git_repos(path)
    if not repo_paths:
        console.print(f"  [yellow]⚠ No git repos found in {path}[/yellow]\n")
        return

    summaries = scan_all_repos(repo_paths)

    table = Table(
        title=f"[bold {theme.primary}]📁 Local Repos[/bold {theme.primary}]",
        show_header=True,
        header_style=f"bold {theme.primary}",
        border_style=theme.border,
    )
    table.add_column("Repo", style=theme.primary)
    table.add_column("24h", justify="center")
    table.add_column("7d", justify="center")
    table.add_column("+/-", justify="center")
    table.add_column("Dirty", justify="center")

    for s in sorted(summaries, key=lambda x: x.commits_24h, reverse=True):
        dirty = f"[{theme.warning}]●[/{theme.warning}]" if s.has_uncommitted else f"[{theme.muted}]—[/{theme.muted}]"
        table.add_row(
            s.repo_name,
            f"[{theme.success}]{s.commits_24h}[/{theme.success}]",
            str(s.commits_7d),
            f"[green]+{s.lines_added}[/green] [red]-{s.lines_deleted}[/red]",
            dirty,
        )

    console.print()
    console.print(table)
    console.print()
