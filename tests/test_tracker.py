"""Tests for the activity tracker classification logic."""

from unittest.mock import patch, MagicMock

from focusguard.core.tracker import ActivityTracker


class TestAppClassification:
    """Test the app → category classification logic."""

    def setup_method(self):
        with patch("focusguard.core.tracker.load_config") as mock_config:
            config = MagicMock()
            config.tracker.poll_interval = 60
            config.tracker.idle_threshold = 300
            config.tracker.app_categories = {
                "coding": ["code", "vscode", "terminal", "iterm", "vim", "cursor", "zed"],
                "browser": ["chrome", "firefox", "safari", "arc"],
                "communication": ["slack", "discord", "zoom"],
                "entertainment": ["youtube", "netflix", "spotify", "reddit"],
                "documentation": ["notion", "obsidian", "docs"],
            }
            config.security.blocklist = []
            mock_config.return_value = config
            self.tracker = ActivityTracker()

    def test_classify_vscode(self):
        assert self.tracker._classify_app("Visual Studio Code", "main.py") == "coding"

    def test_classify_terminal(self):
        assert self.tracker._classify_app("Terminal", "zsh") == "coding"

    def test_classify_chrome(self):
        assert self.tracker._classify_app("Google Chrome", "Google Search") == "browser"

    def test_classify_youtube_in_browser(self):
        assert self.tracker._classify_app("Chrome", "YouTube - Video Title") == "entertainment"

    def test_classify_slack(self):
        assert self.tracker._classify_app("Slack", "#general") == "communication"

    def test_classify_notion(self):
        assert self.tracker._classify_app("Notion", "Project Wiki") == "documentation"

    def test_classify_unknown_app(self):
        assert self.tracker._classify_app("RandomApp", "Something") == "other"

    def test_classify_case_insensitive(self):
        """Classification should be case-insensitive."""
        assert self.tracker._classify_app("VISUAL STUDIO CODE", "FILE.PY") == "coding"

    def test_classify_cursor(self):
        assert self.tracker._classify_app("Cursor", "project") == "coding"

    def test_classify_spotify(self):
        assert self.tracker._classify_app("Spotify", "Playing music") == "entertainment"
