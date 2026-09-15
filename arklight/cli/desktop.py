"""
`arklight desktop scaffold` -- Linux-only target for now. See
docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md for the staged plan
this is Stage 1 of, and docs/Backends/ARKLIGHT_DESKTOP_BACKEND_PROPOSAL.md
for the native-host architecture it implements.

    arklight desktop scaffold <build-dir> -o <project-dir>

Templating + asset-embedding only, no C toolchain required to run this
command itself -- same split `arklight.cli.android` already
established for `arklight android scaffold`: `arklight.backend.
desktop.runtime` is the pure template/content builder (never touches
disk), this module owns everything that leaves out -- reading
`arklight.config.py`'s `"desktop"` section, resolving/validating it
against defaults, reading the build directory's own bytes to embed,
and writing every generated file to disk.

Building the generated project (`make`) is left to the user (see the
generated `README.md`) -- a local `arklight desktop build` that shells
out to `make` for them, mirroring `arklight android build`'s relationship
to `arklight android scaffold`, is later, not-yet-implemented work
(DESKTOP-BACKEND-IMPLEMENTATION.md's Stage 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from arklight.backend.desktop import runtime
from arklight.config import ConfigError, load_config, section

# Defaults for every key `arklight.config.py`'s `"desktop"` section may
# set. A project with no `arklight.config.py` at all (or one with no
# `"desktop"` section) still scaffolds a buildable, if generically
# named, app -- same "still works with zero config" contract the
# Android backend's `_DEFAULTS` follows.
_DEFAULTS: dict[str, object] = {
    "app_name": "ARKlight App",
    "app_id": "com.arklight.app",
    "window_title": None,  # None -> falls back to app_name, see below
    "width": 1024,
    "height": 768,
    "resizable": True,
}

# Targets this command currently accepts. A single-entry tuple, not
# just a hardcoded string check, so the one place that needs to grow
# when a second platform lands is this line plus whatever that
# platform's own runtime module turns out to need -- not a rewrite of
# the validation shape.
SUPPORTED_TARGETS = ("linux",)

# Same shape as `arklight.cli.android._PACKAGE_ID_RE` -- a reverse-DNS
# identifier, >= 2 dotted segments, each starting with a letter or
# underscore. Used here as the `.desktop` launcher's filename and the
# window's program name, not a Python/Java package, but the same
# "dotted, namespaced identifier" convention avoids inventing a
# second syntax for what is conceptually the same kind of value.
_APP_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


class DesktopError(Exception):
    """Raised when a build directory can't be scaffolded into a desktop project."""


@dataclass
class ScaffoldResult:
    project_dir: Path
    written_paths: list[Path] = field(default_factory=list)
    app_name: str = ""
    app_id: str = ""
    binary_name: str = ""
    target: str = "linux"


def _validate_app_id(app_id: object) -> str:
    if not isinstance(app_id, str) or not _APP_ID_RE.match(app_id):
        raise DesktopError(
            f"Invalid desktop.app_id {app_id!r} -- must be a dotted, reverse-DNS-style "
            f"identifier with at least two segments (letters, digits, underscores only; "
            f"no segment may start with a digit), e.g. 'com.example.myapp'."
        )
    return app_id


