"""focusguard daemon — Install/uninstall background daemon.

Delegates to platform-specific modules for launchd (macOS),
systemd (Linux), or Task Scheduler (Windows).
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console

console = Console()

daemon_app = typer.Typer(no_args_is_help=True)


@daemon_app.command()
def install() -> None:
    """Install FocusGuard as a background service.

    Sets up the OS-specific daemon so FocusGuard starts automatically
    on login and survives terminal close.
    """
    handler = _get_platform_handler()
    try:
        handler.install()
        console.print("[green]✓[/green] FocusGuard daemon installed successfully")
        console.print("[dim]It will start automatically on login.[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Failed to install daemon: {e}[/red]")
        raise typer.Exit(1)


@daemon_app.command()
def uninstall() -> None:
    """Remove the FocusGuard background service."""
    handler = _get_platform_handler()
    try:
        handler.uninstall()
        console.print("[green]✓[/green] FocusGuard daemon uninstalled")
    except Exception as e:
        console.print(f"[red]✗ Failed to uninstall daemon: {e}[/red]")
        raise typer.Exit(1)


@daemon_app.command()
def status() -> None:
    """Check if the background daemon is running."""
    from focusguard.core.tracker import is_tracker_running, get_tracker_pid

    if is_tracker_running():
        pid = get_tracker_pid()
        console.print(f"[green]● FocusGuard is running[/green] (PID: {pid})")
    else:
        console.print("[red]● FocusGuard is not running[/red]")
        console.print("[dim]Start with: focusguard start -d[/dim]")


def _get_platform_handler():  # type: ignore[no-untyped-def]
    """Get the appropriate daemon handler for the current platform."""
    if sys.platform == "darwin":
        from focusguard.platform.daemon_macos import MacOSDaemon
        return MacOSDaemon()
    elif sys.platform == "linux":
        from focusguard.platform.daemon_linux import LinuxDaemon
        return LinuxDaemon()
    elif sys.platform == "win32":
        from focusguard.platform.daemon_windows import WindowsDaemon
        return WindowsDaemon()
    else:
        console.print(f"[red]✗ Unsupported platform: {sys.platform}[/red]")
        raise typer.Exit(1)
