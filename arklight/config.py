"""
ARKlight project config -- `arklight.config.py`.

Deliberately small right now: the only consumer that needs anything
from a project-level config file is the live-streaming dev server
(`arklight live-streaming`, see `arklight.cli.live_streaming`), which
wants a place for a project to pin a `host`/`port`/`poll_interval`
without having to pass them as flags on every `--subscribe`. Rather
than guess at a schema for config this branch doesn't have a consumer
for yet, this module defines exactly the keys something *actually*
reads today, with a `known_keys` set future subsystems extend --
adding a new top-level key is a one-line addition to `_SCHEMA` plus
whatever module reads it, not a rewrite of this loader.

Config file format: a plain Python file, `arklight.config.py`, sitting
next to the site's entry file (same directory as `site.py`), containing
a single top-level dict:

    # arklight.config.py
    CONFIG = {
        "live_streaming": {
            "host": "127.0.0.1",
            "port": 8347,
        },
    }

Loaded the same way `arklight.parser.loader` loads a site file (a
plain `exec` of the file's source in its own namespace) -- a project's
config file is exactly as trusted as its site file already is, so this
introduces no new trust boundary. Entirely optional: a project with no
`arklight.config.py` gets `{}` back, and every reader here treats a
missing key as "use the built-in default."
"""

from __future__ import annotations

import difflib
import math
import sys
from pathlib import Path
from typing import Any, Iterable, TextIO

CONFIG_FILENAME = "arklight.config.py"

# Top-level keys this branch understands, and which section owns each
# one. Kept flat and small on purpose -- see module docstring. A
# section not listed here is preserved in the returned dict as-is
# (forward-compatible with a config file written against a newer
# ARKlight that knows more sections than this one does), but nothing
# in this branch will read it.
#
# "android" and "desktop" sections are deliberately not carried over
# from `alpha` here -- see `docs/syncing main with alpha branch/
# MAIN TO ALPHA V0.070.md`, Stages 11-12: the Android backend/CLI
# stays excluded from `main` as standing policy, and the Desktop
# backend is a new-since-v0.054 addition pending an explicit go/no-go
# decision (`main`'s own roadmap still places it at v0.100). Add both
# back to `_KNOWN_SECTIONS`/`_KNOWN_KEYS` together if and when either
# backend actually lands.
#
# "experimental" is read by `arklight.cli.main` (`arklight build`) --
# lets a project silence the heavy-reliance nudge
# (`arklight.experimental.heavy_reliance_nudge`) without touching the
# site file, for a project that's already made peace with leaning on
# an escape hatch and doesn't want to be reminded every build. See
# docs/Foundational/EXPERIMENTAL-APIS.md's "Heavy-reliance nudge"
# section for the full key and default. Also carries
# "devtools_console_reminder" (default `True`): whether the generated
# `arklight.js` mirrors the same compile-time "experimental feature
# active" warnings into the browser's devtools console (`console.warn`,
# deduplicated per feature, same as the end-of-build summary) --
# see `arklight.backend.js.render._experimental_console_reminder_js`.
# Set `False` for a project that would rather keep its shipped JS
# free of this, or that already has its own devtools-console
# conventions. There's no `Site(...)` kwarg for this one (same
# reasoning as `heavy_reliance_nudge` having none) -- it's a build-tool
# behavior toggle, not a design decision the site file itself makes.
#
# "csp" is also read by `arklight.cli.main` (`arklight build`) --
# `{"strict_csp": True | False | None}`, default `None`. This is a
# project-wide *override* for `Site(strict_csp=...)`
# (`arklight/backend/html/csp.py`), not a second place that sets the
# same default: `None` (the default here) means "no override, use
# whatever each site file's own `Site(strict_csp=...)` already says"
# -- a config file that never mentions "csp" changes nothing. Setting
# it to `True`/`False` here forces that value for every build from
# this project regardless of what any individual `Site(...)` call
# says, for a CI pipeline or monorepo that wants one policy decision
# made in one place rather than re-declared per site file. There is
# deliberately no way to set "trusted_script_origins" here -- that
# list is inherently per-site content (which external origins *this*
# site actually trusts), not a project-wide policy, so it stays a
# `Site(...)`-only kwarg with no config-file equivalent.
#
# "rei" is read by `arklight.cli.main` (`arklight build`) -- one key,
# `default_mode`, one of `"plain"`/`"verbose"`/`"narrate"`. Sets what a
# bare `arklight build` (no `--verbose`/`--narrate` flag) does for this
# project. A CLI flag always overrides this for that one invocation --
# the config only changes the no-flag-passed default, the same
# override relationship `--max-width`/`--bg`/etc. already have with
# `Site(...)` kwargs. Missing key or missing section both mean
# `"plain"` (today's unnamed default) -- this is opt-in end to end.
# See docs/Foundational/DESIGN-NOTES.md.
#
# "overdrive" is the one top-level *flag* rather than a section: a bare
# `"overdrive": True` line. Read by `arklight.compiler.pipeline.build()`
# itself (so `arklight build`, `live-streaming`, and library callers all
# agree), it turns two of the pre-write gates' findings -- an unknown
# internal `href`, and a reference outside `assets/` the build can't
# supply -- from build-halting errors into an always-printed
# "passed through unverified" report. Everything provably broken stays
# fatal. Default `False`. See `arklight/compiler/overdrive.py`.
_KNOWN_SECTIONS = {"live_streaming", "experimental", "csp", "rei"}

