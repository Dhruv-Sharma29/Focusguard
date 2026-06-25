"""Tests for personality modes and nudge message generation."""

from focusguard.personality.modes import (
    PersonalityMode,
    generate_nudge_message,
    get_personality,
    PERSONALITIES,
)
from focusguard.personality.prompts import (
    get_system_prompt,
    format_help_prompt,
    format_breakdown_prompt,
    SYSTEM_PROMPTS,
)


class TestPersonalityModes:
    def test_all_modes_defined(self):
        for mode in ["coach", "strict", "friend", "roast"]:
            p = get_personality(mode)
            assert p.name
            assert p.emoji
            assert p.tagline

    def test_unknown_mode_defaults_to_coach(self):
        p = get_personality("nonexistent")
        assert p.mode == PersonalityMode.COACH

    def test_mode_enum_values(self):
        assert PersonalityMode.COACH.value == "coach"
        assert PersonalityMode.ROAST.value == "roast"


class TestNudgeMessages:
    def _context(self, **overrides):
        defaults = {
            "score": 50.0,
            "coding_min": 30.0,
            "distraction_min": 20.0,
            "top_distraction": "YouTube",
            "goal": "Build auth system",
            "idle_minutes": 45.0,
        }
        defaults.update(overrides)
        return defaults

    def test_coach_high_score(self):
        msg = generate_nudge_message("coach", self._context(score=85))
        assert "🏋️" in msg
        assert "coding" in msg.lower() or "focus" in msg.lower()

    def test_coach_low_score(self):
        msg = generate_nudge_message("coach", self._context(score=30))
        assert "🏋️" in msg

    def test_strict_references_data(self):
        msg = generate_nudge_message("strict", self._context(score=45))
        assert "📏" in msg

    def test_friend_is_empathetic(self):
        msg = generate_nudge_message("friend", self._context(score=40))
        assert "🤝" in msg

    def test_roast_is_savage(self):
        msg = generate_nudge_message("roast", self._context(score=30))
        assert "🔥" in msg

    def test_all_modes_return_nonempty(self):
        ctx = self._context()
        for mode in ["coach", "strict", "friend", "roast"]:
            msg = generate_nudge_message(mode, ctx)
            assert len(msg) > 10


class TestPromptTemplates:
    def test_all_system_prompts_exist(self):
        for mode in ["coach", "strict", "friend", "roast"]:
            prompt = get_system_prompt(mode)
            assert len(prompt) > 50

    def test_unknown_mode_returns_coach(self):
        prompt = get_system_prompt("nonexistent")
        assert prompt == SYSTEM_PROMPTS["coach"]

    def test_help_prompt_includes_context(self):
        prompt = format_help_prompt(
            goal="Build auth",
            time_on_goal="2h 30m",
            recent_apps="VS Code, Chrome",
            score=65.0,
            personality_mode="coach",
        )
        assert "Build auth" in prompt
        assert "2h 30m" in prompt
        assert "65" in prompt

    def test_breakdown_prompt_includes_goal(self):
        prompt = format_breakdown_prompt(
            goal="Implement OAuth flow",
            time_on_goal="4h",
            personality_mode="strict",
        )
        assert "Implement OAuth flow" in prompt
        assert "strict" in prompt
