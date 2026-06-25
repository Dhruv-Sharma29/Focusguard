"""macOS daemon handler — launchd plist management.

Installs a LaunchAgent plist at ~/Library/LaunchAgents/ that keeps
FocusGuard running in the background, surviving terminal close
and auto-starting on login.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from focusguard.config import LOG_DIR

PLIST_NAME = "com.focusguard.tracker.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / PLIST_NAME


class MacOSDaemon:
    """macOS launchd daemon handler."""

    def install(self) -> None:
        """Generate and install the launchd plist."""
        LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        python_path = sys.executable
        stdout_log = str(LOG_DIR / "daemon.log")
        stderr_log = str(LOG_DIR / "daemon.err")

        plist_content = dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.focusguard.tracker</string>

                <key>ProgramArguments</key>
                <array>
                    <string>{python_path}</string>
                    <string>-m</string>
                    <string>focusguard</string>
                    <string>start</string>
                    <string>--daemon-mode</string>
                </array>

                <key>RunAtLoad</key>
                <true/>

                <key>KeepAlive</key>
                <dict>
                    <key>SuccessfulExit</key>
                    <false/>
                </dict>

                <key>ThrottleInterval</key>
                <integer>10</integer>

                <key>StandardOutPath</key>
                <string>{stdout_log}</string>

                <key>StandardErrorPath</key>
                <string>{stderr_log}</string>

                <key>ProcessType</key>
                <string>Background</string>
            </dict>
            </plist>
        """)

        PLIST_PATH.write_text(plist_content)

        # Load the agent
        subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            check=True,
            capture_output=True,
        )

    def uninstall(self) -> None:
        """Unload and remove the launchd plist."""
        if PLIST_PATH.exists():
            # Unload first (ignore errors if not loaded)
            subprocess.run(
                ["launchctl", "unload", str(PLIST_PATH)],
                capture_output=True,
            )
            PLIST_PATH.unlink()

    def is_installed(self) -> bool:
        """Check if the plist is installed."""
        return PLIST_PATH.exists()

    def is_loaded(self) -> bool:
        """Check if the agent is loaded in launchctl."""
        result = subprocess.run(
            ["launchctl", "list", "com.focusguard.tracker"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
