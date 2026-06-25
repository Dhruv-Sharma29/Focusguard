"""Tests for the focus score computation engine."""

from datetime import datetime

from focusguard.core.scorer import (
    calculate_focus_score,
    get_score_emoji,
    get_score_label,
    get_trend,
    snapshot_score,
)
from focusguard.db import queries


class TestCalculateFocusScore:
    def test_all_coding_gives_high_score(self, mock_db):
        """100% coding time should yield a high focus score."""
        for _ in range(10):
            queries.log_activity("VS Code", "main.py", "coding", 60, False)

        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert score >= 80.0

    def test_all_entertainment_gives_low_score(self, mock_db):
        """100% entertainment should yield a low score."""
        for _ in range(10):
            queries.log_activity("YouTube", "Video", "entertainment", 60, False)

        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert score < 30.0

    def test_mixed_activity(self, sample_activity):
        """Mixed activity should give a moderate score."""
        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert 20.0 <= score <= 90.0

    def test_no_activity_returns_zero(self, mock_db):
        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today)
        assert score == 0.0

    def test_idle_entries_excluded(self, mock_db):
        """Idle entries should not affect the score."""
        queries.log_activity("VS Code", "main.py", "coding", 60, False)
        queries.log_activity("Unknown", None, "other", 60, True)  # idle
        queries.log_activity("Unknown", None, "other", 60, True)  # idle

        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert score >= 80.0  # Only the coding entry counts

    def test_score_clamped_to_100(self, mock_db):
        for _ in range(50):
            queries.log_activity("VS Code", "file.py", "coding", 60, False)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert score <= 100.0

    def test_score_clamped_to_0(self, mock_db):
        for _ in range(50):
            queries.log_activity("YouTube", "Video", "entertainment", 60, False)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        score = calculate_focus_score(today, use_decay=False)
        assert score >= 0.0


class TestScoreHelpers:
    def test_emoji_green(self):
        assert get_score_emoji(85) == "🟢"

    def test_emoji_yellow(self):
        assert get_score_emoji(60) == "🟡"

    def test_emoji_red(self):
        assert get_score_emoji(30) == "🔴"

    def test_label_focused(self):
        assert get_score_label(85) == "Focused"

    def test_label_distracted(self):
        assert get_score_label(35) == "Distracted"

    def test_label_off_track(self):
        assert get_score_label(15) == "Off Track"


class TestSnapshotScore:
    def test_snapshot_saves_to_db(self, mock_db):
        queries.log_activity("VS Code", "file.py", "coding", 60, False)
        score = snapshot_score("session")
        assert score >= 0.0

        latest = queries.get_latest_score("session")
        assert latest is not None
        assert latest["score"] == score


class TestTrend:
    def test_trend_with_no_data(self, mock_db):
        assert get_trend() == "→"

    def test_trend_stable(self, mock_db):
        for _ in range(6):
            queries.save_focus_score(50.0, 30.0, 10.0, 50.0, "hourly")
        assert get_trend() == "→"
