"""The layer that touches git and the outside world.

`test_metrics.py` drives this file but never aims at it — it exercises the
happy path and infers the rest. These target the parsing and the failure
modes directly: the shapes git actually emits, and what happens when the
tools aren't there.
"""

from __future__ import annotations

import subprocess

import pytest

from serf import observe
from serf.config import Config


# --------------------------------------------------------------------------
# numstat parsing — the shapes git really emits

@pytest.mark.parametrize("line,path,added,deleted", [
    ("3\t1\tsrc/a.py", "src/a.py", 3, 1),
    ("0\t0\tsrc/empty.py", "src/empty.py", 0, 0),
    ("12\t0\tpath with spaces/a b.py", "path with spaces/a b.py", 12, 0),
])
def test_plain_numstat_lines(line, path, added, deleted):
    fc = observe._parse_numstat(line)
    assert (fc.path, fc.added, fc.deleted) == (path, added, deleted)


@pytest.mark.parametrize("line", [
    "-\t-\tassets/logo.png",   # binary: no line accounting exists
    "",                         # blank separator
    "3\t1",                     # truncated, no path
    "garbage",
])
def test_unparseable_numstat_lines_are_dropped(line):
    assert observe._parse_numstat(line) is None


@pytest.mark.parametrize("line,expected", [
    ("1\t1\tsrc/{a.py => b.py}", "src/b.py"),
    ("1\t1\told.py => new.py", "new.py"),
    ("1\t1\tdir/{old => new}/f.py", "dir/new/f.py"),
    ("1\t1\tdir/{ => sub}/f.py", "dir/sub/f.py"),
    ("1\t1\tdir/{sub => }/f.py", "dir/f.py"),
])
def test_rename_forms_resolve_to_the_new_path(line, expected):
    """git emits three different rename shapes. All must land on the new path."""
    fc = observe._parse_numstat(line)
    assert fc.path == expected
    assert "=>" not in fc.path


# --------------------------------------------------------------------------
# the glob translator

@pytest.mark.parametrize("pattern,path,matches", [
    ("**/vendor/**", "vendor/lib/x.py", True),
    ("**/vendor/**", "a/b/vendor/x.py", True),
    ("**/vendor/**", "vendors/x.py", False),
    ("**/vendor/**", "src/vendor.py", False),
    ("**/*.lock", "Cargo.lock", True),
    ("**/*.lock", "deep/nested/Cargo.lock", True),
    ("**/*.lock", "Cargo.lock.bak", False),
    ("*.lock", "Cargo.lock", True),
    ("*.lock", "sub/Cargo.lock", False),   # single star must not cross a slash
    ("src/?.py", "src/a.py", True),
    ("src/?.py", "src/ab.py", False),
    ("build/**", "build/x/y.js", True),
])
def test_glob_translation(pattern, path, matches):
    assert bool(observe._glob_to_regex(pattern).match(path)) is matches


def test_glob_metacharacters_in_literals_are_escaped():
    """A dot is a dot, not 'any character'."""
    rx = observe._glob_to_regex("src/a.py")
    assert rx.match("src/a.py")
    assert not rx.match("src/axpy")


# --------------------------------------------------------------------------
# test-file classification

@pytest.mark.parametrize("path,is_test", [
    ("tests/test_a.py", True),
    ("test/a.py", True),
    ("spec/models.rb", True),
    ("__tests__/x.js", True),
    ("src/test_helpers.py", True),
    ("src/a_test.go", True),
    ("src/button.test.tsx", True),
    ("src/button.spec.ts", True),
    ("src/app.py", False),
    ("src/latest.py", False),        # contains "test" but is not a test
    ("src/contest/entry.py", False),  # ditto, mid-word
    ("src/protest.py", False),
])
def test_test_file_classification(path, is_test):
    assert observe.FileChange(path, 0, 0).is_test is is_test


# --------------------------------------------------------------------------
# failing safely

def test_collect_on_a_non_repository_raises_git_error(tmp_path):
    cfg = Config(repo=tmp_path)
    assert observe.is_repo(cfg) is False
    with pytest.raises(observe.GitError):
        observe.collect(cfg, __import__("datetime").datetime.now(),
                        __import__("datetime").datetime.now())


def test_binary_files_do_not_crash_or_inflate_the_count(repo, cfg, today_window):
    (repo.path / "assets").mkdir()
    (repo.path / "assets" / "logo.png").write_bytes(bytes(range(256)) * 8)
    repo.write("src/a.py", "x = 1\ny = 2\nz = 3\n")
    repo.commit("add code and a binary blob")
    obs = observe.collect(cfg, *today_window)
    paths = [f.path for c in obs.commits for f in c.files]
    assert "src/a.py" in paths
    assert "assets/logo.png" not in paths, "binary files carry no line accounting"


# --------------------------------------------------------------------------
# CI, which lives outside our control

def test_no_gh_binary_means_no_ci_data(cfg, monkeypatch):
    """Absent tooling must read as 'unknown', never as 'zero failures'."""
    monkeypatch.setattr(observe.shutil, "which", lambda _: None)
    assert observe._ci_runs(cfg) is None


def _fake_gh(returncode: int, stdout: str):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout, "")
    return run


def test_gh_failure_means_no_ci_data(cfg, monkeypatch):
    monkeypatch.setattr(observe.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(observe.subprocess, "run", _fake_gh(1, ""))
    assert observe._ci_runs(cfg) is None


def test_gh_returning_junk_means_no_ci_data(cfg, monkeypatch):
    monkeypatch.setattr(observe.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(observe.subprocess, "run", _fake_gh(0, "not json at all"))
    assert observe._ci_runs(cfg) is None


def test_ci_runs_are_parsed_and_pending_is_not_a_failure(cfg, monkeypatch):
    payload = (
        '[{"conclusion":"success","createdAt":"2026-07-29T10:00:00Z","headSha":"aaaa1111bbbb"},'
        ' {"conclusion":"failure","createdAt":"2026-07-29T09:00:00Z","headSha":"cccc2222dddd"},'
        ' {"conclusion":null,"createdAt":"2026-07-29T08:00:00Z","headSha":"eeee3333ffff"}]'
    )
    monkeypatch.setattr(observe.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(observe.subprocess, "run", _fake_gh(0, payload))
    runs = observe._ci_runs(cfg)
    assert [r.conclusion for r in runs] == ["success", "failure", "pending"]
    assert runs[0].sha == "aaaa1111bbbb"


def test_ci_failure_rate_counts_only_real_failures(cfg, monkeypatch):
    """skipped is not a failure; a null conclusion is still in flight."""
    payload = (
        '[{"conclusion":"success"},{"conclusion":"skipped"},'
        ' {"conclusion":"failure"},{"conclusion":"cancelled"}]'
    )
    monkeypatch.setattr(observe.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(observe.subprocess, "run", _fake_gh(0, payload))
    obs = observe.Observation(
        since=None, until=None, trunk="main", commits=[], ci=observe._ci_runs(cfg)
    )
    assert obs.ci_failure_rate == 0.5


def test_ci_failure_rate_is_none_without_data():
    obs = observe.Observation(since=None, until=None, trunk="main",
                              commits=[], ci=None)
    assert obs.ci_failure_rate is None
