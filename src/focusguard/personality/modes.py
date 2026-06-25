"""Personality mode definitions for FocusGuard.

Each mode defines the tone, style, and behavior of the coaching system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PersonalityMode(str, Enum):
    """Available personality modes."""

    COACH = "coach"
    STRICT = "strict"
    FRIEND = "friend"
    ROAST = "roast"


@dataclass(frozen=True)
class Personality:
    """A personality mode definition."""

    mode: PersonalityMode
    name: str
    emoji: str
    tagline: str
    tone: str
    max_response_sentences: int
    uses_data_points: bool  # Whether to reference specific stats in messages


PERSONALITIES: dict[str, Personality] = {
    "coach": Personality(
        mode=PersonalityMode.COACH,
        name="Coach",
        emoji="🏋️",
        tagline="Encouraging and constructive",
        tone="supportive, actionable, and motivating",
        max_response_sentences=3,
        uses_data_points=True,
    ),
    "strict": Personality(
        mode=PersonalityMode.STRICT,
        name="Strict",
        emoji="📏",
        tagline="Direct and no-nonsense",
        tone="direct, factual, and uncompromising",
        max_response_sentences=2,
        uses_data_points=True,
    ),
    "friend": Personality(
        mode=PersonalityMode.FRIEND,
        name="Friend",
        emoji="🤝",
        tagline="Casual and empathetic",
        tone="casual, warm, and understanding",
        max_response_sentences=3,
        uses_data_points=False,
    ),
    "roast": Personality(
        mode=PersonalityMode.ROAST,
        name="Roast",
        emoji="🔥",
        tagline="Savage but funny",
        tone="brutally honest, witty, and savage",
        max_response_sentences=2,
        uses_data_points=True,
    ),
}


def get_personality(mode: str = "coach") -> Personality:
    """Get a personality definition by mode name."""
    return PERSONALITIES.get(mode, PERSONALITIES["coach"])


def generate_nudge_message(mode: str, context: dict) -> str:
    """Generate a personality-appropriate nudge message without AI.

    Uses templates for quick, local responses when AI is not enabled.

    Args:
        mode: Personality mode name.
        context: Dict with keys like 'score', 'coding_min', 'distraction_min',
                 'top_distraction', 'goal', 'idle_minutes'.
    """
    score = context.get("score", 0)
    coding = context.get("coding_min", 0)
    distraction = context.get("distraction_min", 0)
    top_dist = context.get("top_distraction", "something")
    goal = context.get("goal", "your task")
    idle = context.get("idle_minutes", 0)

    if mode == "coach":
        if score >= 80:
            return f"🏋️ Great focus today! {coding:.0f} min of coding. Keep the momentum going."
        elif score >= 50:
            return (
                f"🏋️ Decent progress — {coding:.0f} min coding so far. "
                f"You can push through on \"{goal}\". One step at a time."
            )
        else:
            return (
                f"🏋️ You've been away from coding for {idle:.0f} min. "
                f"Let's refocus on \"{goal}\". What's the smallest next step?"
            )

    elif mode == "strict":
        if score >= 80:
            return f"📏 {score:.0f}/100. Acceptable. Don't get complacent."
        elif score >= 50:
            return f"📏 {distraction:.0f} min on {top_dist}. Not in today's plan."
        else:
            return f"📏 Focus score: {score:.0f}. This is below standard. Close {top_dist}. Now."

    elif mode == "friend":
        if score >= 80:
            return f"🤝 Hey, you're doing amazing! {coding:.0f} min of solid work. Take a breather if you need it 💙"
        elif score >= 50:
            return f"🤝 You've been at this for a while. Need a break? Sometimes stepping away helps."
        else:
            return f"🤝 Hey, I noticed you've been a bit scattered. No judgment — want to talk through what's blocking you?"

    elif mode == "roast":
        if score >= 80:
            return f"🔥 {score:.0f}/100. Did someone hack your computer? This can't be you."
        elif score >= 50:
            return (
                f"🔥 {distraction:.0f} min on {top_dist}. "
                f"Your git contribution graph is crying right now."
            )
        else:
            return (
                f"🔥 Focus score: {score:.0f}. You've spent more time switching tabs "
                f"than actually working. Your IDE filed a missing persons report."
            )

    return f"Focus score: {score:.0f}/100"
