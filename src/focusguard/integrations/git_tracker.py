"""Local git repository tracker using GitPython.

Scans configured local repos for commit activity, modified files,
and lines changed. Never sends data externally — all local.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Summary of a single git commit."""

    sha_short: str
    message: str
    author: str
    timestamp: datetime
    files_changed: int
    insertions: int
    deletions: int


@dataclass
class RepoSummary:
    """Activity summary for a single repo."""

    repo_name: str
    repo_path: str
    commits_24h: int
    commits_7d: int
    recent_commits: list[CommitInfo]
    lines_added: int
    lines_deleted: int
    has_uncommitted: bool


def scan_repo(repo_path: str, days: int = 7) -> RepoSummary | None:
    """Scan a local git repo for recent activity.

    Args:
        repo_path: Absolute path to the git repository.
        days: How many days of history to scan.

    Returns:
        A RepoSummary, or None if the path is not a valid git repo.
    """
    try:
        from git import Repo, InvalidGitRepositoryError  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("GitPython not installed. Install with: pip install focusguard[github]")
        return None

    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        return None

    try:
        repo = Repo(str(path))
    except InvalidGitRepositoryError:
        return None

    repo_name = path.name
    now = datetime.now()
    since_24h = now - timedelta(hours=24)
    since_days = now - timedelta(days=days)

    commits_24h = 0
    commits_7d = 0
    recent_commits: list[CommitInfo] = []
    total_added = 0
    total_deleted = 0

    try:
        for commit in repo.iter_commits(max_count=200):
            commit_time = datetime.fromtimestamp(commit.committed_date)

            if commit_time < since_days:
                break

            commits_7d += 1
            if commit_time >= since_24h:
                commits_24h += 1

            # Get diff stats
            try:
                stats = commit.stats.total
                files_changed = stats.get("files", 0)
                insertions = stats.get("insertions", 0)
                deletions = stats.get("deletions", 0)
            except Exception:
                files_changed = 0
                insertions = 0
                deletions = 0

            total_added += insertions
            total_deleted += deletions

            if len(recent_commits) < 10:
                recent_commits.append(CommitInfo(
                    sha_short=commit.hexsha[:7],
                    message=commit.message.strip().split("\n")[0][:80],
                    author=str(commit.author),
                    timestamp=commit_time,
                    files_changed=files_changed,
                    insertions=insertions,
                    deletions=deletions,
                ))
    except Exception as e:
        logger.debug(f"Error scanning commits for {repo_name}: {e}")

    # Check for uncommitted changes
    has_uncommitted = False
    try:
        has_uncommitted = repo.is_dirty(untracked_files=True)
    except Exception:
        pass

    return RepoSummary(
        repo_name=repo_name,
        repo_path=str(path),
        commits_24h=commits_24h,
        commits_7d=commits_7d,
        recent_commits=recent_commits,
        lines_added=total_added,
        lines_deleted=total_deleted,
        has_uncommitted=has_uncommitted,
    )


def scan_all_repos(repo_paths: list[str], days: int = 7) -> list[RepoSummary]:
    """Scan multiple repos and return summaries.

    Args:
        repo_paths: List of absolute paths to git repos.
        days: How many days of history to scan.

    Returns:
        List of RepoSummary objects (skips invalid repos).
    """
    summaries = []
    for path in repo_paths:
        summary = scan_repo(path, days)
        if summary is not None:
            summaries.append(summary)
    return summaries


def find_git_repos(search_dir: str, max_depth: int = 3) -> list[str]:
    """Auto-discover git repos under a directory.

    Args:
        search_dir: Directory to search.
        max_depth: Maximum directory depth to search.

    Returns:
        List of absolute paths to discovered git repos.
    """
    repos: list[str] = []
    search_path = Path(search_dir).expanduser().resolve()

    if not search_path.is_dir():
        return repos

    def _scan(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            git_dir = current / ".git"
            if git_dir.is_dir():
                repos.append(str(current))
                return  # Don't recurse into git repos
            for child in current.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    _scan(child, depth + 1)
        except PermissionError:
            pass

    _scan(search_path, 0)
    return repos
