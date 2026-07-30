"""The seat's contract with its owner.

A comment is a promise; a test is a bond. `DEFAULT_CONFIG` is the file every
new seat receives, and until now nothing parsed it — so the knobs it
advertises and the globs it ships were promises with nothing behind them.

These bond three things: that the template we hand a stranger actually
loads, that the excludes we ship match what the comment beside them claims,
and that `load()` refuses bad input instead of limping on with it.
"""

from __future__ import annotations

import inspect
import re
import tomllib

import pytest

from serf import config as cfgmod
from serf.observe import _glob_to_regex

# Keys `load()` reads that are deliberately absent from the live template —
# each must still appear as a commented example, checked below.
COMMENTED_OUT = {"venice_key_file", "venice_key_field"}


@pytest.fixture
def repo(tmp_path):
    return tmp_path


def bind(repo, body: str):
    """Write a config with an arbitrary body and load it."""
    path = repo / cfgmod.CONFIG_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return cfgmod.load(repo)


# --------------------------------------------------------------------------
# the template we ship — the bond that did not exist

def test_default_template_is_valid_toml():
    tomllib.loads(cfgmod.DEFAULT_CONFIG)


def test_default_template_round_trips_through_load(repo):
    """Prove the file a stranger receives is one our own loader accepts."""
    cfgmod.write_default(repo)
    cfg = cfgmod.load(repo)

    assert cfg.baron == "carnegie"
    assert cfg.trunk == "main"
    assert cfg.harshness == 3
    assert cfg.churn_window_days == 14
    assert cfg.padding_max_lines == 2
    assert cfg.churn_max_files == 200
    assert cfg.backend == "venice"
    assert cfg.model == "claude-opus-5"
    assert cfg.effort == "high"
    assert cfg.max_tokens == 16000
    assert cfg.exclude == ["**/vendor/**", "**/node_modules/**",
                           "**/*.lock", "**/dist/**"]


def _keys_load_reads() -> set[str]:
    src = inspect.getsource(cfgmod.load)
    return set(re.findall(r'raw\.get\(\s*"([^"]+)"', src))


def test_every_knob_load_reads_appears_in_the_template():
    """Catches silent drift between the loader and the file we ship.

    A knob added to `load()` but never to `DEFAULT_CONFIG` still works via
    its fallback, so nothing breaks and nothing complains — the owner simply
    never learns the setting exists.
    """
    template = cfgmod.DEFAULT_CONFIG
    missing = []
    for key in sorted(_keys_load_reads()):
        live = re.search(rf"^{key}\s*=", template, re.M)
        commented = re.search(rf"^#\s*{key}\s*=", template, re.M)
        if live:
            continue
        if key in COMMENTED_OUT and commented:
            continue
        missing.append(key)
    assert not missing, f"load() reads these but the template never mentions them: {missing}"


def test_optional_credential_knobs_are_at_least_documented():
    for key in COMMENTED_OUT:
        assert re.search(rf"^#\s*{key}\s*=", cfgmod.DEFAULT_CONFIG, re.M), \
            f"{key} is undocumented even as a comment"


# --------------------------------------------------------------------------
# the shipped excludes do what the comment beside them claims

SHIPPED = tomllib.loads(cfgmod.DEFAULT_CONFIG)["exclude"]


@pytest.mark.parametrize("path", [
    "vendor/lib.py",
    "third_party/vendor/deep/lib.py",
    "node_modules/react/index.js",
    "app/node_modules/x/y.js",
    "Cargo.lock",
    "sub/dir/package-lock.json.lock",
    "dist/bundle.js",
    "web/dist/assets/app.css",
])
def test_shipped_excludes_catch_what_they_are_for(path):
    assert any(_glob_to_regex(p).match(path) for p in SHIPPED), \
        f"{path} slipped past the shipped excludes"


