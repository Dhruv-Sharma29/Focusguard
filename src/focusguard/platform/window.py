"""Cross-platform active window detection.

Uses PyWinCtl for a unified API across macOS, Linux, and Windows.
Falls back to psutil process info if window title is unavailable.

On macOS: requires Accessibility permissions (System Preferences → Privacy).
On Linux/X11: works out of the box. Wayland support is limited.
On Windows: works out of the box.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from rich.console import Console

console = Console(stderr=True)


@dataclass
class WindowInfo:
    """Information about the currently active window."""

    app_name: str
    window_title: str | None
    pid: int | None = None

    @property
    def is_unknown(self) -> bool:
        return self.app_name == "Unknown"


def get_active_window() -> WindowInfo:
    """Get information about the currently active (foreground) window.

    Returns:
        A WindowInfo object. If detection fails, returns app_name="Unknown".
    """
    try:
        return _get_active_window_pywinctl()
    except Exception:
        pass

    # Fallback: platform-specific methods
    try:
        if sys.platform == "darwin":
            return _get_active_window_macos()
        elif sys.platform == "win32":
            return _get_active_window_windows()
        else:
            return _get_active_window_linux()
    except Exception:
        return WindowInfo(app_name="Unknown", window_title=None)


def _get_active_window_pywinctl() -> WindowInfo:
    """Use PyWinCtl for cross-platform window detection."""
    import pywinctl as pwc  # type: ignore[import-untyped]

    window = pwc.getActiveWindow()
    if window is None:
        return WindowInfo(app_name="Unknown", window_title=None)

    title = window.title or ""
    # Try to extract app name from the window object
    # PyWinCtl provides getAppName() on some platforms
    try:
        app_name = window.getAppName() or _extract_app_name(title)
    except (AttributeError, Exception):
        app_name = _extract_app_name(title)

    return WindowInfo(
        app_name=app_name,
        window_title=title if title else None,
    )


def _get_active_window_macos() -> WindowInfo:
    """macOS fallback: use AppKit to get the frontmost application."""
    from AppKit import NSWorkspace  # type: ignore[import-untyped]

    workspace = NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()

    if active_app is None:
        return WindowInfo(app_name="Unknown", window_title=None)

    app_name = active_app.localizedName() or "Unknown"
    # AppKit doesn't give us the window title directly without accessibility
    return WindowInfo(app_name=app_name, window_title=None)


def _get_active_window_windows() -> WindowInfo:
    """Windows fallback: use win32gui."""
    import win32gui  # type: ignore[import-untyped]

    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd) or ""
    app_name = _extract_app_name(title)

    return WindowInfo(
        app_name=app_name,
        window_title=title if title else None,
    )


def _get_active_window_linux() -> WindowInfo:
    """Linux fallback: use xdotool or xprop."""
    import subprocess

    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            title = result.stdout.strip()
            return WindowInfo(
                app_name=_extract_app_name(title),
                window_title=title if title else None,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return WindowInfo(app_name="Unknown", window_title=None)


def _extract_app_name(title: str) -> str:
    """Extract a likely app name from a window title.

    Common patterns:
        "filename.py — Visual Studio Code" → "Visual Studio Code"
        "Terminal — zsh" → "Terminal"
        "Google Chrome" → "Google Chrome"
    """
    if not title:
        return "Unknown"

    # Try splitting on common separators (right side is usually the app)
    for separator in [" — ", " - ", " – ", " | "]:
        if separator in title:
            parts = title.split(separator)
            # The app name is usually the last part
            return parts[-1].strip()

    return title.strip()


def check_accessibility_permissions() -> bool:
    """Check if the app has accessibility permissions (macOS only).

    Returns:
        True if permissions are granted or not needed (non-macOS).
    """
    if sys.platform != "darwin":
        return True

    try:
        import subprocess

        # Try to get a window — if it fails, permissions are likely missing
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
