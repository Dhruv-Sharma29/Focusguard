"""GitHub API integration for FocusGuard.

Uses PyGithub with a personal access token stored securely via
python-keyring (never in plaintext config).

Provides weekly summary of commits, PRs, and issues across repos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from focusguard.security.keyring_store import get_secret, store_secret

logger = logging.getLogger(__name__)

TOKEN_KEY = "github_token"


@dataclass
class GitHubSummary:
    """Weekly GitHub activity summary."""

    username: str
    period_days: int
    total_commits: int = 0
    total_prs_opened: int = 0
    total_prs_merged: int = 0
    total_issues_opened: int = 0
    total_issues_closed: int = 0
    most_active_repo: str = ""
    repos_contributed: list[str] = field(default_factory=list)


def is_configured() -> bool:
    """Check if GitHub token is stored in keyring."""
    return get_secret(TOKEN_KEY) is not None


def setup_token(token: str) -> None:
    """Store GitHub PAT securely in the OS keyring.

    Args:
        token: GitHub personal access token.
    """
    store_secret(TOKEN_KEY, token)


def get_weekly_summary(days: int = 7) -> GitHubSummary | None:
    """Fetch a summary of GitHub activity for the authenticated user.

    Args:
        days: Number of days to look back.

    Returns:
        A GitHubSummary, or None if not configured.
    """
    try:
        from github import Github  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyGithub not installed. Install with: pip install focusguard[github]")
        return None

    token = get_secret(TOKEN_KEY)
    if not token:
        return None

    try:
        g = Github(token)
        user = g.get_user()
        username = user.login
        since = datetime.now(timezone.utc) - timedelta(days=days)

        summary = GitHubSummary(username=username, period_days=days)
        repo_commit_counts: dict[str, int] = {}

        # Scan user's repos for activity
        for repo in user.get_repos(sort="pushed", direction="desc"):
            # Skip repos not pushed to recently
            if repo.pushed_at and repo.pushed_at < since:
                continue

            repo_name = repo.full_name

            # Count commits
            try:
                commits = repo.get_commits(author=username, since=since)
                count = 0
                for _ in commits:
                    count += 1
                    if count > 100:  # Safety cap
                        break
                if count > 0:
                    summary.total_commits += count
                    repo_commit_counts[repo_name] = count
                    if repo_name not in summary.repos_contributed:
                        summary.repos_contributed.append(repo_name)
            except Exception:
                pass

            # Count PRs
            try:
                pulls = repo.get_pulls(state="all", sort="created", direction="desc")
                for pr in pulls:
                    if pr.created_at < since:
                        break
                    if pr.user.login == username:
                        summary.total_prs_opened += 1
                        if pr.merged:
                            summary.total_prs_merged += 1
            except Exception:
                pass

            # Count issues
            try:
                issues = repo.get_issues(state="all", sort="created", direction="desc", creator=username)
                for issue in issues:
                    if issue.created_at < since:
                        break
                    if not issue.pull_request:  # Exclude PRs from issues
                        summary.total_issues_opened += 1
                        if issue.state == "closed":
                            summary.total_issues_closed += 1
            except Exception:
                pass

        # Determine most active repo
        if repo_commit_counts:
            summary.most_active_repo = max(repo_commit_counts, key=repo_commit_counts.get)  # type: ignore[arg-type]

        return summary

    except Exception as e:
        logger.error(f"GitHub API error: {e}")
        return None