@pytest.mark.parametrize("path", [
    "src/vendor.py",            # a file named vendor, not a vendor directory
    "src/vendors/lib.py",       # plural
    "src/node_modules.py",
    "src/distribute.py",        # begins with dist but is not dist/
    "src/lock.py",
    "src/app.py",
])
def test_shipped_excludes_do_not_swallow_real_code(path):
    assert not any(_glob_to_regex(p).match(path) for p in SHIPPED), \
        f"{path} was wrongly excluded from the metrics"


def test_bare_star_does_not_cross_a_slash():
    """The exact claim the comment in the template makes, in executable form."""
    bare = _glob_to_regex("*.lock")
    assert bare.match("Cargo.lock")
    assert not bare.match("sub/Cargo.lock")

    anydepth = _glob_to_regex("**/*.lock")
    assert anydepth.match("Cargo.lock")
    assert anydepth.match("sub/Cargo.lock")


# --------------------------------------------------------------------------
# load() refuses bad input

def test_missing_config_names_the_remedy(repo):
    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.load(repo)
    assert "serf init" in str(exc.value)


def test_unknown_baron_is_rejected_and_named(repo):
    with pytest.raises(cfgmod.ConfigError) as exc:
        bind(repo, 'baron = "vanderbilt"\n')
    assert "vanderbilt" in str(exc.value)
    assert "carnegie" in str(exc.value), "the error should list the valid choices"


@pytest.mark.parametrize("baron", cfgmod.BARONS)
def test_every_advertised_baron_actually_loads(baron):
    """The template lists five. All five must be accepted."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        cfg = bind(Path(tmp), f'baron = "{baron}"\n')
        assert cfg.baron == baron


def test_baron_is_case_insensitive(repo):
    assert bind(repo, 'baron = "CARNEGIE"\n').baron == "carnegie"


@pytest.mark.parametrize("value", [0, -1, 6, 99])
def test_harshness_outside_the_range_is_rejected(repo, value):
    with pytest.raises(cfgmod.ConfigError) as exc:
        bind(repo, f"harshness = {value}\n")
    assert "1 and 5" in str(exc.value)


@pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
def test_harshness_inside_the_range_is_accepted(repo, value):
    assert bind(repo, f"harshness = {value}\n").harshness == value


def test_backend_is_lowercased(repo):
    assert bind(repo, 'backend = "Venice"\n').backend == "venice"


def test_a_nearly_empty_config_falls_back_to_defaults(repo):
    """Someone who deletes everything but one line must still get a usable seat."""
    cfg = bind(repo, 'trunk = "trunk"\n')
    assert cfg.trunk == "trunk"
    assert (cfg.baron, cfg.backend, cfg.harshness) == ("carnegie", "venice", 3)
    assert cfg.exclude == []


def test_unrecognised_keys_are_ignored(repo):
    """Forward compatibility: an old binary must not choke on a new knob."""
    cfg = bind(repo, 'baron = "ford"\nsome_future_setting = 42\n')
    assert cfg.baron == "ford"


# --------------------------------------------------------------------------
# write_default()

def test_write_default_creates_the_state_directory(repo):
    assert not (repo / ".serf").exists()
    path = cfgmod.write_default(repo)
    assert path.exists()
    assert path == repo / cfgmod.CONFIG_RELPATH


def test_write_default_refuses_to_clobber_an_edited_config(repo):
    """The only function here that can destroy something hand-written."""
    cfgmod.write_default(repo)
    (repo / cfgmod.CONFIG_RELPATH).write_text('baron = "morgan"\n')

    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.write_default(repo)
    assert "not overwriting" in str(exc.value)
    assert cfgmod.load(repo).baron == "morgan", "the edited file must survive"


# --------------------------------------------------------------------------
# derived paths

def test_state_paths_hang_off_the_repo(tmp_path):
    cfg = cfgmod.Config(repo=tmp_path)
    assert cfg.state_dir == tmp_path / ".serf"
    assert cfg.db_path == tmp_path / ".serf" / "marks.db"