# Top-level keys that are not sections (a dict of their own) but are
# still legitimate at the top of CONFIG -- currently just the one bare
# flag. `config_warnings` must not flag these as "unknown sections".
_KNOWN_TOP_LEVEL_FLAGS = {"overdrive"}

# Every key each known section actually reads. Used only to *warn* about
# a name that matches nothing (a misspelled `"port"`, `"app_nmae"`, or
# a whole misspelled section name used to build with exit 0 and
# silently do nothing) -- never to reject: `section()`'s own
# forward-compatibility contract above is unchanged, so a config
# written for a newer ARKlight still loads on an older one.
# tests/test_config.py pins this table against the readers' own
# `_DEFAULTS` so it can't drift out from under them.
_KNOWN_KEYS: dict[str, frozenset[str]] = {
    "live_streaming": frozenset({"host", "port", "poll_interval"}),
    "csp": frozenset({"strict_csp"}),
    "rei": frozenset({"default_mode"}),
    "experimental": frozenset({"heavy_reliance_nudge", "devtools_console_reminder"}),
}

# Config files a developer coming from the JS world would reasonably
# create next to site.py, expecting ARKlight to read one of them. It
# reads exactly one file, `arklight.config.py` -- see `find_config`.
_FOREIGN_CONFIG_NAMES = (
    "arklight.config.json",
    "arklight.config.js",
    "arklight.config.ts",
    "arklight.config.toml",
    "config.js",
    "config.ts",
)


def overdrive_enabled(config: dict[str, Any]) -> bool:
    """`CONFIG["overdrive"]` as a strict bool (missing means `False`).

    A non-bool (`"yes"`, `1`) is rejected rather than coerced: this
    switch loosens a safety check, so a typo'd value must fail loudly,
    not quietly turn it on -- or off."""
    value = config.get("overdrive", False)
    if not isinstance(value, bool):
        raise ConfigError(f"`CONFIG['overdrive']` must be True or False, got {value!r}.")
    return value


class ConfigError(Exception):
    """Raised for a malformed `arklight.config.py` (not a valid Python
    file, or its `CONFIG` isn't a dict)."""


def find_config(start_dir: str | Path) -> Path | None:
    """Look for `arklight.config.py` directly inside `start_dir` (the
    directory containing the site's entry file). Does not search
    parent directories -- a project's config lives next to its
    `site.py`, not somewhere ancestor directories have to be searched
    for, which keeps "which config applies" unambiguous.
    """
    candidate = Path(start_dir) / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def load_config(start_dir: str | Path) -> dict[str, Any]:
    """Load and return the `CONFIG` dict from `arklight.config.py` in
    `start_dir`, or `{}` if no such file exists.

    Raises `ConfigError` if the file exists but is invalid (syntax
    error, missing `CONFIG`, or `CONFIG` isn't a dict) -- a config file
    that's present but broken should fail loudly rather than silently
    fall back to defaults, since that could mask a typo'd setting a
    user thinks is taking effect.
    """
    path = find_config(start_dir)
    if path is None:
        return {}

    # Imported here, not at module level: the loader pulls in the whole
    # compiler front end, which nothing else in this module needs.
    from arklight.parser.indentation import BracketIndentationError
    from arklight.parser.loader import run_source
    from arklight.parser.preamble import PreambleError

    namespace: dict[str, Any] = {"__file__": str(path)}
    try:
        source = path.read_text(encoding="utf-8")
        # Same trust model as a site.py load, and the same front door:
        # every Python file ARKlight takes in gets its preamble read, so
        # `# define PORT -> 8347` works here like anywhere else, and its
        # bracketed lines are held to the same nesting rule too.
        run_source(namespace, source, filename=str(path))
    except (PreambleError, BracketIndentationError) as exc:
        # Both are SyntaxError subclasses; catch them first so a bad
        # directive or an un-nested bracket isn't reported as plain
        # "invalid Python".
        raise ConfigError(f"{path}: {exc}") from exc
    except SyntaxError as exc:
        raise ConfigError(f"{path}: invalid Python -- {exc}") from exc
    except Exception as exc:  # noqa: BLE001 -- surface any load-time error clearly
        raise ConfigError(f"{path}: failed to load -- {exc}") from exc

    config = namespace.get("CONFIG")
    if config is None:
        raise ConfigError(f"{path}: no top-level `CONFIG = {{...}}` dict found")
    if not isinstance(config, dict):
        raise ConfigError(f"{path}: `CONFIG` must be a dict, got {type(config).__name__}")

    return config


