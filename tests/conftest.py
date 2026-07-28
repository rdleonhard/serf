"""Build real git repositories with controlled dates.

The metrics are derived from git plumbing — blame times, hunk headers,
numstat — so mocking git would test nothing. These fixtures make real
commits at chosen timestamps and let the real code read them.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from serf.config import Config


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    e = os.environ.copy()
    # Isolate from the developer's own git config, hooks, and templates.
    e.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })
    if env:
        e.update(env)
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=e,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed:\n{proc.stderr}")
    return proc.stdout


class Repo:
    """A throwaway repository you can commit into at arbitrary times."""

    def __init__(self, path: Path):
        self.path = path
        _git(path, "init", "-q", "-b", "main")
        _git(path, "config", "user.email", "tester@example.com")
        _git(path, "config", "user.name", "Tester")

    def write(self, rel: str, content: str) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def remove(self, rel: str) -> None:
        (self.path / rel).unlink()

    def move(self, src: str, dst: str) -> None:
        (self.path / dst).parent.mkdir(parents=True, exist_ok=True)
        _git(self.path, "mv", src, dst)

    def commit(self, message: str, when: datetime | None = None) -> str:
        env = {}
        if when is not None:
            stamp = when.isoformat()
            # Author date is what `git blame` reports, so both must be set.
            env = {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        _git(self.path, "add", "-A")
        _git(self.path, "commit", "-q", "--allow-empty", "-m", message, env=env)
        return _git(self.path, "rev-parse", "HEAD").strip()

    def revert(self, ref: str = "HEAD") -> str:
        _git(self.path, "revert", "--no-edit", ref)
        return _git(self.path, "rev-parse", "HEAD").strip()


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def days_ago(now):
    def _days_ago(n: float) -> datetime:
        return now - timedelta(days=n)
    return _days_ago


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(tmp_path)


@pytest.fixture
def cfg(repo: Repo) -> Config:
    return Config(
        repo=repo.path,
        baron="carnegie",
        trunk="main",
        churn_window_days=14,
        padding_max_lines=2,
        exclude=["**/vendor/**"],
    )


@pytest.fixture
def today_window(now):
    """A window that captures commits made 'now' and nothing historical."""
    return (now - timedelta(hours=6), now + timedelta(hours=1))
