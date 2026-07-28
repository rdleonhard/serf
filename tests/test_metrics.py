"""Put a known weight on the pan.

Every number SERF shows a person has to be defensible, because the whole
premise is that its numbers can be trusted. These pin the two that carry
real arithmetic — heat qualification and slag attribution — plus the
gaming detectors, which are the ones a motivated person would try to
fool.
"""

from __future__ import annotations

from serf import metrics, observe


def look(cfg, window):
    obs = observe.collect(cfg, *window)
    return obs, metrics.summarize(obs, cfg)


# --------------------------------------------------------------------------
# the Mark: what counts as a heat

def test_substantial_commit_counts(repo, cfg, today_window):
    repo.write("src/a.py", "def a():\n    return 1\n\ndef b():\n    return 2\n")
    repo.commit("add a and b")
    _, stats = look(cfg, today_window)
    assert stats.mark == 1
    assert stats.disqualified == 0


def test_revert_does_not_count(repo, cfg, today_window):
    repo.write("src/a.py", "def a():\n    return 1\n\ndef b():\n    return 2\n")
    repo.commit("add a and b")
    repo.revert()
    _, stats = look(cfg, today_window)
    assert stats.mark == 1, "the original still counts; only the revert doesn't"
    assert stats.disqualified == 1


def test_revert_is_not_also_called_padding(repo, cfg, today_window):
    """A revert is honest work undone. It must not be accused of gaming."""
    repo.write("src/a.py", "x = 1\ny = 2\nz = 3\n")
    repo.commit("add three")
    repo.revert()
    _, stats = look(cfg, today_window)
    assert stats.gaming.padding == []