def section(config: dict[str, Any], name: str, defaults: dict[str, Any]) -> dict[str, Any]:
    """Return `config[name]` merged over `defaults` (defaults filled
    in for any key the project's config didn't set), or `defaults`
    unchanged if the project's config has no `name` section at all.

    Unknown keys *within* a known section are passed through rather
    than rejected -- validating exact key names per-section is each
    reader's job (it knows what it's about to use them for), not this
    loader's; this only owns finding/parsing the file itself.
    """
    project_section = config.get(name)
    if project_section is None:
        return dict(defaults)
    if not isinstance(project_section, dict):
        raise ConfigError(
            f"`CONFIG[{name!r}]` must be a dict, got {type(project_section).__name__}"
        )
    merged = dict(defaults)
    merged.update(project_section)
    return merged


def config_warnings(config: dict[str, Any], start_dir: str | Path) -> list[str]:
    """
    Non-fatal problems with a *loaded* config: names that match nothing.

    Nothing here changes behavior -- unknown sections and keys are still
    passed through untouched by `section()` (forward compatibility);
    this only makes a typo visible instead of silently doing nothing.
    Returns human-readable messages, one per problem:

    - an unknown top-level entry (`"live_streamin"`), with a "did you
      mean" suggestion when one is close -- `"overdrive"` (the one
      top-level flag, not a section) is not flagged;
    - an unknown key inside a known section (`"prot"`, `"app_nmae"`),
      likewise;
    - when there is *no* `arklight.config.py` at all, a `config.js` /
      `arklight.config.json` / ... found next to the site file, since
      the likeliest reason for one is an author expecting ARKlight to
      read it, and nothing else would ever tell them it doesn't.
    """
    warnings: list[str] = []

    if find_config(start_dir) is None:
        for name in _FOREIGN_CONFIG_NAMES:
            if (Path(start_dir) / name).is_file():
                warnings.append(
                    f"found {name} next to your site file, but ARKlight only reads "
                    f"{CONFIG_FILENAME} (a Python file defining CONFIG = {{...}}) -- "
                    f"{name} is ignored."
                )
        return warnings

    for name, value in config.items():
        if name in _KNOWN_TOP_LEVEL_FLAGS:
            continue
        if name not in _KNOWN_SECTIONS:
            warnings.append(
                f"{CONFIG_FILENAME}: unknown section {name!r} is ignored."
                f"{_did_you_mean(name, _KNOWN_SECTIONS | _KNOWN_TOP_LEVEL_FLAGS)}"
            )
            continue
        known_keys = _KNOWN_KEYS.get(name)
        if known_keys is None or not isinstance(value, dict):
            continue
        for key in value:
            if key not in known_keys:
                warnings.append(
                    f"{CONFIG_FILENAME}: unknown key {key!r} in section {name!r} "
                    f"is ignored.{_did_you_mean(str(key), known_keys)}"
                )
    return warnings


def emit_config_warnings(
    config: dict[str, Any], start_dir: str | Path, *, file: TextIO | None = None
) -> list[str]:
    """Print `config_warnings(...)` to stderr (or `file`), one line
    each, and return them. Called by every command that loads a
    project config, right after it loads successfully."""
    warnings = config_warnings(config, start_dir)
    out = file if file is not None else sys.stderr
    for message in warnings:
        print(f"ARKlight warning: {message}", file=out)
    return warnings


def _did_you_mean(name: str, candidates: Iterable[str]) -> str:
    close = difflib.get_close_matches(str(name), sorted(candidates), n=1, cutoff=0.6)
    return f" Did you mean {close[0]!r}?" if close else ""


def validate_live_streaming(cfg: dict[str, Any]) -> None:
    """
    Check the merged `live_streaming` section's values, raising
    `ConfigError` with the offending key and value.

    Before this, a string port crashed with a raw `TypeError` and an
    out-of-range one with an `OverflowError`, both surfacing to the
    user as an "unexpected error ... outside its known, handled
    failure modes" rather than a clear config problem.
    """
    host = cfg.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ConfigError(
            f"`CONFIG['live_streaming']['host']` must be a non-empty string, got {host!r}."
        )
    port = cfg.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigError(
            f"`CONFIG['live_streaming']['port']` must be an integer from 1 to 65535, "
            f"got {port!r}."
        )
    interval = cfg.get("poll_interval")
    if (
        isinstance(interval, bool)
        or not isinstance(interval, (int, float))
        or not math.isfinite(interval)
        or interval <= 0
    ):
        raise ConfigError(
            "`CONFIG['live_streaming']['poll_interval']` must be a positive number "
            f"of seconds, got {interval!r}."
        )
