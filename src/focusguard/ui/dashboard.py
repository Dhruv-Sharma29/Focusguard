"""Rich terminal dashboard for FocusGuard.

Renders a full-screen productivity dashboard using Rich's Layout system
with panels for focus score, activity breakdown, timeline, and distractions.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from focusguard.config import load_config
from focusguard.core.scorer import (
    calculate_focus_score,
    get_score_emoji,
    get_score_label,
    get_trend,
)
from focusguard.core.tracker import is_tracker_running
from focusguard.db import queries
from focusguard.ui.themes import get_theme, score_style

console = Console()


def render_dashboard() -> None:
    """Render the full productivity dashboard to the terminal."""
    config = load_config()
    theme = get_theme(config.personality.mode)

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Gather data ──────────────────────────────────────────────────────
    score = calculate_focus_score(today_start, now)
    coding_min = queries.get_coding_minutes(today_start, now)
    distraction_min = queries.get_distraction_minutes(today_start, now)
    total_min = queries.get_total_active_minutes(today_start, now)
    trend = get_trend()
    top_distractions = queries.get_top_distractions(5, today_start, now)
    app_breakdown = queries.get_app_breakdown(today_start, now)
    hourly_data = queries.get_hourly_activity(today_start, now)
    git_commits = queries.get_git_commits_today()
    active_goals = queries.get_active_goals()
    tracker_running = is_tracker_running()

    # ── Build layout ─────────────────────────────────────────────────────
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=7),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=2),
    )

    # ── Header ───────────────────────────────────────────────────────────
    status_icon = "[green]●[/green]" if tracker_running else "[red]●[/red]"
    status_text = "tracking" if tracker_running else "stopped"
    header_text = Text.from_markup(
        f"  🛡️  [bold {theme.primary}]FocusGuard[/bold {theme.primary}]"
        f"  {status_icon} {status_text}"
        f"  │  {now.strftime('%A, %B %d %Y • %I:%M %p')}"
    )
    layout["header"].update(Panel(header_text, style=theme.border))

    # ── Left Panel: Score + Goals ────────────────────────────────────────
    score_color = score_style(theme, score)
    emoji = get_score_emoji(score)
    label = get_score_label(score)

    score_display = Text.from_markup(
        f"\n  {emoji} [{score_color}]{score:.0f}[/{score_color}]/100  {trend}\n"
        f"  [{theme.muted}]{label}[/{theme.muted}]\n"
    )

    # Time breakdown
    breakdown = Text.from_markup(
        f"\n  ⌨️  Coding     [{theme.success}]{_fmt_time(coding_min)}[/{theme.success}]\n"
        f"  📱 Distraction [{theme.danger}]{_fmt_time(distraction_min)}[/{theme.danger}]\n"
        f"  ⏱️  Total      [{theme.muted}]{_fmt_time(total_min)}[/{theme.muted}]\n"
        f"  📝 Commits    [{theme.secondary}]{git_commits}[/{theme.secondary}]\n"
    )

    # Active goals
    if active_goals:
        goal_lines = []
        for g in active_goals[:3]:
            elapsed = _time_since(g.get("created_at", ""))
            goal_lines.append(
                f"  → [{theme.primary}]{g['description']}[/{theme.primary}]"
                f" [{theme.muted}]({elapsed})[/{theme.muted}]"
            )
        goals_text = Text.from_markup("\n" + "\n".join(goal_lines) + "\n")
    else:
        goals_text = Text.from_markup(
            f"\n  [{theme.muted}]No active goals. Run: focusguard goal add \"...\"[/{theme.muted}]\n"
        )

    left_content = Group(
        Panel(score_display, title=f"[{theme.primary}]Focus Score[/{theme.primary}]",
              border_style=theme.border),
        Panel(breakdown, title=f"[{theme.primary}]Today[/{theme.primary}]",
              border_style=theme.border),
        Panel(goals_text, title=f"[{theme.primary}]Goals[/{theme.primary}]",
              border_style=theme.border),
    )
    layout["left"].update(left_content)

    # ── Right Panel: Activity Timeline + Breakdown ───────────────────────
    # Category breakdown table
    cat_table = Table(
        show_header=True,
        header_style=f"bold {theme.primary}",
        border_style=theme.border,
        title=f"[{theme.primary}]Activity Breakdown[/{theme.primary}]",
        expand=True,
    )
    cat_table.add_column("Category", style=theme.primary)
    cat_table.add_column("Time", justify="right")
    cat_table.add_column("Bar", ratio=2)

    max_min = max((b["total_minutes"] for b in app_breakdown), default=1)
    cat_colors = {
        "coding": theme.success,
        "documentation": theme.success,
        "browser": theme.secondary,
        "communication": theme.warning,
        "entertainment": theme.danger,
        "other": theme.muted,
    }

    for b in app_breakdown:
        cat = b["category"]
        mins = b["total_minutes"]
        color = cat_colors.get(cat, theme.muted)
        bar_len = int((mins / max_min) * 30) if max_min > 0 else 0
        bar = f"[{color}]{'█' * bar_len}{'░' * (30 - bar_len)}[/{color}]"
        cat_table.add_row(cat.title(), _fmt_time(mins), bar)

    # Hourly timeline
    timeline_table = Table(
        show_header=True,
        header_style=f"bold {theme.primary}",
        border_style=theme.border,
        title=f"[{theme.primary}]Hourly Timeline[/{theme.primary}]",
        expand=True,
    )
    timeline_table.add_column("Hour", style=theme.muted, width=6)
    timeline_table.add_column("Activity", ratio=3)
    timeline_table.add_column("Min", justify="right", width=5)

    # Group hourly data by hour
    hours_map: dict[str, list[dict]] = {}
    for h in hourly_data:
        hour = h["hour"]
        if hour not in hours_map:
            hours_map[hour] = []
        hours_map[hour].append(h)

    for hour_str in sorted(hours_map.keys()):
        entries = hours_map[hour_str]
        total = sum(e["total_minutes"] for e in entries)
        # Create a mini bar showing category mix
        segments = []
        for e in entries:
            cat = e["category"]
            color = cat_colors.get(cat, theme.muted)
            seg_len = max(1, int((e["total_minutes"] / max(total, 1)) * 20))
            segments.append(f"[{color}]{'█' * seg_len}[/{color}]")
        bar = "".join(segments)
        hour_label = f"{int(hour_str):02d}:00"
        timeline_table.add_row(hour_label, bar, f"{total:.0f}")

    right_content = Group(cat_table, timeline_table)
    layout["right"].update(right_content)

    # ── Footer: Top Distractions ─────────────────────────────────────────
    dist_table = Table(
        show_header=True,
        header_style=f"bold {theme.danger}",
        border_style=theme.border,
        expand=True,
    )
    dist_table.add_column("#", style=theme.muted, width=3)
    dist_table.add_column("App", style=theme.danger)
    dist_table.add_column("Time", justify="right")

    for i, d in enumerate(top_distractions, 1):
        app = d["app_name"]
        title = d.get("window_title")
        
        if title and title != "[private]":
            display_name = f"{app}: {title}"
            # Truncate to prevent breaking the table layout
            if len(display_name) > 70:
                display_name = display_name[:67] + "..."
        else:
            display_name = app
            
        dist_table.add_row(str(i), display_name, _fmt_time(d["total_minutes"]))

    if not top_distractions:
        dist_table.add_row("", f"[{theme.success}]No distractions recorded ✓[/{theme.success}]", "")

    footer_content = Panel(
        dist_table,
        title=f"[{theme.danger}]Top Distractions[/{theme.danger}]",
        border_style=theme.border,
    )
    layout["footer"].update(footer_content)

    # ── Render ───────────────────────────────────────────────────────────
    console.print(layout)


def render_quick_stats() -> None:
    """Render a single-line stats summary."""
    config = load_config()
    theme = get_theme(config.personality.mode)

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    score = calculate_focus_score(today_start, now)
    coding_min = queries.get_coding_minutes(today_start, now)
    distraction_min = queries.get_distraction_minutes(today_start, now)
    trend = get_trend()
    emoji = get_score_emoji(score)

    console.print(
        f"  {emoji} Focus: [{score_style(theme, score)}]{score:.0f}/100[/{score_style(theme, score)}] {trend}"
        f"  │  ⌨️  [{theme.success}]{_fmt_time(coding_min)}[/{theme.success}]"
        f"  │  📱 [{theme.danger}]{_fmt_time(distraction_min)}[/{theme.danger}]"
        f"  │  Since {today_start.strftime('%I:%M %p')}"
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fmt_time(minutes: float) -> str:
    """Format minutes into a human-readable string."""
    if minutes < 1:
        return "<1m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


def _time_since(iso_str: str) -> str:
    """Get a human-readable 'time since' string from an ISO timestamp."""
    if not iso_str:
        return "just now"
    try:
        created = datetime.fromisoformat(iso_str)
        delta = datetime.now() - created
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        return f"{minutes}m ago"
    except ValueError:
        return "unknown"
