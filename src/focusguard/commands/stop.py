"""focusguard stop — Stop the activity tracker."""

from __future__ import annotations

import os
import signal
import sys

import psutil
import typer
from rich.console import Console

console = Console()


def stop() -> None:
    """Stop the FocusGuard tracker.

    Sends a graceful shutdown signal to the running tracker process.
    """
    from focusguard.core.tracker import get_tracker_pid
    from focusguard.config import PID_FILE

    pid = get_tracker_pid()

    if pid is None:
        console.print("[yellow]⚠ FocusGuard is not running.[/yellow]")
        raise typer.Exit(1)

    try:
        if sys.platform == "win32":
            # Windows: use psutil to terminate
            proc = psutil.Process(pid)
            proc.terminate()
        else:
            # Unix: send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

        console.print(f"[green]✓[/green] Sent stop signal to FocusGuard (PID: {pid})")

        # Wait briefly for the process to exit
        try:
            proc = psutil.Process(pid)
            proc.wait(timeout=5)
            console.print("[green]✓[/green] FocusGuard stopped successfully")
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            pass

    except ProcessLookupError:
        # Process already dead, clean up PID file
        PID_FILE.unlink(missing_ok=True)
        console.print("[yellow]⚠ Process was already stopped. Cleaned up PID file.[/yellow]")

    except PermissionError:
        console.print("[red]✗ Permission denied. Try running with elevated privileges.[/red]")
        raise typer.Exit(1)