def _validate_dimension(value: object, key: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DesktopError(f"desktop.{key} must be a positive int, got {value!r}.")
    return value


def _read_build_dir(build_dir: Path) -> dict[str, bytes]:
    """Read every file under `build_dir` into memory, keyed by its
    build-relative POSIX path (e.g. `"assets/logo.svg"`) -- the same
    key shape `assets.gen.c`'s lookup table uses. Sorted so the
    embedded asset table (and therefore `assets.gen.c` byte-for-byte)
    is deterministic between runs, same reasoning
    `runtime.generate_assets_source`'s docstring calls out."""
    files: dict[str, bytes] = {}
    for item in sorted(build_dir.rglob("*")):
        if item.is_file():
            rel = item.relative_to(build_dir).as_posix()
            files[rel] = item.read_bytes()
    return files


def scaffold_project(
    build_dir: str | Path,
    *,
    output_dir: str | Path,
    target: str = "linux",
) -> ScaffoldResult:
    """
    Scaffold a native desktop host project at `output_dir` from an
    existing `arklight build` output directory (`build_dir`). Reads
    app identity from `arklight.config.py`'s `"desktop"` section,
    found next to `build_dir` (i.e. `build_dir`'s parent directory --
    same convention `arklight.cli.android.scaffold_project` already
    uses for its `"android"` section).

    `target` must be `"linux"` -- the only platform this backend
    supports so far (see `SUPPORTED_TARGETS` and
    DESKTOP-BACKEND-IMPLEMENTATION.md's staged plan for Windows/macOS).
    Exposed as a keyword now, rather than assumed, so the CLI layer
    and this function agree on one validated value instead of the CLI
    silently hardcoding "linux" past this function's own checks.

    Raises DesktopError for an unsupported `target`, a missing/malformed
    build directory, a non-empty `output_dir`, or an invalid/malformed
    `"desktop"` config section.
    """
    if target not in SUPPORTED_TARGETS:
        supported = ", ".join(SUPPORTED_TARGETS)
        raise DesktopError(
            f"Unsupported desktop target {target!r} -- only {supported} is implemented "
            f"so far, see docs/Backends/DESKTOP-BACKEND-IMPLEMENTATION.md."
        )

    build_dir = Path(build_dir)
    if not build_dir.is_dir():
        raise DesktopError(f"Build directory not found: {build_dir}")
    if not (build_dir / "index.html").is_file():
        raise DesktopError(
            f"{build_dir} has no index.html at its root -- run `arklight build` first, "
            f"then scaffold its output directory. The desktop host loads exactly one "
            f"fixed entry page, index.html."
        )

    project_dir = Path(output_dir)
    if project_dir.exists():
        if not project_dir.is_dir():
            raise DesktopError(f"{project_dir} already exists and is not a directory.")
        if any(project_dir.iterdir()):
            raise DesktopError(
                f"{project_dir} already exists and is not empty. Choose a different "
                f"-o directory, or clear it first."
            )

    try:
        config = load_config(build_dir.parent)
    except ConfigError as exc:
        raise DesktopError(str(exc)) from exc
    desktop_cfg = section(config, "desktop", _DEFAULTS)

    app_name = desktop_cfg["app_name"]
    if not isinstance(app_name, str) or not app_name.strip():
        raise DesktopError(f"desktop.app_name must be a non-empty string, got {app_name!r}.")

    app_id = _validate_app_id(desktop_cfg["app_id"])

    window_title = desktop_cfg["window_title"]
    if window_title is None:
        window_title = app_name
    elif not isinstance(window_title, str) or not window_title.strip():
        raise DesktopError(
            f"desktop.window_title must be a non-empty string (or None), got {window_title!r}."
        )

    width = _validate_dimension(desktop_cfg["width"], "width")
    height = _validate_dimension(desktop_cfg["height"], "height")

    resizable = desktop_cfg["resizable"]
    if not isinstance(resizable, bool):
        raise DesktopError(f"desktop.resizable must be a bool, got {resizable!r}.")

    build_files = _read_build_dir(build_dir)

    files = runtime.project_files(
        app_name=app_name,
        app_id=app_id,
        window_title=window_title,
        width=width,
        height=height,
        resizable=resizable,
    )
    assets_c, assets_h = runtime.generate_assets_source(build_files)
    files["assets.gen.c"] = assets_c
    files["assets.gen.h"] = assets_h

    written: list[Path] = []
    for rel_path, contents in files.items():
        dest = project_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(contents, encoding="utf-8")
        written.append(dest)

    return ScaffoldResult(
        project_dir=project_dir,
        written_paths=sorted(written),
        app_name=app_name,
        app_id=app_id,
        binary_name=runtime.binary_name(app_name),
        target=target,
    )
