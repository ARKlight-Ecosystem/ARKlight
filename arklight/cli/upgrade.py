"""
`arklight --upgrade-alpha` -- switch a git-checkout install of ARKlight
over to the `alpha` branch (fetch, checkout/switch, pull, reinstall in
place) without requiring the user to leave the CLI.

Scope, deliberately narrow:
  - Only supports installs that are actually a git checkout (e.g. `pip
    install -e .` from a clone, which is how this project is normally
    developed against). There is no reasonable way to "switch branches"
    for an install that came from a built wheel/sdist -- there's no
    branch to switch, just a version. In that case this prints a clear
    explanation and exits non-zero rather than doing something
    surprising.
  - Never touches anything outside the detected repo checkout and the
    current Python environment's installed `arklight` package (the
    equivalent of re-running `pip install -e .` after the branch
    change, so console-script entry points and `__version__` land in
    sync with the new branch).
  - Works with or without a virtualenv. On a system Python with no
    venv, modern pip (23.0+) refuses to install into an
    "externally managed" environment (PEP 668, e.g. Debian/Ubuntu's
    system Python); the reinstall step then retries once with
    `--break-system-packages`. A venv, or a Python that isn't
    externally managed, never needs the retry, so the flag is only
    added after pip itself has asked for it -- never up front, which
    would also break on a pip old enough not to know the option.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from arklight.cli.whats_new import read_version, show_release_notes_if_new

_ALPHA_BRANCH = "alpha"
_REMOTE = "origin"

# pip's own marker for a PEP 668 refusal ("error: externally-managed-
# environment"), printed to stderr and carried into UpgradeError's text
# by `_run`.
_EXTERNALLY_MANAGED = "externally-managed-environment"


class UpgradeError(Exception):
    """Raised for any failure in the upgrade-to-alpha flow; the CLI
    catches this and prints `str(exc)` as a clean, single message
    rather than a raw traceback -- same convention as CompileError/
    PackError/PWAError/ScaffoldError elsewhere in the CLI."""


def _run(args: list[str], *, cwd: Path) -> str:
    """Run a subprocess command, raising UpgradeError with the
    command's own stderr on failure rather than letting a raw
    CalledProcessError/traceback surface."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise UpgradeError(f"could not run `{args[0]}` -- is it installed and on PATH?") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise UpgradeError(
            f"`{' '.join(args)}` failed" + (f":\n  {detail}" if detail else "")
        ) from exc
    return result.stdout.strip()


def _pip_install_editable(repo_root: Path) -> None:
    """`pip install -e <repo_root>` into the running interpreter's
    environment.

    On a system Python with no virtualenv, pip 23.0+ refuses with
    `externally-managed-environment` (PEP 668) and this whole flow
    would otherwise dead-end. Only in that case, retry once with
    `--break-system-packages` (and say so). Any other failure -- or a
    second failure -- propagates unchanged."""
    command = [sys.executable, "-m", "pip", "install", "-e", str(repo_root), "--quiet"]
    try:
        _run(command, cwd=repo_root)
    except UpgradeError as exc:
        if _EXTERNALLY_MANAGED not in str(exc):
            raise
        print(
            "[ARKlight] this Python is externally managed and no virtualenv is active; "
            "retrying with --break-system-packages..."
        )
        _run([*command, "--break-system-packages"], cwd=repo_root)


def _find_repo_root(start: Path) -> Path | None:
    """Walk upward from `start` looking for a `.git` directory. Returns
    None if none is found (i.e. this isn't a git checkout at all --
    a wheel/sdist install has no `.git` anywhere above it)."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def upgrade_to_alpha() -> int:
    """Switch the current ARKlight install to the `alpha` branch.

    Returns a process exit code (0 on success), and prints its own
    status/error messages -- callers (the CLI's main()) just need to
    forward the return value, matching every other `_cmd_*` handler.
    """
    import arklight  # local import: avoid a hard dependency at module import time

    package_dir = Path(arklight.__file__).parent
    repo_root = _find_repo_root(package_dir)

    if repo_root is None:
        print(
            "arklight --upgrade-alpha: this install isn't a git checkout "
            "(no .git directory found above the installed package), so "
            "there's no branch to switch to. This flag only works for an "
            "editable/source install, e.g.:\n"
            "  git clone https://github.com/Rae-ARK/ARKlight.git\n"
            "  cd ARKlight && pip install -e .\n"
            "(on a system Python with no virtualenv, add --break-system-packages)\n"
            "then `arklight --upgrade-alpha` from within that checkout.",
            file=sys.stderr,
        )
        return 1

    try:
        before = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
        print(f"[ARKlight] current branch: {before}")

        print(f"[ARKlight] fetching {_REMOTE}/{_ALPHA_BRANCH}...")
        _run(["git", "fetch", _REMOTE, _ALPHA_BRANCH], cwd=repo_root)

        # `git switch -c` if the local branch doesn't exist yet, `git
        # switch` if it does -- avoids "branch already exists" on a
        # second run, and avoids "no such branch" on the first one.
        local_branches = _run(["git", "branch", "--list", _ALPHA_BRANCH], cwd=repo_root)
        if local_branches.strip():
            print(f"[ARKlight] switching to local branch '{_ALPHA_BRANCH}'...")
            _run(["git", "switch", _ALPHA_BRANCH], cwd=repo_root)
        else:
            print(f"[ARKlight] creating and switching to '{_ALPHA_BRANCH}' from {_REMOTE}/{_ALPHA_BRANCH}...")
            _run(
                ["git", "switch", "-c", _ALPHA_BRANCH, f"{_REMOTE}/{_ALPHA_BRANCH}"],
                cwd=repo_root,
            )

        print(f"[ARKlight] pulling latest {_ALPHA_BRANCH}...")
        _run(["git", "pull", _REMOTE, _ALPHA_BRANCH], cwd=repo_root)

        print("[ARKlight] reinstalling (pip install -e .) so the CLI reflects the new branch...")
        _pip_install_editable(repo_root)

    except UpgradeError as exc:
        print(f"arklight --upgrade-alpha: {exc}", file=sys.stderr)
        return 1

    new_version = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root)
    print(f"[ARKlight] now on '{_ALPHA_BRANCH}' @ {new_version}. Re-run `arklight --version` to confirm.")

    # Read straight off the just-pulled pyproject.toml -- this
    # process's already-imported `arklight.__version__` was cached
    # before the `git pull`/reinstall above, so it's stale here, and
    # it's PEP 440-normalized anyway (see whats_new.read_version).
    version = read_version(repo_root)
    if version is not None:
        show_release_notes_if_new(version, force=True)

    return 0
