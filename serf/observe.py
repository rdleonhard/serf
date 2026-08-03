"""Observation surface: git and CI only.

v0 deliberately has no eyes, no clock on the person, and no session
transcripts. It cannot perceive anything about the dev except what they
landed. That scope is what makes the dispatches publishable — see PLAN.md
§7a. Do not widen it without widening the consent flow first.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .config import Config

# --------------------------------------------------------------------------
# shelling out

class GitError(RuntimeError):
    pass


def git(cfg: Config, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cfg.repo), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def is_repo(cfg: Config) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(cfg.repo), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------
# path exclusion

def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


TEST_PATH = re.compile(
    r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]+$|_test\.[^/.]+$|\.(test|spec)\.[^/.]+$"
)


# --------------------------------------------------------------------------
# model

@dataclass
class FileChange:
    path: str
    added: int
    deleted: int

    @property
    def is_test(self) -> bool:
        return bool(TEST_PATH.search(self.path))


@dataclass
class Commit:
    sha: str
    when: datetime
    author: str
    subject: str
    files: list[FileChange] = field(default_factory=list)
    whitespace_only: bool = False
    churned_lines: int = 0      # deleted lines that were themselves recent
    deleted_considered: int = 0  # deleted lines we were able to attribute
    deletion_files_total: int = 0       # files with deletions in this commit
    deletion_files_attributed: int = 0  # of those, how many we actually blamed

    @property
    def added(self) -> int:
        return sum(f.added for f in self.files)

    @property
    def deleted(self) -> int:
        return sum(f.deleted for f in self.files)

    @property
    def touched(self) -> int:
        return self.added + self.deleted

    @property
    def is_revert(self) -> bool:
        return self.subject.lower().startswith("revert")

    @property
    def is_fix(self) -> bool:
        return bool(re.match(r"^(fix|hotfix|patch|bugfix)\b", self.subject, re.I))


@dataclass
class CIRun:
    sha: str
    conclusion: str
    when: str


@dataclass
class Observation:
    since: datetime
    until: datetime
    trunk: str
    commits: list[Commit]
    ci: list[CIRun] | None  # None = no CI data available (gh missing/unauthed)
    head: str = ""          # the branch actually checked out
    unmerged: int = 0       # commits on HEAD that have not reached trunk

    @property
    def diverged(self) -> bool:
        """True when work is happening somewhere the Mark is not looking."""
        return bool(self.head and self.head != self.trunk and self.unmerged)

    @property
    def ci_failure_rate(self) -> float | None:
        if not self.ci:
            return None
        bad = sum(1 for r in self.ci if r.conclusion not in ("success", "skipped"))
        return bad / len(self.ci)


# --------------------------------------------------------------------------
# git log

_LOG_FORMAT = "%x00%H%x1f%aI%x1f%an%x1f%s"


def _parse_numstat(line: str) -> FileChange | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added_s, deleted_s, path = parts[0], parts[1], "\t".join(parts[2:])
    if added_s == "-" or deleted_s == "-":
        return None  # binary; no line accounting to do
    # renames arrive as "old => new" or "dir/{a => b}/f"
    if "=>" in path:
        path = re.sub(r"\{[^{}]*=>\s*([^{}]*)\}", r"\1", path)
        if "=>" in path:
            path = path.split("=>")[-1]
        path = re.sub(r"//+", "/", path.strip())
    return FileChange(path=path, added=int(added_s), deleted=int(deleted_s))


def collect(cfg: Config, since: datetime, until: datetime) -> Observation:
    """Read everything landed on trunk in [since, until)."""
    if not is_repo(cfg):
        raise GitError(f"{cfg.repo} is not a git repository")

    excludes = [_glob_to_regex(p) for p in cfg.exclude]

    raw = git(
        cfg,
        "log",
        cfg.trunk,
        "--no-merges",
        "--numstat",
        f"--format={_LOG_FORMAT}",
        f"--since={since.isoformat()}",
        f"--until={until.isoformat()}",
    )

    commits: list[Commit] = []
    for chunk in raw.split("\0"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        head, _, rest = chunk.partition("\n")
        sha, when_s, author, subject = head.split("\x1f", 3)
        files = []
        for line in rest.splitlines():
            fc = _parse_numstat(line.strip())
            if fc is None:
                continue
            if any(rx.match(fc.path) for rx in excludes):
                continue
            files.append(fc)
        commits.append(
            Commit(
                sha=sha,
                when=datetime.fromisoformat(when_s),
                author=author,
                subject=subject,
                files=files,
            )
        )

    for c in commits:
        _annotate(cfg, c)

    return Observation(
        since=since,
        until=until,
        trunk=cfg.trunk,
        commits=commits,
        ci=_ci_runs(cfg),
        head=head_branch(cfg),
        unmerged=unmerged_onto_trunk(cfg),
    )


def head_branch(cfg: Config) -> str:
    """The branch actually checked out, which is not always the trunk."""
    return git(cfg, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()


def unmerged_onto_trunk(cfg: Config) -> int:
    """How many commits sit on HEAD that trunk has never seen.

    The Mark counts landed work, so work on a side branch reads as zero. That
    is correct arithmetic and a misleading silence: without this number the
    board cannot tell "you did nothing" from "you did not land it".
    """
    out = git(cfg, "rev-list", "--count", f"{cfg.trunk}..HEAD", check=False).strip()
    return int(out) if out.isdigit() else 0


def _annotate(cfg: Config, commit: Commit) -> None:
    """Fill in whitespace_only and churn for a single commit."""
    parent = f"{commit.sha}^"
    if not _rev_exists(cfg, parent):
        return  # root commit: nothing to diff against

    ws = git(cfg, "diff", "-w", "--numstat", parent, commit.sha, check=False).strip()
    commit.whitespace_only = bool(commit.files) and not ws

    window = timedelta(days=cfg.churn_window_days)

    # Blaming every deleted line is the honest computation but it is O(files);
    # a cap keeps a pathological commit from hanging the daily run. When the
    # cap bites we record it, so slag can be reported as a sample rather than
    # passed off as complete. A silently truncated number is worse than none.
    with_deletions = [fc for fc in commit.files if fc.deleted > 0]
    commit.deletion_files_total = len(with_deletions)

    for fc in with_deletions[: cfg.churn_max_files]:
        commit.deletion_files_attributed += 1
        for start, count in _deleted_ranges(cfg, commit.sha, fc.path):
            for authored in _blame_times(cfg, parent, fc.path, start, count):
                commit.deleted_considered += 1
                if commit.when - authored <= window:
                    commit.churned_lines += 1


def _rev_exists(cfg: Config, rev: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(cfg.repo), "rev-parse", "--verify", "--quiet", rev],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")


def _deleted_ranges(cfg: Config, sha: str, path: str) -> list[tuple[int, int]]:
    """Line ranges in the PARENT that this commit deleted or replaced."""
    out = git(
        cfg, "diff", "--unified=0", f"{sha}^", sha, "--", path, check=False
    )
    ranges = []
    for line in out.splitlines():
        m = _HUNK.match(line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) is not None else 1
        if count > 0:
            ranges.append((start, count))
    return ranges


def _blame_times(
    cfg: Config, rev: str, path: str, start: int, count: int
) -> list[datetime]:
    out = git(
        cfg,
        "blame",
        "--line-porcelain",
        "-L",
        f"{start},+{count}",
        rev,
        "--",
        path,
        check=False,
    )
    times = []
    for line in out.splitlines():
        if line.startswith("author-time "):
            # git log gives us tz-aware commit times, so keep these aware too.
            times.append(datetime.fromtimestamp(int(line.split()[1]), tz=timezone.utc))
    return times


# --------------------------------------------------------------------------
# CI (optional)

def _ci_runs(cfg: Config, limit: int = 50) -> list[CIRun] | None:
    if shutil.which("gh") is None:
        return None
    proc = subprocess.run(
        [
            "gh", "run", "list",
            "--branch", cfg.trunk,
            "--limit", str(limit),
            "--json", "conclusion,createdAt,headSha",
        ],
        capture_output=True,
        text=True,
        cwd=str(cfg.repo),
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return [
        CIRun(
            sha=r.get("headSha", "")[:12],
            conclusion=r.get("conclusion") or "pending",
            when=r.get("createdAt", ""),
        )
        for r in rows
    ]
