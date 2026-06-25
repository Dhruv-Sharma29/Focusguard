"""focusguard coach — AI coaching and personality commands."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from focusguard.config import load_config
from focusguard.db import queries
from focusguard.db.models import init_db
from focusguard.personality.modes import generate_nudge_message, get_personality
from focusguard.ui.themes import get_theme, score_style

console = Console()
coach_app = typer.Typer(no_args_is_help=True)


@coach_app.command("help")
def coach_help(
    breakdown: Annotated[
        bool,
        typer.Option("--breakdown", "-b", help="Break current goal into subtasks."),
    ] = False,
) -> None:
    """Ask the AI coach for help.

    Sends only your current goal + time stuck to the AI. Nothing else.
    Requires AI to be enabled: focusguard coach enable
    """
    _run_help(breakdown=breakdown)


@coach_app.command("enable")
def enable_ai(
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help="AI provider: 'ollama' or 'openai'."),
    ] = "ollama",
) -> None:
    """Enable AI coaching."""
    from focusguard.config import save_config
    
    config = load_config()
    config.ai.enabled = True
    config.ai.provider = provider
    save_config(config)

    console.print(f"\n  [green]✓[/green] AI coaching enabled with provider: [cyan]{provider}[/cyan]")
    if provider == "ollama":
        console.print("  [dim]Make sure Ollama is running: ollama serve[/dim]")
        console.print("  [dim]Pull the default model: ollama pull llama3.2:3b[/dim]")
    elif provider == "openai":
        console.print("  [dim]Set your API key: focusguard coach setup-openai[/dim]")
    console.print()


@coach_app.command("disable")
def disable_ai() -> None:
    """Disable AI coaching (fallback to local templates)."""
    from focusguard.config import save_config
    
    config = load_config()
    config.ai.enabled = False
    save_config(config)
    
    console.print("\n  [yellow]■[/yellow] AI coaching disabled. Using local text templates instead.\n")


@coach_app.command("setup-openai")
def setup_openai() -> None:
    """Configure OpenAI API key (stored securely in OS keyring)."""
    from focusguard.security.keyring_store import store_secret

    api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
    store_secret("openai_api_key", api_key)
    console.print("\n  [green]✓[/green] API key stored securely in OS keyring.")
    console.print("  [dim]Your key is never written to a config file.[/dim]\n")


@coach_app.command("mode")
def set_mode(
    mode: Annotated[str, typer.Argument(help="Personality: coach, strict, friend, roast")],
) -> None:
    """Switch personality mode."""
    valid = {"coach", "strict", "friend", "roast"}
    if mode not in valid:
        console.print(f"  [red]✗[/red] Unknown mode: {mode}")
        console.print(f"  [dim]Valid modes: {', '.join(valid)}[/dim]")
        raise typer.Exit(1)

    personality = get_personality(mode)
    console.print(f"\n  {personality.emoji} Switched to [bold]{personality.name}[/bold] mode")
    console.print(f"  [dim]{personality.tagline}[/dim]\n")


@coach_app.command("nudge")
def nudge() -> None:
    """Get a nudge based on your current activity."""
    init_db()
    _run_personality_report(load_config().personality.mode)


@coach_app.command("roast")
def roast() -> None:
    """Get roasted about your productivity."""
    init_db()
    _run_personality_report("roast")


# ── Internal helpers ─────────────────────────────────────────────────────────


def _run_personality_report(mode: str) -> None:
    """Generate a personality-flavored productivity report."""
    init_db()
    theme = get_theme(mode)
    personality = get_personality(mode)
    config = load_config()

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Gather context
    from focusguard.core.scorer import calculate_focus_score
    score = calculate_focus_score(today_start, now)
    coding_min = queries.get_coding_minutes(today_start, now)
    distraction_min = queries.get_distraction_minutes(today_start, now)
    top_distractions = queries.get_top_distractions(1, today_start, now)
    top_dist_name = top_distractions[0]["app_name"] if top_distractions else "nothing"
    active_goals = queries.get_active_goals()
    goal_desc = active_goals[0]["description"] if active_goals else "no goal set"

    context = {
        "score": score,
        "coding_min": coding_min,
        "distraction_min": distraction_min,
        "top_distraction": top_dist_name,
        "goal": goal_desc,
        "idle_minutes": max(0, (now - today_start).seconds / 60 - coding_min),
    }

    # Try AI first, fall back to templates
    message = None
    if config.ai.enabled:
        try:
            from focusguard.integrations.llm import chat
            from focusguard.personality.prompts import get_system_prompt

            system_prompt = get_system_prompt(mode)
            user_msg = (
                f"My focus score is {score:.0f}/100. "
                f"I've coded for {coding_min:.0f} min and been distracted for {distraction_min:.0f} min. "
                f"Top distraction: {top_dist_name}. "
                f"Current goal: {goal_desc}."
            )
            message = chat(system_prompt, user_msg)
        except Exception as e:
            message = None  # Fall through to template

    if message is None:
        message = generate_nudge_message(mode, context)

    # Render
    s_style = score_style(theme, score)
    console.print()
    console.print(Panel(
        f"\n  [{s_style}]{score:.0f}/100[/{s_style}]  •  "
        f"⌨️ {coding_min:.0f}m coding  •  📱 {distraction_min:.0f}m distraction\n\n"
        f"  {message}\n",
        title=f"{personality.emoji} [{theme.primary}]{personality.name} Mode[/{theme.primary}]",
        border_style=theme.border,
        padding=(0, 2),
    ))
    console.print()


def _run_help(breakdown: bool = False) -> None:
    """Run the AI help flow."""
    init_db()
    config = load_config()
    theme = get_theme(config.personality.mode)
    mode = config.personality.mode

    # Gather minimal context
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_goals = queries.get_active_goals()
    if not active_goals:
        console.print(f"\n  [{theme.warning}]⚠ No active goal set.[/{theme.warning}]")
        console.print(f"  [dim]Set one first: focusguard goal add \"...\"[/dim]\n")
        return

    goal = active_goals[0]
    goal_desc = goal["description"]
    created = goal.get("created_at", "")

    # Calculate time on goal
    try:
        created_dt = datetime.fromisoformat(created)
        elapsed = now - created_dt
        if elapsed.days > 0:
            time_str = f"{elapsed.days}d {elapsed.seconds // 3600}h"
        else:
            time_str = f"{elapsed.seconds // 3600}h {(elapsed.seconds % 3600) // 60}m"
    except ValueError:
        time_str = "unknown"

    # Get recent apps (names only — no titles or URLs)
    recent_activity = queries.get_activity_range(now - __import__("datetime").timedelta(minutes=30), now)
    recent_apps = list(dict.fromkeys(a["app_name"] for a in recent_activity[-5:]))
    recent_apps_str = ", ".join(recent_apps) if recent_apps else "none detected"

    from focusguard.core.scorer import calculate_focus_score
    score = calculate_focus_score(today_start, now)

    if not config.ai.enabled:
        console.print(f"\n  [{theme.warning}]⚠ AI is not enabled.[/{theme.warning}]")
        console.print(f"  [dim]Enable with: focusguard coach enable[/dim]")
        console.print(f"\n  [{theme.primary}]Current goal:[/{theme.primary}] {goal_desc}")
        console.print(f"  [{theme.muted}]Working for: {time_str}[/{theme.muted}]")
        console.print(f"  [{theme.muted}]Recent apps: {recent_apps_str}[/{theme.muted}]")
        console.print(f"\n  [dim]💡 Try rubber ducking: explain what you're stuck on out loud.[/dim]\n")
        return

    try:
        from focusguard.integrations.llm import chat
        from focusguard.personality.prompts import (
            format_breakdown_prompt,
            format_help_prompt,
            get_system_prompt,
        )

        system_prompt = get_system_prompt(mode)

        if breakdown:
            user_msg = format_breakdown_prompt(goal_desc, time_str, mode)
        else:
            user_msg = format_help_prompt(goal_desc, time_str, recent_apps_str, score, mode)

        response = chat(system_prompt, user_msg)

        personality = get_personality(mode)
        console.print()
        console.print(Panel(
            f"\n  {response}\n",
            title=f"{personality.emoji} [{theme.primary}]{personality.name}[/{theme.primary}]",
            subtitle=f"[{theme.muted}]Goal: {goal_desc} • {time_str}[/{theme.muted}]",
            border_style=theme.border,
            padding=(0, 2),
        ))
        console.print()

    except Exception as e:
        console.print(f"\n  [red]✗ AI error: {e}[/red]")
        console.print(f"  [dim]Falling back to local mode.[/dim]\n")
