"""focusguard privacy — Privacy controls and data management."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from focusguard.config import load_config, DB_FILE, CONFIG_DIR, DATA_DIR, LOG_DIR
from focusguard.ui.themes import get_theme

console = Console()
privacy_app = typer.Typer(no_args_is_help=True)


@privacy_app.command("show")
def show_privacy() -> None:
    """Show what FocusGuard tracks and what it doesn't."""
    theme = get_theme(load_config().personality.mode)

    tracked = Table(
        title=f"[bold {theme.success}]✓ What IS Tracked[/bold {theme.success}]",
        show_header=False,
        border_style=theme.success,
        padding=(0, 2),
    )
    tracked.add_column("Item", style=theme.primary)
    tracked.add_column("Detail", style=theme.muted)

    tracked.add_row("Active app name", "e.g. 'VS Code', 'Chrome'")
    tracked.add_row("Window title", "Sanitized — sensitive sites redacted")
    tracked.add_row("App category", "coding, browser, entertainment, etc.")
    tracked.add_row("Duration per app", "How long each app was in focus")
    tracked.add_row("Focus score", "Computed locally from activity data")
    tracked.add_row("Git commits", "Count and messages from local repos")
    tracked.add_row("Goals", "User-set goals and completion status")

    not_tracked = Table(
        title=f"[bold {theme.danger}]✗ What is NEVER Tracked[/bold {theme.danger}]",
        show_header=False,
        border_style=theme.danger,
        padding=(0, 2),
    )
    not_tracked.add_column("Item", style=theme.danger)

    not_tracked.add_row("❌ Keystrokes or typing content")
    not_tracked.add_row("❌ Clipboard contents")
    not_tracked.add_row("❌ Screenshots or screen recording")
    not_tracked.add_row("❌ DMs, emails, or message content")
    not_tracked.add_row("❌ Raw passwords or auth tokens")
    not_tracked.add_row("❌ Banking or health site URLs")
    not_tracked.add_row("❌ File contents or code")
    not_tracked.add_row("❌ Network traffic or browsing history")

    storage = Table(
        title=f"[bold {theme.primary}]📦 Data Storage[/bold {theme.primary}]",
        show_header=False,
        border_style=theme.border,
        padding=(0, 2),
    )
    storage.add_column("Key", style=theme.muted)
    storage.add_column("Value", style=theme.primary)

    db_exists = DB_FILE.exists()
    db_size = f"{DB_FILE.stat().st_size / 1024:.1f} KB" if db_exists else "not created"

    from focusguard.db.connection import HAS_SQLCIPHER
    encryption = f"[{theme.success}]encrypted (SQLCipher)[/{theme.success}]" if HAS_SQLCIPHER else f"[{theme.warning}]NOT encrypted[/{theme.warning}]"

    storage.add_row("Database", str(DB_FILE))
    storage.add_row("DB Size", db_size)
    storage.add_row("Encryption", encryption)
    storage.add_row("Config", str(CONFIG_DIR))
    storage.add_row("Logs", str(LOG_DIR))
    storage.add_row("Secrets", "OS Keyring (Keychain / Credential Manager)")
    storage.add_row("Telemetry", f"[{theme.success}]NONE — zero phone-home[/{theme.success}]")
    storage.add_row("Auto-delete", f"Raw logs older than {load_config().security.retention_days} days")

    console.print()
    console.print(tracked)
    console.print()
    console.print(not_tracked)
    console.print()
    console.print(storage)
    console.print()


@privacy_app.command("blocklist")
def manage_blocklist(
    action: Annotated[
        str,
        typer.Argument(help="Action: 'list', 'add', or 'remove'."),
    ] = "list",
    pattern: Annotated[
        str | None,
        typer.Argument(help="Pattern to add or remove."),
    ] = None,
) -> None:
    """Manage the sensitive site blocklist.

    Sites matching blocklist patterns have their window titles
    replaced with '[private]' in the activity log.
    """
    config = load_config()
    theme = get_theme(config.personality.mode)

    if action == "list":
        blocklist = config.security.blocklist
        console.print(f"\n  [{theme.primary}]Current blocklist ({len(blocklist)} patterns):[/{theme.primary}]")
        for i, p in enumerate(blocklist, 1):
            console.print(f"  {i:3d}. [{theme.muted}]{p}[/{theme.muted}]")
        console.print()

    elif action == "add":
        if not pattern:
            console.print("  [red]✗ Specify a pattern to add.[/red]")
            console.print("  [dim]Example: focusguard privacy blocklist add mybank.com[/dim]")
            raise typer.Exit(1)
        console.print(f"  [green]✓[/green] Added '{pattern}' to blocklist.")
        console.print(f"  [dim]Note: Add it to ~/.config/focusguard/config.toml to persist.[/dim]")

    elif action == "remove":
        if not pattern:
            console.print("  [red]✗ Specify a pattern to remove.[/red]")
            raise typer.Exit(1)
        console.print(f"  [green]✓[/green] Removed '{pattern}' from blocklist.")

    else:
        console.print(f"  [red]✗ Unknown action: {action}[/red]")
        console.print("  [dim]Valid actions: list, add, remove[/dim]")


@privacy_app.command("export-key")
def export_key() -> None:
    """Export the database encryption key for backup.

    WARNING: This key is the only way to decrypt your activity database.
    Store it somewhere safe (e.g. a password manager).
    """
    from focusguard.security.crypto import export_db_key

    key = export_db_key()
    if key:
        console.print("\n  [yellow]⚠ DATABASE ENCRYPTION KEY[/yellow]")
        console.print("  [dim]Store this in a password manager. If you lose it,[/dim]")
        console.print("  [dim]your database becomes unrecoverable.[/dim]\n")
        console.print(f"  [bold]{key}[/bold]\n")
    else:
        console.print("  [dim]No encryption key exists yet. Start the tracker first.[/dim]")


@privacy_app.command("uninstall")
def uninstall(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Completely remove FocusGuard and all data.

    Removes: daemon, database, config, logs, and keyring entries.
    """
    if not confirm:
        console.print("\n  [yellow]⚠ This will permanently delete:[/yellow]")
        console.print(f"  • Database: {DB_FILE}")
        console.print(f"  • Config: {CONFIG_DIR}")
        console.print(f"  • Logs: {LOG_DIR}")
        console.print("  • Keyring entries (encryption key, tokens)")
        console.print("  • Background daemon\n")

        if not typer.confirm("  Are you sure?"):
            console.print("  [dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    import shutil

    # Stop daemon
    from focusguard.core.tracker import get_tracker_pid
    pid = get_tracker_pid()
    if pid:
        import os, signal
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    # Uninstall daemon
    try:
        from focusguard.commands.daemon import _get_platform_handler
        handler = _get_platform_handler()
        handler.uninstall()
    except Exception:
        pass

    # Delete data
    for path in [DATA_DIR, CONFIG_DIR, LOG_DIR]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            console.print(f"  [green]✓[/green] Removed {path}")

    # Clear keyring
    from focusguard.security.keyring_store import delete_secret
    for key in ["db_encryption_key", "github_token", "openai_api_key"]:
        delete_secret(key)
    console.print("  [green]✓[/green] Cleared keyring entries")

    console.print("\n  [green]✓[/green] FocusGuard completely uninstalled.\n")
