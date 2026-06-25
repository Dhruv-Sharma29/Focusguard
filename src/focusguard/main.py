"""FocusGuard CLI — main entry point.

All commands are registered here and dispatched by Typer.
Entry point: `focusguard` (registered in pyproject.toml).
"""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from focusguard import __version__

console = Console()

# ── Root App ─────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="focusguard",
    help="🛡️ FocusGuard — Privacy-first developer productivity tracker",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[cyan]FocusGuard[/cyan] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Show version and exit.",
                     callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """FocusGuard — Privacy-first developer productivity tracker."""


# ── Import and register commands ─────────────────────────────────────────────

from focusguard.commands.start import start  # noqa: E402
from focusguard.commands.stop import stop  # noqa: E402
from focusguard.commands.report import report  # noqa: E402
from focusguard.commands.stats import stats  # noqa: E402
from focusguard.commands.goal import goal_app  # noqa: E402
from focusguard.commands.daemon import daemon_app  # noqa: E402
from focusguard.commands.coach import coach_app  # noqa: E402
from focusguard.commands.github_cmd import github_app  # noqa: E402
from focusguard.commands.privacy import privacy_app  # noqa: E402

app.command()(start)
app.command()(stop)
app.command()(report)
app.command()(stats)
app.add_typer(goal_app, name="goal", help="Manage focus goals")
app.add_typer(daemon_app, name="daemon", help="Background daemon management")
app.add_typer(coach_app, name="coach", help="AI coaching & personality modes")
app.add_typer(github_app, name="github", help="GitHub integration")
app.add_typer(privacy_app, name="privacy", help="Privacy controls")


# ── Convenience aliases ──────────────────────────────────────────────────────

@app.command(hidden=True)
def roast() -> None:
    """Get roasted about your productivity."""
    from focusguard.commands.coach import _run_personality_report
    _run_personality_report("roast")


@app.command(hidden=True)
def help_me() -> None:
    """Ask the AI coach for help (alias for `coach help`)."""
    from focusguard.commands.coach import _run_help
    _run_help()


# Allow `python -m focusguard`
if __name__ == "__main__":
    app()