def test_whitespace_only_does_not_count(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", "def a():\n    return 1\n\ndef b():\n    return 2\n")
    repo.commit("baseline", when=days_ago(1))
    repo.write("src/a.py", "def a():\n        return 1\n\ndef b():\n        return 2\n")
    repo.commit("reindent")
    _, stats = look(cfg, today_window)
    assert stats.mark == 0
    assert len(stats.gaming.whitespace_only) == 1


def test_one_line_single_file_is_padding(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", "x = 1\ny = 2\nz = 3\n")
    repo.commit("baseline", when=days_ago(1))
    repo.write("src/a.py", "x = 1\ny = 2\nz = 3\nw = 4\n")
    repo.commit("one more")
    _, stats = look(cfg, today_window)
    assert stats.mark == 0
    assert len(stats.gaming.padding) == 1


def test_small_change_across_two_files_still_counts(repo, cfg, today_window, days_ago):
    """The padding rule is `tiny AND one file`. Two files is real work."""
    repo.write("src/a.py", "x = 1\n")
    repo.write("src/b.py", "y = 1\n")
    repo.commit("baseline", when=days_ago(1))
    repo.write("src/a.py", "x = 2\n")
    repo.write("src/b.py", "y = 2\n")
    repo.commit("bump both")
    _, stats = look(cfg, today_window)
    assert stats.mark == 1


# --------------------------------------------------------------------------
# slag: rework attribution

FOUR = "one = 1\ntwo = 2\nthree = 3\nfour = 4\n"
FOUR_REWRITTEN = "one = 11\ntwo = 22\nthree = 33\nfour = 44\n"


def test_deleting_recent_lines_is_slag(repo, cfg, today_window, days_ago):
    repo.write("src/recent.py", FOUR)
    repo.commit("write it", when=days_ago(13))       # inside the 14-day window
    repo.write("src/recent.py", FOUR_REWRITTEN)
    repo.commit("tear it out and do it again")
    _, stats = look(cfg, today_window)
    assert stats.slag_pct == 100.0


def test_deleting_old_lines_is_not_slag(repo, cfg, today_window, days_ago):
    repo.write("src/old.py", FOUR)
    repo.commit("write it", when=days_ago(15))       # outside the 14-day window
    repo.write("src/old.py", FOUR_REWRITTEN)
    repo.commit("revisit settled code")
    _, stats = look(cfg, today_window)
    assert stats.slag_pct == 0.0


def test_slag_boundary_is_inclusive(repo, cfg, today_window, days_ago):
    """Exactly at the window edge counts as rework, not as settled code."""
    repo.write("src/edge.py", FOUR)
    repo.commit("write it", when=days_ago(13.99))
    repo.write("src/edge.py", FOUR_REWRITTEN)
    repo.commit("rewrite at the edge")
    _, stats = look(cfg, today_window)
    assert stats.slag_pct == 100.0


def test_mixed_ages_give_a_partial_rate(repo, cfg, today_window, days_ago):
    repo.write("src/old.py", FOUR)
    repo.commit("old work", when=days_ago(30))
    repo.write("src/new.py", FOUR)
    repo.commit("recent work", when=days_ago(2))
    repo.write("src/old.py", FOUR_REWRITTEN)
    repo.write("src/new.py", FOUR_REWRITTEN)
    repo.commit("rewrite both")
    _, stats = look(cfg, today_window)
    assert stats.slag_pct == 50.0


def test_pure_addition_has_no_slag(repo, cfg, today_window):
    """The empty-deletion case: nothing to attribute, so report nothing."""
    repo.write("src/a.py", FOUR)
    repo.commit("first pour")
    _, stats = look(cfg, today_window)
    assert stats.deleted == 0
    assert stats.slag_pct is None, "no deletions must not read as 0% rework"


def test_first_commit_has_no_parent_and_does_not_crash(repo, cfg, today_window):
    repo.write("src/a.py", FOUR)
    repo.commit("root commit")
    _, stats = look(cfg, today_window)
    assert stats.mark == 1


# --------------------------------------------------------------------------
# the gaming detector

def test_tests_shrinking_while_code_grows_is_flagged(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", "def a():\n    return 1\n")
    repo.write("tests/test_a.py", "def test_a():\n    assert a() == 1\n\ndef test_b():\n    assert True\n")
    repo.commit("baseline", when=days_ago(1))

    repo.write("src/a.py", "def a():\n    return 1\n\ndef b():\n    return 2\n\ndef c():\n    return 3\n")
    repo.write("tests/test_a.py", "def test_a():\n    pass\n")
    repo.commit("more code, fewer assertions")

    _, stats = look(cfg, today_window)
    assert len(stats.gaming.test_deletion) == 1


def test_tests_growing_with_code_is_clean(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", "def a():\n    return 1\n")
    repo.write("tests/test_a.py", "def test_a():\n    assert a() == 1\n")
    repo.commit("baseline", when=days_ago(1))

    repo.write("src/a.py", "def a():\n    return 1\n\ndef b():\n    return 2\n")
    repo.write("tests/test_a.py", "def test_a():\n    assert a() == 1\n\ndef test_b():\n    assert b() == 2\n")
    repo.commit("code and coverage together")

    _, stats = look(cfg, today_window)
    assert stats.gaming.any is False


def test_deleting_tests_alone_is_not_flagged(repo, cfg, today_window, days_ago):
    """Removing a dead test without growing code is cleanup, not concealment."""
    repo.write("src/a.py", "def a():\n    return 1\n")
    repo.write("tests/test_a.py", "def test_a():\n    assert True\n\ndef test_dead():\n    assert True\n")
    repo.commit("baseline", when=days_ago(1))
    repo.write("tests/test_a.py", "def test_a():\n    assert True\n")
    repo.commit("drop a dead test")
    _, stats = look(cfg, today_window)
    assert stats.gaming.test_deletion == []


# --------------------------------------------------------------------------
# path handling

def test_excluded_paths_are_invisible(repo, cfg, today_window):
    repo.write("src/a.py", FOUR)
    repo.write("vendor/lib/huge.py", "\n".join(f"line{i} = {i}" for i in range(200)) + "\n")
    repo.commit("add code and a vendored blob")
    _, stats = look(cfg, today_window)
    assert stats.files == 1
    assert stats.added == 4, "vendored lines must not inflate the day's tonnage"


def test_rename_resolves_to_the_new_path(repo, cfg, today_window, days_ago):
    repo.write("src/before.py", FOUR)
    repo.commit("baseline", when=days_ago(1))
    repo.move("src/before.py", "src/after.py")
    repo.write("src/after.py", FOUR + "five = 5\n")
    repo.commit("rename and extend")
    obs, _ = look(cfg, today_window)
    paths = [f.path for c in obs.commits for f in c.files]
    assert all("=>" not in p for p in paths), f"unparsed rename in {paths}"
    assert any(p.endswith("after.py") for p in paths)


def test_merge_commits_are_ignored(repo, cfg, today_window, days_ago):
    from tests.conftest import _git
    repo.write("src/a.py", FOUR)
    repo.commit("baseline", when=days_ago(2))
    _git(repo.path, "checkout", "-q", "-b", "side")
    repo.write("src/side.py", "s = 1\ns = 2\ns = 3\n")
    repo.commit("side work")
    _git(repo.path, "checkout", "-q", "main")
    repo.write("src/main.py", "m = 1\nm = 2\nm = 3\n")
    repo.commit("main work")
    _git(repo.path, "merge", "--no-ff", "-q", "-m", "merge side", "side")
    _, stats = look(cfg, today_window)
    assert stats.mark == 2, "the merge itself must not be counted as a heat"


# --------------------------------------------------------------------------
# the evidence packet is a contract with the model

def test_packet_carries_the_load_bearing_facts(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", FOUR)
    repo.commit("baseline", when=days_ago(2))
    repo.write("src/a.py", FOUR_REWRITTEN)
    repo.commit("rework it")
    obs, stats = look(cfg, today_window)
    packet = metrics.evidence_packet(stats, obs, cfg, [("2026-01-01", 7)])

    for expected in ("THE MARK", "GAMING CHECK", "SELF vs SELF", "COMMITS",
                     "rework it", "src/a.py", "2026-01-01: 7"):
        assert expected in packet, f"packet lost {expected!r}"


def test_packet_is_explicit_when_nothing_landed(repo, cfg, today_window, days_ago):
    repo.write("src/a.py", FOUR)
    repo.commit("yesterday's work", when=days_ago(3))
    obs, stats = look(cfg, today_window)
    packet = metrics.evidence_packet(stats, obs, cfg, [])
    assert stats.mark == 0
    assert "(none)" in packet


# --------------------------------------------------------------------------
# truncation must be visible, never silent

def test_churn_cap_marks_slag_as_a_sample(repo, cfg, today_window, days_ago):
    """When the cap bites, slag is approximate and must say so."""
    cfg.churn_max_files = 1
    repo.write("src/one.py", FOUR)
    repo.write("src/two.py", FOUR)
    repo.commit("baseline", when=days_ago(2))
    repo.write("src/one.py", FOUR_REWRITTEN)
    repo.write("src/two.py", FOUR_REWRITTEN)
    repo.commit("rewrite both")

    obs, stats = look(cfg, today_window)
    assert stats.slag_complete is False
    packet = metrics.evidence_packet(stats, obs, cfg, [])
    assert "SAMPLE" in packet, "a truncated slag figure must be flagged to the model"


def test_slag_is_complete_when_under_the_cap(repo, cfg, today_window, days_ago):
    repo.write("src/one.py", FOUR)
    repo.commit("baseline", when=days_ago(2))
    repo.write("src/one.py", FOUR_REWRITTEN)
    repo.commit("rewrite it")

    obs, stats = look(cfg, today_window)
    assert stats.slag_complete is True
    assert "SAMPLE" not in metrics.evidence_packet(stats, obs, cfg, [])
