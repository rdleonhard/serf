"""Seat configuration. One seat = one baron + one bound repo.

Lives at <repo>/.serf/config.toml so the dev owns it. Nothing here is sent
anywhere except the model call in verdict.py.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_RELPATH = Path(".serf") / "config.toml"

DEFAULT_CONFIG = """\
# $SERF seat configuration.
# This file is yours. Nothing in it leaves your machine except the evidence
# packet sent to the model when you run `serf mark`.

baron = "carnegie"          # carnegie | rockefeller | morgan | ford | deming
trunk = "main"              # the branch that counts as landed work
harshness = 3               # 1-5. Only the STARTING register — it is earned
                            # upward from here and eased back if you go quiet.

churn_window_days = 14      # code rewritten within N days counts as slag
padding_max_lines = 2       # commits at or under this are checked for padding

# Where the verdict is generated. "venice" runs on rented compute the serf
# does not own, which is the point (MECHANISM.md). "anthropic" calls the
# API directly and is kept for A/B.
backend = "venice"
model = "claude-opus-5"
effort = "high"             # low | medium | high | xhigh | max
max_tokens = 16000

# Venice credential. Env VENICE_API_KEY wins if set; otherwise point this at
# a file holding the key (plain text, or JSON with a "venice_key" field).
# venice_key_file = "~/.config/venice/key.json"

# Paths excluded from the metrics entirely (globs, matched on the path).
# Note: a bare "*" never crosses a "/", so "*.lock" matches Cargo.lock but
# NOT sub/Cargo.lock. Lead with "**/" when you mean "at any depth".
exclude = ["**/vendor/**", "**/node_modules/**", "**/*.lock", "**/dist/**"]
"""

BARONS = ("carnegie", "rockefeller", "morgan", "ford", "deming")


@dataclass
class Config:
    repo: Path
    baron: str = "carnegie"
    trunk: str = "main"
    harshness: int = 3
    churn_window_days: int = 14
    padding_max_lines: int = 2
    churn_max_files: int = 200
    backend: str = "venice"
    model: str = "claude-opus-5"
    effort: str = "high"
    max_tokens: int = 16000
    venice_key_file: str = ""
    venice_key_field: str = "venice_key"
    exclude: list[str] = field(default_factory=list)

    @property
    def state_dir(self) -> Path:
        return self.repo / ".serf"

    @property
    def db_path(self) -> Path:
        return self.state_dir / "marks.db"


class ConfigError(RuntimeError):
    pass


def load(repo: Path) -> Config:
    path = repo / CONFIG_RELPATH
    if not path.exists():
        raise ConfigError(f"no seat bound here — run `serf init` in {repo}")

    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    baron = str(raw.get("baron", "carnegie")).lower()
    if baron not in BARONS:
        raise ConfigError(f"unknown baron {baron!r}; pick one of {', '.join(BARONS)}")

    harshness = int(raw.get("harshness", 3))
    if not 1 <= harshness <= 5:
        raise ConfigError("harshness must be between 1 and 5")

    return Config(
        repo=repo,
        baron=baron,
        trunk=str(raw.get("trunk", "main")),
        harshness=harshness,
        churn_window_days=int(raw.get("churn_window_days", 14)),
        padding_max_lines=int(raw.get("padding_max_lines", 2)),
        churn_max_files=int(raw.get("churn_max_files", 200)),
        backend=str(raw.get("backend", "venice")).lower(),
        model=str(raw.get("model", "claude-opus-5")),
        effort=str(raw.get("effort", "high")),
        max_tokens=int(raw.get("max_tokens", 16000)),
        venice_key_file=str(raw.get("venice_key_file", "")),
        venice_key_field=str(raw.get("venice_key_field", "venice_key")),
        exclude=list(raw.get("exclude", [])),
    )


def write_default(repo: Path) -> Path:
    path = repo / CONFIG_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ConfigError(f"{path} already exists — not overwriting")
    path.write_text(DEFAULT_CONFIG)
    return path
