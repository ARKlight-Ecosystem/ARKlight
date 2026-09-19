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

from pathlib import Path
from typing import Any

CONFIG_FILENAME = "arklight.config.py"

# Top-level keys this branch understands, and which section owns each
# one. Kept flat and small on purpose -- see module docstring. A
# section not listed here is preserved in the returned dict as-is
# (forward-compatible with a config file written against a newer
# ARKlight that knows more sections than this one does), but nothing
# in this branch will read it.
#
# "android" is read by `arklight.cli.android` (`arklight android
# scaffold`) -- see docs/Foundational/DESIGN-NOTES.md's "v0.0438:
# Android backend" section, "App identity metadata" subsection, for
# the full key list and defaults.
#
# "desktop" is read by `arklight.cli.desktop` (`arklight desktop
# scaffold`) -- see docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md
# for the full key list and defaults.
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
_KNOWN_SECTIONS = {"live_streaming", "android", "desktop", "experimental", "csp"}


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
    from arklight.parser.loader import run_source
    from arklight.parser.preamble import PreambleError

    namespace: dict[str, Any] = {"__file__": str(path)}
    try:
        source = path.read_text(encoding="utf-8")
        # Same trust model as a site.py load, and the same front door:
        # every Python file ARKlight takes in gets its preamble read, so
        # `# define PORT -> 8347` works here like anywhere else.
        run_source(namespace, source, filename=str(path))
    except PreambleError as exc:
        # A PreambleError is a SyntaxError subclass; catch it first so a
        # bad directive isn't reported as "invalid Python".
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
