"""Windows daemon handler — Task Scheduler management.

Creates a scheduled task that runs FocusGuard at logon using pythonw.exe
(no visible console window).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TASK_NAME = "FocusGuard"


class WindowsDaemon:
    """Windows Task Scheduler handler."""

    def install(self) -> None:
        """Create a scheduled task to run FocusGuard at logon."""
        # Use pythonw.exe for windowless execution
        python_path = sys.executable
        pythonw_path = python_path.replace("python.exe", "pythonw.exe")
        if not Path(pythonw_path).exists():
            pythonw_path = python_path

        command = f'"{pythonw_path}" -m focusguard start --daemon-mode'

        # Create the task using schtasks
        subprocess.run(
            [
                "schtasks", "/Create",
                "/TN", TASK_NAME,
                "/TR", command,
                "/SC", "ONLOGON",
                "/RL", "LIMITED",
                "/F",  # Force overwrite if exists
            ],
            check=True,
            capture_output=True,
        )

        # Start it immediately
        subprocess.run(
            ["schtasks", "/Run", "/TN", TASK_NAME],
            capture_output=True,
        )

    def uninstall(self) -> None:
        """Remove the scheduled task."""
        # Stop the running process first
        subprocess.run(
            ["schtasks", "/End", "/TN", TASK_NAME],
            capture_output=True,
        )
        subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True,
        )

    def is_installed(self) -> bool:
        """Check if the task exists."""
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True,
        )
        return result.returncode == 0
