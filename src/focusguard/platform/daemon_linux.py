"""Linux daemon handler — systemd user service management.

Installs a systemd user service at ~/.config/systemd/user/ that keeps
FocusGuard running in the background.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from focusguard.config import LOG_DIR

SERVICE_NAME = "focusguard.service"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_PATH = SYSTEMD_USER_DIR / SERVICE_NAME


class LinuxDaemon:
    """Linux systemd user service handler."""

    def install(self) -> None:
        """Generate and install the systemd user service."""
        SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        python_path = sys.executable

        service_content = dedent(f"""\
            [Unit]
            Description=FocusGuard Activity Tracker
            After=graphical-session.target
            Documentation=https://github.com/focusguard/focusguard

            [Service]
            Type=simple
            ExecStart={python_path} -m focusguard start --daemon-mode
            Restart=on-failure
            RestartSec=10
            Environment=DISPLAY=:0

            # Security hardening
            PrivateTmp=true
            NoNewPrivileges=true

            [Install]
            WantedBy=default.target
        """)

        SERVICE_PATH.write_text(service_content)

        # Reload systemd and enable the service
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", SERVICE_NAME], check=True, capture_output=True)
        subprocess.run(["systemctl", "--user", "start", SERVICE_NAME], check=True, capture_output=True)

    def uninstall(self) -> None:
        """Stop, disable, and remove the systemd service."""
        subprocess.run(["systemctl", "--user", "stop", SERVICE_NAME], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", SERVICE_NAME], capture_output=True)

        if SERVICE_PATH.exists():
            SERVICE_PATH.unlink()

        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    def is_installed(self) -> bool:
        """Check if the service file exists."""
        return SERVICE_PATH.exists()

    def is_active(self) -> bool:
        """Check if the service is currently active."""
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "active"
