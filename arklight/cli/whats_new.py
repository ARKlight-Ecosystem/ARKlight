"""
Print that version's user-facing release note, once, right after
ARKlight lands on a new version -- either via `arklight
--upgrade-alpha` (see `arklight/cli/upgrade.py`) or the first ordinary
`arklight <command>` run after a plain reinstall.

Source of truth: `docs/version history/vX.Y.md`, one file per shipped
milestone (see that directory's own README for the format). Looked up
by the *exact* installed version string -- never "sort the directory
and take the newest file" -- because that directory currently carries
several forward-looking, **PLANNED** (not-yet-shipped) files that sort
ahead of the real latest shipped version (`v0.065.md`-`v0.078.md`; see
the directory's own README, which calls this out as a known bug in
itself). Matching on the exact version sidesteps that entirely: a
version with no shipped note simply has no file, and this prints
nothing rather than announcing unshipped work.

Same caveat as `arklight search --retrieve-doc`
(`arklight/cli/doc_retrieval.py`): `docs/` isn't packaged into the
installed wheel (`pyproject.toml`'s `[tool.setuptools.packages.find]`
only includes `arklight*`), so this only finds anything from an
ARKlight source checkout. Unlike the license gate, that's not treated
as an error -- a missing release note is never a reason to block or
warn; it just prints nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

from arklight.cli.license_gate import HOME_ENV_VAR

_MARKER_NAME = "whats-new-shown"
_VERSION_HISTORY_DIRNAME = "version history"
_PYPROJECT_VERSION = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _repo_root() -> Path:
    # arklight/cli/whats_new.py -> arklight/cli -> arklight -> repo root.
    return Path(__file__).resolve().parents[2]


def read_version(repo_root: Path | None = None) -> str | None:
    """
    The exact, un-normalized version string as written in
    `pyproject.toml` -- e.g. `"0.0641"`, NOT the PEP 440-normalized
    `"0.641"` that `importlib.metadata` (and therefore
    `arklight.__version__`) reports once the package is actually
    installed, which silently drops the leading zero from that release
    segment. `docs/version history/*.md` filenames (and
    `CHANGELOG.md`'s own headers) use the raw pyproject.toml spelling,
    so release-note lookups have to match against *this*, not against
    `arklight.__version__` -- that normalized string would never find
    `v0.0641.md`.

    Returns None if there's no `pyproject.toml` to read (e.g. a real
    wheel/PyPI install with no source checkout on disk) -- same
    "nothing to show" case every other lookup in this module already
    handles quietly.
    """
    root = repo_root if repo_root is not None else _repo_root()
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    match = _PYPROJECT_VERSION.search(text)
    return match.group(1) if match else None


def _marker_path() -> Path:
    import os

    home = os.environ.get(HOME_ENV_VAR)
    base = Path(home) if home else Path.home() / ".arklight"
    return base / _MARKER_NAME


def _last_shown_version(marker: Path) -> str | None:
    try:
        return marker.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def _record_shown_version(marker: Path, version: str) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(version + "\n", encoding="utf-8")


def _release_notes_path(version: str) -> Path | None:
    """Exact-match lookup only -- see module docstring for why this
    never falls back to "newest file in the directory"."""
    candidate = _repo_root() / "docs" / _VERSION_HISTORY_DIRNAME / f"v{version}.md"
    return candidate if candidate.is_file() else None


def show_release_notes_if_new(version: str, *, force: bool = False) -> None:
    """
    Print `docs/version history/v<version>.md` to the terminal.

    Normally gated so it fires at most once per version (tracked in a
    small marker file, same convention as `license_gate.py`'s
    `license-accepted` marker) -- repeated `arklight build` runs on a
    version the user has already seen a note for stay silent.

    `force=True` skips that gate: `--upgrade-alpha` calls it this way
    right after switching versions, since "you just upgraded" already
    *is* the reason to show it, without waiting for some later command
    to trip the marker check.

    Silent no-op if there's nothing to show (no source checkout, or
    this particular version has no user-facing note yet) -- see module
    docstring for why that's the right behavior here, unlike the
    license gate's hard block.
    """
    marker = _marker_path()
    if not force and _last_shown_version(marker) == version:
        return

    path = _release_notes_path(version)
    if path is not None:
        heading = f"[ARKlight] What's new in v{version}"
        print(f"\n{heading}\n{'-' * len(heading)}")
        print(path.read_text(encoding="utf-8").strip())
        print()

    # Recorded either way: a version with genuinely no note yet
    # shouldn't be re-checked (and silently miss) on every single
    # future run just because it never had a file to find.
    _record_shown_version(marker, version)
