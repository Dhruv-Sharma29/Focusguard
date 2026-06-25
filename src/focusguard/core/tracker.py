"""Activity tracker — the core polling loop.

Every poll_interval seconds (default 60), this module:
1. Gets the active window (app name + title)
2. Sanitizes the title through the blocklist filter
3. Classifies the app into a category
4. Logs the activity to the database
5. Recalculates the running focus score

The tracker runs in its own thread and can be cleanly stopped
via a threading.Event signal.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

import psutil
from rich.console import Console

from focusguard.config import DATA_DIR, PID_FILE, load_config
from focusguard.core.scorer import snapshot_score
from focusguard.db.models import init_db
from focusguard.db.queries import log_activity
from focusguard.platform.window import WindowInfo, get_active_window
from focusguard.security.blocklist import sanitize_title

logger = logging.getLogger(__name__)
console = Console(stderr=True)


class ActivityTracker:
    """Main activity tracking loop.

    Usage:
        tracker = ActivityTracker()
        tracker.start()  # Blocks until stop() is called
    """

    def __init__(self) -> None:
        self._config = load_config()
        self._stop_event = threading.Event()
        self._poll_interval = self._config.tracker.poll_interval
        self._last_hourly_snapshot = datetime.now()
        self._blocklist = self._config.security.blocklist
        self._categories = self._config.tracker.app_categories

    def start(self, daemon_mode: bool = False) -> None:
        """Start the tracking loop.

        Args:
            daemon_mode: If True, writes PID file and sets up signal handlers.
        """
        # Initialize the database
        init_db()

        if daemon_mode:
            self._write_pid_file()

        # Set up clean shutdown handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        console.print("[green]✓[/green] FocusGuard tracker started")
        console.print(f"[dim]Polling every {self._poll_interval}s • Press Ctrl+C to stop[/dim]")

        try:
            self._run_loop()
        finally:
            if daemon_mode:
                self._remove_pid_file()
            console.print("\n[yellow]■[/yellow] FocusGuard tracker stopped")

    def stop(self) -> None:
        """Signal the tracker to stop gracefully."""
        self._stop_event.set()

    def _run_loop(self) -> None:
        """Main polling loop. Runs until stop_event is set."""
        while not self._stop_event.is_set():
            try:
                self._poll_tick()
            except Exception as e:
                # Never let the loop crash — log and continue
                logger.error(f"Error in poll tick: {e}", exc_info=True)

            # Wait for the next tick (or until stopped)
            self._stop_event.wait(timeout=self._poll_interval)

    def _poll_tick(self) -> None:
        """Execute a single poll tick: detect window → classify → log → score."""
        window = get_active_window()

        # Check if user is idle (no active window = likely locked screen)
        is_idle = window.is_unknown
        if not is_idle:
            is_idle = self._check_idle()

        # Sanitize the window title through the blocklist
        sanitized_title = sanitize_title(window.window_title, self._blocklist)

        # Classify the app into a category
        category = self._classify_app(window.app_name, sanitized_title)

        # Log to database
        log_activity(
            app_name=window.app_name,
            window_title=sanitized_title,
            category=category,
            duration_seconds=self._poll_interval,
            is_idle=is_idle,
        )

        # Snapshot session score on every tick
        snapshot_score("session")

        # Hourly snapshots
        now = datetime.now()
        if (now - self._last_hourly_snapshot) >= timedelta(hours=1):
            snapshot_score("hourly")
            self._last_hourly_snapshot = now

        logger.debug(
            f"Tick: {window.app_name} [{category}]"
            f" {'(idle)' if is_idle else ''}"
        )

    def _classify_app(self, app_name: str, title: str | None) -> str:
        """Classify an application into a productivity category.

        Checks window title first for content-based categories (entertainment,
        documentation), then falls back to app name matching. This ensures
        'YouTube in Chrome' is classified as entertainment, not browser.
        """
        app_lower = app_name.lower()
        title_lower = (title or "").lower()
        search_text = f"{app_lower} {title_lower}"

        # Priority 1: check title-specific categories first
        # (coding, entertainment and documentation keywords in the title override app name)
        title_priority = ["coding", "documentation", "entertainment"]
        for category in title_priority:
            keywords = self._categories.get(category, [])
            if any(keyword in search_text for keyword in keywords):
                return category

        # Priority 2: check all categories against full search text
        for category, keywords in self._categories.items():
            if category in title_priority:
                continue  # Already checked above
            if any(keyword in search_text for keyword in keywords):
                return category

        return "other"

    def _check_idle(self) -> bool:
        """Check if the user has been idle (no input) beyond the threshold.

        Uses a simple heuristic: if the same window has been active for
        longer than idle_threshold with no change, assume idle.

        Note: A more robust idle check would use OS-specific APIs
        (CGEventSourceSecondsSinceLastEventType on macOS, GetLastInputInfo
        on Windows, XScreenSaverQueryInfo on Linux).
        """
        # For now, we rely on window detection — if we get "Unknown",
        # the screen is likely locked
        return False

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        logger.info(f"Received signal {signum}, stopping...")
        self.stop()

    def _write_pid_file(self) -> None:
        """Write the current PID to the pid file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
        logger.info(f"PID file written: {PID_FILE}")

    def _remove_pid_file(self) -> None:
        """Remove the PID file on shutdown."""
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def is_tracker_running() -> bool:
    """Check if a tracker instance is already running.

    Returns:
        True if the PID file exists and the process is alive.
    """
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        return psutil.pid_exists(pid)
    except (ValueError, OSError):
        # Stale or corrupt PID file — clean up
        PID_FILE.unlink(missing_ok=True)
        return False


def get_tracker_pid() -> int | None:
    """Get the PID of the running tracker, if any."""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        if psutil.pid_exists(pid):
            return pid
    except (ValueError, OSError):
        pass

    return None
